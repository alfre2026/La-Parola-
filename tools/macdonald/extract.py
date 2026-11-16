"""Estrae dal PDF del commentario di MacDonald (AT, CLV 2013) le righe in ordine di lettura
(due colonne, fasce a tutta pagina), con lo stile di ogni pezzo (grassetto, corsivo, apice).

Uso:  pip install pymupdf;  python3 extract.py AT.pdf righe.jsonl
Poi build.py costruisce il JSON da importare nell'app."""
import sys, json, re, pymupdf

FIGURE_FONTS = ('Arial', 'PlatinumBg', 'HSGrotesk', 'MyriadPro', 'Candara', 'SimSun')
MID_L, MID_R = 209.0, 218.0          # la colonna sinistra finisce a ~206, la destra inizia a ~221

def span_style(s):
    f = s['font']
    bold = 'Bold' in f or 'Semibold' in f or bool(s['flags'] & 16)
    ital = 'Italic' in f or 'BoldIt' in f or f.endswith('It') or bool(s['flags'] & 2)
    sup = bool(s['flags'] & 1) and s['size'] < 7.5
    return bold, ital, sup

def clean_chars(chars):
    """Toglie gli spazi spuri: dopo le legature (fi, ff, ffi, fl, ffl) hanno l'origine più a sinistra
    dell'ultimo carattere scritto; altri hanno larghezza nulla (il carattere dopo parte dallo stesso punto)."""
    out, maxo = [], -1e9
    n = len(chars)
    for k, c in enumerate(chars):
        o = c['origin'][0]
        if c['c'] in (' ', '\u00a0'):
            if o < maxo - 0.3:
                continue
            nxt = next((x for x in chars[k + 1:] if x['c'] not in (' ', '\u00a0')), None)
            prv = chars[k - 1] if k > 0 else None
            if (nxt is not None and prv is not None and nxt['origin'][0] - o < 0.5 and out and out[-1] not in (' ', '\u00a0')
                    and nxt['origin'][0] - prv['bbox'][2] < 0.8 and prv['c'].isalpha() and nxt['c'].isalpha()):
                continue                      # spazio di larghezza nulla in mezzo a una parola
        out.append(c['c'])
        if c['c'] not in (' ', '\u00a0'):
            maxo = max(maxo, o)
    return ''.join(out)


