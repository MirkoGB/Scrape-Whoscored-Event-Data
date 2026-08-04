# ============================================
# Script: Estrazione numeri di maglia (WhoScored) con DEBUG
# Input:  r_processed_data_list (lista di data frame evento-by-evento)
# Output: players_team_numbers_<CODICE>.csv (es. ..._IT.csv)
# Nota: Il codice campionato si deduce incrociando le squadre del dataset
#       con i file "Who_scored_Codici_Squadre_<CODICE>.csv" in out_dir (o ".").
# ============================================

suppressPackageStartupMessages({
  library(tidyverse)
  library(stringr)
})

# ---- Utility: coalesce minimale, "moda" intera, e logger ----
`%||%` <- function(a, b) if (is.null(a) || all(is.na(a))) b else a
mode_int <- function(x) as.integer(names(which.max(table(x))))
dbg <- function(..., .verbose = TRUE) if (.verbose) message(format(Sys.time(), "%H:%M:%S"), " | ", paste0(..., collapse = ""))

# -----------------------------------------------------
# Funzione: extract_jersey_map(df, verbose)
# Estrae (playerId, jersey, teamName) dai qualifiers "PreMatch".
# Aggiunge debug su:
#  - numero righe PreMatch con JerseyNumber
#  - size di vettori trovati
#  - eventuali mismatch lunghezze
# -----------------------------------------------------
extract_jersey_map <- function(df, verbose = TRUE) {
  if (!all(c("period","qualifiers") %in% names(df))) {
    dbg("extract_jersey_map: colonne mancanti (period/qualifiers). Salto dataframe.", .verbose = verbose)
    return(tibble())
  }
  rows <- which(purrr::map_lgl(seq_len(nrow(df)), function(i) {
    df$period[i] == "PreMatch" &&
      !is.null(df$qualifiers[[i]]) &&
      any(purrr::map_chr(df$qualifiers[[i]], "type") == "JerseyNumber")
  }))
  dbg("extract_jersey_map: righe PreMatch con JerseyNumber = ", length(rows), .verbose = verbose)
  if (length(rows) == 0) return(tibble())
  
  out <- bind_rows(lapply(rows, function(i) {
    q <- df$qualifiers[[i]]
    
    types <- tryCatch(purrr::map_chr(q, "type"), error = function(e) character())
    if (!all(c("JerseyNumber","InvolvedPlayers") %in% types)) {
      dbg("  riga ", i, ": qualifiers senza entrambe le chiavi richieste. types=", paste(types, collapse=","), .verbose = verbose)
      return(tibble())
    }
    
    jerseys <- tryCatch({
      q[[which(types=="JerseyNumber")]]$value %>% str_split(",") %>% unlist() %>% str_trim() %>% as.integer()
    }, error = function(e) { dbg("  riga ", i, ": errore parsing JerseyNumber: ", e$message, .verbose = verbose); integer() })
    
    players <- tryCatch({
      q[[which(types=="InvolvedPlayers")]]$value %>% str_split(",") %>% unlist() %>% str_trim() %>% as.integer()
    }, error = function(e) { dbg("  riga ", i, ": errore parsing InvolvedPlayers: ", e$message, .verbose = verbose); integer() })
    
    dbg("  riga ", i, ": jerseys=", length(jerseys), " players=", length(players), .verbose = verbose)
    
    n <- min(length(jerseys), length(players))
    if (length(jerseys) != length(players)) {
      dbg("  riga ", i, ": WARNING mismatch lunghezze (uso min=", n, ")", .verbose = verbose)
    }
    if (n == 0) return(tibble())
    
    tibble(
      playerId = players[seq_len(n)],
      jersey   = jerseys[seq_len(n)],
      teamName = df$teamName[i] %||% NA_character_
    )
  }))
  
  if (nrow(out) == 0) dbg("extract_jersey_map: nessuna coppia estratta da questo df.", .verbose = verbose)
  out
}

