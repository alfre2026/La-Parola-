#!/usr/bin/env python3
"""Traduzione automatica in italiano delle frasi di segs.json (scritto da build.py).

Modello: OPUS-MT «opus-mt-tc-big-en-it» (Helsinki-NLP, CC BY 4.0), convertito per CTranslate2.
Il lavoro è diviso in N blocchi contigui di peso simile: questo programma traduce il blocco k.

Uso: translate.py <segs.json> <cartella modello> <k> <N> <uscita.json> [--only "JHN.3 GEN.1"]
Uscita: {"<indice unità>": {"t": [frasi del titolo], "p": [[frasi del paragrafo], ...]}}
"""
import json, sys, time, os
import ctranslate2
import sentencepiece as spm


def chunk_of(sizes, n):
    total = sum(sizes) or 1
    out, acc = [], 0
    for s in sizes:
        out.append(min(n - 1, int(acc * n / total)))
        acc += s
    return out


def main():
    segs_path, model_dir, k, n, out_path = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
    only = sys.argv[sys.argv.index('--only') + 1].split() if '--only' in sys.argv else None
    S = json.load(open(segs_path, encoding='utf-8'))
    sizes = [sum(len(x) for p in u['p'] for x in p['s']) + sum(len(x) for x in u['t']) for u in S]
    owner = chunk_of(sizes, n)
    pick = [i for i, u in enumerate(S) if owner[i] == k]
    if only:
        pick = [i for i, u in enumerate(S) if any(u['r'] == o or u['r'].startswith(o + '.') for o in only)]
    texts = set()
    for i in pick:
        texts.update(S[i]['t'])
        for p in S[i]['p']:
            texts.update(p['s'])
    texts = sorted(texts, key=len)
    total_chars = sum(len(t) for t in texts)
    print(f'blocco {k}/{n}: {len(pick)} unità, {len(texts)} frasi, {total_chars} caratteri', flush=True)

    threads = os.cpu_count() or 4
    tr = ctranslate2.Translator(model_dir, device='cpu', compute_type='int8',
                                inter_threads=max(1, threads // 2), intra_threads=2)
    sp_s = spm.SentencePieceProcessor(model_file=os.path.join(model_dir, 'source.spm'))
    sp_t = spm.SentencePieceProcessor(model_file=os.path.join(model_dir, 'target.spm'))

    done, t0, last = {}, time.time(), 0
    B = 48
    batches = [texts[j:j + B] for j in range(0, len(texts), B)]
    chars = 0
    for bi, batch in enumerate(batches):
        toks = [sp_s.encode(t, out_type=str)[:400] + ['</s>'] for t in batch]
        res = tr.translate_batch(toks, beam_size=4, max_decoding_length=512, replace_unknowns=True,
                                 max_batch_size=24, batch_type='examples')
        for src, r in zip(batch, res):
            hyp = [x for x in r.hypotheses[0] if x not in ('</s>', '<pad>', '<s>')]
            done[src] = sp_t.decode(hyp).strip()
        chars += sum(len(t) for t in batch)
        now = time.time()
        if now - last > 60 or bi == len(batches) - 1:
            last = now
            el = now - t0
            rate = chars / el if el else 0
            eta = (total_chars - chars) / rate if rate else 0
            print(f'  {chars}/{total_chars} car. ({100 * chars / total_chars:.1f}%) · {rate:.0f} car/s · '
                  f'mancano {eta / 60:.0f} min', flush=True)

    out = {}
    for i in pick:
        u = S[i]
        out[str(i)] = {'t': [done[x] for x in u['t']], 'p': [[done[x] for x in p['s']] for p in u['p']]}
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(',', ':'))
    print(f'fatto in {(time.time() - t0) / 60:.1f} min', flush=True)


if __name__ == '__main__':
    main()
