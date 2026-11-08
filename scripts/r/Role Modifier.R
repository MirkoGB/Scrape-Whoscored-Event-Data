# =====================================================
# RUOLO GIOCATORE PER PARTITA (estratto da FormationSet)
# Dipendenze: usa dbg, purrr, dplyr, stringr.
# Aggiunge la colonna: "playerRole" (integer)
# Codici tipici Opta: 1=GK, 2=DEF, 3=MID, 4=FW, 5=SUB/UNKNOWN
# =====================================================

# ---- helper: estrai mappa ruoli da una singola riga di qualifiers ----
.parse_formation_row <- function(qualifiers_list) {
  # Cerca InvolvedPlayers
  p_obj <- purrr::detect(qualifiers_list, function(x) x$type == "InvolvedPlayers")
  # Cerca PlayerPosition
  pos_obj <- purrr::detect(qualifiers_list, function(x) x$type == "PlayerPosition")
  
  if (is.null(p_obj) || is.null(pos_obj)) return(tibble::tibble())
  
  # Parsing stringhe "id1, id2, ..."
  p_ids <- p_obj$value %>% 
    stringr::str_split(",") %>% 
    unlist() %>% 
    stringr::str_trim() %>% 
    as.integer()
  
  p_roles <- pos_obj$value %>% 
    stringr::str_split(",") %>% 
    unlist() %>% 
    stringr::str_trim() %>% 
    as.integer()
  
  if (length(p_ids) != length(p_roles)) {
    # Caso raro di mismatch lunghezze, ritorniamo vuoto per sicurezza
    return(tibble::tibble())
  }
  
  tibble::tibble(playerId = p_ids, playerRole = p_roles)
}

# ---- helper: costruisci mappa (playerId -> role) per intera partita ----
.build_match_role_map <- function(df, verbose = TRUE) {
  # Filtra solo eventi FormationSet
  # Nota: Opta usa a volte "FormationSet", a volte "Formation Set"
  fs_rows <- df %>% 
    filter(type %in% c("FormationSet", "Formation Set"))
  
  if (nrow(fs_rows) == 0) {
    dbg(".build_match_role_map: nessun evento FormationSet trovato.", .verbose = verbose)
    return(tibble::tibble(playerId = integer(), playerRole = integer()))
  }
  
  # Itera su tutte le righe di formazione trovate (start + eventuali cambi modulo)
  role_map <- purrr::map_dfr(seq_len(nrow(fs_rows)), function(i) {
    .parse_formation_row(fs_rows$qualifiers[[i]])
  })
  
  # Deduplica: se un giocatore appare più volte, teniamo la prima (solitamente la titolare)
  # oppure l'ultima? Solitamente la prima definizione è quella "base".
  role_map <- role_map %>%
    filter(!is.na(playerId)) %>%
    distinct(playerId, .keep_all = TRUE)
  
  role_map
}

# ---- annota UN data frame con playerRole ----
.annotate_one_df_with_roles <- function(df, verbose = TRUE) {
  
  # Assicuriamoci che playerId sia integer per il join
  if ("playerId" %in% names(df)) {
    # Gestione se playerId è lista (comune in raw data) o vettore
    if (is.list(df$playerId)) {
      # Fallback rapido se non è stato normalizzato prima
      # (ma si assume che lo script di base lo abbia fatto o lo faccia MinutesModifier)
      # Qui facciamo un tentativo safe
      # Non modifichiamo la struttura originale drasticamente, facciamo un vettore temp per il join
      temp_ids <- purrr::map_int(df$playerId, ~ if(length(.x)) as.integer(.x[[1]]) else NA_integer_)
    } else {
      temp_ids <- as.integer(df$playerId)
    }
  } else {
    dbg(".annotate_one_df_with_roles: colonna playerId mancante.", .verbose = verbose)
    df$playerRole <- NA_integer_
    return(df)
  }
  
  # 1. Costruisci la mappa dei ruoli per questa partita
  role_map_tbl <- .build_match_role_map(df, verbose = FALSE)
  
  # Debug
  n_mapped <- nrow(role_map_tbl)
  dbg(".annotate_one_df_with_roles: trovati ", n_mapped, " ruoli unici nella distinta.", .verbose = verbose)
  
  # 2. Join
  # Creiamo una versione temporanea per fare il join pulito se il df originale ha playerId sporchi
  df_temp <- df
  df_temp$join_id <- temp_ids
  
  # Se esiste già playerRole, lo rimuoviamo per sovrascriverlo/aggiornarlo
  if ("playerRole" %in% names(df_temp)) df_temp$playerRole <- NULL
  
  df_annotated <- df_temp %>%
    left_join(role_map_tbl, by = c("join_id" = "playerId")) %>%
    select(-join_id) # Rimuovi colonna tecnica
  
  # Statistiche annotazione
  n_filled <- sum(!is.na(df_annotated$playerRole))
  tot_rows <- nrow(df_annotated)
  pct <- round(100 * n_filled / tot_rows, 1)
  
  dbg(".annotate_one_df_with_roles: annotate ", n_filled, "/", tot_rows, 
      " righe (", pct, "%).", .verbose = verbose)
  
  df_annotated
}

# ---- annota TUTTA la lista con playerRole ----
annotate_r_list_with_roles <- function(r_processed_data_list, verbose = TRUE) {
  if (!is.list(r_processed_data_list) || !length(r_processed_data_list)) {
    stop("r_processed_data_list mancante o vuoto.")
  }
  
  out <- vector("list", length(r_processed_data_list))
  
  for (k in seq_along(r_processed_data_list)) {
    dbg("annotate_r_list_with_roles: processo df#", k, .verbose = verbose)
    out[[k]] <- .annotate_one_df_with_roles(
      r_processed_data_list[[k]],
      verbose = verbose
    )
  }
  out
}

# ===== ESEMPIO D'USO (in-place) =====
# Se vuoi eseguirlo automaticamente quando fai source():

r_processed_data_list <- annotate_r_list_with_roles(
  r_processed_data_list,
  verbose = TRUE
)