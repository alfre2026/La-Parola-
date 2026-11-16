#!/usr/bin/env python3
"""Matthew Henry, Commentary on the Whole Bible (1706-1721, pubblico dominio).

Dal testo inglese del modulo CrossWire SWORD «MHC», estratto per capitolo nel
repository pubblico samueldotj/bible-commentaries (cartella en/henry), scrive:

  mh/en/<LIBRO>.json      testo originale per l'app, un file per libro
  <work>/segs.json        frasi da tradurre (solo con --segs)

Formato dei file per l'app (uguale per en e it):
  {"b": "JHN", "u": [{"r": "JHN.3.1-21", "k": "p", "t": "titolo", "p": ["paragrafo", ...]}, ...]}
  k: "b" introduzione al libro, "c" introduzione al capitolo, "p" sezione su uno o più versetti.
  Un paragrafo che inizia con "# " è un titoletto.

Uso: build.py <cartella en/henry> <cartella di uscita mh/en> [--segs work/segs.json]
"""
import json, os, re, sys, collections

CODES = ('GEN EXO LEV NUM DEU JOS JDG RUT 1SA 2SA 1KI 2KI 1CH 2CH EZR NEH EST JOB PSA PRO ECC SNG ISA JER LAM '
         'EZK DAN HOS JOL AMO OBA JON MIC NAM HAB ZEP HAG ZEC MAL MAT MRK LUK JHN ACT ROM 1CO 2CO GAL EPH PHP '
         'COL 1TH 2TH 1TI 2TI TIT PHM HEB JAS 1PE 2PE 1JN 2JN 3JN JUD REV').split()
NAMES = ['Genesi', 'Esodo', 'Levitico', 'Numeri', 'Deuteronomio', 'Giosuè', 'Giudici', 'Rut', '1 Samuele', '2 Samuele',
         '1 Re', '2 Re', '1 Cronache', '2 Cronache', 'Esdra', 'Neemia', 'Ester', 'Giobbe', 'Salmi', 'Proverbi',
         'Ecclesiaste', 'Cantico dei Cantici', 'Isaia', 'Geremia', 'Lamentazioni', 'Ezechiele', 'Daniele', 'Osea',
         'Gioele', 'Amos', 'Abdia', 'Giona', 'Michea', 'Naum', 'Abacuc', 'Sofonia', 'Aggeo', 'Zaccaria', 'Malachia',
         'Matteo', 'Marco', 'Luca', 'Giovanni', 'Atti', 'Romani', '1 Corinzi', '2 Corinzi', 'Galati', 'Efesini',
         'Filippesi', 'Colossesi', '1 Tessalonicesi', '2 Tessalonicesi', '1 Timoteo', '2 Timoteo', 'Tito', 'Filemone',
         'Ebrei', 'Giacomo', '1 Pietro', '2 Pietro', '1 Giovanni', '2 Giovanni', '3 Giovanni', 'Giuda', 'Apocalisse']
NAME = dict(zip(CODES, NAMES))
SALMO = 'Salmo'   # un salmo solo: «Salmo 23:1»

REF_ID = re.compile(r'^([1-3]?[A-Z]{2,3})(?:\.(\d+)(?:\.(\d+)(?:-(?:(\d+)\.)?(\d+))?)?)?$')


def chapter_files(src, code):
    d = os.path.join(src, code)
    if not os.path.isdir(d):
        return []
    files = [f for f in os.listdir(d) if f.endswith('.json')]
    key = lambda f: -1 if f == 'intro.json' else int(f[:-5])
    return [os.path.join(d, f) for f in sorted(files, key=key)]


def it_label(ref_id, text):
    """Riferimento in italiano per il testo da tradurre ("Mal. ii. 7" -> "Malachia 2:7")."""
    m = REF_ID.match(ref_id)
    if not m:
        return None
    code, c1, v1, c2, v2 = m.groups()
    if code not in NAME or not c1:
        return None
    t = text.strip()
    if re.fullmatch(r'\d+', t):          # seguito di un elenco: «v. 24, 33, 37»
        return None
    if re.match(r'^v(?:er|v)?\.?\s*\d', t, re.I) or re.match(r'^verses?\s+\d', t, re.I):
        if not v1:
            return None
        if c2 and c2 != c1:
            return f'vv. {v1}–{c2}:{v2}'
        return f'v. {v1}' if not v2 or v2 == v1 else f'vv. {v1}-{v2}'
    name = NAME[code]
    if code == 'PSA':
        name = SALMO
    single = code in ('OBA', 'PHM', '2JN', '3JN', 'JUD')
    has_verse = bool(re.search(r'\d', re.sub(r'^[1-3]\s', '', t)))
    if single and not has_verse:
        return name
    if not v1 or not has_verse:
        return f'{name} {c1}'
    if c2 and c2 != c1:
        return f'{name} {c1}:{v1}–{c2}:{v2}'
    return f'{name} {c1}:{v1}' + (f'-{v2}' if v2 and v2 != v1 else '')


