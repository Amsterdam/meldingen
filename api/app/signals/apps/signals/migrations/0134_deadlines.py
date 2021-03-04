# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2021 Gemeente Amsterdam
# Generated by Django 2.2.13 on 2021-02-21 22:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('signals', '0133_new_subcategories'),
    ]

    operations = [
        migrations.AddField(
            model_name='categoryassignment',
            name='deadline',
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name='categoryassignment',
            name='deadline_factor_3',
            field=models.DateTimeField(null=True),
        ),
    ]
