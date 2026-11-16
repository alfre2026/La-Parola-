#!/usr/bin/env python3
"""Traduzione italiana accurata di Matthew Henry con Claude (API «Message Batches» di Anthropic).

Sostituisce, unità per unità, la traduzione automatica OPUS-MT dei file mh/it/<LIBRO>.json con una
traduzione fatta da Claude: fedele e completa, nomi e citazioni come nella Nuova Riveduta 2006,
numeri di schema e riferimenti conservati. Un'unità tradotta così ha "c": 1.

Stato in tools/henry/claude/state.json (a ogni passo si fa il commit: il lavoro riprende da dove era):
  {"model": ..., "batch": {"id": ..., "chunks": {custom_id: [id elementi]}} | null,
   "attempts": n, "finished": false, "log": [...]}

Comandi (chiave in ANTHROPIC_API_KEY; modello in CLAUDE_MODEL, predefinito claude-sonnet-5-5):
  estimate <segs.json> <mh/it>                          richieste, token e costo stimati
  submit   <segs.json> <mh/it> <state.json>             invia le unità ancora da tradurre (se non c'è un lotto in corso)
  collect  <segs.json> <mh/it> <state.json> [minuti]    attende il lotto (al massimo «minuti»), poi scrive mh/it
"""
import json, os, re, sys, time, glob
import urllib.request, urllib.error

API = os.environ.get('ANTHROPIC_BASE_URL', 'https://api.anthropic.com').rstrip('/')
MODEL = os.environ.get('CLAUDE_MODEL', 'claude-sonnet-5-5')
MAX_USD = float(os.environ.get('MAX_USD', '120'))
MAX_CHARS = 12000          # testo inglese per richiesta (circa 3.500 token)
MAX_ATTEMPTS = 3
PRICE = {                  # dollari per milione di token, lotti (metà prezzo)
    'claude-sonnet-5-5': (1.00, 5.00),
    'claude-haiku-5-5': (0.05, 0.25),
    'claude-opus-5-5': (2.00, 10.00),
}

NAMES = ('Mosè, Aaronne, Abraamo, Sara, Isacco, Rebecca, Giacobbe, Esaù, Giuseppe, Beniamino, Ruben, Simeone, Levi, '
         'Giuda (figlio di Giacobbe e la tribù), Issacar, Zabulon, Neftali, Ascer, Efraim, Manasse, Faraone, Giosuè, '
         'Caleb, Raab, Gedeone, Iefte, Sansone, Debora, Barac, Rut, Boaz, Anna, Eli, Samuele, Saul, Gionatan, Davide, '
         'Natan, Bat-Sceba, Absalom, Salomone, Roboamo, Geroboamo, Elia, Eliseo, Acab, Izebel, Ieu, Ezechia, Giosia, '
         'Nabucodonosor, Esdra, Neemia, Ester, Mardocheo, Aman, Giobbe, Isaia, Geremia, Ezechiele, Daniele, Osea, '
         'Gioele, Abdia, Giona, Michea, Naum, Abacuc, Sofonia, Aggeo, Zaccaria, Malachia, Giovanni Battista, Maria, '
         'Giuseppe (sposo di Maria), Pietro, Andrea, Giacomo, Giovanni, Filippo, Bartolomeo, Natanaele, Tommaso, '
         'Matteo, Giuda Iscariota, Nicodemo, Lazzaro, Marta, Zaccheo, Ponzio Pilato, Erode, Caiafa, Anna (sommo '
         'sacerdote), Stefano, Saulo/Paolo, Barnaba, Sila, Timoteo, Tito, Apollo, Aquila, Priscilla, Onesimo, '
         'Gerusalemme, Sion, Samaria, Galilea, Betlemme, Nazaret, Capernaum, Giordano, Egitto, Babilonia, Israele, '
         'Canaan, Sinai, Oreb, Efeso, Corinto, Antiochia, Damasco, Roma, Macedonia, Acaia, Creta')

