# -*- coding: utf-8 -*-
"""Reproducible frozen pre-match dossier for Inter-Como, 8 November 2026."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from sot import tactical_matchup as TM

LABELS = {
    "shots":"Tiri totali", "sot":"Tiri in porta", "goals":"Gol", "passes":"Passaggi tentati",
    "pass_accuracy":"Passaggi riusciti (quota)", "possession":"Quota tocchi (proxy possesso)",
    "field_tilt":"Quota tocchi ultimo terzo", "ppda":"PPDA (più basso = più azioni di pressione)",
    "progressive":"Passaggi riusciti avanti ≥10 m", "box_entries":"Passaggi riusciti in area",
    "third_entries":"Ingressi ultimo terzo via passaggio", "switches":"Cambi corsia ≥40 unità y",
    "high_regains":"Recuperi alti osservati", "transition_shots":"Tiri entro 10 s da recupero",
    "long_chains":"Catene osservate con ≥10 passaggi", "long_chain_threats":"Catene lunghe con tiro/tocco area",
    "build_exits":"Uscite osservate da basso fino all'ultimo terzo",
    "inferred_carries":"Spostamenti con palla inferiti", "shots_against":"Tiri concessi",
    "sot_against":"Tiri in porta concessi", "goals_against":"Gol subiti",
    "transition_shots_against":"Tiri concessi dopo recupero avversario",
    "box_entries_against":"Passaggi avversari in area", "xg_internal":"xG interno descrittivo",
    "receiver_coverage":"Quota passaggi aperti con ricevente inferito",
}


def table(frame):
    # Avoid an optional tabulate dependency.
    cols=list(frame.columns)
    def fmt(x):
        if pd.isna(x):return "—"
        if isinstance(x,(float,np.floating)):return f"{x:.2f}"
        return str(x).replace("|","/")
    lines=["| "+" | ".join(map(str,cols))+" |","|"+"|".join(["---"]*len(cols))+"|"]
    return "\n".join(lines+["| "+" | ".join(fmt(x) for x in row)+" |" for row in frame.itertuples(index=False,name=None)])


def pitch(ax):
    ax.set(xlim=(-3,103),ylim=(-3,103),aspect=68/105)
    ax.plot([0,100,100,0,0],[0,0,100,100,0],color="#89999b",lw=1)
    ax.plot([50,50],[0,100],color="#89999b",lw=.7)
    ax.add_patch(Ellipse((50,50),2*9.15/1.05,2*9.15/.68,fill=False,color="#89999b",lw=.7))
    for x in (0,100):
        d=15.71 if x==0 else -15.71
        ax.plot([x,x+d,x+d,x],[20.35,20.35,79.65,79.65],color="#89999b",lw=.7)
    ax.set_xticks([]);ax.set_yticks([])
    ax.annotate("Attacco →",(50,-1),ha="center",fontsize=9)


def charts(data, links, positions, models, out):
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"savefig.dpi":160})
    fig,axes=plt.subplots(1,2,figsize=(14,7),layout="constrained")
    edge_tables=[];player_tables=[]
    for ax,team in zip(axes,["Inter","Como"]):
        recent=data[(data.team==team)&data.season.eq("2026-2027")].sort_values("date").tail(5)
        ids=set(recent.matchId)
        pos=positions[(positions.team==team)&positions.matchId.isin(ids)]
        rows=[]
        for pid,g in pos.groupby("playerId"):
            rows.append(dict(playerId=pid,playerName=g.playerName.iloc[-1],
                x=np.average(g.x,weights=g.touches),y=np.average(g.y,weights=g.touches),
                touches=int(g.touches.sum()),shots=int(g.shots.sum()),sot=int(g.sot.sum()),
                appearances=int(g.matchId.nunique())))
        p=pd.DataFrame(rows).sort_values("touches",ascending=False)
        p.assign(team=team).to_csv(out/f"players_{team.lower()}.csv",index=False)
        player_tables.append(p.assign(team=team))
        top=p.head(11).set_index("playerId")
        li=links[(links.team==team)&links.matchId.isin(ids)]
        edges=li.groupby(["passer","receiver","passer_name","receiver_name"]).size().rename("passes_inferred").reset_index()
        edges=edges.sort_values("passes_inferred",ascending=False)
        edges.assign(team=team).to_csv(out/f"passing_links_{team.lower()}.csv",index=False)
        edge_tables.append(edges.assign(team=team))
        pitch(ax)
        for r in edges.head(25).itertuples():
            if r.passer not in top.index or r.receiver not in top.index:continue
            a,b=top.loc[r.passer],top.loc[r.receiver]
            ax.annotate("",(b.x,b.y),(a.x,a.y),arrowprops=dict(arrowstyle="->",color="#577e93",
                alpha=.4,lw=.5+3*r.passes_inferred/max(edges.passes_inferred)))
        ax.scatter(top.x,top.y,s=80+top.touches*1.0,c="#236b91" if team=="Inter" else "#bf6b32",edgecolor="white",zorder=3)
        for r in top.itertuples():
            ax.annotate(r.playerName.split()[-1],(r.x,r.y),xytext=(3,7),textcoords="offset points",fontsize=8,zorder=4)
        ax.set_title(f"{team} · ultime {len(ids)} gare complete\nCentri delle azioni con palla; riceventi inferiti")
    fig.suptitle("Reti di passaggio osservabili · non sono posizioni medie senza palla",fontsize=14)
    fig.savefig(out/"passing_networks.png");plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(14,4),layout="constrained")
    for ax,target in zip(axes,["goals","shots","sot"]):
        m=models[target]
        for i,team in enumerate(["Inter","Como"]):
            mu=m["lambda_home" if i==0 else "lambda_away"];lo,hi=m["count80"][i]
            ax.errorbar(mu,1-i,xerr=[[max(mu-lo,0)],[max(hi-mu,0)]],fmt="o",capsize=5,
                color="#236b91" if i==0 else "#bf6b32",ms=9)
            ax.text(mu,1-i+.16,f"{mu:.1f} · 80%: {lo}–{hi}",ha="center",fontsize=9)
        ax.set_yticks([1,0],["Inter","Como"]);ax.set_ylim(-.5,1.5);ax.set_xlim(left=0)
        ax.set_title(LABELS[target]);ax.grid(axis="x",alpha=.2)
    fig.suptitle("Previsione pre-partita · intervalli predittivi, non risultati garantiti")
    fig.savefig(out/"forecast_intervals.png");plt.close(fig)
    return pd.concat(player_tables),pd.concat(edge_tables)


def write_report(data, models, players, edges, out, cutoff, fixture_date):
    audit=pd.read_csv(out/"audit.csv")
    validation=pd.read_csv(out/"validation_summary.csv")
    profile_cols=list(LABELS)
    profiles=[]
    for team in ["Inter","Como"]:
        for season in ["2025-2026","2026-2027"]:
            for scope in ["tutte","campo_partita","ultime5"]:
                g=data[(data.team==team)&(data.season==season)].sort_values("date")
                if scope=="campo_partita":g=g[g.is_home.eq(team=="Inter")]
                if scope=="ultime5":g=g.tail(5)
                profiles.append(dict(team=team,season=season,scope=scope,n=len(g),**g[profile_cols].mean().to_dict()))
    profiles=pd.DataFrame(profiles);profiles.to_csv(out/"team_profiles.csv",index=False)
    now=profiles[profiles.season.eq("2026-2027")&profiles.scope.eq("tutte")].set_index("team")
    comparison=pd.DataFrame({"Metrica":[LABELS[c] for c in profile_cols],
                            "Inter":[now.loc["Inter",c] for c in profile_cols],
                            "Como":[now.loc["Como",c] for c in profile_cols]})
    venue=profiles[profiles.scope.eq("campo_partita")][
        ["team","season","n","shots","sot","shots_against","sot_against","passes"]].copy()
    venue["campo"]=venue.team.map({"Inter":"casa","Como":"trasferta"})
    preds=[]
    for target in TM.TARGETS:
        m=models[target]
        preds.append({"Grandezza":LABELS[target],"Inter":m["lambda_home"],"Como":m["lambda_away"],
            "80% Inter":"–".join(map(str,m["count80"][0])),"80% Como":"–".join(map(str,m["count80"][1])),
            "Modello":m["variant"]})
    selected=validation[validation.selected & ~validation.period.eq("development")]
    outcomes=models["outcomes"]
    availability=[]
    pm=pd.read_parquet(ROOT/"data/processed/ITA-serie-a/2026-2027/player_match.parquet")
    for team,patterns in [("Inter",["Lautaro","Luis Henrique"]),("Como",["Diao","Rodr","Kean","Addai"])]:
        valid=data[data.team.eq(team)&data.season.eq("2026-2027")]
        p=pm[pm.team.eq(team)&pm.matchId.isin(valid.matchId)&pm.minutes.gt(0)]
        for pattern in patterns:
            g=p[p.playerName.str.contains(pattern,case=False,regex=False)]
            if g.empty:continue
            ids=set(g.matchId)
            availability.append(dict(team=team,player=g.playerName.iloc[-1],appearances=len(ids),
                minutes=float(g.minutes.sum()),shots=int(g.shots.sum()),
                team_shot_share=float(g.shots.sum()/valid.shots.sum()),
                last_appearance=str(g.date.max().date()),
                team_shots_with=float(valid[valid.matchId.isin(ids)].shots.mean()),
                team_shots_without=float(valid[~valid.matchId.isin(ids)].shots.mean())))
    availability=pd.DataFrame(availability)
    availability.to_csv(out/"availability_context.csv",index=False)
    rawsummary=data.groupby("season").matchId.nunique().reset_index(name="partite_accettate")
    lines=[f"# Inter–Como · dossier del {cutoff}",
        f"Partita: **{fixture_date}, Inter in casa**. Informazione disponibile strettamente prima del {cutoff}. "
        "Dati di Serie A soltanto; coppe europee non incluse nel modello. Previsione congelata, non aggiornata al risultato.",
        "## Previsione",table(pd.DataFrame(preds)),
        f"**Inter {outcomes['home']:.1%} · pareggio {outcomes['draw']:.1%} · Como {outcomes['away']:.1%}.** "
        f"Entrambe a segno {outcomes['both_score']:.1%}; almeno tre gol {outcomes['over25']:.1%}.",
        "Risultati esatti più probabili: "+", ".join(f"{x['score']} ({x['probability']:.1%})" for x in outcomes['scorelines'])+".",
        "![Intervalli](forecast_intervals.png)",
        "Le distribuzioni di gol, tiri e passaggi sono modelli marginali separati. Non simulo combinazioni "
        "gol/tiri/passaggi come se fossero indipendenti. Gli esiti 1X2 assumono indipendenza dei gol condizionata "
        "alle intensità, con incertezza dei parametri condivisa dal bootstrap per data. "
        "Gli intervalli includono dispersione residua e sensibilità dei parametri; non includono tutte le "
        "incertezze su formazione, espulsioni e cambi tattici. Non sono quote consigliate.",
        "## Qualità e copertura",table(rawsummary),
        table(audit[~audit.accepted][["season","matchId","home","away","reasons"]]),
        "Sono esclusi interi incontri se manca il risultato finale, il termine del secondo tempo o la "
        "coerenza col calendario. Nessuna statistica da un incontro incompleto entra in allenamento o profilo. "
        "I tiri sono ricontati dai CSV; i gol usano il risultato finale, inclusi autogol. "
        "xG interno è descrittivo e NON entra nei predittori: il suo fit di stagione non è causalmente "
        "disponibile a ogni data storica. Fonte grezza: WhoScored/Opta nel repository.",
        "## Confronto tattico attuale",table(comparison),
        "Le medie sono per partita, non per 90 minuti, e comprendono eventuali fasi in inferiorità numerica. "
        "Sono profili descrittivi, non effetti causali della tattica. `team_profiles.csv` separa inoltre "
        "2025/26, casa/trasferta pertinenti e ultime cinque gare.",
        "### Il confronto casa/trasferta con la scorsa stagione",table(venue),
        "Sono medie grezze: cinque partite attuali per ciascun campo contro diciannove nella scorsa "
        "stagione. Avversari diversi e campioni piccoli impediscono di trasferirle direttamente "
        "alla partita di domenica. Il modello corregge per avversario, campo e recenza.",
        "### Lettura della partita e scenari da verificare",
        f"**Inter: volume e accesso all'area.** Nelle gare complete attuali produce "
        f"{now.loc['Inter','shots']:.1f} tiri e {now.loc['Inter','box_entries']:.1f} ingressi via passaggio "
        f"in area per partita, contro {now.loc['Como','shots']:.1f} e {now.loc['Como','box_entries']:.1f} del Como. "
        "Questi numeri suggeriscono una maggiore capacità osservata di arrivare vicino alla porta; "
        "non significano che l'Inter manterrà lo stesso volume contro questo avversario.",
        f"**Como: costruzione e recupero.** Completa catene lunghe che terminano con tiro/tocco in area "
        f"{now.loc['Como','long_chain_threats']:.1f} volte a gara e registra "
        f"{now.loc['Como','high_regains']:.1f} recuperi alti, contro "
        f"{now.loc['Inter','long_chain_threats']:.1f} e {now.loc['Inter','high_regains']:.1f} dell'Inter. "
        "Il Como non va trattato come una squadra che aspetta soltanto nella propria metà campo. "
        "La frequenza dei recuperi alti non misura però la qualità del pressing su un'uscita specifica dell'Inter.",
        f"**Transizioni: il punto di attenzione per il Como.** Registra "
        f"{now.loc['Como','transition_shots']:.2f} tiri dopo recupero e ne concede "
        f"{now.loc['Como','transition_shots_against']:.2f}; l'Inter rispettivamente "
        f"{now.loc['Inter','transition_shots']:.2f} e {now.loc['Inter','transition_shots_against']:.2f}. "
        "Ipotesi tattica: una perdita del Como in costruzione può offrire all'Inter un attacco rapido "
        "prima del riassetto. Non osservo il riassetto o le corse dei difensori: è uno scenario da confermare con video.",
        "**Connessioni e alternative di formazione.** Le reti delle ultime cinque gare evidenziano "
        "le coppie Akanji–Bastoni e Carlos Augusto–Dimarco per l'Inter, e Ramón–Couto e Milla–Kempf "
        "per il Como. Sono collegamenti osservati, non linee libere misurate. Se Carlos Augusto resta "
        "fuori dall'undici, quella rete non rappresenta automaticamente la formazione di domenica. "
        "Una pressione sulla prima costruzione o una ricezione di Nico Paz alle spalle del centrocampo "
        "sono ipotesi di lettura, non eventi senza palla che questo dataset possa certificare.",
        "**Tre scenari utili.** (1) Costruzione pulita di entrambe: cercare chi trasforma il possesso "
        "in ingressi in area, non soltanto chi accumula passaggi. (2) Perdita in uscita: osservare la "
        "prima azione dopo il recupero e la rapidità del tiro. (3) Vantaggio precoce o espulsione: "
        "ritmi e volumi possono cambiare; la previsione pre-partita non è una previsione live condizionata al punteggio.",
        "## Giocatori e connessioni", "![Reti di passaggio](passing_networks.png)",
        "Posizioni dei nodi: centri dei soli tocchi registrati. Non sono schieramenti medi o posizioni "
        "senza palla. Frecce: riceventi inferiti con evento immediatamente successivo della stessa squadra, "
        "entro 5 secondi e 12 metri dall'arrivo del passaggio; ripartenze da fermo escluse. "
        "La percentuale di riceventi assegnati è riportata sopra. Non conosco le linee di passaggio "
        "disponibili ma non scelte, le corse di smarcamento, le marcature o la compattezza del blocco."]
    for team in ["Inter","Como"]:
        p=players[players.team.eq(team)].head(12)
        li=edges[edges.team.eq(team)].head(8)
        lines += [f"### {team}: ultime cinque complete",table(p[["playerName","appearances","touches","shots","sot"]]),
                  table(li[["passer_name","receiver_name","passes_inferred"]])]
    lines += ["## Definizioni operative e limiti",
        "- Pressione: PPDA del progetto (passaggi avversari nei propri 60% / azioni difensive in zona corrispondente), "
        "e recuperi alti osservati. Non è un conteggio delle pressioni né misura le corse di pressing.\n"
        "- Progressione: passaggi riusciti con avanzamento nominale ≥10 metri verso la porta; non è la definizione "
        "standard di progressive pass del fornitore. Campo assunto 105×68 m.\n"
        "- Transizione offensiva: tiro entro 10 secondi dal primo recupero esplicito di una catena osservata, "
        "senza cambio squadra o interruzione. La stessa metrica invertita descrive la vulnerabilità difensiva.\n"
        "- Catene: sequenze conservative interrotte da avversario in controllo, passaggio fallito, fallo/fuorigioco, "
        "corner, tiro, fine tempo o pausa >15 secondi. Non coincidono con le possession sequences Opta.\n"
        "- Conduzioni inferite: due azioni consecutive dello stesso giocatore entro 8 secondi, spostamento "
        "2–30 m, prima azione diversa da un passaggio. Non è tracking, distanza totale corsa o movimento senza palla.\n"
        "- Un passaggio fra linee difensive non è identificabile senza le posizioni degli avversari. "
        "Contiamo ingressi in area/ultimo terzo e collegamenti osservati, non inventiamo linee difensive.",
        "## Validazione prima della previsione",
        "2024/25 inizializza la storia. Agosto 2025–gennaio 2026 sceglie emivita (120/240 giorni), "
        "ridge (3/12) e famiglia di modello. I mesi febbraio–maggio 2026 sono il test separato; "
        "agosto–inizio novembre 2026 è un ulteriore controllo sull'annata attuale. "
        "Ogni mese usa soltanto dati precedenti all'inizio del mese: un calendario di validazione "
        "più conservativo del refit settimanale. Le covariate sono medie delle precedenti sei gare, "
        "con date strettamente anteriori. Standardizzazione e fit avvengono sul solo training.",
        "Confronto: media squadra/campo con shrinkage, Poisson ridge attacco/difesa/campo, "
        "variante con prior delle forze dell'anno scorso e livello libero della stagione corrente "
        "(sotto 30 partite di campionato usa il solo prior), "
        "e un'estensione del Poisson su più stagioni con otto covariate disponibili prima della partita "
        "su progressione, transizione, recupero alto e catene lunghe. "
        "Le otto covariate hanno ridge aggiuntiva 24. Per adottarle richiedo un guadagno di log-score "
        "nel development con z appaiato per partita >2,50, su almeno 100 partite. "
        "Se non passano restano descrittive. Il test successivo non determina la selezione.",
        "La variante season_prior è stata aggiunta dopo aver osservato una sottostima di livello "
        "nel primo controllo della stagione corrente. Parametri e selezione automatica restano "
        "determinati dal development storico, ma il controllo 2026/27 è quindi esplorativo, non "
        "una nuova prova prospettica intoccata. Questo limite va mantenuto anche se la variante migliora.",
        table(selected[["target","period","variant","matches","mae","poisson_nll","calibration_ratio","coverage80"]]),
        "**Esito della selezione.** Le covariate tattiche non superano la soglia per nessuno dei quattro "
        "obiettivi: spiegano il profilo, ma non migliorano abbastanza il pronostico storico. "
        "La variante stagionale viene selezionata per i tiri in porta; gli altri obiettivi usano il modello "
        "su più stagioni. Nel test febbraio–maggio l'errore medio sui tiri passa da 3,81 della media "
        "squadra/campo a 3,50; sui tiri in porta da 1,74 a 1,69. Sono miglioramenti osservati, "
        "non una prova di superiorità sulle quote del mercato.",
        "**Limite attuale.** Nei 98 incontri della stagione corrente i valori osservati superano "
        "le previsioni aggregate di circa 23% per i gol, 12% per i tiri, 10% per i tiri in porta "
        "e 5% per i passaggi. Il rapporto non è una correzione specifica Inter–Como: applicarlo "
        "meccanicamente dopo il test introdurrebbe un aggiustamento non validato. La copertura "
        "dell'intervallo nominale 80% sui passaggi scende al 68%. Le previsioni di volume e "
        "le percentuali finali vanno quindi considerate provvisorie.",
        "### Controllo separato del risultato 1X2",
        table(pd.read_csv(out/"outcome_validation.csv")),
        "Log-loss e Brier più bassi sono migliori. Il confronto 1X2 usa la frequenza di campionato "
        "disponibile a inizio mese, non una quota bookmaker. La validazione usa intensità puntuali; "
        "la previsione finale integra anche la sensibilità bootstrap, che non ha un test indipendente separato.",
        "Calibrazione: rapporto osservato/previsto vicino a 1 è preferibile; copertura80 è la quota "
        "dentro l'intervallo nominale 80% (per conteggi discreti può superare 80%). "
        "La dispersione NB è fissata dai residui di development, mai dal test. "
        "Il dettaglio di TUTTI i concorrenti è in `validation_summary.csv`; le previsioni "
        "storiche sono in `validation_predictions.parquet`.",
        "## Informazioni pre-partita esterne, non coefficienti inventati",
        "Al 6 novembre Sky riporta Lautaro Martínez e Luis Henrique indisponibili; per il Como "
        "Diao, Rodríguez, Addai e Kean, con situazione Chalobah ancora da chiarire. "
        "Le probabili strutture sono 3-5-2 Inter e 4-2-3-1 Como. Le formazioni non sono ufficiali. "
        "Queste informazioni orientano la lettura tattica ma non applico un moltiplicatore arbitrario "
        "alle probabilità: nel modello non è stato validato un effetto individuale delle assenze.",
        table(availability),
        "Le medie con/senza giocatore hanno campioni molto piccoli, avversari e contesti diversi. "
        "Non sono stime causali del valore del giocatore. L'ultima presenza e la quota di tiri servono "
        "a capire quanto il profilo storico rappresenti l'organico previsto, non a sottrarre tiri alla previsione.",
        "Fonti consultate il 6 novembre: [Sky, probabili formazioni](https://sport.sky.it/calcio/serie-a/2026/11/06/probabili-formazioni-serie-a-giornata-11-ultime-news), "
        "[Gazzetta, Inter–Como](https://www.gazzetta.it/Calcio/prob_form/inter-como/2638225), "
        "[Inter, partita](https://www.inter.it/it/biglietti/intercomo). "
        "Sky/Gazzetta indicano ore 18 italiane; la pagina biglietti Inter visualizza 17 senza esplicitare il fuso.",
        "## Riproduzione",
        "```powershell\n.\\.venv\\Scripts\\python.exe scripts/analizza_como_inter.py\n"
        ".\\.venv\\Scripts\\python.exe -m pytest tests/test_tactical_matchup.py -q -p no:cacheprovider\n```",
        "Cache isolata con fingerprint di dimensione/mtime dei file fonte e versione del codice. "
        "Le nuove esecuzioni aggiornano soltanto questo dossier; grezzi e risultati degli altri modelli "
        "restano invariati."]
    (out/"report.md").write_text("\n\n".join(lines),encoding="utf-8")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cutoff",default="2026-11-06")
    p.add_argument("--match-date",default="2026-11-08")
    p.add_argument("--force",action="store_true")
    p.add_argument("--bootstrap",type=int,default=120)
    p.add_argument("--data-only",action="store_true")
    p.add_argument("--reuse-models",action="store_true")
    args=p.parse_args()
    if args.bootstrap<20:raise ValueError("Servono almeno 20 repliche bootstrap")
    out=ROOT/"reports"/f"inter_como_{args.match_date}"
    out.mkdir(exist_ok=True,parents=True)
    with threadpool_limits(limits=1):
        data,links,pos=TM.build_dataset(ROOT,out,args.cutoff,force=args.force)
        if args.data_only:return
        model_file=out/"forecast.json"
        if args.reuse_models:
            saved=json.loads(model_file.read_text(encoding="utf-8"))
            fingerprint=json.loads((out/"dataset_meta.json").read_text())["fingerprint"]
            if (saved.get("dataset_fingerprint")!=fingerprint or saved["cutoff"]!=args.cutoff
                    or saved.get("match_date")!=args.match_date
                    or saved.get("model_version")!=TM.MODEL_VERSION):
                raise ValueError("Il modello salvato non corrisponde ai dati/cutoff attuali; rieseguire il fit")
            models=saved["models"]
        else:
            models=TM.train_and_validate(data,args.cutoff,args.match_date,out,bootstraps=args.bootstrap)
            model_file.write_text(json.dumps(dict(cutoff=args.cutoff,match_date=args.match_date,
                model_version=TM.MODEL_VERSION,
                dataset_fingerprint=json.loads((out/"dataset_meta.json").read_text())["fingerprint"],
                bootstrap=args.bootstrap,models=models),indent=2),encoding="utf-8")
        players,edges=charts(data,links,pos,models,out)
        write_report(data,models,players,edges,out,args.cutoff,args.match_date)
        print(json.dumps(models["outcomes"],indent=2),flush=True)
        print(f"Report: {out/'report.md'}",flush=True)


if __name__=="__main__":main()
