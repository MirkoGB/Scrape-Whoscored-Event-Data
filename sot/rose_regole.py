"""Acquisizione delle dichiarazioni dell'utente, separata dalle regole attive.

I campi narrativi sono conservati integralmente: non si deducono impostazioni
«standard», formule, crediti residui o limiti da frasi incomplete.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import re

from sot.rose import RoseError, rules_status

FIELDS = ('Lega', 'Stagione / formato / fonte voti', 'Moduli / dimensione e vincoli rosa',
          'Bonus e malus', 'Media difesa / minimo difensori / senza voto / sotto 6',
          'Capitano e formula', 'Panchina / sostituzioni / adattamenti / voti politici',
          'Scambi ammessi / finestre / limiti / approvazioni',
          'Crediti / costi dopo scambio / reintegri', 'Data del regolamento e fonte',
          'Rose cambiate rispetto agli export del 6 ottobre',
          'Vincoli o indisponibilità note (facoltativo, con data)')
ALIASES = {'fantamassa':'fantamassa21'}


def read_declarations(text, known_ids):
    declarations = {}
    for match in re.finditer(r'```text\s*\n(.*?)```', text, re.S):
        block = match.group(1)
        if not re.search(r'^Lega:', block, re.M):
            continue
        fields, current = {}, None
        for line in block.splitlines():
            key, sep, value = line.partition(':')
            if sep and key.strip() in FIELDS:
                current = key.strip()
                if current in fields:
                    raise RoseError(f'Campo ripetuto: {current}')
                fields[current] = value.strip() or None
            elif line.strip():
                if current is None:
                    raise RoseError('Testo senza campo nel blocco regolamento')
                fields[current] = ((fields[current] or '')+'\n'+line).strip()
        name = fields.get('Lega')
        league_id = ALIASES.get(name,name)
        if league_id not in known_ids:
            raise RoseError(f'Lega non riconosciuta: {name}')
        if league_id in declarations:
            raise RoseError(f'Dichiarazione duplicata: {league_id}')
        declarations[league_id] = dict(nome_dichiarato=name, riga=text[:match.start()].count('\n')+1,
                                      campi={k:fields.get(k) for k in FIELDS})
    if set(declarations) != set(known_ids):
        raise RoseError('Mancano dichiarazioni per: '+', '.join(sorted(set(known_ids)-set(declarations))))
    return declarations


def normalize(config, declaration, season, clarifications=None):
    draft = deepcopy(config)
    f = declaration['campi']
    parts = [x.strip() for x in (f['Stagione / formato / fonte voti'] or '').split('/')]
    if len(parts)!=3 or parts[0]!=season or parts[1].lower() not in ('classic','mantra') or parts[2].lower() not in ('redazione','statistico','italia'):
        raise RoseError(f'Stagione, formato o fonte non riconosciuti per {config["id"]}')
    draft['stagione_confermata'] = True
    draft['regole_confermate'] = False
    draft['fonte_regolamento'] = 'fantacalcio_rose/regole_da_completare.md'
    rules = draft['regole']
    rules['formato'], rules['fonte_voti'] = parts[1].lower(),parts[2].lower()
    roster = f['Moduli / dimensione e vincoli rosa'] or ''
    size = re.search(r'\b(\d+)\s+Giocatori\b',roster,re.I)
    fixed = re.search(r'vincolo\s+(\d+)P\s*-\s*(\d+)D\s*-\s*(\d+)C\s*-\s*(\d+)A\b',roster,re.I)
    minimum = re.search(r'almeno\s+(\d+)\s+portieri\b',roster,re.I)
    constraints = dict(dimensione_dichiarata=int(size[1]) if size else None,
                       totale_esatto=int(size[1]) if size and fixed else None,
                       esatti_per_ruolo=dict(zip('pdca',map(int,fixed.groups()))) if fixed else None,
                       minimo_portieri=int(minimum[1]) if minimum else None,
                       interpretazione_dimensione='esatta_con_vincoli_per_ruolo' if fixed else None)
    if fixed and (size is None or sum(constraints['esatti_per_ruolo'].values())!=constraints['totale_esatto']):
        raise RoseError('Dimensione e vincoli per ruolo incoerenti')
    rules['vincoli_rosa'] = constraints
    # Il testo sui moduli non viene espanso in una lista presunta.
    rules['moduli_consentiti'] = None
    cap = f['Capitano e formula'] or ''
    cap = cap.replace('’', "'")
    if re.match(r"Non c'è\b",cap,re.I):
        rules['modificatori']['capitano']['attivo'] = False
    elif re.match(r"C'è\b",cap,re.I):
        rules['modificatori']['capitano']['attivo'] = True
    if 'Pc, A' in cap:
        rules['modificatori']['capitano']['ruoli_esclusi_dichiarati'] = ['pc','a']
    defense = f['Media difesa / minimo difensori / senza voto / sotto 6'] or ''
    if '4 difensori o più' in defense:
        rules['modificatori']['difesa']['minimo_difensori_schierati'] = 4
    if 'senza voto non contano nella media' in defense:
        rules['modificatori']['difesa']['gestione_sv'] = {'esclusi_dalla_media':True,'meno_di_quattro_voti':None}
    # Conserva tutte le dichiarazioni e le questioni non formalizzate in una
    # sezione esterna a regole: il testo non diventa una formula eseguibile.
    budget = re.search(r'Crediti di partenza\s+(\d+)\s+prima',f['Crediti / costi dopo scambio / reintegri'] or '',re.I)
    draft['dichiarazioni_ricevute'] = dict(declaration, budget_iniziale=int(budget[1]) if budget else None,
        rose_invariate=(f['Rose cambiate rispetto agli export del 6 ottobre'] or '').lower()=='nessun cambiamento')
    if clarifications is not None:
        if 'moduli' in clarifications:
            rules['moduli_consentiti']=deepcopy(clarifications['moduli'][rules['formato']])
            draft['dichiarazioni_ricevute']['fonte_moduli']=clarifications['moduli']['fonte_'+rules['formato']]
        captain = clarifications.get('capitano')
        if captain is not None and rules['modificatori']['capitano']['attivo'] is True:
            rules['modificatori']['capitano']['formula'] = deepcopy(captain['formula'])
            draft['dichiarazioni_ricevute']['fonte_formula_capitano'] = captain['fonte']
        scoring = clarifications.get('bonus_malus')
        if scoring is not None:
            rules['bonus_malus'] = deepcopy(scoring['comuni'])
            rules['bonus_malus'].update(deepcopy(scoring['eccezioni'].get(config['id'],{})))
            rules['bonus_malus']['assist'] = deepcopy(scoring['assist_per_lega'][config['id']])
            draft['dichiarazioni_ricevute']['fonte_bonus_malus'] = scoring['fonte']
        limit = clarifications.get('limiti_rosa',{}).get(config['id'])
        if limit is not None:
            maximum = limit['massimo_giocatori']
            if type(maximum) is not int or maximum <= 0:
                raise RoseError('Massimo rosa non valido')
            constraints.update(dimensione_dichiarata=maximum,totale_esatto=None,
                               totale_massimo=maximum,interpretazione_dimensione='massimo')
            draft['dichiarazioni_ricevute']['correzione_limite_rosa'] = deepcopy(limit)
        defense = rules['modificatori']['difesa']
        defense.update(deepcopy(clarifications['difesa_comune']))
        low = clarifications['bonus_difesa_sotto_6']
        if config['id'] in low:
            defense['bonus_sotto_6'] = low[config['id']]
            # Completa il dominio senza sovrascrivere le fasce negative di
            # fantazavomerda, esclusa esplicitamente dalla precisazione.
            bands = defense['fasce_complete']
            if bands[0]['min_incluso'] == 6:
                defense['fasce_complete'] = [dict(min_incluso='-inf',max_escluso=6,bonus=low[config['id']])]+bands
            elif bands[0] != dict(min_incluso='-inf',max_escluso=6,bonus=low[config['id']]):
                raise RoseError('Precisazione sotto 6 in conflitto con le fasce esistenti')
        rules['sostituzioni'] = dict(
            panchina=deepcopy(clarifications['panchine'][config['id']]),
            modalita_dichiarata='stesso_ruolo',numero_massimo=None,
            ordine_ingresso=None,gestione_sv=None,voti_politici_rinvii=None)
        substitutions = clarifications.get('sostituzioni')
        if substitutions is not None:
            rules['sostituzioni'].update({k:deepcopy(v) for k,v in substitutions.items() if k!='fonte'})
            draft['dichiarazioni_ricevute']['fonte_sostituzioni'] = substitutions['fonte']
        draft['dichiarazioni_ricevute']['precisazioni'] = {
            'fonte':clarifications['fonte'],'testo':clarifications['testo']}
    return draft


def check_roster(players, constraints):
    """Verifica solo i vincoli espliciti. Nessun giudizio sull'undici o scambio."""
    counts = Counter(p['ruolo_classic'] for p in players)
    violations = []
    total = constraints['totale_esatto']
    maximum = constraints.get('totale_massimo')
    if maximum is not None and len(players)>maximum:
        violations.append(f'Massimo {maximum} giocatori, osservati {len(players)}')
    if total is not None and len(players)!=total:
        violations.append(f'Totale richiesto {total}, osservato {len(players)}')
    fixed = constraints['esatti_per_ruolo']
    if fixed is not None:
        violations += [f'Ruolo {r.upper()}: richiesti {n}, osservati {counts[r]}' for r,n in fixed.items() if counts[r]!=n]
    minimum = constraints['minimo_portieri']
    if minimum is not None and counts['p']<minimum:
        violations.append(f'Almeno {minimum} portieri richiesti, osservati {counts["p"]}')
    complete = constraints['interpretazione_dimensione'] is not None
    return dict(giocatori=len(players),ruoli_classic={r:counts[r] for r in 'pdca'},
                conforme_vincoli_espliciti=not violations,verifica_completa=complete,
                conforme_regolamento=None,violazioni=violations,
                dimensione_dichiarata=constraints['dimensione_dichiarata'],
                dimensione_coerente=(len(players)<=maximum if maximum is not None else
                    len(players)==constraints['dimensione_dichiarata']) if constraints['dimensione_dichiarata'] is not None else None,
                dimensione_coincide=(len(players)==constraints['dimensione_dichiarata']) if constraints['dimensione_dichiarata'] is not None else None)
