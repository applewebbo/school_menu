# Generated by Django 5.1.4 on 2024-12-24 10:39

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("school_menu", "0015_alter_detailedmeal_season_alter_simplemeal_season"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="detailedmeal",
            name="date",
        ),
        migrations.RemoveField(
            model_name="simplemeal",
            name="date",
        ),
        migrations.CreateModel(
            name="AnnualMeal",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "day",
                    models.SmallIntegerField(
                        choices=[
                            (1, "Lunedì"),
                            (2, "Martedì"),
                            (3, "Mercoledì"),
                            (4, "Giovedì"),
                            (5, "Venerdì"),
                        ],
                        default=1,
                    ),
                ),
                (
                    "week",
                    models.SmallIntegerField(
                        choices=[
                            (1, "Settimana 1"),
                            (2, "Settimana 2"),
                            (3, "Settimana 3"),
                            (4, "Settimana 4"),
                        ],
                        default=1,
                    ),
                ),
                (
                    "season",
                    models.SmallIntegerField(
                        blank=True,
                        choices=[(1, "Estivo"), (2, "Invernale")],
                        default=2,
                        null=True,
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("S", "Standard"),
                            ("G", "No Glutine"),
                            ("L", "No Lattosio"),
                            ("V", "Vegetariano"),
                            ("P", "Speciale"),
                        ],
                        default="S",
                        max_length=1,
                    ),
                ),
                ("menu", models.TextField(max_length=600)),
                ("snack", models.CharField(blank=True, max_length=200)),
                ("date", models.DateField()),
                (
                    "school",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="school_menu.school",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]