from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0014_alter_anonymousmenunotification_options_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS webpush_pushinformation;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS webpush_subscriptioninfo;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS webpush_group;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
