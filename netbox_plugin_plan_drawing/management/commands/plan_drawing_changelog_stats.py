from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.models import Count, F, Func, IntegerField, Sum, TextField, Value
from django.db.models.functions import Cast, Coalesce, Length

from core.models import ObjectChange

from netbox_plugin_plan_drawing.models import PlanDrawing


class ColumnSize(Func):
    """
    The storage size of a value in PostgreSQL, after compression.
    """
    function = 'pg_column_size'
    output_field = IntegerField()


def stored_size(field):
    return Coalesce(ColumnSize(field), Value(0))


def raw_size(field):
    return Coalesce(Length(Cast(field, TextField())), Value(0))


def human(size):
    for unit in ('B', 'KiB', 'MiB', 'GiB'):
        if abs(size) < 1024 or unit == 'GiB':
            return f'{size:.0f} {unit}' if unit == 'B' else f'{size:.1f} {unit}'
        size /= 1024


class Command(BaseCommand):
    help = (
        'Report how much space the change log entries of plan drawings take up. Every save of a '
        'drawing records the complete drawing XML before and after the change.'
    )

    def handle(self, *args, **options):
        content_type = ContentType.objects.get_for_model(PlanDrawing)
        changes = (
            ObjectChange.objects
            .filter(changed_object_type=content_type)
            .values('changed_object_id')
            .annotate(
                count=Count('pk'),
                stored=Sum(stored_size('prechange_data') + stored_size('postchange_data')),
                raw=Sum(raw_size('prechange_data') + raw_size('postchange_data')),
            )
        )
        changes = {row['changed_object_id']: row for row in changes}
        drawings = PlanDrawing.objects.annotate(content_size=Length('content')).order_by(F('name'))

        header = f'{"Drawing":<40} {"Content":>10} {"Changes":>8} {"Log stored":>11} {"Log raw":>11} {"Per change":>11}'
        self.stdout.write(header)
        self.stdout.write('-' * len(header))
        totals = {'count': 0, 'stored': 0, 'raw': 0}
        for drawing in drawings:
            row = changes.pop(drawing.pk, {'count': 0, 'stored': 0, 'raw': 0})
            self._write_row(drawing.name, drawing.content_size, row)
            for key in totals:
                totals[key] += row[key] or 0
        for object_id, row in changes.items():
            self._write_row(f'(deleted drawing #{object_id})', None, row)
            for key in totals:
                totals[key] += row[key] or 0
        self.stdout.write('-' * len(header))
        self._write_row('Total', None, totals)

        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_total_relation_size(%s)', [ObjectChange._meta.db_table])
            table_size = cursor.fetchone()[0]
        self.stdout.write('')
        self.stdout.write(
            f'Change log table {ObjectChange._meta.db_table}: {human(table_size)} in total, '
            f'{ObjectChange.objects.count()} entries for all object types.'
        )
        self.stdout.write(
            '"Log stored" is the size after PostgreSQL compression; "Log raw" the uncompressed JSON size.'
        )

    def _write_row(self, name, content_size, row):
        count = row['count'] or 0
        stored = row['stored'] or 0
        raw = row['raw'] or 0
        per_change = human(stored / count) if count else '-'
        content = human(content_size) if content_size is not None else ''
        self.stdout.write(
            f'{name[:40]:<40} {content:>10} {count:>8} {human(stored):>11} {human(raw):>11} {per_change:>11}'
        )
