# Generated by Django 2.1 on 2018-09-18 12:16

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('signals', '0009_initial_data_categories'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='sub_category',
            field=models.ForeignKey(null=True,
                                    on_delete=django.db.models.deletion.CASCADE,
                                    to='signals.SubCategory'),
        ),
        migrations.AddField(
            model_name='maincategory',
            name='slug',
            field=models.SlugField(null=True, unique=True),
        ),
        migrations.AddField(
            model_name='subcategory',
            name='slug',
            field=models.SlugField(null=True, unique=True),
        ),
        migrations.AlterUniqueTogether(
            name='subcategory',
            unique_together={('main_category', 'slug')},
        ),
    ]
