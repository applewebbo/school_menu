# Generated by Django 4.1.2 on 2023-10-10 06:42

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("school_menu", "0005_alter_settings_options_settings_week_bias_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="meal",
            name="type",
            field=models.SmallIntegerField(
                choices=[
                    (1, "Standard"),
                    (2, "Gluten Free"),
                    (3, "Lactose Free"),
                    (4, "Vegan"),
                ],
                default=1,
            ),
        ),
    ]