SYSTEM = f"""Sei un traduttore esperto di inglese del Settecento e di teologia evangelica. Traduci in italiano il «Commentary on the Whole Bible» di Matthew Henry (1706–1721) per un lettore evangelico italiano che lo usa per studiare la Bibbia e preparare predicazioni. La traduzione deve essere affidabile: fedele al senso e completa.

Regole:
1. Traduci tutto, frase per frase: non riassumere, non omettere, non aggiungere spiegazioni tue. Italiano moderno, chiaro e scorrevole, nel registro di un buon libro evangelico; conserva le immagini e i giochi di parole di Henry quando è possibile.
2. Conserva esattamente, nella stessa posizione, i numeri dello schema: I., II., III., 1., 2., (1.), (2.), [1.], [2.]. «First», «Secondly», «Thirdly», «Lastly» diventano «Primo», «Secondo», «Terzo», «Infine».
3. I riferimenti biblici sono già in italiano (per esempio «Giovanni 3:16», «Salmo 23:1», «vv. 1-21», «v. 2»): copiali identici.
4. Nomi di persone e di luoghi e termini biblici come nella Nuova Riveduta 2006: {NAMES}.
5. Le parole della Bibbia che Henry cita (sono della versione King James): rendile come nella Nuova Riveduta 2006 quando riconosci il passo; altrimenti in italiano fedele. Il «tu» arcaico (thou, thee, thy) diventa «tu», «te», «tuo».
6. Espressioni ricorrenti: «Note,» → «Nota:»; «Observe,» → «Osserva:»; «Here we have» → «Qui abbiamo»; «the gospel» → «il vangelo»; «covenant» → «patto»; «righteousness» → «giustizia»; «saints» → «santi»; «ordinances» → «ordinanze».
7. Parole o frasi latine, greche o ebraiche: lasciale come sono e aggiungi subito dopo, tra parentesi, la traduzione italiana; per il greco e l'ebraico anche la pronuncia (per esempio: makrothymei (pron. makrothiméi, «è paziente»)).
8. Date nei titoli: «(b. c. 1491.)» → «(1491 a.C.)», «(a. d. 58.)» → «(58 d.C.)».
9. Riceverai degli elementi <t id="…">titolo</t> e <p id="…">paragrafo</p>, preceduti da righe di contesto che iniziano con «===». Rispondi SOLO con gli stessi elementi, con gli stessi id e nello stesso ordine, ciascuno con la sua traduzione: niente righe di contesto, niente altro testo prima o dopo.
"""


def thinking_for(model):
    # Sonnet 5.5 non accetta «disabled»: «between_tools» toglie il ragionamento iniziale; Haiku 5.5 lo accetta.
    return {'type': 'disabled'} if 'haiku' in model else {'type': 'between_tools'}


# ---------------- dati ----------------
def load_segs(path):
    S = json.load(open(path, encoding='utf-8'))
    for i, u in enumerate(S):
        u['i'] = i
    return S


def load_it(it_dir):
    books = {}
    for f in sorted(glob.glob(os.path.join(it_dir, '*.json'))):
        b = json.load(open(f, encoding='utf-8'))
        books[b['b']] = b
    return books


def done_ranges(books):
    return {(b, u['r']) for b, bk in books.items() for u in bk['u'] if u.get('c')}


def unit_items(u):
    """Elementi da tradurre di un'unità: (id, testo inglese)."""
    out = []
    if u['k'] == 'p' and u.get('te'):
        out.append((f"{u['i']}t", u['te']))
    for j, p in enumerate(u['p']):
        out.append((f"{u['i']}.{j}", p['x']))
    return out


def label(u):
    if u['k'] == 'b':
        return f"Introduzione al libro {u['tb'] or u['b']}"
    if u['k'] == 'c':
        return f"Introduzione al capitolo {u['r'].split('.')[1]}"
    return f"Sezione {u['r']}"


