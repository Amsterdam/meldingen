# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2019 - 2021 Gemeente Amsterdam
# Generated by Django 2.1.7 on 2019-03-14 12:59

import datetime

import django.db.models.deletion
from django.db import migrations, models

now = datetime.datetime.utcnow()
timestr = now.strftime("%Y%m%d")

backup_categories = "CREATE TABLE signals_category_backup_{} " \
                    "AS TABLE signals_category".format(timestr)
backup_main_categories = "CREATE TABLE signals_maincategory_backup_{} " \
                         "AS TABLE signals_maincategory".format(timestr)

copy_maincategories = """
insert into signals_category(id, name, handling, slug, is_active)
select nextval('signals_subcategory_id_seq'), name, 'REST', slug, true from signals_maincategory;
"""

link_new_parent_categories = """
update signals_category as currentrow
set parent_id=newparent.id
from (
    select id, slug
    from signals_maincategory
) as main_categories
left join signals_category as newparent
on main_categories.slug = newparent.slug
where currentrow.parent_id is not null
and currentrow.parent_id = main_categories.id
;
"""


class Migration(migrations.Migration):
    dependencies = [
        ('signals', '0038_auto_20190314_1311'),
    ]

    operations = [
        migrations.AlterField(
            model_name='category',
            name='parent',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT,
                                    related_name='children', to='signals.Category'),
        ),
        migrations.AlterField(
            model_name='category',
            name='handling',
            field=models.CharField(
                choices=[('A3DMC', 'A3DMC'), ('A3DEC', 'A3DEC'), ('A3WMC', 'A3WMC'),
                         ('A3WEC', 'A3WEC'), ('I5DMC', 'I5DMC'), ('STOPEC', 'STOPEC'),
                         ('KLOKLICHTZC', 'KLOKLICHTZC'), ('GLADZC', 'GLADZC'),
                         ('A3DEVOMC', 'A3DEVOMC'), ('WS1EC', 'WS1EC'), ('WS2EC', 'WS2EC'),
                         ('REST', 'REST')], default='REST', max_length=20),
        ),
        migrations.AlterModelOptions(
            name='category',
            options={'ordering': ('name',), 'verbose_name_plural': 'Categories'},
        ),
        migrations.RunSQL(backup_categories),
        migrations.RunSQL(backup_main_categories),
        migrations.RunSQL(copy_maincategories),
        migrations.RunSQL(link_new_parent_categories),
    ]
