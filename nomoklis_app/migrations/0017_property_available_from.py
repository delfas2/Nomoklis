# Generated migration for adding available_from field to Property

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nomoklis_app', '0016_remove_systemsettings_pricing_model_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='property',
            name='available_from',
            field=models.DateField(blank=True, help_text='Data, nuo kada objektas bus laisvas nuomai', null=True, verbose_name='Laisvas nuo'),
        ),
    ]