def make_chunks(S, done):
    chunks, cur, size, book = [], [], 0, None
    for u in S:
        if (u['b'], u['r']) in done:
            continue
        items = unit_items(u)
        if not items:
            continue
        if cur and (u['b'] != book):
            chunks.append(cur); cur, size = [], 0
        book = u['b']
        head = ('h', f"=== {label(u)} ===")
        cur.append(head)
        for it in items:
            if size and size + len(it[1]) > MAX_CHARS:
                chunks.append(cur); cur, size = [('h', f"=== {label(u)} (seguito) ===")], 0
            cur.append(it)
            size += len(it[1])
    if any(x[0] != 'h' for x in cur):
        chunks.append(cur)
    return chunks


def esc(t):
    return t.replace('<', '‹').replace('>', '›')


def chunk_text(ch, book_name):
    lines = [f"=== Libro: {book_name} ==="]
    for x in ch:
        if x[0] == 'h':
            lines.append(x[1])
        else:
            tag = 't' if x[0].endswith('t') else 'p'
            lines.append(f'<{tag} id="{x[0]}">{esc(x[1])}</{tag}>')
    return '\n'.join(lines)


BOOK_IT = dict(zip(('GEN EXO LEV NUM DEU JOS JDG RUT 1SA 2SA 1KI 2KI 1CH 2CH EZR NEH EST JOB PSA PRO ECC SNG ISA JER '
                    'LAM EZK DAN HOS JOL AMO OBA JON MIC NAM HAB ZEP HAG ZEC MAL MAT MRK LUK JHN ACT ROM 1CO 2CO GAL '
                    'EPH PHP COL 1TH 2TH 1TI 2TI TIT PHM HEB JAS 1PE 2PE 1JN 2JN 3JN JUD REV').split(),
                   ['Genesi', 'Esodo', 'Levitico', 'Numeri', 'Deuteronomio', 'Giosuè', 'Giudici', 'Rut', '1 Samuele',
                    '2 Samuele', '1 Re', '2 Re', '1 Cronache', '2 Cronache', 'Esdra', 'Neemia', 'Ester', 'Giobbe',
                    'Salmi', 'Proverbi', 'Ecclesiaste', 'Cantico dei Cantici', 'Isaia', 'Geremia', 'Lamentazioni',
                    'Ezechiele', 'Daniele', 'Osea', 'Gioele', 'Amos', 'Abdia', 'Giona', 'Michea', 'Naum', 'Abacuc',
                    'Sofonia', 'Aggeo', 'Zaccaria', 'Malachia', 'Matteo', 'Marco', 'Luca', 'Giovanni', 'Atti',
                    'Romani', '1 Corinzi', '2 Corinzi', 'Galati', 'Efesini', 'Filippesi', 'Colossesi',
                    '1 Tessalonicesi', '2 Tessalonicesi', '1 Timoteo', '2 Timoteo', 'Tito', 'Filemone', 'Ebrei',
                    'Giacomo', '1 Pietro', '2 Pietro', '1 Giovanni', '2 Giovanni', '3 Giovanni', 'Giuda',
                    'Apocalisse']))


def plan(S, books):
    done = done_ranges(books)
    chunks = make_chunks(S, done)
    unit_book = {u['i']: u['b'] for u in S}
    reqs = []
    for n, ch in enumerate(chunks):
        first = next(x for x in ch if x[0] != 'h')
        b = unit_book[int(re.match(r'\d+', first[0]).group(0))]
        reqs.append((f"k{n:05d}", [x[0] for x in ch if x[0] != 'h'], chunk_text(ch, BOOK_IT.get(b, b))))
    return reqs


