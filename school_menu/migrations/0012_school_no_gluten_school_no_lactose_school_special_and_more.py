# Generated by Django 5.1.4 on 2024-12-10 14:01

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("school_menu", "0011_alter_simplemeal_afternoon_snack_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="school",
            name="no_gluten",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="school",
            name="no_lactose",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="school",
            name="special",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="school",
            name="vegetarian",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="detailedmeal",
            name="type",
            field=models.SmallIntegerField(
                choices=[
                    (1, "Standard"),
                    (2, "Gluten Free"),
                    (3, "Lactose Free"),
                    (4, "Vegetarian"),
                    (5, "Special"),
                ],
                default=1,
            ),
        ),
        migrations.AlterField(
            model_name="simplemeal",
            name="type",
            field=models.SmallIntegerField(
                choices=[
                    (1, "Standard"),
                    (2, "Gluten Free"),
                    (3, "Lactose Free"),
                    (4, "Vegetarian"),
                    (5, "Special"),
                ],
                default=1,
            ),
        ),
    ]
