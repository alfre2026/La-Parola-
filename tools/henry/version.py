#!/usr/bin/env python3
"""Scrive mh/version.json: un'impronta per ogni file di mh/it e mh/en.

L'app la confronta con quella dei libri già salvati sul telefono e riscarica quelli cambiati
(per esempio quando la traduzione con Claude sostituisce quella automatica).

Uso: version.py <cartella mh>
"""
import hashlib, json, os, sys, glob


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else 'mh'
    out = {}
    for lang in ('it', 'en'):
        out[lang] = {}
        for f in sorted(glob.glob(os.path.join(root, lang, '*.json'))):
            out[lang][os.path.basename(f)[:-5]] = hashlib.sha1(open(f, 'rb').read()).hexdigest()[:10]
    claude = 0
    for f in glob.glob(os.path.join(root, 'it', '*.json')):
        claude += sum(1 for u in json.load(open(f, encoding='utf-8'))['u'] if u.get('c'))
    out['claude'] = claude          # unità già tradotte con Claude
    with open(os.path.join(root, 'version.json'), 'w', encoding='utf-8') as fh:
        json.dump(out, fh, separators=(',', ':'))
    print('versioni scritte;', claude, 'unità tradotte con Claude')


if __name__ == '__main__':
    main()
