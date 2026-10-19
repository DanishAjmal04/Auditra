from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compliance', '0002_unify_auditra_users'),
    ]

    operations = [
        migrations.AddField(
            model_name='dporecord',
            name='organization_name',
            field=models.CharField(default='Auditra Organization', max_length=200),
        ),
        migrations.AddField(
            model_name='dporecord',
            name='dpo_required',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='dporecord',
            name='name',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AlterField(
            model_name='dporecord',
            name='contact',
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AlterField(
            model_name='dporecord',
            name='designated_at',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='dporecord',
            name='scope',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='dporecord',
            name='independent',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='dporecord',
            name='direct_access_to_management',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='dporecord',
            name='conflict_free',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='dporecord',
            name='published_contact_details',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='dporecord',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