# ---------- forme arcaiche (solo per il testo da tradurre) ----------
ETH_SKIP = {'teeth', 'bosheth', 'listeth', 'seth', 'heth', 'japheth', 'nazareth', 'elizabeth', 'elisabeth', 'kenneth',
            'beth', 'meth', 'hazareth'}
ORDINAL = re.compile(r'(?:twent|thirt|fort|fift|sixt|sevent|eight|ninet)ieth$')


def make_eth_map(counter):
    out = {}
    for w in counter:
        if not (w.endswith('eth') and len(w) > 4 and w.islower()) or w in ETH_SKIP or ORDINAL.search(w):
            continue
        stem = w[:-3]
        if w.endswith('ieth'):            # crieth -> cries, lieth -> lies, sanctifieth -> sanctifies
            out[w] = stem[:-1] + 'ies'
            continue
        if re.search(r'(?:s|x|z|ch|sh)$', stem):
            cand = [stem + 'es', stem + 's']
        elif stem.endswith('o'):          # goeth -> goes, doeth -> does
            cand = [stem + 'es']
        else:
            cand = [stem + 'es', stem + 's']   # cometh -> comes, worketh -> works
        best = max(cand, key=lambda c: counter.get(c, 0))
        if counter.get(best, 0) or len(cand) == 1:
            out[w] = best
    return out


ARCH = [(r'\bhath\b', 'has'), (r'\bHath\b', 'Has'), (r'\bdoth\b', 'does'), (r'\bDoth\b', 'Does'),
        (r'\bsaith\b', 'says'), (r'\bSaith\b', 'Says')]


def modernize(t, eth):
    for a, b in ARCH:
        t = re.sub(a, b, t)
    return re.sub(r'\b[a-z]+eth\b', lambda m: eth.get(m.group(0), m.group(0)), t)


# ---------- frasi ----------
ABBR = {'v', 'vv', 'ver', 'ch', 'chap', 'cap', 'viz', 'cf', 'ibid', 'dr', 'mr', 'mrs', 'st', 'mt', 'no', 'vol', 'p', 'pp',
        'i.e', 'e.g', 'ed', 'esp', 'ps', 'gen', 'exod', 'lev', 'num', 'deut', 'josh', 'judg', 'sam', 'chron', 'neh',
        'esth', 'prov', 'eccl', 'eccles', 'cant', 'isa', 'jer', 'lam', 'ezek', 'dan', 'hos', 'obad', 'mic', 'nah',
        'hab', 'zeph', 'hag', 'zech', 'mal', 'matt', 'rom', 'cor', 'gal', 'eph', 'phil', 'col', 'thess', 'tim',
        'tit', 'philem', 'heb', 'jam', 'pet', 'rev', 'jac', 'apoc', 'lib', 'sect', 'ep', 'op', 'comp', 'lat', 'gr',
        'heb', 'antiq', 'hist', 'b', 'c', 'l', 'ii', 'iii'}
MARK = re.compile(r'^[\(\[]?(?:\d{1,3}|[IVXLC]{1,6}|[ivxlc]{1,6})\.[\)\]]?$')
BOUND = re.compile(r'([.!?][\'"’”\)\]]*)(\s+)(?=[\'"‘“\(\[]?[A-Z0-9])')


def split_sentences(t):
    out, last = [], 0
    for m in BOUND.finditer(t):
        end = m.end(1)
        word = re.findall(r'\S+$', t[:m.start(1) + 1])
        w = word[0] if word else ''
        bare = w.rstrip('.!?\'"’”)]').lstrip('([\'"‘“').lower()
        prev = re.findall(r'(\S+)\s+\S+$', t[:m.start(1) + 1])
        pw = (prev[0] if prev else '').lower().rstrip(',')
        if t[m.start(1)] == '.':
            if not bare.endswith('&c') and (bare in ABBR or re.fullmatch(r'[a-z]', bare)):
                continue
            if MARK.match(w):
                # numero di schema («II.», «(1.)») all'inizio di una frase: non è la fine di una frase
                head = t[:m.start(1) + 1 - len(w)].rstrip()
                if pw.rstrip('.') not in ('v', 'vv', 'ver') and (not head or head[-1] in '.;:,!?)]—-'):
                    continue
        piece = t[last:end].strip()
        if piece:
            out.append(piece)
        last = m.end(2)
    rest = t[last:].strip()
    if rest:
        out.append(rest)
    # unisce i pezzi minimi (solo un numero di schema rimasto da solo)
    merged = []
    for s in out:
        if merged and (len(s) < 4 or MARK.match(merged[-1].split()[-1]) and len(merged[-1]) < 8):
            merged[-1] = merged[-1] + ' ' + s
        else:
            merged.append(s)
    return merged


