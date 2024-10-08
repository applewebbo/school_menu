# Generated by Django 5.0.4 on 2024-05-02 06:40

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("school_menu", "0005_alter_simplemeal_menu"),
    ]

    operations = [
        migrations.AlterField(
            model_name="school",
            name="season_choice",
            field=models.SmallIntegerField(
                choices=[(1, "Primaverile"), (2, "Invernale"), (3, "AUTOMATICA")],
                default=3,
                verbose_name="stagione",
            ),
        ),
    ]