# -----------------------------------------------------
# Funzione: build_player_lookup(r_list, verbose)
# Crea tabella (playerId, playerName) distinta.
# Debug:
#  - quanti df processati
#  - quante righe valide trovate
# -----------------------------------------------------
build_player_lookup <- function(r_list, verbose = TRUE) {
  dbg("build_player_lookup: inizio su ", length(r_list), " data frame.", .verbose = verbose)
  res <- map_dfr(seq_along(r_list), function(k) {
    df <- r_list[[k]]
    if (!("playerId" %in% names(df))) {
      dbg("  df#", k, ": playerId assente. salto.", .verbose = verbose); return(tibble())
    }
    if (is.list(df$playerId)) {
      df <- df %>% mutate(
        playerId = map_int(playerId, ~ if (length(.x) == 0 || is.na(.x[[1]])) NA_integer_ else as.integer(.x[[1]]))
      )
    } else {
      df <- df %>% mutate(playerId = suppressWarnings(as.integer(playerId)))
    }
    if (!("playerName" %in% names(df))) {
      dbg("  df#", k, ": playerName assente. salto.", .verbose = verbose); return(tibble())
    }
    out <- df %>%
      filter(!is.na(playerId), !is.na(playerName)) %>%
      distinct(playerId, playerName)
    dbg("  df#", k, ": coppie valide = ", nrow(out), .verbose = verbose)
    out
  })
  dbg("build_player_lookup: totale coppie distinte = ", nrow(res %>% distinct()), .verbose = verbose)
  res %>% distinct()
}

# -----------------------------------------------------
# Funzione: collect_dataset_teams(r_list, verbose)
# Estrae elenco squadre presenti e normalizza teamName.
# Debug:
#  - quante squadre distinte
#  - top 5 esempi normalizzati
# -----------------------------------------------------
collect_dataset_teams <- function(r_list, verbose = TRUE) {
  dbg("collect_dataset_teams: raccolta squadre...", .verbose = verbose)
  teams <- map_dfr(seq_along(r_list), function(k) {
    df <- r_list[[k]]
    cols <- names(df)
    tibble(
      teamName = if ("teamName" %in% cols) as.character(df$teamName) else NA_character_,
      teamId   = if ("teamId"   %in% cols) suppressWarnings(as.integer(df$teamId)) else NA_integer_
    )
  }) %>%
    distinct() %>%
    mutate(teamName_norm = tolower(str_trim(teamName)))
  dbg("collect_dataset_teams: squadre distinte = ", nrow(teams %>% filter(!is.na(teamName) | !is.na(teamId)) %>% distinct(teamId, teamName_norm)), .verbose = verbose)
  if (verbose) {
    ex <- teams %>% filter(!is.na(teamName_norm)) %>% distinct(teamName_norm) %>% head(5) %>% pull()
    if (length(ex)) dbg("  esempi: ", paste(ex, collapse = " | "), .verbose = verbose)
  }
  teams
}

# -----------------------------------------------------
# Funzione: detect_league_from_teamcodes(dataset_teams, dir, verbose)
# Debug:
#  - quanti file trovati
#  - per ogni file: overlap id, overlap nome, overlap totale
#  - file vincente e codice estratto
# -----------------------------------------------------

.read_codes_file <- function(fp, verbose = TRUE) {
  # prova letture in cascata: csv2 (;) → read_delim (;) → csv (,)
  m <- tryCatch(readr::read_csv2(fp, show_col_types = FALSE), error = function(e) NULL)
  if (is.null(m)) m <- tryCatch(readr::read_delim(fp, delim = ";", show_col_types = FALSE), error = function(e) NULL)
  if (is.null(m)) m <- tryCatch(readr::read_csv(fp,  show_col_types = FALSE), error = function(e) NULL)
  if (is.null(m) && !grepl("(?i)\\.csv$", fp, perl = TRUE)) {
    # prova ad aggiungere .csv se manca l'estensione
    m <- tryCatch(readr::read_csv2(paste0(fp, ".csv"), show_col_types = FALSE), error = function(e) NULL)
    if (is.null(m)) m <- tryCatch(readr::read_delim(paste0(fp, ".csv"), delim = ";", show_col_types = FALSE), error = function(e) NULL)
  }
  if (is.null(m)) return(NULL)
  
  # normalizza i nomi colonna in minuscolo
  names(m) <- tolower(names(m))
  
  # mappa colonne possibili (inclusi "squadra" e "codice")
  id_col_opts   <- c("teamid","id","codice")
  name_col_opts <- c("teamname","name","squadra")
  
  id_col   <- intersect(id_col_opts,   names(m))[1]
  name_col <- intersect(name_col_opts, names(m))[1]
  
  if (is.na(id_col) && is.na(name_col)) return(NULL)
  
  m %>%
    mutate(
      teamId        = if (!is.na(id_col)) suppressWarnings(as.integer(.data[[id_col]])) else NA_integer_,
      teamName      = if (!is.na(name_col)) as.character(.data[[name_col]]) else NA_character_,
      teamName_norm = tolower(stringr::str_trim(teamName))
    ) %>%
    distinct(teamId, teamName_norm)
}


