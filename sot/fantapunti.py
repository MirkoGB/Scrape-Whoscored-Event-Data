# -*- coding: utf-8 -*-
"""Il fantavoto **di questa lega**, ricalcolato dai bonus. Blocco F1.

**Non e' la colonna `fantavoto_redazione`**, e la differenza e' misurata, non
supposta: il barema della fonte — ricavato per differenza e verificato su 57.574
righe — non contiene il **+1 di porta inviolata**, che `regole_fantacalcio.md`
§1.1 invece prevede. Leggere `FV` e chiamarlo fantavoto costerebbe un punto per
ogni clean sheet, cioe' circa un quarto delle partite di ogni portiere.

Vincolo 7: due definizioni della stessa grandezza non si mescolano. Qui restano
in due colonne, `fantavoto_fonte` e `fantavoto_lega`, e la seconda e' quella su
cui il modello lavora.

## La porta inviolata si deriva, non si legge

E' fra le 72 colonne che la Fase 7 ha trovato **mai valorizzate** anche in
WhoScored (`cleanSheet*`), e non e' pubblicata neanche dalla fonte dei voti. La
derivazione e' `ruolo == "p"` e `gol_subiti == 0`, **sulla riga**, cioe' sui gol
subiti da quel portiere in quella partita.

Il caso limite lo dice bene: un portiere che entra al 70' sul 2-0 e non subisce
gol prende `porta_inviolata` in questa derivazione, benche' la sua squadra abbia
subito due reti. E' la lettura corretta del regolamento — il bonus e' del
portiere, non della squadra, e i gol subiti sono attribuiti per riga dalla
fonte — ma va scritto, perche' e' il tipo di dettaglio che qualcuno un giorno
scambiera' per un difetto.

## Cosa NON c'e' qui dentro

Il **modificatore di difesa**. Non e' una proprieta' del giocatore (§2.2): e'
una funzione della media della linea schierata, quindi non e' decomponibile e
non puo' stare in una colonna per riga. Vive nel suo blocco, e quel blocco e'
fermo sulla decisione 0.3.
"""

from __future__ import annotations

import pandas as pd

from sot import lega as L, voti as V

# Le voci di bonus che si leggono direttamente da una riga di voti. Restano
# separate da quelle derivate, perche' la provenienza e' diversa e il vincolo 4
# vuole che ogni scelta di pulizia sia visibile.
DA_FONTE = ("gol_segnati", "rigori_segnati", "rigori_sbagliati", "rigori_parati",
            "assist", "autoreti", "gol_subiti")
DERIVATE = ("porta_inviolata",)


def con_fantavoto_lega(voti: pd.DataFrame = None,
                       scala: str = "redazione") -> pd.DataFrame:
    """Aggiunge `bonus_lega`, `fantavoto_lega` e `porta_inviolata`.

    Le righe **senza voto** (s.v.) restano senza fantavoto: un s.v. non produce
    punti, ne' in positivo ne' in negativo, e metterci uno zero lo farebbe
    entrare in ogni media come se fosse una prestazione.
    """
    v = (V.carica() if voti is None else voti).copy()
    voto = v[f"voto_{scala}"]

    # Solo al portiere, e solo dove c'e' un voto: senza voto non c'e' nemmeno il
    # bonus, perche' la riga non produce punti affatto.
    v["porta_inviolata"] = ((v["ruolo"] == "p") & (v["gol_subiti"] == 0)
                            & voto.notna() & (~v["allenatore"]))

    bonus = sum(L.BONUS[c] * v[c] for c in DA_FONTE)
    bonus = bonus + L.BONUS["porta_inviolata"] * v["porta_inviolata"].astype(int)
    bonus = bonus + (L.BONUS["ammonizione"] * v["ammonizione"].astype(int)
                     + L.BONUS["espulsione"] * v["espulsione"].astype(int))

    v["bonus_lega"] = bonus.where(voto.notna()).round(2)
    v["fantavoto_lega"] = (voto + v["bonus_lega"]).round(2)
    v["fantavoto_fonte"] = v[f"fantavoto_{scala}"]
    return v


def scarto_dalla_fonte(v: pd.DataFrame) -> pd.DataFrame:
    """Dove il fantavoto di lega e quello della fonte divergono, e perche'.

    **Deve divergere esattamente sulle porte inviolate e su nient'altro.** Se
    divergesse altrove, o il barema di lega e' stato scritto male o quello della
    fonte e' cambiato: in entrambi i casi e' una cosa da guardare, non da
    arrotondare. E' la stessa logica della riconciliazione che ha fatto emergere
    i cartellini.
    """
    d = v.loc[v["fantavoto_lega"].notna()].copy()
    d["scarto"] = (d["fantavoto_lega"] - d["fantavoto_fonte"]).round(2)
    fuori = d.loc[d["scarto"] != 0]
    return fuori


def per_giocatore_stagione(v: pd.DataFrame = None) -> pd.DataFrame:
    """Il totale stagionale, che e' **la grandezza su cui si compra** (§3.3).

    La fantamedia si riporta accanto come diagnostica e non come bersaglio: un
    giocatore con fantamedia alta e poche presenze vale meno di uno con
    fantamedia media e trentotto presenze, ed e' il punto su cui il documento
    insiste.
    """
    v = con_fantavoto_lega() if v is None else v
    g = v.loc[~v["allenatore"]].groupby(["stagione", "giocatore_id"])
    out = pd.DataFrame({
        "giocatore": g["giocatore"].first(),
        "ruolo": g["ruolo"].first(),
        "squadra_id": g["squadra_id"].last(),
        "in_campo": g.size(),
        "presenze": g["fantavoto_lega"].count(),
        "voto_medio": g["voto_redazione"].mean(),
        # La dispersione del voto **entro** la stagione, che serve al
        # modificatore: le fasce sono a scalini, quindi la variabilita' della
        # linea decide quanto spesso si cambia fascia, e una media non basta.
        "sd_voto_stagione": g["voto_redazione"].std(),
        "bonus_totale": g["bonus_lega"].sum(),
        "punti_stagione": g["fantavoto_lega"].sum(),
        **{c: g[c].sum() for c in DA_FONTE},
        "porte_inviolate": g["porta_inviolata"].sum(),
        "ammonizioni": g["ammonizione"].sum(),
        "espulsioni": g["espulsione"].sum(),
    }).reset_index()
    out["fantamedia"] = (out["punti_stagione"] / out["presenze"]).round(3)
    return out.round(3)
