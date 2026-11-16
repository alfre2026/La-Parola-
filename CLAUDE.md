# La Parola — istruzioni per Claude

App web installabile (PWA) per leggere la Bibbia, sottolineare, prendere appunti e preparare predicazioni.
Sito: https://alfre2026.github.io/La-Parola-/ — GitHub Pages dal ramo `main`, cartella principale.

## File
- `index.html` contiene tutto: stile, struttura e script (nessun file .js o .css separato).
- `manifest.json`, `service-worker.js`, icone `icon-192.png`, `icon-512.png`, `icon-maskable-512.png` (adattiva Android: disegno dentro l'80% centrale).
- Tutti i file stanno nella cartella principale e si richiamano con percorsi relativi: il sito vive in una sottocartella.

## Regole
- Dati in `localStorage` con le chiavi `lp_notes`, `lp_sermons`, `lp_comments`: non rinominarle, l'utente perderebbe i dati. Ogni nuova chiave con prefisso `lp_`.
- Sullo stesso indirizzo (alfre2026.github.io) ci sono altre app: il service worker elimina solo le cache che iniziano con `la-parola-`.
- Service worker: prima la rete (attesa massima 3 s), poi la copia salvata. Un file nuovo va aggiunto all'elenco `EXTRA`. Non serve cambiare il nome della cache a ogni modifica: l'app si aggiorna da sola alla riapertura.
- Niente `alert`, `confirm`, `prompt`: avvisi con `toast()`, conferme con il doppio tocco di `confirmed()`.
- Si usa dal telefono Android con Chrome. Il tocco su un pulsante annulla la selezione del testo: per questo l'ultima selezione valida resta memorizzata in `picked`.

## Prima di pubblicare
Prova in Chrome con schermo da telefono (circa 408×900, touch): nessun errore in console, sottolineatura e appunto su una selezione, salvataggio e modifica di una predicazione, apertura senza rete.

## Pubblicazione
Ramo `claude/...` → pull request con `gh api` (REST; `gh pr` qui non funziona) → unione in `main` con `gh api -X PUT repos/alfre2026/la-parola-/pulls/N/merge`. Pages si aggiorna in circa un minuto (controllo: `gh api repos/alfre2026/la-parola-/actions/runs`).

## Stato
Prototipo: testo biblico solo dimostrativo (Genesi 1:1-4), sottolineature visibili solo nell'elenco degli appunti, dei commentari si registra solo il nome del file, nessuna sincronizzazione tra dispositivi.
