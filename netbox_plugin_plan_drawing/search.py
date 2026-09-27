from netbox.search import SearchIndex

from .models import PlanDrawing


class PlanDrawingIndex(SearchIndex):
    model = PlanDrawing
    fields = (
        ('name', 100),
        ('description', 500),
        ('comments', 5000),
    )
    display_attrs = ('site', 'location', 'description')


indexes = (PlanDrawingIndex,)
