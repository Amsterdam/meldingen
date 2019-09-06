from datetime import datetime

from django.db import connection

# TODO: Investigate JSON straight from Postgres (?)

# Note: it is anticipated that several chunks of SQL will be needed in the
# general case to support all category and area subdivisions. For now we only
# support parametrized intervals and always group by sub category.
SQL = """
select
    gauged_cas.category_id as category_id,
    count(distinct(gauged_status._signal_id)) as N_MELDING_GESLOTEN -- one signal closed twice is counted as 1, hence distinct
from (
    select
        _signal_id,
        state
    from (
        select
            _signal_id,
            state,
            row_number() over(partition by _signal_id order by created_at desc) as row_num
        from
            public.signals_status
        where
            state not in ('o', 'a', 's')
            and created_at >= %(begin)s :: timestamp
            and created_at < %(end)s :: timestamp) as numbered
    where
        numbered.row_num = 1) as gauged_status
inner join (
    select
        _signal_id,
        category_id
    from (
        select
            _signal_id,
            category_id,
            row_number() over(partition by _signal_id order by created_at desc) as row_num
        from
            public.signals_categoryassignment
        where
            created_at < %(end)s :: timestamp) as numbered
    where
        numbered.row_num = 1) as gauged_cas
    on
        gauged_status._signal_id = gauged_cas._signal_id
group by
    gauged_cas.category_id;
"""


class NMeldingOpen:
    code = "N_MELDING_OPEN"
    description = "Aantal open meldingen aan het eind van gegeven periode."

    sql = SQL

    def derive(self, begin, end, category, area):
        # Note: for know the following holds
        # - category granularity is per sub category
        # - area granularity is everywhere
        assert isinstance(begin, datetime)
        assert isinstance(end, datetime)

        db_query_parameters = {
            'begin': begin,
            'end': end,
            'category': category,
            'area': area,
        }
        with connection.cursor() as cursor:
            cursor.execute(self.sql, db_query_parameters)
            result = cursor.fetchall()
        return result
