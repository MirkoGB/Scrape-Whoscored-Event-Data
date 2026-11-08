# =====================================================
# MINUTI GIOCATI PER PARTITA (per ogni giocatore)
# Dipendenze: usa dbg, `%||%`, e le funzioni già definite prima.
# =====================================================

# ---- helper: secondi da (minute, second) con NA-safe ----
.time_sec <- function(minute, second) {
  m <- suppressWarnings(as.integer(replace_na(minute, 0)))
  s <- suppressWarnings(as.integer(replace_na(second, 0)))
  m * 60L + s
}

# ---- helper: fine partita (ultimo timestamp disponibile) ----
.match_end_sec <- function(df, verbose = TRUE) {
  # prova a usare le colonne "minute" e "second"; fallback a 90'
  if (!all(c("minute","second") %in% names(df))) {
    dbg(".match_end_sec: minute/second mancanti → uso 90'", .verbose = verbose)
    return(90L * 60L)
  }
  tsec <- .time_sec(df$minute, df$second)
  tsec <- tsec[is.finite(tsec)]
  if (!length(tsec)) {
    dbg(".match_end_sec: nessun timestamp valido → uso 90'", .verbose = verbose)
    return(90L * 60L)
  }
  mx <- max(tsec, na.rm = TRUE)
  dbg(".match_end_sec: fine partita stimata a ", mx, " sec (", round(mx/60,1), " min)", .verbose = verbose)
  mx
}

# ---- helper: normalizza playerId in un df (come sopra) ----
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

# ---- Estrai titolari da PreMatch → InvolvedPlayers (se disponibile) ----
.extract_starters <- function(df, verbose = TRUE) {
  if (!all(c("period","qualifiers") %in% names(df))) return(tibble())
  rows <- which(purrr::map_lgl(seq_len(nrow(df)), function(i) {
    df$period[i] == "PreMatch" &&
      !is.null(df$qualifiers[[i]]) &&
      any(purrr::map_chr(df$qualifiers[[i]], "type") == "InvolvedPlayers")
  }))
  if (!length(rows)) return(tibble())
  bind_rows(lapply(rows, function(i){
    q <- df$qualifiers[[i]]
    types <- purrr::map_chr(q, "type")
    if (!any(types == "InvolvedPlayers")) return(tibble())
    players <- q[[which(types=="InvolvedPlayers")]]$value %>%
      stringr::str_split(",") %>% unlist() %>% stringr::str_trim() %>% as.integer()
    tibble(playerId = players, teamName = df$teamName[i] %||% NA_character_)
  })) %>% distinct()
}

# ---- Estrai eventi di sostituzione con timestamp ----
.extract_subs <- function(df, verbose = TRUE) {
  if (!("type" %in% names(df))) return(tibble())
  if (!all(c("minute","second") %in% names(df))) return(tibble())
  df <- .normalize_player_id(df)
  sub_df <- df %>%
    filter(type %in% c("SubstitutionOn","SubstitutionOff")) %>%
    mutate(tsec = .time_sec(minute, second)) %>%
    select(type, playerId, teamName = dplyr::any_of("teamName"), tsec)
  if (nrow(sub_df) == 0) dbg(".extract_subs: nessuna sostituzione nel df.", .verbose = verbose)
  sub_df
}