detect_league_from_teamcodes <- function(dataset_teams, codes_dir = ".", verbose = TRUE) {
  files_csv <- list.files(path = codes_dir,
                          pattern = "(?i)^Who_scored_Codici_Squadre_.*\\.csv$",
                          full.names = TRUE, recursive = TRUE)
  files_noext <- list.files(path = codes_dir,
                            pattern = "^Who_scored_Codici_Squadre_[A-Z]{2}$",
                            full.names = TRUE, recursive = TRUE)
  files <- unique(c(files_csv, files_noext))
  dbg("detect_league_from_teamcodes: file trovati = ", length(files), .verbose = verbose)
  if (length(files) == 0) return("UNK")
  
  score_one <- function(fp) {
    m <- .read_codes_file(fp, verbose = verbose)
    if (is.null(m) || nrow(m) == 0) {
      dbg("  ", basename(fp), ": vuoto/non leggibile o colonne non riconosciute.", .verbose = verbose)
      return(tibble(file = fp, by_id=0L, by_name=0L, overlap = 0L))
    }
    
    by_id   <- inner_join(dataset_teams %>% filter(!is.na(teamId)),
                          m %>% filter(!is.na(teamId)),
                          by = "teamId") %>% nrow()
    by_name <- inner_join(dataset_teams %>% filter(!is.na(teamName_norm)),
                          m %>% filter(!is.na(teamName_norm)),
                          by = "teamName_norm") %>% nrow()
    overlap <- by_id + by_name
    dbg("  ", basename(fp), ": by_id=", by_id, " by_name=", by_name, " overlap=", overlap, .verbose = verbose)
    tibble(file = fp, by_id=by_id, by_name=by_name, overlap = overlap)
  }
  
  scores <- bind_rows(lapply(files, score_one)) %>% arrange(desc(overlap))
  if (nrow(scores) == 0 || scores$overlap[1] == 0) {
    dbg("detect_league_from_teamcodes: nessun match. Restituisco UNK.", .verbose = verbose)
    return("UNK")
  }
  
  topfile <- basename(scores$file[1])
  # estrai suffisso a due lettere (EN/ES/FR/DE/IT) dal nome file
  m <- regexec("Who_scored_Codici_Squadre_([A-Z]{2})(?i)(?:\\.csv)?$", topfile, perl = TRUE)
  code <- regmatches(topfile, m)[[1]]
  lg <- if (length(code) == 2) code[2] else "UNK"
  dbg("detect_league_from_teamcodes: scelto ", topfile, " → codice=", lg, .verbose = verbose)
  lg
}

