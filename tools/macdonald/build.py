#!/usr/bin/env python3
"""Costruisce il JSON del commentario di W. MacDonald (Antico Testamento) per l'app La Parola.

Uso:  python3 build.py righe.jsonl MacDonald_AT.json [it_irb20.json]
Ingresso: le righe estratte da extract.py (JSONL, in ordine di lettura); facoltativo il testo della
Riveduta 2020 (stesso file che scarica l'app) per conoscere il numero di versetti dei capitoli.
Uscita: {key, title, author, abbr, entries:[{title, ref, src, text}]}, il formato che l'app importa,
più un file .log con i casi particolari (titoli senza versetti, refusi corretti, note ricollocate…).
Il PDF e il JSON non vanno nel repository (copyright): si importano dal telefono.
"""
import json, re, sys, collections

OFFSET = 14   # pagina del libro = pagina del PDF - 14

SEGMENTS = [   # (tipo, nome, prima e ultima pagina del PDF)
    ('gen', "Introduzione all'Antico Testamento", 15, 24),
    ('gen', 'Introduzione al Pentateuco', 25, 32),
    ('book', 'Genesi', 33, 100), ('book', 'Esodo', 101, 158), ('book', 'Levitico', 159, 200),
    ('book', 'Numeri', 201, 240), ('book', 'Deuteronomio', 241, 280),
    ('gen', 'Introduzione ai libri storici', 281, 284),
    ('book', 'Giosuè', 285, 310), ('book', 'Giudici', 311, 342), ('book', 'Rut', 343, 352),
    ('book', '1 Samuele', 353, 386), ('book', '2 Samuele', 387, 420), ('book', '1 Re', 421, 462),
    ('book', '2 Re', 463, 502), ('book', '1 Cronache', 503, 526), ('book', '2 Cronache', 527, 558),
    ('book', 'Esdra', 559, 570), ('book', 'Neemia', 571, 586), ('book', 'Ester', 587, 600),
    ('gen', 'Introduzione ai libri poetici', 601, 606),
    ('book', 'Giobbe', 607, 648), ('book', 'Salmi', 649, 936), ('book', 'Proverbi', 937, 1038),
    ('book', 'Ecclesiaste', 1039, 1090), ('book', 'Cantico dei Cantici', 1091, 1102),
    ('gen', 'Introduzione ai Profeti', 1103, 1108),
    ('book', 'Isaia', 1109, 1182), ('book', 'Geremia', 1183, 1224), ('book', 'Lamentazioni', 1225, 1232),
    ('book', 'Ezechiele', 1233, 1280), ('book', 'Daniele', 1281, 1304), ('book', 'Osea', 1305, 1318),
    ('book', 'Gioele', 1319, 1324), ('book', 'Amos', 1325, 1334), ('book', 'Abdia', 1335, 1340),
    ('book', 'Giona', 1341, 1348), ('book', 'Michea', 1349, 1356), ('book', 'Naum', 1357, 1362),
    ('book', 'Abacuc', 1363, 1370), ('book', 'Sofonia', 1371, 1376), ('book', 'Aggeo', 1377, 1382),
    ('book', 'Zaccaria', 1383, 1402), ('book', 'Malachia', 1403, 1410),
    ('skip', 'Bibliografia generale', 1411, 1416),
    ('gen', 'Il periodo intertestamentario', 1417, 1424),
]

CHAPTERS = {'Genesi': 50, 'Esodo': 40, 'Levitico': 27, 'Numeri': 36, 'Deuteronomio': 34, 'Giosuè': 24,
            'Giudici': 21, 'Rut': 4, '1 Samuele': 31, '2 Samuele': 24, '1 Re': 22, '2 Re': 25,
            '1 Cronache': 29, '2 Cronache': 36, 'Esdra': 10, 'Neemia': 13, 'Ester': 10, 'Giobbe': 42,
            'Salmi': 150, 'Proverbi': 31, 'Ecclesiaste': 12, 'Cantico dei Cantici': 8, 'Isaia': 66,
            'Geremia': 52, 'Lamentazioni': 5, 'Ezechiele': 48, 'Daniele': 12, 'Osea': 14, 'Gioele': 3,
            'Amos': 9, 'Abdia': 1, 'Giona': 4, 'Michea': 7, 'Naum': 3, 'Abacuc': 3, 'Sofonia': 3,
            'Aggeo': 2, 'Zaccaria': 14, 'Malachia': 4}

# approfondimenti (dall'indice): titolo -> pagina del libro
EXCURSUS = {
    'I patti principali della Scrittura': 33, 'Il segno della circoncisione': 49, 'Omosessualità': 51,
    'Le figure veterotestamentarie': 76, 'Le dispensazioni': 112, 'Il tabernacolo: immagine di Cristo': 130,
    'Le città di rifugio': 290, "L'angelo del Signore": 308, 'La divisione del regno': 427,
    'Evidenti discordanze': 515, 'Salmi imprecatori': 844, 'La distruzione di Sennacherib': 1131,
    'Sacrifici millenniali': 1261,
}