def page_lines(page):
    d = page.get_text('rawdict')
    lines = []
    for b in d['blocks']:
        if b['type'] != 0:
            continue
        for l in b['lines']:
            spans = []
            prev_raw = None
            for s in l['spans']:
                t = clean_chars(s['chars'])
                raw = s
                if not t:
                    continue
                if s['font'].startswith(FIGURE_FONTS):
                    prev_raw = None
                    continue
                bold, ital, sup = span_style(s)
                if s['size'] < 9.3 and not sup:
                    # maiuscoletto: «S» + «IGNORE» in corpo minore, attaccato alla maiuscola
                    if (spans and prev_raw is not None and re.fullmatch(r"[A-ZÀ-Ý’'.\- ]+", t.strip() or '-')
                            and spans[-1]['t'].rstrip()[-1:].isupper() and abs(s['bbox'][0] - prev_raw['bbox'][2]) < 1.5):
                        spans[-1] = dict(spans[-1], t=spans[-1]['t'] + t)
                        prev_raw = raw
                    continue
                spans.append({'t': t, 'b': bold, 'i': ital, 'sup': sup, 'sz': round(s['size'], 1), 'f': s['font'], 'x': round(s['bbox'][0], 1)})
                prev_raw = raw
            if not spans or not ''.join(x['t'] for x in spans).strip():
                continue
            x0, y0, x1, y1 = l['bbox']
            lines.append({'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1, 'spans': spans})
    return lines

def merge_same_baseline(lines):
    """Unisce i pezzi della stessa riga (stessa colonna, stessa y) spezzati in più 'line'."""
    lines.sort(key=lambda l: (round(l['y0']), l['x0']))
    out = []
    for l in lines:
        if out:
            p = out[-1]
            across_gutter = p['x1'] <= MID_L + 1 and l['x0'] >= MID_R - 1
            if abs(p['y0'] - l['y0']) < 2.5 and abs(p['y1'] - l['y1']) < 3.5 and not across_gutter and l['x0'] >= p['x1'] - 1 and l['x0'] - p['x1'] < 40:
                gap = l['x0'] - p['x1']
                if gap > 1.0 and not p['spans'][-1]['t'].endswith(' ') and not l['spans'][0]['t'].startswith(' ') and not l['spans'][0]['sup']:
                    p['spans'][-1] = dict(p['spans'][-1], t=p['spans'][-1]['t'] + ' ')
                p['spans'].extend(l['spans']); p['x1'] = max(p['x1'], l['x1']); p['y1'] = max(p['y1'], l['y1'])
                continue
        out.append(l)
    return out

def join_table_cells(lines):
    """Celle di una piccola tabella sulla stessa riga (es. ISRAELE | GIUDA): una riga sola, separate da «—»."""
    lines.sort(key=lambda l: (round(l['y0']), l['x0']))
    out = []
    for l in lines:
        if out:
            p = out[-1]
            same_col = (p['x1'] <= MID_R and l['x1'] <= MID_R) or (p['x0'] >= MID_L and l['x0'] >= MID_L)
            if (same_col and abs(p['y0'] - l['y0']) < 2.5 and 30 <= l['x0'] - p['x1'] <= 150
                    and l['x1'] - l['x0'] < 100 and p['x1'] - p['x0'] < 160
                    and not any(s['sup'] for s in l['spans'])):
                p['spans'] = p['spans'] + [dict(l['spans'][0], t=' — ', b=False, i=False, sup=False)] + l['spans']
                p['x1'] = l['x1']
                continue
        out.append(l)
    return out


def attach_sups(lines):
    """Numeri di nota stampati come riga a sé (apice): li inserisco nella riga di testo che li contiene."""
    sups = [l for l in lines if all(s['sup'] for s in l['spans'])]
    rest = [l for l in lines if not all(s['sup'] for s in l['spans'])]
    for s in sups:
        best, bd = None, 1e9
        for h in rest:
            if not (h['y0'] - 4 <= s['y0'] <= h['y1'] and h['x0'] - 2 <= s['x0'] <= h['x1'] + 12):
                continue
            d = abs((h['y0'] + h['y1']) / 2 - (s['y0'] + s['y1']) / 2)
            if d < bd:
                best, bd = h, d
        if best is None:
            continue                       # apice dentro una figura
        for sp in s['spans']:
            k = len(best['spans'])
            while k > 0 and best['spans'][k - 1].get('x', 0) > sp['x']:
                k -= 1
            best['spans'].insert(k, sp)
        best['x1'] = max(best['x1'], s['x1'])
    return rest


def order_page(lines):
    """Ordine di lettura: fasce separate dalle righe a tutta pagina; in ogni fascia
    prima la colonna sinistra, poi la destra. Una riga corta subito sotto un blocco
    a tutta pagina (ultima riga di una citazione, firma) e senza una riga accanto
    nell'altra colonna appartiene al blocco."""
    for l in lines:
        if l['x1'] <= MID_R:
            l['col'] = 'L'
        elif l['x0'] >= MID_L:
            l['col'] = 'R'
        else:
            l['col'] = 'F'
    lines.sort(key=lambda l: (l['y0'], l['x0']))
    changed = True
    while changed:
        changed = False
        for i, l in enumerate(lines):
            if l['col'] != 'F':
                continue
            for m in lines[i + 1:]:
                if m['y0'] - l['y0'] > 13.5:
                    break
                if m['col'] == 'F' or m['y0'] - l['y0'] < 6:
                    continue
                other = [n for n in lines if n is not m and n['col'] in ('L', 'R') and n['col'] != m['col'] and abs(n['y0'] - m['y0']) < 6]
                if not other:
                    m['col'] = 'F'; changed = True
                break
    # righe brevi subito sopra un blocco a tutta pagina (titoli come NOTE), staccate dal testo
    # della loro colonna e senza nulla accanto nell'altra colonna
    changed = True
    while changed:
        changed = False
        for i, l in enumerate(lines):
            if l['col'] != 'F':
                continue
            above = [m for m in lines if m['col'] in ('L', 'R') and 0 < l['y0'] - m['y1'] <= 30]
            if not above:
                continue
            m = max(above, key=lambda m: m['y0'])
            same = [n for n in lines if n is not m and n['col'] == m['col'] and n['y1'] <= m['y0'] + 1]
            prev = max(same, key=lambda n: n['y0']) if same else None
            if prev is not None and m['y0'] - prev['y1'] < 12:
                continue
            other = [n for n in lines if n['col'] in ('L', 'R') and n['col'] != m['col'] and n['y1'] > m['y0'] - 6 and n['y0'] < l['y0']]
            if other:
                continue
            m['col'] = 'F'; changed = True
    lines.sort(key=lambda l: (l['y0'], l['x0']))
    out, band = [], []
    def flush():
        band.sort(key=lambda l: (0 if l['col'] == 'L' else 1, l['y0'], l['x0']))
        out.extend(band); band.clear()
    for l in lines:
        if l['col'] == 'F':
            flush(); out.append(l)
        else:
            band.append(l)
    flush()
    return out

def main(pdf, out):
    doc = pymupdf.open(pdf)
    with open(out, 'w', encoding='utf-8') as fo:
        for pno in range(len(doc)):
            page = doc[pno]
            H = page.rect.height
            ls = page_lines(page)
            keep = []
            for l in ls:
                txt = ''.join(s['t'] for s in l['spans']).strip()
                if l['y1'] < 42:                                   # testatina
                    continue
                if l['y0'] > 580 and re.fullmatch(r'[0-9IVXLC]+', txt):   # numero di pagina
                    continue
                keep.append(l)
            keep = order_page(join_table_cells(attach_sups(merge_same_baseline(keep))))
            for l in keep:
                fo.write(json.dumps({'p': pno + 1, 'col': l['col'], 'x0': round(l['x0'], 1), 'x1': round(l['x1'], 1),
                                     'y0': round(l['y0'], 1), 'y1': round(l['y1'], 1), 'spans': l['spans']}, ensure_ascii=False) + '\n')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