# -----------------------------------------------------
# Funzione principale: save_players_team_numbers(r_processed_data_list, out_dir, verbose)
# Debug step-by-step con dimensioni e anteprime.
# -----------------------------------------------------
save_players_team_numbers <- function(r_processed_data_list,
                                      out_dir = ".",
                                      codes_dir = ".",
                                      verbose = TRUE) {
  if (!is.list(r_processed_data_list) || length(r_processed_data_list) == 0) {
    stop("r_processed_data_list mancante o vuoto.")
  }
  dbg("Pipeline: START. df nella lista = ", length(r_processed_data_list), .verbose = verbose)
  
  # (1) Estrazione maglie
  jersey_table <- purrr::map_dfr(seq_along(r_processed_data_list), function(k) {
    dbg("[1] Estrazione df#", k, .verbose = verbose)
    extract_jersey_map(r_processed_data_list[[k]], verbose = verbose)
  })
  dbg("[1] Totale righe estratte (playerId-jersey-team) = ", nrow(jersey_table), .verbose = verbose)
  
  # (1b) Aggregazione per moda
  jersey_table <- jersey_table %>%
    filter(!is.na(jersey)) %>%
    group_by(playerId, teamName) %>%
    summarise(jersey = mode_int(jersey), .groups = "drop")
  dbg("[1b] Dopo aggregazione per moda: righe = ", nrow(jersey_table), .verbose = verbose)
  
  # (2) Lookup nomi
  player_lookup <- build_player_lookup(r_processed_data_list, verbose = verbose)
  dbg("[2] Lookup righe = ", nrow(player_lookup), .verbose = verbose)
  
  # (3) Merge finale
  jersey_final <- jersey_table %>%
    left_join(player_lookup, by = "playerId") %>%
    select(playerName, playerId, jersey, teamName) %>%
    arrange(teamName, jersey) %>%
    distinct() %>%
    filter(!is.na(playerName))
  dbg("[3] Tabella finale righe = ", nrow(jersey_final), .verbose = verbose)
  if (verbose && nrow(jersey_final) > 0) {
    dbg("    Preview:\n", capture.output(print(head(jersey_final, 5))) %>% paste(collapse = "\n"), .verbose = TRUE)
  }
  
  # (4) Deduzione codice campionato usando codes_dir (NON out_dir)
  dataset_teams <- collect_dataset_teams(r_processed_data_list, verbose = verbose)
  league_code <- detect_league_from_teamcodes(dataset_teams, codes_dir, verbose = verbose)
  out_path <- file.path(out_dir, sprintf("players_team_numbers_%s.csv", league_code))
  dbg("[4] league_code = ", league_code, " | out_path = ", out_path, .verbose = verbose)
  
  # (5) Merge con file esistente (se presente)
  if (file.exists(out_path)) {
    dbg("[5] File esistente trovato. Merge + moda...", .verbose = verbose)
    old <- readr::read_csv(out_path, show_col_types = FALSE) %>%
      mutate(playerId = suppressWarnings(as.integer(playerId)),
             jersey   = suppressWarnings(as.integer(jersey)))
    dbg("    Righe file esistente = ", nrow(old), .verbose = verbose)
    
    jersey_final <- bind_rows(old, jersey_final) %>%
      group_by(playerId, teamName, playerName) %>%
      summarise(jersey = mode_int(jersey), .groups = "drop") %>%
      arrange(teamName, jersey)
    dbg("    Dopo merge: righe = ", nrow(jersey_final), .verbose = verbose)
  } else {
    dbg("[5] Nessun file preesistente. Creazione nuovo.", .verbose = verbose)
  }
  
  # (6) Salvataggio
  readr::write_csv(jersey_final, out_path)
  dbg("[6] Scritto: ", out_path, "  ✓", .verbose = verbose)
  
  invisible(out_path)
}

# -----------------------------------------------------
# Esempio d'uso:
#load("r_processed_data_list_IT.RData")  # deve definire r_processed_data_list
save_players_team_numbers(r_processed_data_list, out_dir="./2025-2026 Whoscored", codes_dir="./2025-2026 Whoscored", verbose=TRUE)
# -----------------------------------------------------


# =====================================================
# SEZIONE OPZIONALE: Annotazione dei data frame con il numero di maglia
# Obiettivo:
#   - Costruire una mappa (playerId, teamName) -> jersey prevalente.
#   - Per ogni df della lista, aggiungere la colonna "jerseyNumber"
#     per le righe che hanno un playerId riconoscibile.
# Note:
#   - Il join principale avviene su (playerId, teamName) per evitare
#     collisioni in caso di giocatori con lo stesso id su team diversi.
#   - Se non si trova match su (playerId, teamName), si tenta un fallback
#     su solo playerId.
# Debug:
#   - progressivo per ogni df, percentuale di righe annotate, anteprima.
# =====================================================

# ---- COSTRUISCI LA MAPPA JERSEY A PARTIRE DALLA LISTA ----
build_jersey_map_from_list <- function(r_list, verbose = TRUE) {
  # Estrai da qualifiers "PreMatch" e prendi la moda come già fatto
  jersey_raw <- purrr::map_dfr(seq_along(r_list), function(k) {
    dbg("build_jersey_map_from_list: estrazione df#", k, .verbose = verbose)
    extract_jersey_map(r_list[[k]], verbose = verbose)
  })
  
  # Aggrega alla moda per (playerId, teamName)
  jersey_map <- jersey_raw %>%
    filter(!is.na(jersey)) %>%
    group_by(playerId, teamName) %>%
    summarise(jersey = mode_int(jersey), .groups = "drop") %>%
    arrange(teamName, jersey)
  
  dbg("build_jersey_map_from_list: coppie (playerId, teamName) = ",
      nrow(jersey_map), .verbose = verbose)
  if (verbose && nrow(jersey_map) > 0) {
    dbg("  preview mappa:\n",
        capture.output(print(head(jersey_map, 5))) %>% paste(collapse = "\n"),
        .verbose = TRUE)
  }
  jersey_map
}

