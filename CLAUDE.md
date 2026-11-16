# La Parola — istruzioni per Claude

App web installabile (PWA) per leggere la Bibbia, sottolineare, prendere appunti e preparare predicazioni.
Sito: https://alfre2026.github.io/La-Parola-/ — GitHub Pages dal ramo `main`, cartella principale.

## File
- `index.html` contiene tutto: stile, struttura e script (nessun file .js o .css separato).
- `manifest.json`, `service-worker.js`, icone `icon-192.png`, `icon-512.png`, `icon-maskable-512.png` (adattiva Android: disegno dentro l'80% centrale).
- Tutti i file stanno nella cartella principale e si richiamano con percorsi relativi: il sito vive in una sottocartella.

## Regole
- Dati: il testo biblico (circa 4 MB) e i dati dell'utente stanno in IndexedDB (database `laparola`, chiavi `data`, `comms`, `bible:<id>`), perché localStorage è troppo piccolo; se IndexedDB non c'è si ripiega su localStorage con chiavi `lp_data`, `lp_comms`. Le vecchie chiavi del prototipo `lp_notes`, `lp_sermons`, `lp_comments` NON vanno rinominate né cancellate: all'avvio `migrateLegacy()` ne importa predicazioni e appunti una sola volta. Ogni nuova chiave localStorage con prefisso `lp_`. Non cambiare i nomi di database e chiavi: l'utente perderebbe i dati.
- Sullo stesso indirizzo (alfre2026.github.io) ci sono altre app: il service worker elimina solo le cache che iniziano con `la-parola-`.
- Service worker: prima la rete (attesa massima 3 s), poi la copia salvata. Un file nuovo va aggiunto all'elenco `EXTRA`. Non serve cambiare il nome della cache a ogni modifica: l'app si aggiorna da sola alla riapertura.
- Niente `alert`, `confirm`, `prompt`: avvisi con `toast()`, conferme con il doppio tocco di `confirmed()`.
- Si usa dal telefono Android con Chrome. Il tocco su un pulsante annulla la selezione del testo: per questo l'ultima selezione valida resta memorizzata in `picked`.

## Prima di pubblicare
Prova in Chrome con schermo da telefono (circa 408×900, touch): nessun errore in console, sottolineatura e appunto su una selezione, salvataggio e modifica di una predicazione, apertura senza rete.

## Pubblicazione
Ramo `claude/...` → pull request con `gh api` (REST; `gh pr` qui non funziona) → unione in `main` con `gh api -X PUT repos/alfre2026/la-parola-/pulls/N/merge`. Pages si aggiorna in circa un minuto (controllo: `gh api repos/alfre2026/la-parola-/actions/runs`).

## Stato
Versione completa (nov. 2026): lettore a capitoli con testo biblico scaricabile (Riveduta 2020 da GitHub, una volta sola) o importabile da file (JSON o «Giovanni 3:16 testo», per la NR06); menu su ogni versetto (il tocco vale anche nello spazio tra le righe); 12 colori pastello; evidenziatore a pennarello: tratti SVG per riga (funzione `drawInk`, filtro `#inkrough`, sovrapposti al testo in `multiply`), per versetto intero o per parole (doppio tocco su una parola, un altro tocco per estendere); note con icona accanto al versetto; trasferimento dei versetti nei sermoni (punti numerati, vista «Predica»); commentari importati da testo/file con riferimenti riconosciuti in automatico e associabili a mano ai versetti; ricerca, segnalibri, backup JSON.
Aspetto: carta con grana e leggere macchie (sfondo SVG su `html.t-carta`; il tema è la classe `t-carta`/`t-chiaro`/`t-scuro` sull'elemento `html`); testo biblico in EB Garamond, scrittura dell'utente (note, punti dei sermoni) in Kalam con inchiostro blu su righe; i caratteri sono incorporati in base64 in `index.html` (nessun file esterno). Il testo NR06 non è nel repository (copyright). Nessuna sincronizzazione tra dispositivi.
