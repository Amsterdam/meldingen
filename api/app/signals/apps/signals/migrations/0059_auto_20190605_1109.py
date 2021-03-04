# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2019 - 2021 Gemeente Amsterdam
# Generated by Django 2.1.7 on 2019-06-05 09:09

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('signals', '0058_service_promise_for_ovl'),
    ]

    operations = [
        migrations.DeleteModel(
            name='MainCategory',
        ),
        migrations.AlterModelOptions(
            name='attachment',
            options={
                'ordering': ('created_at',)
            },
        ),
        migrations.AlterModelOptions(
            name='categorytranslation',
            options={
                'verbose_name': 'categorie omzetting',
                'verbose_name_plural': 'categorie omzettingen'
            },
        ),
        migrations.AlterModelOptions(
            name='statusmessagetemplate',
            options={
                'ordering': ('category', 'state', 'order'),
                'verbose_name': 'Standaard afmeldtekst',
                'verbose_name_plural': 'Standaard afmeldteksten'
            },
        ),
        migrations.RemoveField(
            model_name='signal',
            name='image',
        ),
        migrations.AlterField(
            model_name='attachment',
            name='_signal',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='attachments',
                to='signals.Signal'
            ),
        ),
        migrations.AlterField(
            model_name='statusmessagetemplate',
            name='state',
            field=models.CharField(
                choices=[
                    ('m', 'Gemeld'),
                    ('i', 'In afwachting van behandeling'),
                    ('b', 'In behandeling'),
                    ('h', 'On hold'),
                    ('ingepland', 'Ingepland'),
                    ('ready to send', 'Te verzenden naar extern systeem'),
                    ('o', 'Afgehandeld'),
                    ('a', 'Geannuleerd'),
                    ('reopened', 'Heropend'),
                    ('s', 'Gesplitst'),
                    ('closure requested', 'Verzoek tot afhandeling'),
                    ('sent', 'Verzonden naar extern systeem'),
                    ('send failed', 'Verzending naar extern systeem mislukt'),
                    ('done external', 'Melding is afgehandeld in extern systeem')
                ],
                max_length=20
            ),
        ),
        migrations.AlterIndexTogether(
            name='statusmessagetemplate',
            index_together={
                ('category', 'state', 'order')
            },
        ),
    ]