# ---- FUNZIONE DI SUPPORTO: normalizza playerId in un df ----
# Se playerId è list, prende il primo elemento; altrimenti converte ad int.
.normalize_player_id <- function(df) {
  if (!("playerId" %in% names(df))) {
    df$playerId <- NA_integer_
    return(df)
  }
  if (is.list(df$playerId)) {
    df <- df %>% mutate(
      playerId = purrr::map_int(playerId, ~ {
        if (length(.x) == 0 || is.na(.x[[1]])) NA_integer_ else as.integer(.x[[1]])
      })
    )
  } else {
    df <- df %>% mutate(playerId = suppressWarnings(as.integer(playerId)))
  }
  df
}

# ---- ANNOTA UN SINGOLO DATA FRAME CON LA COLONNA jerseyNumber ----
.annotate_one_df_with_jersey <- function(df, jersey_map, prefer_team_match = TRUE, verbose = TRUE) {
  # Normalizza playerId per garantire il join
  df <- .normalize_player_id(df)
  
  # Crea colonna vuota jerseyNumber; se già esiste, non la sovrascrive
  if (!("jerseyNumber" %in% names(df))) df$jerseyNumber <- NA_integer_
  
  # Se non ci sono playerId nella df, torna subito
  if (all(is.na(df$playerId))) {
    dbg(".annotate_one_df_with_jersey: nessun playerId in df. salto.", .verbose = verbose)
    return(df)
  }
  
  # Join principale su (playerId, teamName) se richiesto
  if (prefer_team_match && ("teamName" %in% names(df))) {
    left1 <- df %>%
      left_join(jersey_map, by = c("playerId", "teamName")) %>%
      mutate(jerseyNumber = ifelse(is.na(jerseyNumber), jersey, jerseyNumber)) %>%
      select(-jersey)
  } else {
    left1 <- df
  }
  
  # Fallback: se jerseyNumber ancora NA, prova match su solo playerId
  left2 <- left1
  missing_mask <- is.na(left2$jerseyNumber) & !is.na(left2$playerId)
  if (any(missing_mask)) {
    tmp <- left2 %>%
      left_join(jersey_map %>% distinct(playerId, jersey), by = "playerId") %>%
      mutate(jerseyNumber = ifelse(is.na(jerseyNumber), jersey, jerseyNumber)) %>%
      select(-jersey)
    left2 <- tmp
  }
  
  # Debug: percentuale di righe annotate
  annotated <- sum(!is.na(left2$jerseyNumber))
  total_pid <- sum(!is.na(left2$playerId))
  pct <- if (total_pid > 0) round(100 * annotated / total_pid, 1) else 0
  dbg(".annotate_one_df_with_jersey: annotate ", annotated, "/", total_pid,
      " righe con playerId (", pct, "%).", .verbose = verbose)
  
  # Anteprima opzionale
  if (verbose) {
    prev <- left2 %>%
      filter(!is.na(playerId)) %>%
      select(playerName = dplyr::any_of("playerName"),
             playerId, teamName = dplyr::any_of("teamName"),
             jerseyNumber) %>%
      head(5)
    if (nrow(prev) > 0) {
      dbg("  preview df annotata:\n",
          capture.output(print(prev)) %>% paste(collapse = "\n"),
          .verbose = TRUE)
    }
  }
  
  left2
}

# ---- FUNZIONE PRINCIPALE: ANNOTA TUTTA LA LISTA ----
annotate_r_list_with_jersey <- function(r_processed_data_list,
                                        prefer_team_match = TRUE,
                                        verbose = TRUE) {
  # Costruisci mappa jersey una sola volta
  jersey_map <- build_jersey_map_from_list(r_processed_data_list, verbose = verbose)
  
  # Applica a ciascun df in list mantenendo l'ordine
  out_list <- vector("list", length(r_processed_data_list))
  for (k in seq_along(r_processed_data_list)) {
    dbg("annotate_r_list_with_jersey: processo df#", k, .verbose = verbose)
    out_list[[k]] <- .annotate_one_df_with_jersey(
      r_processed_data_list[[k]],
      jersey_map = jersey_map,
      prefer_team_match = prefer_team_match,
      verbose = verbose
    )
  }
  out_list
}

# =========================
# ESEMPIO D'USO:
annotated_list <- annotate_r_list_with_jersey(r_processed_data_list, prefer_team_match = TRUE, verbose = TRUE)
  # Se vuoi sostituire in-place:
r_processed_data_list <- annotated_list
# =========================