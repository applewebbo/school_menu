from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from tablib import Dataset

from school_menu.models import DetailedMeal, School, SimpleMeal
from school_menu.resources import DetailedMealResource, SimpleMealResource
from school_menu.utils import validate_dataset

User = get_user_model()


class Command(BaseCommand):
    help = "Interactively import a CSV menu file for a school"

    def _prompt_choice(self, prompt, choices):
        """Display numbered choices and return the selected value."""
        for i, (label, _) in enumerate(choices, 1):
            self.stdout.write(f"  {i}. {label}")
        while True:
            raw = input(f"{prompt} [1-{len(choices)}]: ").strip()
            if raw.isdigit() and 1 <= int(raw) <= len(choices):
                return choices[int(raw) - 1][1]
            self.stdout.write(
                self.style.WARNING(f"Inserisci un numero tra 1 e {len(choices)}.")
            )

    def _prompt_yes_no(self, prompt):
        while True:
            raw = input(f"{prompt} [s/n]: ").strip().lower()
            if raw in ("s", "si", "sì", "y", "yes"):
                return True
            if raw in ("n", "no"):
                return False
            self.stdout.write(self.style.WARNING("Rispondi con s o n."))

    def handle(self, *args, **kwargs):
        # --- Selezione scuola ---
        schools = list(School.objects.select_related("user").order_by("name"))
        if not schools:
            raise CommandError("Nessuna scuola trovata nel database.")

        self.stdout.write("\n=== IMPORTAZIONE MENU CSV ===\n")
        self.stdout.write("Scuole disponibili:")
        school_choices = [(f"{s.name} ({s.city}) - {s.user.email}", s) for s in schools]
        for i, (label, _) in enumerate(school_choices, 1):
            self.stdout.write(f"  {i}. {label}")
        while True:
            raw = input(f"Seleziona la scuola [1-{len(school_choices)}]: ").strip()
            if raw.isdigit() and 1 <= int(raw) <= len(school_choices):
                school = school_choices[int(raw) - 1][1]
                break
            self.stdout.write(
                self.style.WARNING(
                    f"Inserisci un numero tra 1 e {len(school_choices)}."
                )
            )

        self.stdout.write(f"\nScuola selezionata: {self.style.SUCCESS(school.name)}")
        self.stdout.write(f"Tipo menu: {school.get_menu_type_display()}\n")

        menu_type = school.menu_type

        # --- Stagione ---
        self.stdout.write("Stagione:")
        season_choices = [
            ("Estivo", SimpleMeal.Seasons.ESTIVO),
            ("Invernale", SimpleMeal.Seasons.INVERNALE),
        ]
        season = self._prompt_choice("Seleziona la stagione", season_choices)

        # --- Tipo alternativo ---
        self.stdout.write("\nTipo di menu:")
        type_choices = [("Standard", DetailedMeal.Types.STANDARD)]
        if school.no_gluten:
            type_choices.append(("Senza glutine", DetailedMeal.Types.GLUTEN_FREE))
        if school.no_lactose:
            type_choices.append(("Senza lattosio", DetailedMeal.Types.LACTOSE_FREE))
        if school.vegetarian:
            type_choices.append(("Vegetariano", DetailedMeal.Types.VEGETARIAN))
        if school.special:
            type_choices.append(("Speciale", DetailedMeal.Types.SPECIAL))
        meal_type = self._prompt_choice("Seleziona il tipo", type_choices)

        # --- Percorso file ---
        while True:
            csv_path = input("\nPercorso del file CSV: ").strip().strip("'\"")
            try:
                with open(csv_path, encoding="utf-8") as f:
                    content = f.read()
                break
            except FileNotFoundError:
                self.stdout.write(self.style.ERROR(f"File non trovato: {csv_path}"))
            except OSError as e:
                self.stdout.write(
                    self.style.ERROR(f"Errore nella lettura del file: {e}")
                )

        # --- Caricamento e validazione dataset ---
        dataset = Dataset()
        dataset.load(content, format="csv")
        validates, message, filtered_dataset = validate_dataset(dataset, menu_type)

        if not validates:
            raise CommandError(f"Validazione fallita: {message}")

        self.stdout.write(
            self.style.SUCCESS(f"\nFile valido: {len(filtered_dataset)} righe trovate.")
        )

        # --- Riepilogo ---
        season_label = "Estivo" if season == SimpleMeal.Seasons.ESTIVO else "Invernale"
        self.stdout.write("\n--- RIEPILOGO ---")
        self.stdout.write(f"  Scuola:   {school.name} ({school.city})")
        self.stdout.write(f"  Stagione: {season_label}")
        self.stdout.write(f"  Tipo:     {meal_type}")
        self.stdout.write(f"  File:     {csv_path}")
        self.stdout.write(f"  Righe:    {len(filtered_dataset)}")

        # --- Conta record esistenti ---
        if menu_type == School.Types.SIMPLE:
            ModelClass = SimpleMeal
            resource = SimpleMealResource()
        else:
            ModelClass = DetailedMeal
            resource = DetailedMealResource()

        existing_count = ModelClass.objects.filter(
            school=school, season=season, type=meal_type
        ).count()

        overwrite = False
        if existing_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"\nAttenzione: esistono già {existing_count} voci per questa configurazione."
                )
            )
            overwrite = self._prompt_yes_no("Vuoi sovrascrivere i dati esistenti?")
            if not overwrite:
                raise CommandError("Importazione annullata dall'utente.")

        if not self._prompt_yes_no("\nProcedere con l'importazione?"):
            raise CommandError("Importazione annullata dall'utente.")

        # --- Dry run ---
        result = resource.import_data(
            filtered_dataset, dry_run=True, school=school, season=season, type=meal_type
        )
        if result.has_errors():
            raise CommandError(
                "Errori rilevati durante il dry run. Importazione annullata."
            )

        # --- Cancellazione record esistenti se richiesta ---
        if overwrite and existing_count > 0:
            ModelClass.objects.filter(
                school=school, season=season, type=meal_type
            ).delete()
            self.stdout.write(f"Eliminati {existing_count} record esistenti.")

        # --- Import effettivo ---
        resource.import_data(
            filtered_dataset,
            dry_run=False,
            school=school,
            season=season,
            type=meal_type,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ Importazione completata: {len(filtered_dataset)} righe importate."
            )
        )
