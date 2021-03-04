# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2020 - 2021 Gemeente Amsterdam
# Generated by Django 2.2.12 on 2020-05-29 06:46

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('signals', '0110_SIG-2715_category_changes'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='category',
            options={
                'ordering': ('name',),
                'permissions': (
                    ('sia_can_view_all_categories', 'Bekijk all categorieën (overschrijft categorie rechten van afdeling)'),  # noqa
                    ('sia_category_read', 'Inzien van categorieën'),
                    ('sia_category_write', 'Wijzigen van categorieën')
                ),
                'verbose_name_plural': 'Categories'
            },
        ),
        migrations.AlterModelOptions(
            name='department',
            options={
                'ordering': ('name',),
                'permissions': (
                    ('sia_department_read', 'Inzien van afdeling instellingen'),
                    ('sia_department_write', 'Wijzigen van afdeling instellingen')
                )
            },
        ),
        migrations.AlterModelOptions(
            name='signal',
            options={
                'ordering': ('created_at',),
                'permissions': (
                    ('sia_read', 'Leesrechten algemeen'),
                    ('sia_write', 'Schrijfrechten algemeen'),
                    ('sia_split', 'Splitsen van een melding'),
                    ('sia_signal_create_initial', 'Melding aanmaken'),
                    ('sia_signal_create_note', 'Notitie toevoegen bij een melding'),
                    ('sia_signal_change_status', 'Wijzigen van status van een melding'),
                    ('sia_signal_change_category', 'Wijzigen van categorie van een melding'),
                    ('sia_signal_export', 'Meldingen exporteren'),
                    ('sia_signal_report', 'Rapportage beheren')
                )
            },
        ),
        migrations.AlterModelOptions(
            name='status',
            options={
                'get_latest_by': 'datetime',
                'ordering': ('created_at',),
                'permissions': (
                    ('push_to_sigmax', 'Doorsturen van een melding (THOR)'),
                ),
                'verbose_name_plural': 'Statuses'
            },
        ),
        migrations.AlterModelOptions(
            name='statusmessagetemplate',
            options={
                'ordering': ('category', 'state', 'order'),
                'permissions': (
                    ('sia_statusmessagetemplate_write', 'Wijzingen van standaardteksten'),
                ),
                'verbose_name': 'Standaard afmeldtekst',
                'verbose_name_plural': 'Standaard afmeldteksten'
            },
        ),
        migrations.AlterField(
            model_name='areatype',
            name='id',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='category',
            name='departments',
            field=models.ManyToManyField(through='signals.CategoryDepartment', to='signals.Department'),
        ),
        migrations.AlterField(
            model_name='category',
            name='handling',
            field=models.CharField(choices=[
                ('A3DMC', 'A3DMC'),
                ('A3DEC', 'A3DEC'),
                ('A3WMC', 'A3WMC'),
                ('A3WEC', 'A3WEC'),
                ('I5DMC', 'I5DMC'),
                ('STOPEC', 'STOPEC'),
                ('KLOKLICHTZC', 'KLOKLICHTZC'),
                ('GLADZC', 'GLADZC'),
                ('A3DEVOMC', 'A3DEVOMC'),
                ('WS1EC', 'WS1EC'),
                ('WS2EC', 'WS2EC'),
                ('WS3EC', 'WS3EC'),
                ('REST', 'REST'),
                ('ONDERMIJNING', 'ONDERMIJNING'),
                ('EMPTY', 'EMPTY'),
                ('LIGHTING', 'LIGHTING'),
                ('GLAD_OLIE', 'GLAD_OLIE'),
                ('TECHNISCHE_STORING', 'TECHNISCHE_STORING'),
                ('STOPEC3', 'STOPEC3'),
                ('URGENTE_MELDINGEN', 'URGENTE_MELDINGEN'),
                ('3WGM', '3WGM'),
                ('HANDLING_MARKTEN', 'HANDLING_MARKTEN')
            ], default='REST', max_length=20),
        ),
        migrations.AlterField(
            model_name='servicelevelobjective',
            name='category',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='slo', to='signals.Category'),  # noqa
        ),
        migrations.AlterField(
            model_name='signal',
            name='source',
            field=models.CharField(default='online', max_length=128),
        ),
        migrations.AlterField(
            model_name='status',
            name='state',
            field=models.CharField(blank=True, choices=[
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
                ('done external', 'Melding is afgehandeld in extern systeem'),
                ('reopen requested', 'Verzoek tot heropenen')
            ], default='m', help_text='Melding status', max_length=20),
        ),
        migrations.AlterField(
            model_name='statusmessagetemplate',
            name='category',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='status_message_templates', to='signals.Category'),  # noqa
        ),
        migrations.AlterField(
            model_name='statusmessagetemplate',
            name='state',
            field=models.CharField(choices=[
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
                ('done external', 'Melding is afgehandeld in extern systeem'),
                ('reopen requested', 'Verzoek tot heropenen')
            ], max_length=20),
        ),
        migrations.AlterField(
            model_name='type',
            name='created_by',
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
    ]