def estimate(reqs, model=MODEL):
    chars = sum(len(r[2]) for r in reqs)
    tin = chars / 3.1 + len(reqs) * 60            # testo + intestazioni (il sistema va in cache)
    tout = chars * 1.08 / 3.0
    pin, pout = PRICE.get(model, PRICE['claude-sonnet-5-5'])
    usd = tin / 1e6 * pin + tout / 1e6 * pout + len(reqs) * 1500 / 1e6 * pin * 0.1
    return {'requests': len(reqs), 'chars': chars, 'tokens_in': int(tin), 'tokens_out': int(tout), 'usd': round(usd, 2)}


# ---------------- API ----------------
def api(method, path, body=None, raw=False):
    key = os.environ.get('ANTHROPIC_API_KEY', '')
    url = path if path.startswith('http') else API + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        'x-api-key': key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json'})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                b = r.read()
                return b if raw else json.loads(b)
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors='replace')[:600]
            if e.code in (429, 500, 502, 503, 529) and attempt < 5:
                time.sleep(20 * (attempt + 1)); continue
            raise SystemExit(f'Errore API {e.code}: {msg}')
        except urllib.error.URLError as e:
            if attempt < 5:
                time.sleep(20 * (attempt + 1)); continue
            raise SystemExit(f'Rete: {e}')


def params(text):
    return {'model': MODEL, 'max_tokens': 16000, 'thinking': thinking_for(MODEL), 'output_config': {'effort': 'low'},
            'system': [{'type': 'text', 'text': SYSTEM, 'cache_control': {'type': 'ephemeral'}}],
            'messages': [{'role': 'user', 'content': text}]}


# ---------------- stato ----------------
def load_state(path):
    if os.path.exists(path):
        return json.load(open(path, encoding='utf-8'))
    return {'model': MODEL, 'batch': None, 'attempts': 0, 'finished': False, 'log': []}


