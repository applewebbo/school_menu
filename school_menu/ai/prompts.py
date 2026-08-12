"""
Prompts for the AI menu import (#234).

Written in Italian because the files are Italian school menus: asking in the language of
the document keeps the dish names untouched instead of half-translated.

The prompt only asks for what cannot be fixed by rule. Accents, ordering, duplicates and
field lengths are handled deterministically in `normalise`, so there is no point spending
tokens insisting on them here.
"""

from school_menu.ai.normalise import MAX_WEEK, MIN_WEEK, WEEKDAYS
from school_menu.models import MenuImportDraft

BASE = """
Sei un assistente che estrae il menu di una mensa scolastica italiana da un documento.
Rispondi esclusivamente con un oggetto JSON conforme allo schema richiesto, senza testo
di accompagnamento e senza blocchi di codice.

Regole generali:
- riporta i piatti con le parole usate nel documento, senza riscriverli o tradurli;
- non inventare nulla: se un campo non compare nel documento lascialo come stringa vuota;
- ignora intestazioni, note, allergeni, tabelle nutrizionali e loghi;
- se il documento contiene piu' menu (ad esempio per fasce di eta' diverse), estrai solo
  quello principale.
"""

WEEKLY = """
Il menu e' settimanale e ruota su piu' settimane. Restituisci una riga per ogni giorno
di ogni settimana, con questi campi:
- "giorno": uno tra {days};
- "settimana": il numero della settimana di rotazione, da {min_week} a {max_week};
{columns}

Se il documento non indica il numero della settimana ma contiene un solo menu
settimanale, usa {min_week}. Non includere sabato e domenica.
"""

SIMPLE_COLUMNS = """- "pranzo": il menu del pranzo, con i piatti separati da una virgola;
- "spuntino": lo spuntino del mattino;
- "merenda": la merenda del pomeriggio."""

DETAILED_COLUMNS = """- "primo": il primo piatto;
- "secondo": il secondo piatto;
- "contorno": il contorno;
- "frutta": la frutta o il dessert;
- "spuntino": lo spuntino o la merenda."""

ANNUAL = """
Il menu e' annuale: ogni voce e' legata a una data precisa. Restituisci una riga per ogni
giorno indicato nel documento, con questi campi:
- "data": la data nel formato GG/MM/AAAA;
- "primo": il primo piatto;
- "secondo": il secondo piatto;
- "contorno": il contorno;
- "frutta": la frutta o il dessert;
- "altro": eventuali altre voci (pane, spuntino, merenda).

Se l'anno non e' scritto accanto alla data, ricavalo dall'anno scolastico indicato nel
documento. Non includere sabato e domenica.
"""


def build_system_instruction(kind):
    """The instruction sent alongside the file, tailored to the school's menu type."""
    if kind == MenuImportDraft.Kinds.ANNUAL:
        specific = ANNUAL
    else:
        columns = (
            DETAILED_COLUMNS
            if kind == MenuImportDraft.Kinds.DETAILED
            else SIMPLE_COLUMNS
        )
        specific = WEEKLY.format(
            days=", ".join(WEEKDAYS),
            min_week=MIN_WEEK,
            max_week=MAX_WEEK,
            columns=columns,
        )
    return f"{BASE.strip()}\n{specific.strip()}"
