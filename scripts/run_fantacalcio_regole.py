"""Registra e controlla le regole ricevute senza applicare quelle ambigue."""
from pathlib import Path
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sot.rose_regole import read_declarations,normalize,check_roster
from sot.rose import rules_status


def main():
    folder=ROOT/'fantacalcio_rose'
    source=folder/'regole_da_completare.md'
    settings=json.loads((folder/'leghe.json').read_text(encoding='utf-8'))
    rosters_path=ROOT/'reports/fantacalcio_scambi/rose_per_lega.json'
    rosters={l['id']:l for l in json.loads(rosters_path.read_text(encoding='utf-8'))}
    declarations=read_declarations(source.read_text(encoding='utf-8'),{l['id'] for l in settings['leghe']})
    clarification_path=folder/'precisazioni_regole.json'
    clarifications=json.loads(clarification_path.read_text(encoding='utf-8'))
    drafts=[normalize(c,declarations[c['id']],settings['stagione'],clarifications) for c in settings['leghe']]
    audit=[]
    for cfg in drafts:
        checks=[dict(squadra=t['nome'],mia_squadra=t['mia_squadra'],**check_roster(t['rosa'],cfg['regole']['vincoli_rosa'])) for t in rosters[cfg['id']]['squadre']]
        audit.append(dict(lega=cfg['id'],formato=cfg['regole']['formato'],fonte_voti=cfg['regole']['fonte_voti'],
                          stime_provider_attuali='redazione',ricalibrazione_provider_necessaria=cfg['regole']['fonte_voti']!='redazione',
                          stato_regole=rules_status(cfg),rose=checks))
    def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
    result=dict(stato='in_revisione_non_applicato',stagione=settings['stagione'],
                fonti={str(p.relative_to(ROOT)):sha(p) for p in [source,clarification_path,folder/'leghe.json',rosters_path]},
                leghe=drafts,audit=audit)
    (folder/'regole_in_revisione.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# Verifica delle regole ricevute','',
           'Le dichiarazioni sono registrate in `regole_in_revisione.json`. Le parti ambigue',
           'non sono applicate a `leghe.json` o agli snapshot A–E. Il file compilato è preservato.',
           'Le precisazioni successive della conversazione sono in `precisazioni_regole.json`.', '',
           '| Lega | Formato / voti confermati | Dimensione dichiarata | Rose esportate | Capitano |',
           '|---|---|---:|---|---|']
    for cfg,a in zip(drafts,audit):
        sizes=sorted({x['giocatori'] for x in a['rose']})
        captain=cfg['regole']['modificatori']['capitano']['attivo']
        captain_label=('Voto base − 6' if cfg['regole']['modificatori']['capitano']['formula'] is not None
                       else 'Attivo, formula mancante') if captain else 'Assente'
        constraint=cfg['regole']['vincoli_rosa']
        size_label=('Massimo ' if constraint.get('totale_massimo') is not None else '')+str(constraint['dimensione_dichiarata'])
        lines.append(f"| {cfg['id']} | {a['formato']} / {a['fonte_voti']} | {size_label} | {', '.join(map(str,sizes))} | {captain_label} |")
    lines+=['','## Conferme registrate','',
        '- Stagione 2026/27 e rose dichiarate invariate per tutte le leghe.',
        '- Fantamassa è ricondotta a `fantamassa21`; restrizione capitano Pc/A conservata.',
        '- Confermati tutti gli undici moduli ufficiali Mantra; sette moduli standard Classic.',
        '- Capitano nelle tre leghe in cui è attivo: modificatore aggiuntivo = voto base − 6.',
        '  Esempi: 5 → −1; 5,5 → −0,5; 6 → 0; 6,5 → +0,5; 7 → +1.',
        '  Usa il voto base, prima dei bonus/malus; non il fantavoto.',
        '- Sostituzioni esclusivamente nello stesso ruolo, anche in Mantra, senza adattamenti.',
        '- Nessun tetto numerico ai cambi: ingressi limitati da disponibilità delle riserve,',
        '  ruoli e composizione della panchina. «Illimitato» non crea riserve aggiuntive.',
        '- Fantamassa: massimo 35 giocatori, corretto dall’utente. Tutte le otto rose,',
        '  comprese quelle da 32 giocatori, rispettano questo limite.',
        '- Fantagas2020, fantaonlyfans e fantaunipd: tutte le 26 rose rispettano 3P–8D–8C–6A.',
        '- Fantazavomerda: tutte le 12 rose hanno almeno due portieri.',
        '- Attivazione della difesa con almeno quattro difensori; senza voto esclusi dalla media.',
        '- Media difesa: migliori quattro voti fra portiere e difensori schierati; il portiere',
        '  può restare escluso dai quattro. Con meno di quattro voti utili dopo i cambi il modificatore non si applica.',
        '- Sotto la media del 6: modificatore zero per fantagas2020, fantamassa21, fantaonlyfans',
        '  e fantaunipdgiantiamiamo. Le fasce negative di fantazavomerda sono conservate.',
        '- Panchina fantagas2020 e fantaonlyfans: 1P–2D–2C–2A (7 posti). Nelle altre tre è libera;',
        '  resta da specificare la precedenza fra riserve dello stesso ruolo.',
        '- Budget iniziali conservati come dichiarazioni, senza dedurne i crediti residui.',
        '- Finestre degli scambi dichiarate nelle soste nazionali; date e reintegri non dedotti.', '',
        '## Bonus e malus confermati','',
        '| Evento | fantagas2020 / fantaonlyfans | fantamassa21 / fantaunipd | fantazavomerda |',
        '|---|---:|---:|---:|',
        '| Gol non su rigore | +3 | +3 | +3 |',
        '| Rigore segnato | +3 | +3 | +2 |',
        '| Rigore sbagliato | −3 | −3 | −2 |',
        '| Assist | +1 | Quality: +0,5 / +1 / +1,5 | Quality: +0,5 / +1 / +1,5 |',
        '| Ammonizione | −0,5 | −0,5 | −0,5 |',
        '| Espulsione | −1 | −1 | −1 |',
        '| Autorete | −2 | −2 | −2 |',
        '| Gol subito | −1 | −1 | −1 |',
        '| Porta inviolata | +1 | +1 | +1 |',
        '| Rigore parato | +3 | +3 | +3 |', '',
        'Gol su azione e rigori segnati sono eventi separati nella fonte: il rigore',
        'riceve un solo bonus, +3 oppure +2 secondo la lega.', '',
        '## Informazioni ancora necessarie','',
        '1. Precedenza fra riserve dello stesso ruolo;',
        '   gestione senza voto e voti politici/rinvii, capitano senza voto;',
        '   eventuale limite di posti nelle tre panchine a composizione libera.',
        '2. Fantazavomerda: Lula FC ha 27 giocatori e PIO AVE 26, contro i 29 dichiarati.',
        '   Precisare se 29 è un massimo o un totale obbligatorio; nessuna rosa viene corretta.',
        '3. Crediti negli scambi, costi assegnati dopo lo scambio e regole di reintegro per 2×1.',
        '   «Tutti gli scambi ammessi» non determina come completare una rosa incompleta.', '',
        '## Conseguenze per C e D','',
        'Il calcolo separato `calcola_convenienza_scambi.py` usa queste regole nel perimetro',
        'condizionato del [protocollo](protocollo_convenienza.md), con ricalibrazione distinta',
        'per Redazione e Statistico. Le stime individuali originarie C restano conservate.',
        'La tabella voti G1–G5 importata contiene soltanto il conteggio aggregato degli assist:',
        'mancano le categorie Quality Assist. Occorre acquisire e verificare quel dettaglio',
        'per fantamassa, fantaunipd e fantazavomerda, anche nello storico di calibrazione.',
        'Lo scenario centrale assist +1 è un surrogato dichiarato, accompagnato da',
        'sensibilità +0,5/+1,5: non rappresenta categorie Quality osservate.',
        'Sono implementati formazioni, panchina, modificatori e confronto prima/dopo.',
        'Il [README](README.md) descrive il report e i limiti residui. Restano distinte',
        'convenienza sportiva stimata, validazione del ranking e legalità amministrativa.', '',
        '## Discrepanze di dimensione rispetto al testo','']
    for a in audit:
        for t in a['rose']:
            if t['dimensione_coerente'] is False:
                lines.append(f"- {a['lega']} / {t['squadra']}: {t['giocatori']} osservati, {t['dimensione_dichiarata']} dichiarati.")
    (folder/'verifica_regole.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(leghe=len(drafts),rose=sum(len(a['rose']) for a in audit),
        discrepanze_dimensione=sum(t['dimensione_coerente'] is False for a in audit for t in a['rose']),
        stato=result['stato']),ensure_ascii=False))


if __name__=='__main__':main()