# ---- Calcolo minuti per una singola partita (un df della lista) ----
minutes_one_match <- function(df, match_idx = NA_integer_, verbose = TRUE) {
  end_sec <- .match_end_sec(df, verbose = verbose)
  
  # titolari e sostituzioni
  starters <- .extract_starters(df, verbose = verbose) %>%
    mutate(start_sec = 0L)
  subs <- .extract_subs(df, verbose = verbose)
  
  # giocatori che entrano
  on_tbl <- subs %>%
    filter(type == "SubstitutionOn") %>%
    group_by(playerId, teamName) %>%
    summarise(start_sec = min(tsec, na.rm = TRUE), .groups = "drop")
  
  # giocatori che escono (prendi primo OFF)
  off_tbl <- subs %>%
    filter(type == "SubstitutionOff") %>%
    group_by(playerId, teamName) %>%
    summarise(off_sec = min(tsec, na.rm = TRUE), .groups = "drop")
  
  # set dei giocatori coinvolti
  players_all <- bind_rows(
    starters %>% select(playerId, teamName, start_sec),
    on_tbl     %>% select(playerId, teamName, start_sec)
  ) %>%
    group_by(playerId, teamName) %>%
    summarise(start_sec = min(replace_na(start_sec, 0L)), .groups = "drop") %>%
    # escludi NA playerId
    filter(!is.na(playerId))
  
  # end time: se presente OFF → usa quello, altrimenti fine partita
  minutes_tbl <- players_all %>%
    left_join(off_tbl, by = c("playerId","teamName")) %>%
    mutate(
      end_sec = ifelse(!is.na(off_sec), off_sec, end_sec <- end_sec %||% end_sec),
      end_sec = ifelse(is.na(end_sec), off_sec, end_sec),    # schützt R CMD
      end_sec = ifelse(is.na(end_sec), end_sec <- end_sec, end_sec)
    )
  
  # il trucco sopra è un po' verboso: più chiaramente forziamo ad usare off_sec se disponibile
  minutes_tbl$end_sec <- ifelse(is.na(minutes_tbl$off_sec), end_sec, minutes_tbl$off_sec)
  minutes_tbl$off_sec <- NULL
  
  # clamp: end >= start, altrimenti metti start (0 minuti)
  minutes_tbl <- minutes_tbl %>%
    mutate(
      end_sec = pmax(end_sec, start_sec, na.rm = TRUE),
      minutes_played = round((end_sec - start_sec) / 60, 1),
      match_idx = match_idx
    ) %>%
    arrange(teamName, desc(minutes_played))
  
  dbg("minutes_one_match[#", match_idx, "]: giocatori conteggiati = ", nrow(minutes_tbl), .verbose = verbose)
  if (verbose && nrow(minutes_tbl)) {
    dbg("  preview:\n",
        capture.output(print(head(minutes_tbl, 10))) %>% paste(collapse = "\n"),
        .verbose = TRUE)
  }
  minutes_tbl
}

# ---- Calcolo per l'intera lista + salvataggio per campionato ----
save_players_minutes <- function(r_processed_data_list,
                                 out_dir = ".",
                                 codes_dir = ".",
                                 verbose = TRUE) {
  if (!is.list(r_processed_data_list) || !length(r_processed_data_list)) {
    stop("r_processed_data_list mancante o vuoto.")
  }
  dbg("Minutes Pipeline: START su ", length(r_processed_data_list), " df.", .verbose = verbose)
  
  # 1) calcola per ogni partita
  minutes_all <- purrr::map_dfr(seq_along(r_processed_data_list), function(k) {
    minutes_one_match(r_processed_data_list[[k]], match_idx = k, verbose = verbose)
  })
  
  # 2) join con i nomi (riuso della tua funzione)
  player_lookup <- build_player_lookup(r_processed_data_list, verbose = verbose)
  minutes_all <- minutes_all %>%
    left_join(player_lookup, by = "playerId") %>%
    select(match_idx, teamName, playerName, playerId, start_sec, end_sec, minutes_played) %>%
    arrange(match_idx, teamName, desc(minutes_played))
  
  dbg("Minutes Pipeline: righe totali = ", nrow(minutes_all), .verbose = verbose)
  
  # 3) deduci codice campionato e salva
  dataset_teams <- collect_dataset_teams(r_processed_data_list, verbose = verbose)
  league_code <- detect_league_from_teamcodes(dataset_teams, codes_dir, verbose = verbose)
  out_path <- file.path(out_dir, sprintf("players_minutes_%s.csv", league_code))
  
  readr::write_csv(minutes_all, out_path)
  dbg("Minutes Pipeline: scritto ", out_path, " ✓", .verbose = verbose)
  
  invisible(out_path)
}



# Calcola e salva i minuti per campionato
save_players_minutes(
  r_processed_data_list,
  out_dir  = "./2025-2026 Whoscored",   # dove salvare
  codes_dir = "./2025-2026 Whoscored",  # dove stanno i Who_scored_Codici_Squadre_*.csv
  verbose  = TRUE
)

