#!/usr/bin/env python3
"""Ritocchi alla traduzione italiana (mh/it) confrontandola con l'originale (mh/en).

- Date dei titoli: «(b. c. 1491.)» -> «(1491 a.C.)», «(a. d. 58.)» -> «(58 d.C.)»
  (il traduttore automatico le rendeva in modi diversi, a volte sbagliati).
- Spazi prima della punteggiatura.

Uso: fix_it.py <mh/en> <mh/it>
"""
import json, os, re, sys, glob

DATE = re.compile(r'\s*\(\s*(b|a)\.\s*([cd])\.\s*(\d{1,4})\.?\s*\)\s*$', re.I)
TAIL = re.compile(r'\s*\([^()]*\d[^()]*\)\s*$')


def tidy(t):
    t = re.sub(r'\s+([,.;:!?)\]])', r'\1', t)
    t = re.sub(r'([(\[])\s+', r'\1', t)
    return re.sub(r'\s{2,}', ' ', t).strip()


def fix_title(en, it):
    m = DATE.search((en or '').replace('\xa0', ' '))
    if not m or not it:
        return it
    era = 'a.C.' if m.group(1).lower() == 'b' else 'd.C.'
    base = TAIL.sub('', it).rstrip()
    return f'{base} ({m.group(3)} {era})'


def main():
    en_dir, it_dir = sys.argv[1], sys.argv[2]
    n = 0
    for f in sorted(glob.glob(os.path.join(it_dir, '*.json'))):
        it = json.load(open(f, encoding='utf-8'))
        en = json.load(open(os.path.join(en_dir, os.path.basename(f)), encoding='utf-8'))
        by_r = {u['r']: u for u in en['u']}
        for u in it['u']:
            e = by_r.get(u['r'])
            if e and u.get('t') and u['k'] == 'p':
                t = fix_title(e.get('t'), u['t'])
                if t != u['t']:
                    u['t'] = t
                    n += 1
            u['p'] = [tidy(p) for p in u['p']]
        with open(f, 'w', encoding='utf-8') as fh:
            json.dump(it, fh, ensure_ascii=False, separators=(',', ':'))
    print('titoli corretti:', n)


if __name__ == '__main__':
    main()
