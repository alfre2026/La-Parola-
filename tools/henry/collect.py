#!/usr/bin/env python3
"""Riunisce i blocchi tradotti (translate.py) nei file dell'app: mh/it/<LIBRO>.json.

Uso: collect.py <segs.json> <cartella dei blocchi> <cartella di uscita> [--pilot <file.json>]
Con --pilot scrive invece un solo file di prova, con inglese e italiano affiancati.
"""
import json, os, re, sys, glob


def tidy(t):
    t = re.sub(r'\s+([,.;:!?)\]])', r'\1', t)
    t = re.sub(r'([(\[])\s+', r'\1', t)
    t = re.sub(r'\s{2,}', ' ', t)
    return t.strip()


def main():
    segs_path, chunks_dir, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    pilot = sys.argv[sys.argv.index('--pilot') + 1] if '--pilot' in sys.argv else None
    S = json.load(open(segs_path, encoding='utf-8'))
    T = {}
    for f in sorted(glob.glob(os.path.join(chunks_dir, '**', '*.json'), recursive=True)):
        T.update(json.load(open(f, encoding='utf-8')))
    books, missing = {}, 0
    for i, u in enumerate(S):
        tr = T.get(str(i))
        if tr is None:
            missing += 1
            continue
        e = {'r': u['r'], 'k': u['k']}
        title = u['tb'] if u['k'] == 'b' else tidy(' '.join(tr['t']))
        if title:
            e['t'] = title
        paras = []
        for src, segs in zip(u['p'], tr['p']):
            t = tidy(' '.join(segs))
            if t:
                paras.append(('# ' if src['h'] else '') + t)
        e['p'] = paras
        if pilot:
            e['en'] = [' '.join(p['s']) for p in u['p']]
        books.setdefault(u['b'], []).append(e)
    if pilot:
        with open(pilot, 'w', encoding='utf-8') as fh:
            json.dump(books, fh, ensure_ascii=False, indent=1)
        print('prova scritta:', pilot, sum(len(v) for v in books.values()), 'unità')
        return
    os.makedirs(out_dir, exist_ok=True)
    for b, units in books.items():
        with open(os.path.join(out_dir, b + '.json'), 'w', encoding='utf-8') as fh:
            json.dump({'b': b, 'lang': 'it', 'u': units}, fh, ensure_ascii=False, separators=(',', ':'))
    print(len(books), 'libri,', sum(len(v) for v in books.values()), 'unità; mancanti:', missing)
    if missing:
        sys.exit(1)


if __name__ == '__main__':
    main()