# =====================================================
# ANNOTAZIONE: aggiungi "minutesPlayed" a ciascun df della lista
# Regole:
#  - minutes_one_match() calcola per la singola partita i minuti per giocatore.
#  - Join principale su (playerId, teamName), poi fallback su solo playerId.
#  - Le righe con playerId == NA restano minutesPlayed == NA.
# Debug:
#  - per ogni df: quante righe con playerId e quante annotate con minuti.
# =====================================================

# ---- annota UN data frame con minutesPlayed ----
.annotate_one_df_with_minutes <- function(df, prefer_team_match = TRUE, verbose = TRUE) {
  # normalizza playerId per sicurezza
  df <- .normalize_player_id(df)
  
  # calcola mappa minuti per questa partita (usa funzione già definita)
  mins_tbl <- minutes_one_match(df, match_idx = NA_integer_, verbose = FALSE) %>%
    select(playerId, teamName, minutes_played)
  
  # crea colonna se non esiste
  if (!("minutesPlayed" %in% names(df))) df$minutesPlayed <- NA_real_
  
  # se non ci sono playerId nel df, esci lasciando NA
  if (all(is.na(df$playerId))) {
    dbg(".annotate_one_df_with_minutes: nessun playerId → nessuna annotazione.", .verbose = verbose)
    return(df)
  }
  
  # join principale su (playerId, teamName)
  if (prefer_team_match && ("teamName" %in% names(df))) {
    left1 <- df %>%
      left_join(mins_tbl, by = c("playerId", "teamName")) %>%
      mutate(minutesPlayed = ifelse(is.na(minutesPlayed), minutes_played, minutesPlayed)) %>%
      select(-minutes_played)
  } else {
    left1 <- df
  }
  
  # fallback: per le righe rimaste NA, prova join su solo playerId
  left2 <- left1
  missing_mask <- is.na(left2$minutesPlayed) & !is.na(left2$playerId)
  if (any(missing_mask)) {
    tmp <- left2 %>%
      left_join(mins_tbl %>% distinct(playerId, minutes_played), by = "playerId") %>%
      mutate(minutesPlayed = ifelse(is.na(minutesPlayed), minutes_played, minutesPlayed)) %>%
      select(-minutes_played)
    left2 <- tmp
  }
  
  # NB: le righe con playerId NA restano NA (richiesta dell’utente)
  
  # debug rapido
  tot_pid <- sum(!is.na(left2$playerId))
  ann_pid <- sum(!is.na(left2$minutesPlayed) & !is.na(left2$playerId))
  pct <- if (tot_pid > 0) round(100 * ann_pid / tot_pid, 1) else 0
  dbg(".annotate_one_df_with_minutes: annotate ", ann_pid, "/", tot_pid,
      " righe con playerId (", pct, "%).", .verbose = verbose)
  
  # mini preview
  if (verbose) {
    prev <- left2 %>%
      filter(!is.na(playerId)) %>%
      select(playerName = dplyr::any_of("playerName"),
             playerId, teamName = dplyr::any_of("teamName"),
             minutesPlayed) %>%
      head(5)
    if (nrow(prev) > 0) {
      dbg("  preview minuti:\n",
          capture.output(print(prev)) %>% paste(collapse = "\n"),
          .verbose = TRUE)
    }
  }
  
  left2
}

# ---- annota TUTTA la lista con minutesPlayed ----
annotate_r_list_with_minutes <- function(r_processed_data_list,
                                         prefer_team_match = TRUE,
                                         verbose = TRUE) {
  if (!is.list(r_processed_data_list) || !length(r_processed_data_list)) {
    stop("r_processed_data_list mancante o vuoto.")
  }
  out <- vector("list", length(r_processed_data_list))
  for (k in seq_along(r_processed_data_list)) {
    dbg("annotate_r_list_with_minutes: processo df#", k, .verbose = verbose)
    out[[k]] <- .annotate_one_df_with_minutes(
      r_processed_data_list[[k]],
      prefer_team_match = prefer_team_match,
      verbose = verbose
    )
  }
  out
}

# ===== ESEMPIO D'USO (in-place) =====
# Calcola e aggiunge la colonna minutesPlayed in ogni df della lista.
r_processed_data_list <- annotate_r_list_with_minutes(
  r_processed_data_list,
  prefer_team_match = TRUE,
  verbose = TRUE
)














