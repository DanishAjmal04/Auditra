from django.db import migrations


def create_rules(apps, schema_editor):
    from compliance.rules_catalogue import sync_rules

    sync_rules(apps.get_model('compliance', 'Rule'))


class Migration(migrations.Migration):

    dependencies = [
        ('compliance', '0008_rule_article_length'),
    ]

    operations = [
        migrations.RunPython(create_rules, migrations.RunPython.noop),
    ]
