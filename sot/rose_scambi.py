"""Operazioni strutturali per lega. Nessun punteggio schierabile implicito.

Pacchetti ed enumerazione pigra condividono la simulazione manuale. I ruoli
sono descrittivi: conservarne il multinsieme non prova la legalità della rosa.
Le valutazioni individuali del provider non vengono sommate come utilità.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations, product
import hashlib
import json

from sot.rose import RoseError, nome_chiave, rules_status


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def ids_tuple(values):
    values = tuple(values)
    if any(type(value) is not int or value <= 0 for value in values):
        raise RoseError('Gli ID FC devono essere interi positivi')
    if len(set(values)) != len(values):
        raise RoseError('ID ripetuto nello stesso pacchetto')
    return tuple(sorted(values))


@dataclass(frozen=True)
class Exchange:
    lega: str
    squadra: str
    controparte: str
    cedi: tuple[int, ...]
    ricevi: tuple[int, ...]

    def __post_init__(self):
        object.__setattr__(self, 'cedi', ids_tuple(self.cedi))
        object.__setattr__(self, 'ricevi', ids_tuple(self.ricevi))
        if nome_chiave(self.squadra) == nome_chiave(self.controparte):
            raise RoseError('Lo scambio richiede due squadre diverse')
        if (len(self.cedi), len(self.ricevi)) not in ((0, 0), (1, 1), (2, 2)):
            raise RoseError('Supportati scambio nullo, 1x1 e 2x2; 2x1 richiede regole e reintegri espliciti')
        if set(self.cedi) & set(self.ricevi):
            raise RoseError('Un giocatore non può comparire su entrambi i lati')

    def document(self):
        return dict(lega=self.lega, squadra=self.squadra, controparte=self.controparte,
                    cedi=list(self.cedi), ricevi=list(self.ricevi))

    @property
    def id(self):
        return fingerprint(self.document())

    def inverse(self):
        return Exchange(self.lega, self.squadra, self.controparte, self.ricevi, self.cedi)


def league_state(rosters, config, values):
    if rosters['id'] != config['id']:
        raise RoseError('Configurazione di una lega diversa dalle rose')
    teams, players = {}, {}
    seen_names = set()
    for team in rosters['squadre']:
        name = team['nome']
        if nome_chiave(name) in seen_names:
            raise RoseError('Squadra duplicata')
        seen_names.add(nome_chiave(name))
        mine = nome_chiave(name) == nome_chiave(config['mia_squadra'])
        if team['mia_squadra'] != mine:
            raise RoseError('Indicatore della squadra utente incoerente')
        members = []
        for row in team['rosa']:
            pid = row['giocatore_id_fc']
            ids_tuple([pid])
            if pid in players:
                raise RoseError(f'ID FC {pid} posseduto da due squadre della stessa lega')
            if row['lega'] != config['id'] or row['squadra'] != name or row['mia_squadra'] != mine:
                raise RoseError('Proprietà incoerente nella riga della rosa')
            if row['ruolo_classic'] not in ('p', 'd', 'c', 'a') or not row['ruolo_mantra']:
                raise RoseError('Ruoli correnti mancanti')
            if pid not in values:
                raise RoseError(f'Scheda C mancante per ID {pid}')
            memberships = [m for m in values[pid]['appartenenze'] if m['lega'] == config['id']]
            if len(memberships) != 1 or memberships[0] != dict(lega=config['id'], squadra=name, mia_squadra=mine, costo=row['costo']):
                raise RoseError(f'Fase C non allineata alla proprietà corrente: {pid}')
            players[pid] = dict(row)
            members.append(pid)
        if not members or len(members) != team['giocatori']:
            raise RoseError('Dimensione rosa incoerente')
        teams[name] = ids_tuple(members)
    own = [name for name in teams if nome_chiave(name) == nome_chiave(config['mia_squadra'])]
    if len(own) != 1:
        raise RoseError('Squadra utente non identificata')
    return dict(lega=config['id'], mia_squadra=own[0], rose=teams, giocatori=players)


def canonical_team(state, name):
    matches = [team for team in state['rose'] if nome_chiave(team) == nome_chiave(name)]
    if len(matches) != 1:
        raise RoseError(f'Squadra assente dalla lega {state["lega"]}: {name}')
    return matches[0]


def apply_exchange(state, exchange):
    """Nuova mappa di proprietà; non modifica input, XLSX, costi o crediti."""
    if exchange.lega != state['lega']:
        raise RoseError('Scambio fra leghe diverse')
    if exchange.squadra not in state['rose'] or exchange.controparte not in state['rose']:
        raise RoseError('Squadra non presente nella lega')
    own, other = state['rose'][exchange.squadra], state['rose'][exchange.controparte]
    if not set(exchange.cedi) <= set(own) or not set(exchange.ricevi) <= set(other):
        raise RoseError('Giocatore non posseduto dalla squadra indicata')
    updated = dict(state['rose'])
    updated[exchange.squadra] = ids_tuple((set(own)-set(exchange.cedi)) | set(exchange.ricevi))
    updated[exchange.controparte] = ids_tuple((set(other)-set(exchange.ricevi)) | set(exchange.cedi))
    return dict(state, rose=updated)


def packages(state, team, size):
    if size not in (1, 2):
        raise RoseError('Dimensione pacchetto non supportata')
    team = canonical_team(state, team)
    return combinations(state['rose'][team], size)


def iter_candidates(state, opponent=None, size=None):
    """Prodotto cartesiano esatto, senza ranking, tagli o filtri di ruolo."""
    sizes = (1, 2) if size is None else (size,)
    if any(k not in (1, 2) for k in sizes):
        raise RoseError('Dimensione pacchetto non supportata')
    own = state['mia_squadra']
    opponents = [canonical_team(state, opponent)] if opponent else sorted(t for t in state['rose'] if t != own)
    if own in opponents:
        raise RoseError('La controparte coincide con la squadra utente')
    for other in opponents:
        for k in sizes:
            for send, receive in product(packages(state, own, k), packages(state, other, k)):
                yield Exchange(state['lega'], own, other, send, receive)


def signature(state, package):
    return tuple(sorted(state['giocatori'][pid]['ruolo_classic'] for pid in package))


def fully_estimated(package, values):
    return all(values[pid]['stato'] == 'stima_provider' for pid in package)


def candidate_counts(state, values):
    rows = []
    own = state['mia_squadra']
    for other in sorted(t for t in state['rose'] if t != own):
        for size in (1, 2):
            a, b = list(packages(state, own, size)), list(packages(state, other, size))
            sa, sb = Counter(signature(state, p) for p in a), Counter(signature(state, p) for p in b)
            rows.append(dict(lega=state['lega'], controparte=other, formato=f'{size}x{size}',
                             combinazioni=len(a)*len(b),
                             firma_classic_invariata=sum(n*sb[key] for key,n in sa.items()),
                             con_stime_individuali=sum(fully_estimated(p,values) for p in a)*sum(fully_estimated(p,values) for p in b)))
    return rows


def roster_profile(state, team, values):
    members = state['rose'][team]
    return dict(squadra=team, giocatori=len(members), ids=list(members),
                ruoli_classic={r:sum(state['giocatori'][pid]['ruolo_classic']==r for pid in members) for r in ('p','d','c','a')},
                ruoli_mantra=dict(sorted(Counter(state['giocatori'][pid]['ruolo_mantra'] for pid in members).items())),
                con_stima_provider=sum(fully_estimated([pid],values) for pid in members),
                senza_stima=[pid for pid in members if not fully_estimated([pid],values)],
                punti_schierabili=None, formazione_ottimale=None,
                disponibilita_medica_verificata=False)


def blockers(config):
    status = rules_status(config)
    reasons = (['regole_incomplete'] if not status['pronta_per_valutazione'] else [])
    # Una configurazione compilata non crea il calcolo C mancante. Questa
    # guardia resta finché esiste solo il modello individuale del provider.
    reasons.append('valutatore_formazioni_e_punti_di_lega_non_disponibile')
    return dict(stato='non_valutabile', motivi=reasons, campi_regole_mancanti=status['campi_da_confermare'])


def simulate(state, exchange, config, values):
    if config['id'] != state['lega']:
        raise RoseError('Configurazione di altra lega')
    if exchange.squadra != state['mia_squadra']:
        raise RoseError('La simulazione deve partire dalla squadra utente')
    after = apply_exchange(state, exchange)
    if apply_exchange(after, exchange.inverse())['rose'] != state['rose']:
        raise RoseError('Lo scambio non è reversibile')
    result = dict(id=exchange.id, **exchange.document(), tipo='simulazione_strutturale',
                  formato=f'{len(exchange.cedi)}x{len(exchange.ricevi)}',
                  **blockers(config), controlli_proprieta=True, reversibile=True,
                  legalita_regolamento=None, consigliato=False,
                  guadagno_punti_schierabili_utente=None, guadagno_punti_schierabili_controparte=None,
                  robustezza=None, probabilita_accettazione=None,
                  motivo_utente=None, motivo_controparte=None, alternativa_meno_costosa=None)
    result['rose'] = []
    for team in (exchange.squadra, exchange.controparte):
        before_profile, after_profile = roster_profile(state,team,values), roster_profile(after,team,values)
        result['rose'].append(dict(squadra=team, prima=before_profile, dopo=after_profile,
                                   delta_ruoli_classic={r:after_profile['ruoli_classic'][r]-before_profile['ruoli_classic'][r] for r in ('p','d','c','a')}))
    result['giocatori_coinvolti'] = [dict(giocatore_id_fc=pid, nome=state['giocatori'][pid]['nome_fc'],
                                         squadra_export=state['giocatori'][pid]['squadra'],
                                         costo_export=state['giocatori'][pid]['costo'],
                                         stato_stima=values[pid]['stato']) for pid in exchange.cedi+exchange.ricevi]
    result['nota_costi'] = 'Costi storici dell’export originale; non prezzo dello scambio, nuovi costi o crediti trasferiti.'
    result['scambio_nullo'] = not exchange.cedi and not exchange.ricevi
    if result['scambio_nullo']:
        # Identità matematica, valida anche quando i livelli di utilità sono ignoti.
        result['guadagno_punti_schierabili_utente'] = 0.
        result['guadagno_punti_schierabili_controparte'] = 0.
    return result