def save_state(st, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(st, fh, ensure_ascii=False, indent=1)


def note(st, msg):
    line = time.strftime('%Y-%m-%d %H:%M UTC ', time.gmtime()) + msg
    st['log'].append(line)
    print(line, flush=True)


def cmd_submit(segs, it_dir, state_path):
    st = load_state(state_path)
    if st.get('finished'):
        return print('Traduzione con Claude già completata.')
    if st.get('batch'):
        return print('C\'è già un lotto in corso:', st['batch']['id'])
    S, books = load_segs(segs), load_it(it_dir)
    reqs = plan(S, books)
    if not reqs:
        st['finished'] = True; note(st, 'Tutte le unità sono tradotte con Claude.'); save_state(st, state_path); return
    if st['attempts'] >= MAX_ATTEMPTS:
        st['finished'] = True
        note(st, f'Dopo {MAX_ATTEMPTS} tentativi restano {len(reqs)} richieste: per queste resta la traduzione automatica.')
        save_state(st, state_path); return
    est = estimate(reqs)
    note(st, f'Stima ({MODEL}): {est}')
    if est['usd'] > MAX_USD:
        note(st, f'Costo stimato oltre il limite di {MAX_USD} $: non invio.'); save_state(st, state_path); return
    # prova con una richiesta normale: chiave, credito e parametri a posto prima del lotto intero
    sample = reqs[0][2].split('\n')
    sample = '\n'.join(sample[:2] + [next(l for l in sample if l.startswith('<p'))])
    r = api('POST', '/v1/messages', dict(params(sample), max_tokens=4000))
    out = ''.join(c.get('text', '') for c in r.get('content', []) if c.get('type') == 'text')
    note(st, 'Prova riuscita: ' + out[:300].replace('\n', ' '))
    body = {'requests': [{'custom_id': cid, 'params': params(text)} for cid, _, text in reqs]}
    r = api('POST', '/v1/messages/batches', body)
    st['model'] = MODEL
    st['batch'] = {'id': r['id'], 'chunks': {cid: ids for cid, ids, _ in reqs}, 'created': r.get('created_at')}
    st['attempts'] += 1
    note(st, f"Lotto {r['id']} inviato: {len(reqs)} richieste (tentativo {st['attempts']}).")
    save_state(st, state_path)


TAG = re.compile(r'<(t|p) id="([^"]+)">(.*?)</\1>', re.S)


def cmd_collect(segs, it_dir, state_path, minutes=300):
    st = load_state(state_path)
    b = st.get('batch')
    if not b:
        return print('Nessun lotto in corso.')
    t0 = time.time()
    while True:
        info = api('GET', f"/v1/messages/batches/{b['id']}")
        rc = info.get('request_counts', {})
        print(time.strftime('%H:%M'), info.get('processing_status'), rc, flush=True)
        if info.get('processing_status') == 'ended':
            break
        if time.time() - t0 > minutes * 60:
            return print('Il lotto non è ancora finito: riprendo alla prossima esecuzione.')
        time.sleep(120)
    raw = api('GET', info['results_url'], raw=True).decode('utf-8')
    S, books = load_segs(segs), load_it(it_dir)
    got, bad = {}, {'errored': 0, 'expired': 0, 'canceled': 0, 'incomplete': 0}
    usage = {'in': 0, 'out': 0}
    for line in raw.splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        res = r.get('result', {})
        if res.get('type') != 'succeeded':
            bad[res.get('type', 'errored')] = bad.get(res.get('type', 'errored'), 0) + 1
            continue
        msg = res['message']
        u = msg.get('usage', {})
        usage['in'] += u.get('input_tokens', 0) + u.get('cache_read_input_tokens', 0) + u.get('cache_creation_input_tokens', 0)
        usage['out'] += u.get('output_tokens', 0)
        text = ''.join(c.get('text', '') for c in msg.get('content', []) if c.get('type') == 'text')
        want = set(b['chunks'].get(r['custom_id'], []))
        found = {i: v.strip() for _, i, v in TAG.findall(text) if i in want}
        if len(found) < len(want):
            bad['incomplete'] += 1
        got.update(found)
    # unità complete -> mh/it
    by_book = {}
    for u in S:
        items = unit_items(u)
        if not items or not all(i in got for i, _ in items):
            continue
        ok = True
        for i, en in items:
            itx = got[i]
            if not itx or len(itx) < 0.45 * len(en) or len(itx) > 2.6 * len(en) + 40:
                ok = False; break
        if ok:
            by_book.setdefault(u['b'], {})[u['r']] = u
    n = 0
    for code, units in by_book.items():
        bk = books.get(code)
        if not bk:
            continue
        for e in bk['u']:
            u = units.get(e['r'])
            if not u:
                continue
            if u['k'] == 'p' and u.get('te'):
                e['t'] = got[f"{u['i']}t"].replace('‹', '<').replace('›', '>')
            e['p'] = [('# ' if p['h'] else '') + got[f"{u['i']}.{j}"].replace('‹', '<').replace('›', '>')
                      for j, p in enumerate(u['p'])]
            e['c'] = 1
            n += 1
        bk['tr'] = 'claude'
        with open(os.path.join(it_dir, code + '.json'), 'w', encoding='utf-8') as fh:
            json.dump(bk, fh, ensure_ascii=False, separators=(',', ':'))
    pin, pout = PRICE.get(st.get('model', MODEL), PRICE['claude-sonnet-5-5'])
    note(st, f"Lotto {b['id']} finito: {n} unità tradotte con Claude; problemi {bad}; token {usage} "
             f"(circa {usage['in'] / 1e6 * pin + usage['out'] / 1e6 * pout:.2f} $).")
    st['batch'] = None
    save_state(st, state_path)


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    cmd = sys.argv[1]
    if cmd == 'estimate':
        S, books = load_segs(sys.argv[2]), load_it(sys.argv[3])
        reqs = plan(S, books)
        for m in PRICE:
            print(m, estimate(reqs, m))
    elif cmd == 'submit':
        cmd_submit(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == 'collect':
        cmd_collect(sys.argv[2], sys.argv[3], sys.argv[4], float(sys.argv[5]) if len(sys.argv) > 5 else 300)
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