def cut_long(s, lim=420):
    if len(s) <= lim:
        return [s]
    parts, cur = [], ''
    for c in re.split(r'(?<=;)\s+|(?<=:)\s+(?=[A-Z(\[])', s):
        if cur and len(cur) + len(c) + 1 > lim:
            parts.append(cur)
            cur = c
        else:
            cur = (cur + ' ' + c).strip()
    if cur:
        parts.append(cur)
    out = []
    for p in parts:
        if len(p) <= lim * 1.6:
            out.append(p)
            continue
        cur = ''
        for c in re.split(r'(?<=,)\s+', p):
            if cur and len(cur) + len(c) + 1 > lim:
                out.append(cur)
                cur = c
            else:
                cur = (cur + ' ' + c).strip()
        if cur:
            out.append(cur)
    return out


INLINE_MARK = re.compile(r'\s+(?=[\(\[]\d{1,3}\.[\)\]]\s)|(?<=[,;:])\s+(?=[IVX]{1,5}\.\s+[A-Z])')
LEAD_MARK = re.compile(r'^((?:[IVXLC]{1,6}|\d{1,3})\.|[\(\[]\d{1,3}\.[\)\]])\s+(?=\S)')


def segments(text):
    """Frasi da tradurre e numeri di schema («I.», «2.», «(1.)», «[2.]») tenuti da parte:
    il traduttore automatico a volte li perde, così si rimettono dopo."""
    segs, marks = [], []
    for line in text.split('\n'):          # la poesia tiene gli a capo
        line = line.strip()
        if not line:
            continue
        for s in split_sentences(line):
            for c in cut_long(s):
                for piece in INLINE_MARK.split(c):
                    piece = piece.strip()
                    if not piece:
                        continue
                    m = LEAD_MARK.match(piece)
                    mk = ''
                    if m:
                        mk, piece = m.group(1), piece[m.end():]
                    segs.append(piece)
                    marks.append(mk)
    return segs, marks


def main():
    src, out = sys.argv[1], sys.argv[2]
    segs_out = sys.argv[sys.argv.index('--segs') + 1] if '--segs' in sys.argv else None
    os.makedirs(out, exist_ok=True)
    books = {}
    counter = collections.Counter()
    for code in CODES:
        units = []
        for f in chapter_files(src, code):
            for u in json.load(open(f, encoding='utf-8'))['units']:
                units.append(u)
                if segs_out:
                    for p in u['paragraphs']:
                        counter.update(re.findall(r'[A-Za-z]+', p['text']))
        books[code] = units
    eth = make_eth_map(counter) if segs_out else {}
    seg_units = []
    stats = collections.Counter()
    for code, units in books.items():
        app = []
        for u in units:
            k = {'book': 'b', 'chapter': 'c', 'passage': 'p'}[u['kind']]
            title = NAME[code] if k == 'b' else (u.get('title') or '').strip()
            paras = [('# ' if p.get('heading') else '') + p['text'].strip() for p in u['paragraphs'] if p['text'].strip()]
            e = {'r': u['range'], 'k': k}
            if title:
                e['t'] = title
            e['p'] = paras
            app.append(e)
            stats['units'] += 1
            stats['paras'] += len(paras)
            if segs_out:
                sp = []
                for p in u['paragraphs']:
                    t = p['text'].strip()
                    if not t:
                        continue
                    pos = 0
                    for r in p.get('refs', []):
                        lab = it_label(r['ref'], r['text'])
                        i = t.find(r['text'], pos)
                        if i < 0:
                            continue
                        if lab:
                            t = t[:i] + lab + t[i + len(r['text']):]
                            pos = i + len(lab)
                            stats['refs'] += 1
                        else:
                            pos = i + len(r['text'])
                    t = modernize(t, eth)
                    head = bool(p.get('heading'))
                    ss, mk = segments(t)
                    stats['segs'] += len(ss)
                    stats['marks'] += sum(1 for x in mk if x)
                    sp.append({'h': head, 's': ss, 'm': mk})
                tt = segments(modernize(title, eth))[0] if (title and k != 'b') else []
                seg_units.append({'b': code, 'r': u['range'], 'k': k, 't': tt, 'tb': title if k == 'b' else '', 'p': sp})
        with open(os.path.join(out, code + '.json'), 'w', encoding='utf-8') as fh:
            json.dump({'b': code, 'u': app}, fh, ensure_ascii=False, separators=(',', ':'))
    if segs_out:
        os.makedirs(os.path.dirname(segs_out) or '.', exist_ok=True)
        with open(segs_out, 'w', encoding='utf-8') as fh:
            json.dump(seg_units, fh, ensure_ascii=False, separators=(',', ':'))
    print(dict(stats), 'eth', len(eth))


if __name__ == '__main__':
    main()
