# Generated by Django 5.1.4 on 2024-12-12 09:25

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        (
            "school_menu",
            "0012_school_no_gluten_school_no_lactose_school_special_and_more",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="detailedmeal",
            name="type",
            field=models.CharField(
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
        migrations.AlterField(
            model_name="simplemeal",
            name="type",
            field=models.CharField(
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
    ]
