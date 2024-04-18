# Generated by Django 5.0.4 on 2024-04-18 09:43

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("school_menu", "0003_school_season_choice_school_week_bias_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="school",
            name="menu_type",
            field=models.CharField(
                choices=[("S", "Semplice"), ("D", "Dettagliato")],
                default="D",
                max_length=1,
            ),
        ),
    ]