COL_LEFT = {'L': 42.5, 'R': 221.1}
COL_RIGHT = {'L': 206.2, 'R': 384.8}
SUP = str.maketrans('0123456789', '⁰¹²³⁴⁵⁶⁷⁸⁹')
RANK = {'R': 1, 'A': 2, '1': 3, 'a': 4, 'P': 5, 'S': 6}

LOG = collections.defaultdict(list)
VCOUNT = {}      # libro -> [numero di versetti per capitolo]


def load_vcount(path):
    try:
        d = json.loads(open(path, 'rb').read().decode('utf-8-sig'))
    except Exception:
        return
    for (name, n), b in zip(CHAPTERS.items(), d[:39]):
        VCOUNT[name] = [len(c) for c in b['chapters']]


def last_verse_of(book, c):
    vc = VCOUNT.get(book)
    if vc and 1 <= c <= len(vc):
        return vc[c - 1]
    return 999


def norm(s):
    s = s.lower().replace('’', "'").replace(' ', ' ')
    s = re.sub(r'[^a-zàèéìòù0-9\' ]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


EXC_NORM = {norm(k): k for k in EXCURSUS}


# ================================================================ righe
def first_span(l):
    for s in l['spans']:
        if s['t'].strip() and not s['sup']:
            return s
    return None


def line_text(l):
    return ''.join(s['t'] for s in l['spans'])


VREF_RE = re.compile(r'^\s*(\d{1,3}):(\d{1,3})([a-c]?)(?:\s*[-–—]\s*(?:(\d{1,3})[:.])?(\d{1,3})([a-c]?))?((?:\s*,\s*\d{1,3}[a-c]?(?:\s*[-–]\s*\d{1,3}[a-c]?)?)*)')


def verse_start(l):
    """Riferimento in grassetto all'inizio della riga: (c1, v1, c2, v2, testo del riferimento)."""
    s = first_span(l)
    if not s or not s['b']:
        return None
    bold = ''
    for sp in l['spans']:
        if sp['sup']:
            break
        if sp['b'] or not sp['t'].strip():
            bold += sp['t']
        else:
            break
    m = VREF_RE.match(bold)
    if not m:
        return None
    c1, v1 = int(m.group(1)), int(m.group(2))
    c2, v2 = c1, v1
    if m.group(5):
        v2 = int(m.group(5))
        if m.group(4):
            c2 = int(m.group(4))
    for part in re.findall(r'\d{1,3}(?:\s*[-–]\s*\d{1,3})?', m.group(7) or ''):   # «4:4-5, 24»
        nums = [int(x) for x in re.findall(r'\d+', part)]
        if c2 == c1 and max(nums) > v2:
            v2 = max(nums)
    if (c2, v2) < (c1, v1):
        if c2 == c1:                      # «23:21:23» e simili refusi
            v2 = v1
        else:
            return None
    return (c1, v1, c2, v2, m.group(0).strip())


def line_kind(l):
    s = first_span(l)
    f, sz = s['f'], s['sz']
    if sz >= 19 or f.startswith('BookAntiqua') or (f.startswith('BellGothic') and sz >= 15):
        return 'title'
    if 11.4 <= sz <= 14.5 and s['b']:
        if verse_start(l):
            return 'body'                 # riga di commento stampata in corpo maggiore
        if re.match(r'^\s*\d{1,3}\s+\(', line_text(l)):
            return 'small'                # nota stampata in corpo maggiore
        return 'h12'
    if 10.3 <= sz <= 10.8:
        if s['b'] and s['i']:
            return 'subhead'
        if s['b']:
            return 'head'
        return 'outline'
    if 9.2 <= sz <= 9.8:
        return 'small'
    return 'body'


LABEL_RE = re.compile(r'^\s*([IVXL]+|[A-Z]|\d{1,2}|[a-z])\.\s+(?=\S)')
NOTE_START_RE = re.compile(r'^\s*\d{1,3}\.?\s')


# ================================================================ paragrafi
class Par:
    def __init__(self, kind, l):
        self.kind = kind
        self.lines = [l]
        self.runs = []          # [testo, stile]  stile: '', 'b', 'i', 'sup'
        self.p0 = self.p1 = l['p']

    @property
    def first(self):
        return self.lines[0]

    def plain(self):
        t = ''.join(x for x, st in self.runs if st != 'sup')
        return re.sub(r'\s+', ' ', t).strip()


def is_full(l, kind):
    if l['col'] == 'F':
        return l['x1'] >= 375 or (l['x1'] >= 352 and l['x0'] < 90)
    right = COL_RIGHT[l['col']] - (14.2 if kind == 'small' else 0)
    return l['x1'] >= right - 5


def indent_of(l):
    if l['col'] == 'F':
        return l['x0'] - 42.5
    return l['x0'] - COL_LEFT[l['col']]


def ends_hyphen(l):
    t = line_text(l).rstrip()
    return len(t) > 1 and t[-1] in '-­' and t[-2].isalpha()


def trim_tail(runs):
    k = len(runs) - 1
    while k >= 0 and not runs[k][0].strip():
        k -= 1
    if k >= 0:
        runs[k][0] = runs[k][0].rstrip()
    del runs[k + 1:]
    return k


def add_line(par, l, joiner):
    runs = par.runs
    if runs and joiner == 'hyph':
        k = trim_tail(runs)
        nxt = line_text(l).lstrip()
        prev_word = re.findall(r'[\wÀ-ÿ]+(?=-$)', runs[k][0]) if k >= 0 else []
        next_word = re.match(r'[\wÀ-ÿ]+', nxt)
        upper_pair = bool(prev_word and next_word and prev_word[-1].isupper() and next_word.group(0).isupper() and len(next_word.group(0)) > 1)
        if k >= 0 and (nxt[:1].islower() or upper_pair):
            runs[k][0] = runs[k][0][:-1]          # «crede-» + «re» -> «credere»
    elif runs and joiner == ' ':
        trim_tail(runs)
        tail = runs[-1][0] if runs else ''
        if not re.search(r'(https?://|www\.)\S*$', tail):
            runs.append([' ', ''])
    elif runs and joiner == '\n':
        trim_tail(runs)
        runs.append(['\n', ''])
    started = False
    for s in l['spans']:
        t = s['t'].replace(' ', ' ')
        if not started:
            t = t.lstrip()
            if not t:
                continue
            started = True
        st = 'sup' if s['sup'] else ('b' if s['b'] else ('i' if s['i'] else ''))
        if st == 'sup':
            t = t.strip()
            if not t:
                continue
        runs.append([t, st])
    if par.lines[-1] is not l:
        par.lines.append(l)
    par.p1 = l['p']


def build_paragraphs(lines):
    pars, cur = [], None
    for l in lines:
        kind = line_kind(l)
        new, joiner = True, None
        if cur is not None and cur.kind == kind and kind in ('body', 'small', 'outline', 'head', 'subhead'):
            a = cur.lines[-1]
            same_flow = a['p'] == l['p'] and a['col'] == l['col']
            gap = l['y0'] - a['y1'] if same_flow else 0
            if kind == 'outline':
                done = re.search(r'\)\s*$', line_text(a)) and heading_range(line_text(a)) is not None
                if not LABEL_RE.match(line_text(l)) and not done:
                    new, joiner = False, ('hyph' if ends_hyphen(a) else (' ' if is_full(a, 'body') else '\n'))
            elif kind in ('head', 'subhead'):
                done = re.search(r'\)\s*$', line_text(a)) and heading_range(line_text(a)) is not None
                if gap <= 6 and not LABEL_RE.match(line_text(l)) and not done and not re.match(r'^\s*Salmo\s+\d', line_text(l)):
                    new, joiner = False, ('hyph' if ends_hyphen(a) else ' ')
            elif kind == 'body' and verse_start(l):
                new = True
            elif kind == 'body' and (a['col'] == 'F') != (l['col'] == 'F'):
                new = True                                       # fine o inizio di un blocco a tutta pagina
            elif gap > 6:
                new = True
            elif kind == 'small' and NOTE_START_RE.match(line_text(l)) and first_span(l)['b']:
                new = True                                       # nuova nota
            elif kind == 'small' and (l['col'] == 'F') != (a['col'] == 'F') and same_flow is False and a['p'] == l['p']:
                new = True
            elif ends_hyphen(a):
                new, joiner = False, 'hyph'
            elif is_full(a, kind):
                new, joiner = False, ' '
            else:
                ia, il = indent_of(a), indent_of(l)
                if kind == 'body':
                    if 8 <= il < 40 and ia < 8:
                        new = True                               # rientro di prima riga
                    else:
                        new, joiner = False, '\n'                # a capo (poesia, elenchi)
                else:
                    if il > ia + 8:
                        new = True
                    else:
                        new, joiner = False, '\n'
        if new:
            cur = Par(kind, l)
            pars.append(cur)
            add_line(cur, l, None)
        else:
            add_line(cur, l, joiner)
    return pars


# ================================================================ testo con stili
def runs_to_md(runs, notes_used=None):
    """Grassetto **…**, corsivo *…*, note come cifre in apice."""
    merged = []
    for t, st in runs:
        if st == 'sup':
            if notes_used is not None and t.isdigit():
                notes_used.append(int(t))
            merged.append([t.translate(SUP), 'sup'])
            continue
        if st in ('b', 'i') and not t.strip():
            st = ''                                   # spazi in grassetto: neutri
        if merged and merged[-1][1] == st:
            merged[-1][0] += t
        else:
            merged.append([t, st])
    out = []                                          # «**a** **b**» -> «**a b**»
    for t, st in merged:
        if st in ('b', 'i') and len(out) >= 2 and out[-1][1] == '' and not out[-1][0].strip() \
                and '\n' not in out[-1][0] and out[-2][1] == st:
            sp = out.pop()
            out[-1][0] += sp[0] + t
        elif out and out[-1][1] == st and st != 'sup':
            out[-1][0] += t
        else:
            out.append([t, st])
    s = ''
    for i, (t, st) in enumerate(out):
        if st in ('b', 'i') and t.strip():
            mark = '**' if st == 'b' else '*'
            lead = t[:len(t) - len(t.lstrip())]
            trail = t[len(t.rstrip()):]
            core = t.strip()
            nxt = out[i + 1] if i + 1 < len(out) else None
            if st == 'i' and (s.endswith('*') or (nxt and nxt[1] == 'b' and not trail and not nxt[0][:1].isspace())):
                s += t                                # corsivo attaccato al grassetto: lo lascio tondo
                continue
            if st == 'b' and s.endswith('*') and not lead:
                s += ' '
            parts = core.split('\n')
            s += lead + '\n'.join(mark + p.strip() + mark if p.strip() else '' for p in parts) + trail
        else:
            s += t
    s = re.sub(r'[ \t]+', ' ', s)
    s = re.sub(r' *\n *', '\n', s)
    return s.strip()


def strip_leading_ref(par, reftext):
    """Toglie «1:3-5» dall'inizio del paragrafo (il riferimento è già nella voce)."""
    want = re.sub(r'\s+', '', reftext)
    got = ''
    runs = par.runs
    i = 0
    while i < len(runs) and len(got) < len(want):
        t = runs[i][0]
        j = 0
        while j < len(t) and len(got) < len(want):
            if not t[j].isspace():
                got += t[j]
            j += 1
        if len(got) >= len(want):
            runs[i][0] = t[j:].lstrip()
            del runs[:i]
            return
        i += 1


# ================================================================ riferimenti
def ref_str(book, c1, v1, c2, v2):
    if v1 == 1 and v2 >= 999:
        return f'{book} {c1}' if c1 == c2 else f'{book} {c1}-{c2}'
    if c1 == c2:
        return f'{book} {c1}:{v1}' if v1 == v2 else f'{book} {c1}:{v1}-{v2}'
    if v2 >= 999:
        return f'{book} {c1}:{v1}-{c2}:999'
    return f'{book} {c1}:{v1}-{c2}:{v2}'


def heading_range(text, chap=None):
    """(capp. 1–11) (cap. 3) (11:10–25:18) (49:29–50) (Salmi 1–41) (cap. 11:1-9) (vv. 5-6) (12:1-9; 13:1)…"""
    t = re.sub(r'\[[^\]]*\]', '', text.replace('\u00a0', ' '))
    m = re.search(r'\(([^()]*)\)\s*$', t)
    if not m:
        return None
    r = m.group(1).strip()
    vv = re.match(r'^vv?\.\s*', r, re.I)
    r = re.sub(r'^(?:capp?\.|capitol[oi]|Salm[oi]|vv?\.)\s*', '', r, flags=re.I).replace('—', '–').strip()
    r = re.split(r'\s*[;,]\s*', r)[0]
    if vv:
        c = chap or 1
        mm = re.fullmatch(r'(\d{1,3})[a-c]?(?:\s*[-–]\s*(\d{1,3})[a-c]?)?', r)
        if mm:
            a, b = int(mm.group(1)), int(mm.group(2) or mm.group(1))
            return (c, a, c, b) if b >= a else None
        return None
    mm = re.fullmatch(r'(\d{1,3})(?:\s*[-–]\s*(\d{1,3}))?', r)
    if mm:
        a, b = int(mm.group(1)), int(mm.group(2) or mm.group(1))
        return (a, 1, b, 999) if b >= a else None
    mm = re.fullmatch(r'(\d{1,3}):(\d{1,3})[a-c]?\s*–\s*(\d{1,3})', r)       # «49:29–50»
    if mm:
        c1, v1, c2 = int(mm.group(1)), int(mm.group(2)), int(mm.group(3))
        if c2 > c1:
            return (c1, v1, c2, 999)
    mm = re.fullmatch(r'(\d{1,3}):(\d{1,3})[a-c]?(?:\s*[-–]\s*(?:(\d{1,3}):)?(\d{1,3})[a-c]?)?', r)
    if mm:
        c1, v1 = int(mm.group(1)), int(mm.group(2))
        c2, v2 = c1, v1
        if mm.group(4):
            v2 = int(mm.group(4))
            if mm.group(3):
                c2 = int(mm.group(3))
        if (c2, v2) >= (c1, v1):
            return (c1, v1, c2, v2)
    mm = re.fullmatch(r'(\d{1,3})\s*[-–]\s*(\d{1,3}):(\d{1,3})', r)            # «11–12:3»
    if mm:
        return (int(mm.group(1)), 1, int(mm.group(2)), int(mm.group(3)))
    return None


# ================================================================ voci
class Entry:
    def __init__(self, title, refs, page, kind):
        self.title = title
        self.refs = refs
        self.paras = []
        self.notes = []
        self.p0 = self.p1 = page
        self.kind = kind

    def add(self, md, par=None):
        if md:
            self.paras.append(md)
        if par is not None:
            self.p1 = max(self.p1, par.p1)


def src_note(e):
    b0, b1 = e.p0 - OFFSET, e.p1 - OFFSET
    if b0 == b1:
        return f'Pagina {b0} del libro (p. {e.p0} del PDF)'
    return f'Pagine {b0}-{b1} del libro (pp. {e.p0}-{e.p1} del PDF)'


def parse_notes(pars):
    notes, cur = {}, None
    for par in pars:
        if par.kind not in ('small', 'body'):
            continue
        runs = [list(r) for r in par.runs]
        first = next((r for r in runs if r[0].strip()), None)
        m = re.match(r'^\s*(\d{1,3})\.?(?=\s|\(|$)\s*', first[0]) if first and first[1] == 'b' else None
        if m:
            cur = int(m.group(1))
            first[0] = first[0][m.end():]
            # il contesto «(1:2)» o «(Introduzione)» può essere in grassetto: lo rendo tondo (poi lo tolgo)
            for r in runs:
                if not r[0].strip():
                    continue
                if r[0].lstrip().startswith('(') and r[1] == 'b':
                    r[1] = ''
                break
            notes[cur] = runs_to_md(runs)
        elif cur is not None:
            md = runs_to_md(runs)
            if md:
                notes[cur] += '\n' + md
    return notes


def strip_note_ctx(t):
    """«(1:2) Testo» -> «Testo»: il riferimento tra parentesi è già quello della voce."""
    return re.sub(r'^\((?:[^()]|\([^()]*\))*\)\s*', '', t, count=1).strip()


# ================================================================ struttura di un libro
class Outline:
    """Pila dei titoli dello schema (I., A., 1., a., Salmo, lettera del Salmo 119)."""
    def __init__(self, book, whole):
        self.book, self.whole = book, whole
        self.stack = []                 # [(rank, label, text, range)]
        self.last = {}                  # ultima etichetta per livello

    def classify(self, text):
        m = LABEL_RE.match(text)
        if not m:
            return None
        lab = m.group(1)
        if lab.isdigit():
            return '1'
        if lab.islower():
            return 'a'
        if lab in ('I', 'V', 'X'):
            prev = self.last.get('A')
            if prev and len(prev) == 1 and ord(lab) == ord(prev) + 1:
                return 'A'               # «I.» dopo «H.»: è una lettera
            return 'R'
        if re.fullmatch(r'[IVX]+', lab):
            return 'R'
        return 'A'

    def push(self, kind, label, text, rng):
        r = RANK[kind]
        while self.stack and RANK[self.stack[-1][0]] >= r:
            self.stack.pop()
        if rng is None:
            rng = self.stack[-1][3] if self.stack else self.whole
        self.stack.append((kind, label, text, rng))
        self.last[kind] = label

    def innermost(self):
        return self.stack[-1] if self.stack else None


def clean_heading(t):
    t = re.sub(r'\s+', ' ', t).strip()
    t = re.sub(r'\s+([,.;:)])', r'\1', t)
    return t


def sup_numbers(runs):
    return [int(t) for t, st in runs if st == 'sup' and t.isdigit()]


def parse_ref(s):
    m = re.match(r'^(.*?) (\d+)(?::(\d+))?(?:-(\d+)(?::(\d+))?)?$', s)
    if not m:
        return None
    book, c1 = m.group(1), int(m.group(2))
    if m.group(3) is None:
        c2 = int(m.group(4)) if m.group(4) else c1
        return book, c1, 1, c2, 999
    v1 = int(m.group(3))
    if m.group(5):
        return book, c1, v1, int(m.group(4)), int(m.group(5))
    if m.group(4):
        return book, c1, v1, c1, int(m.group(4))
    return book, c1, v1, c1, v1


def process_book(book, pars, out):
    nch = CHAPTERS[book]
    whole = (1, 1, nch, 999)
    W = ref_str(book, *whole)
    ol = Outline(book, whole)
    entries = []
    intro = Entry('Introduzione', [W], pars[0].p0 if pars else 0, 'intro')
    somm = None
    somm_lines = []
    phase = 'intro'
    cur = None
    exc = None
    last_verse = None
    last_was_head = False
    pending = []
    notes_pars = []
    norange = set()
    prev_vs = None

    def new_entry(title, ref, page, kind):
        e = Entry(title, [ref], page, kind)
        e.notes.extend(pending)
        pending.clear()
        entries.append(e)
        return e

    def heading_entry(par):
        h = ol.innermost()
        if h is None:
            return new_entry('Introduzione al commento', W, par.p0, 'head')
        e = new_entry(h[2], ref_str(book, *h[3]), par.p0, 'head')
        e.infer = h[2] in norange
        return e

    for par in pars:
        k = par.kind
        txt = par.plain()
        nt = norm(txt)
        if k == 'title':
            continue
        if phase == 'intro':
            if k == 'h12' and nt == 'sommario':
                phase = 'somm'
                somm = Entry('Sommario', [W], par.p0, 'somm')
                continue
            if k in ('head', 'subhead', 'h12'):
                if nt == 'introduzione':
                    continue
                intro.add('#### ' + clean_heading(txt), par)
                intro.notes.extend(sup_numbers(par.runs))
            else:
                intro.add(runs_to_md(par.runs, intro.notes), par)
            continue
        if phase == 'somm':
            if k == 'outline':
                lev = ol.classify(txt) or 'cont'
                depth = {'R': 0, 'A': 1, '1': 2, 'a': 3}.get(lev, 1)
                if lev in ('R', 'A', '1', 'a'):
                    ol.last[lev] = LABEL_RE.match(txt).group(1)
                somm_lines.append(' ' * depth + clean_heading(txt))
                somm.p1 = max(somm.p1, par.p1)
                continue
            phase = 'comm'
            ol.last = {}
            somm.add('\n'.join(somm_lines))
            if nt in ('commentario', 'introduzione') and k in ('h12', 'head'):
                continue
        if phase == 'comm':
            if k in ('head', 'subhead', 'h12') and nt in ('note', 'nota'):
                phase = 'notes'
                continue
            if k in ('head', 'subhead', 'h12'):
                text = clean_heading(txt)
                hn = sup_numbers(par.runs)
                # «(cap. 12)» rimasto da solo: completa il titolo precedente
                if re.fullmatch(r'\([^()]*\)', text) and last_was_head and ol.stack:
                    kd, lab, t0, rng = ol.stack[-1]
                    t1 = t0 + ' ' + text
                    chap = rng[0] if rng and rng[0] == rng[2] else None
                    ol.stack[-1] = (kd, lab, t1, heading_range(t1, chap) or rng)
                    pending.extend(hn)
                    continue
                last_was_head = True
                # approfondimento
                key = next((v for kk, v in EXC_NORM.items() if nt == kk or nt.startswith(kk)), None)
                if key:
                    ref = last_verse if last_verse else (ref_str(book, *ol.innermost()[3]) if ol.innermost() else W)
                    cur = exc = new_entry(key, ref, par.p0, 'exc')
                    exc.notes.extend(hn)
                    LOG['excursus'].append((book, key, ref, par.p0))
                    continue
                if book == 'Salmi' and k == 'head' and re.match(r'^Salmo\s+\d{1,3}\b', text):
                    n = int(re.match(r'^Salmo\s+(\d{1,3})', text).group(1))
                    ol.push('P', str(n), text, (n, 1, n, 999))
                    cur = exc = None
                    pending.extend(hn)
                    continue
                lev = ol.classify(text)
                if lev:
                    if k == 'h12':
                        LOG['h12_heading'].append((book, par.p0, text))
                    parent = ol.innermost()
                    chap = parent[3][0] if parent and parent[3][0] == parent[3][2] else (1 if nch == 1 else None)
                    rng = heading_range(text, chap)
                    if rng is None:
                        LOG['heading_norange'].append((book, par.p0, text))
                        norange.add(text)
                    ol.push(lev, LABEL_RE.match(text).group(1), text, rng)
                    cur = exc = None
                    pending.extend(hn)
                    continue
                if k == 'h12':
                    LOG['h12_skipped'].append((book, par.p0, text))
                    continue
                # titolo senza etichetta ma con versetti tra parentesi: sottosezione (es. nei Salmi)
                h = ol.innermost()
                chap = h[3][0] if h and h[3][0] == h[3][2] else (1 if nch == 1 else None)
                rng = heading_range(text, chap)
                if rng and re.search(r'\(\s*(?:vv?\.\s*)?\d', text) and cur is not exc:
                    if book == 'Salmi' and h and h[0] in ('P', 'S') and re.search(r'\(\s*\d{1,3}\s*[-–]\s*\d{1,3}\s*\)\s*$', text) and ':' not in text:
                        n = int([x for x in ol.stack if x[0] == 'P'][-1][1])
                        mm = re.search(r'\((\d{1,3})\s*[-–]\s*(\d{1,3})\)\s*$', text)
                        rng = (n, int(mm.group(1)), n, int(mm.group(2)))
                    ol.push('S', text, text, rng)
                    cur = exc = None
                    pending.extend(hn)
                    LOG['subsection'].append((book, par.p0, text, rng))
                    continue
                if cur is exc and exc is not None:
                    exc.add('#### ' + text, par)                    # sottotitolo dell'approfondimento
                    exc.notes.extend(hn)
                    LOG['exc_sub'].append((exc.title, text))
                    continue
                if cur is None:
                    cur = heading_entry(par)
                cur.add('#### ' + text, par)
                cur.notes.extend(hn)
                LOG['inline_heading'].append((book, par.p0, text))
                continue
            last_was_head = False
            # testo
            vs = verse_start(par.first) if k == 'body' else None
            if vs:
                c1, v1, c2, v2, rt = vs
                ps = [x for x in ol.stack if x[0] == 'P']
                if book == 'Salmi' and ps and c1 == c2 and c1 != int(ps[-1][1]) and abs(c1 - int(ps[-1][1])) == 1 \
                        and prev_vs and prev_vs[2] == int(ps[-1][1]) and v1 > prev_vs[3]:
                    LOG['typo_fixed'].append((book, par.p0, rt, f'{ps[-1][1]}:{v1}'))
                    c1 = c2 = int(ps[-1][1])
                elif prev_vs and c1 == c2 == prev_vs[2] and v1 == v2 and (c1, v1) < (prev_vs[0], prev_vs[1]) \
                        and prev_vs[3] < 900 and prev_vs[3] + 1 <= last_verse_of(book, c1):
                    LOG['typo_fixed'].append((book, par.p0, rt, f'{c1}:{prev_vs[3] + 1}'))
                    v1 = v2 = prev_vs[3] + 1
                if c1 > nch or c2 > nch or v1 > last_verse_of(book, c1) or (v2 < 900 and v2 > last_verse_of(book, c2)):
                    LOG['bad_ref'].append((book, par.p0, rt))
                prev_vs = (c1, v1, c2, v2)
                h = ol.innermost()
                ref = ref_str(book, c1, v1, c2, v2)
                cur = new_entry(h[2] if h else '', ref, par.p0, 'verse')
                exc = None
                last_verse = ref
                strip_leading_ref(par, rt)
                cur.add(runs_to_md(par.runs, cur.notes), par)
                continue
            if par.first['col'] == 'F' and k == 'body' and all(r[1] == 'b' or not r[0].strip() for r in par.runs if r[1] != 'sup'):
                LOG['caption_skipped'].append((book, par.p0, txt[:90]))
                continue
            if cur is None:
                cur = heading_entry(par)
            cur.add(runs_to_md(par.runs, cur.notes), par)
            continue
        if phase == 'notes':
            if k in ('head', 'h12', 'subhead') and nt.startswith('bibliografia'):
                phase = 'biblio'
                continue
            notes_pars.append(par)
            continue
        # bibliografia: tralasciata
    if somm is not None and not somm.paras:
        somm.add('\n'.join(somm_lines))
    infer_ranges(book, entries)
    notes = parse_notes(notes_pars)
    result = [intro] + ([somm] if somm and somm.paras else []) + entries
    used = {n for e in result for n in e.notes}
    for n in sorted(set(notes) - used):
        target = note_target(book, notes[n], result, intro)
        target.notes.append(n)
        LOG['note_by_context'].append((book, n, target.refs[:1], notes[n][:40]))
    for e in result:
        attach_notes(e, notes, book)
    out.extend(result)


def infer_ranges(book, entries):
    """Titolo senza versetti («5. La moltiplicazione dei pani»): dai versetti tra la voce precedente e la successiva."""
    for i, e in enumerate(entries):
        if not getattr(e, 'infer', False):
            continue
        prev = next((parse_ref(x.refs[0]) for x in reversed(entries[:i]) if x.kind in ('verse', 'head') and not getattr(x, 'infer', False)), None)
        nxt = next((parse_ref(x.refs[0]) for x in entries[i + 1:] if x.kind in ('verse', 'head') and not getattr(x, 'infer', False)), None)
        if not prev or not nxt:
            continue
        _, _, _, pc2, pv2 = prev
        _, nc1, nv1, _, _ = nxt
        if pv2 >= 900 or pv2 >= last_verse_of(book, pc2):
            s = (pc2 + 1, 1)
        else:
            s = (pc2, pv2 + 1)
        t = (nc1, nv1 - 1) if nv1 > 1 else (nc1 - 1, last_verse_of(book, nc1 - 1))
        if s <= t and t[1] < 900:
            new = ref_str(book, s[0], s[1], t[0], t[1])
            LOG['range_inferred'].append((book, e.title, e.refs[0], new))
            e.refs = [new]


def note_target(book, text, result, intro):
    m = re.match(r'^\(([^)]*)\)', text)
    ctx = m.group(1) if m else ''
    mm = re.search(r'(\d{1,3}):(\d{1,3})', ctx)
    if mm:
        c, v = int(mm.group(1)), int(mm.group(2))
        best = None
        for e in result:
            if e.kind not in ('verse', 'head', 'exc'):
                continue
            r = parse_ref(e.refs[0])
            if r and (r[1], r[2]) <= (c, v) <= (r[3], r[4]):
                span = (r[3] - r[1]) * 1000 + (min(r[4], 200) - r[2])
                if best is None or span < best[0]:
                    best = (span, e)
        if best:
            return best[1]
    mm = re.search(r'Salmo\s+(\d{1,3})', ctx)
    if mm:
        for e in result:
            if e.refs and e.refs[0] == f'{book} {int(mm.group(1))}':
                return e
    return intro


def attach_notes(e, notes, where):
    seen = []
    for n in e.notes:
        if n not in seen:
            seen.append(n)
    e.notes = seen
    lines = []
    for n in seen:
        if n in notes:
            lines.append(str(n).translate(SUP) + ' ' + strip_note_ctx(notes[n]))
        else:
            LOG['note_missing'].append((where, n, e.refs[:1]))
    if lines:
        e.paras.append('#### Note')
        e.paras.extend(lines)


def process_gen(name, pars, out):
    e = Entry(name, [], pars[0].p0, 'gen')
    phase = 'text'
    notes_pars = []
    for par in pars:
        k = par.kind
        txt = par.plain()
        nt = norm(txt)
        if k == 'title':
            continue
        if phase == 'text':
            if k in ('head', 'h12', 'subhead') and nt in ('note', 'nota'):
                phase = 'notes'
                continue
            if k in ('head', 'subhead', 'h12'):
                e.add('#### ' + clean_heading(txt), par)
            else:
                e.add(runs_to_md(par.runs, e.notes), par)
            continue
        if phase == 'notes':
            if k in ('head', 'h12', 'subhead') and nt.startswith('bibliografia'):
                phase = 'biblio'
                continue
            notes_pars.append(par)
    attach_notes(e, parse_notes(notes_pars), name)
    out.append(e)


# ================================================================ tabelle
PR_GROUPS = ['22:22-23', '24-25', '26-27', '28', '29', '23:1-3', '23:4-5', '6-8', '9', '10-11', '12', '13-14',
             '23:15-16', '17-18', '19-21', '23:22-25', '26-28', '29-35', '24:1-2', '3-4', '5-6', '7', '8-9', '10',
             '24:11-12', '13-14', '15-16', '17-18', '19-20', '21-22']


def fix_tables(entries):
    """La griglia dei «trenta gruppi» di Proverbi 22:20 si legge per colonne, non per righe."""
    for e in entries:
        if e.refs and e.refs[0] == 'Proverbi 22:20':
            for i, p in enumerate(e.paras):
                cells = re.findall(r'[\d:\-]+', p)
                if len(cells) == 30 and sorted(cells) == sorted(PR_GROUPS) and not re.search(r'[a-zA-Z]', p):
                    e.paras[i] = '\n'.join(f'{n}. {c}' for n, c in enumerate(PR_GROUPS, 1))
                    LOG['table_fixed'].append(e.refs[0])


# ================================================================ main
def main(lines_path, out_path, bible_path=None):
    if bible_path:
        load_vcount(bible_path)
    by_page = collections.defaultdict(list)
    for ln in open(lines_path, encoding='utf-8'):
        l = json.loads(ln)
        by_page[l['p']].append(l)
    entries = []
    for kind, name, p0, p1 in SEGMENTS:
        if kind == 'skip':
            continue
        lines = [l for p in range(p0, p1 + 1) for l in by_page.get(p, [])]
        pars = build_paragraphs(lines)
        if kind == 'gen':
            process_gen(name, pars, entries)
        else:
            process_book(name, pars, entries)
    fix_tables(entries)
    out = []
    for e in entries:
        text = '\n\n'.join(p for p in e.paras if p.strip())
        if not text.strip():
            LOG['empty_entry'].append((e.title, e.refs, e.p0))
            continue
        out.append({'title': e.title, 'ref': '; '.join(e.refs), 'src': src_note(e), 'text': text})
    doc = {
        'key': 'macdonald-commentario-discepolo-at',
        'title': 'Il commentario biblico del discepolo – Antico Testamento',
        'author': 'William MacDonald',
        'abbr': 'nr',
        'entries': out,
    }
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(doc, f, ensure_ascii=False, separators=(',', ':'))
    with open(out_path + '.log', 'w', encoding='utf-8') as f:
        for k, v in LOG.items():
            f.write(f'== {k} ({len(v)})\n')
            for x in v:
                f.write(f'  {x}\n')
    print(len(out), 'voci;', {k: len(v) for k, v in LOG.items()})


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
