# Generated by Django 5.0.6 on 2024-05-16 09:10

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("school_menu", "0006_alter_school_season_choice"),
    ]

    operations = [
        migrations.AddField(
            model_name="simplemeal",
            name="snack",
            field=models.CharField(default="-", max_length=200),
            preserve_default=False,
        ),
    ]
