# Riparazione una tantum degli avvii lasciati dai Firefox di Selenium.
# Anteprima: powershell -File scripts/ripara_avvio_firefox.ps1 -WhatIf
# -PreventLogin blocca anche i futuri avvii Firefox al login per l'utente corrente.
# Non cambia altri avvii o il download del martedi'.
[CmdletBinding(SupportsShouldProcess)]
param(
    [switch]$PreventLogin,
    [ValidatePattern('^S-1-5-21-\d+-\d+-\d+-\d+$')]
    [string]$TargetUserSid
)

$ErrorActionPreference = 'Stop'
$targetProfile = $env:USERPROFILE
$registryRoot = 'HKCU:'
if ($TargetUserSid) {
    $registryRoot = "Registry::HKEY_USERS\$TargetUserSid"
    if (-not (Test-Path -LiteralPath $registryRoot)) {
        throw "Il profilo $TargetUserSid non e' caricato. Accedere prima con l'utente destinatario."
    }
    $targetProfile = Get-ItemPropertyValue -LiteralPath (
        "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\$TargetUserSid"
    ) -Name ProfileImagePath
    $targetProfile = [Environment]::ExpandEnvironmentVariables($targetProfile)
}
$cacheRoot = Join-Path $targetProfile '.cache\selenium\firefox'
$cachePrefix = [IO.Path]::GetFullPath($cacheRoot).TrimEnd('\') + '\'
$runKey = "$registryRoot\Software\Microsoft\Windows\CurrentVersion\Run"
$policyKey = "$registryRoot\Software\Policies\Mozilla\Firefox"
$policyName = 'DisableLaunchOnLogin'
$policy = Get-Item -LiteralPath $policyKey -ErrorAction SilentlyContinue
$policyExisted = $policy -and ($policy.GetValueNames() -contains $policyName)
$policyBackup = [ordered]@{
    Key = $policyKey
    Name = $policyName
    Existed = [bool]$policyExisted
    Value = $(if ($policyExisted) { $policy.GetValue($policyName) } else { $null })
    Kind = $(if ($policyExisted) { [string]$policy.GetValueKind($policyName) } else { $null })
}
$needsPolicy = $PreventLogin -and (
    -not $policyExisted -or $policyBackup.Value -ne 1 -or $policyBackup.Kind -ne 'DWord')

function Test-SeleniumFirefox([string]$Executable) {
    if (-not $Executable) { return $false }
    $path = [IO.Path]::GetFullPath($Executable.Trim('"'))
    return $path.StartsWith($cachePrefix, [StringComparison]::OrdinalIgnoreCase) -and
        [IO.Path]::GetFileName($path) -ieq 'firefox.exe'
}

$entries = @((Get-ItemProperty -LiteralPath $runKey).PSObject.Properties |
    Where-Object {
        $_.Name -like 'Mozilla-Firefox-*' -and
        [string]$_.Value -match '^"?(.+?firefox\.exe)"?\s+-os-autostart\s*$' -and
        (Test-SeleniumFirefox $Matches[1])
    })
$tasks = @(Get-ScheduledTask |
    Where-Object {
        $_.TaskPath -eq '\Mozilla\' -and
        $_.TaskName -like 'Firefox Background Update *' -and
        $_.Actions.Count -eq 1 -and
        (Test-SeleniumFirefox $_.Actions[0].Execute) -and
        $_.Actions[0].Arguments -match '--backgroundtask\s+backgroundupdate' -and
        $_.State -ne 'Disabled'
    })
$browsers = @(Get-CimInstance Win32_Process -Filter "Name = 'firefox.exe'" |
    Where-Object {
        (Test-SeleniumFirefox $_.ExecutablePath) -and
        $_.CommandLine -match '\s-os-autostart\s*$'
    })

# Il backup precede ogni modifica; si conservano i valori Run e gli XML completi.
$backup = Join-Path $PSScriptRoot ('..\reports\firefox_autostart_backup_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
if ((($entries.Count + $tasks.Count) -gt 0 -or $needsPolicy) -and -not $WhatIfPreference) {
    New-Item -ItemType Directory -Path $backup | Out-Null
    ConvertTo-Json -InputObject @($entries | Select-Object Name,Value) |
        Set-Content -LiteralPath (Join-Path $backup 'run.json') -Encoding UTF8
    if ($needsPolicy) {
        $policyBackup | ConvertTo-Json |
            Set-Content -LiteralPath (Join-Path $backup 'policy.json') -Encoding UTF8
    }
    foreach ($task in $tasks) {
        Export-ScheduledTask -TaskName $task.TaskName -TaskPath $task.TaskPath |
            Set-Content -LiteralPath (Join-Path $backup ($task.TaskName + '.xml')) -Encoding Unicode
    }
    Write-Output "Backup: $backup"
}

if ($needsPolicy -and $PSCmdlet.ShouldProcess($policyKey, 'Blocca avvio al login di tutte le versioni Firefox per questo utente')) {
    if (-not (Test-Path -LiteralPath $policyKey)) {
        New-Item -Path $policyKey -Force | Out-Null
    }
    New-ItemProperty -LiteralPath $policyKey -Name $policyName -Value 1 -PropertyType DWord -Force | Out-Null
    if ((Get-ItemPropertyValue -LiteralPath $policyKey -Name $policyName) -ne 1) {
        throw 'Blocco persistente Firefox non applicato.'
    }
    Write-Output "Blocco persistente: DisableLaunchOnLogin=1 ($targetProfile)."
}

foreach ($task in $tasks) {
    if ($PSCmdlet.ShouldProcess($task.TaskName, 'Disabilita aggiornamento autonomo Firefox Selenium')) {
        Disable-ScheduledTask -TaskName $task.TaskName -TaskPath $task.TaskPath | Out-Null
        Write-Output "Disabilitata: $($task.TaskName)"
    }
}
foreach ($browser in $browsers) {
    if ($PSCmdlet.ShouldProcess("Firefox Selenium PID $($browser.ProcessId)", 'Chiudi finestra avviata al login')) {
        $process = Get-Process -Id $browser.ProcessId -ErrorAction SilentlyContinue
        if ($process -and -not $process.CloseMainWindow()) {
            Write-Warning "PID $($browser.ProcessId): chiudere la finestra manualmente. Nessuna chiusura forzata."
        }
    }
}
foreach ($entry in $entries) {
    if ($PSCmdlet.ShouldProcess($entry.Name, 'Rimuovi avvio Firefox Selenium al login')) {
        Remove-ItemProperty -LiteralPath $runKey -Name $entry.Name
        Write-Output "Rimosso avvio: $($entry.Name)"
    }
}
Write-Output "Individuati: $($entries.Count) avvii al login, $($tasks.Count) attivita', $($browsers.Count) browser automatici."
