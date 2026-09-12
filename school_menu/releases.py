"""Plain-language, per-release changelog shown on the public ``/releases`` page.

Newest first. Append one entry per release (the ``/release`` skill does this as
part of the workflow). Keep the notes non-technical Italian: 2-4 short bullet
points a parent would understand, condensed from the GitHub release notes — not
the raw commit list.
"""

from datetime import date

RELEASES: list[dict] = [
    {
        "version": "2026.2.7",
        "date": date(2026, 9, 12),
        "notes": [
            "Le pagine di accesso, registrazione e recupero password sono state uniformate e sono ora completamente in italiano.",
            "I messaggi di conferma (es. dopo la registrazione) appaiono ora in alto sullo schermo e sono più chiari.",
            "Migliorata la visibilità delle pagine delle scuole sui motori di ricerca, per trovarle più facilmente cercando su Google.",
            "Introdotta una pulizia automatica degli account creati ma mai confermati via email.",
        ],
    },
    {
        "version": "2026.2.6",
        "date": date(2026, 9, 10),
        "notes": [
            "Nuova pagina “Novità e aggiornamenti” con il riepilogo di ogni versione in parole semplici (è quella che stai leggendo).",
            "Gli avvisi via email in caso di problemi con il backup del database ora arrivano davvero al destinatario corretto.",
            "Migliorata la gestione dello spazio occupato dai backup e verificata la procedura di ripristino.",
        ],
    },
    {
        "version": "2026.2.5",
        "date": date(2026, 9, 9),
        "notes": [
            "Notifiche giornaliere più affidabili sui telefoni Android.",
            "Corretto un problema per cui la stessa notifica poteva arrivare due volte.",
            "Aggiunto un controllo interno che verifica ogni giorno che le notifiche siano partite.",
        ],
    },
    {
        "version": "2026.2.4",
        "date": date(2026, 9, 9),
        "notes": [
            "Risolto l'errore che impediva di confermare l'importazione di un menu annuale.",
            "La pagina di accesso ora mostra un messaggio quando email o password non sono corrette.",
            "Anche la pagina di registrazione segnala gli errori del modulo.",
            "Aggiornate le librerie di sistema.",
        ],
    },
    {
        "version": "2026.2.3",
        "date": date(2026, 9, 8),
        "notes": [
            "Prima di salvare, l'importazione da CSV mostra una pagina di revisione dove correggere le righe.",
            "La tabella di revisione è divisa in pagine da 20 righe per gestire meglio i menu lunghi.",
            "Corretto l'errore che bloccava la pagina di reimpostazione della password aperta dall'email.",
        ],
    },
    {
        "version": "2026.2.2",
        "date": date(2026, 8, 16),
        "notes": [
            "L'esito dell'importazione con l'assistente AI viene mostrato una sola volta.",
            "Corretta la lettura dei file CSV con caratteri speciali; gli errori tecnici rimandano a un codice di assistenza.",
            "Dopo la conferma di un'importazione si torna correttamente alla pagina del menu.",
        ],
    },
    {
        "version": "2026.2.1",
        "date": date(2026, 8, 14),
        "notes": [
            "Chiuse tre falle di sicurezza che potevano esporre le impostazioni di altre scuole o dirottare le iscrizioni alle notifiche.",
            "La pagina di anteprima dell'importazione AI ora è utilizzabile anche da telefono.",
            "Rimosso il codice di Facebook che veniva caricato su ogni pagina.",
            "Corretto un problema di pubblicazione che poteva mostrare il sito con uno stile non aggiornato.",
        ],
    },
    {
        "version": "2026.2",
        "date": date(2026, 8, 13),
        "notes": [
            "Novità: importazione del menu assistita dall'AI. Si carica il file così com'è (PDF, foglio di calcolo, CSV con intestazioni diverse) e viene interpretato in automatico.",
            "Prima di salvare si vede un'anteprima modificabile: niente viene scritto finché non si conferma.",
            "L'importazione riconosce la stagione e il tipo di menu e segnala se il file non corrisponde.",
            "L'importazione da un CSV già valido resta invariata e non consuma crediti.",
        ],
    },
    {
        "version": "2026.1.9",
        "date": date(2026, 8, 11),
        "notes": [
            "Connessione sempre protetta (HTTPS) e cookie più sicuri.",
            "Aggiornamento dei componenti interni del sito.",
        ],
    },
    {
        "version": "2026.1.8",
        "date": date(2026, 8, 1),
        "notes": [
            "Risolto un errore che in alcuni casi impediva l'accesso al sito.",
            "Spostamento del progetto su GitHub, con storico e segnalazioni conservati.",
        ],
    },
]
