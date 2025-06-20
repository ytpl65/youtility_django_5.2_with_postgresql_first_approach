from django.contrib.gis.db.models import PointField, LineStringField, PolygonField
from graphene_django.converter import convert_django_field
from .scalars import PointScalar, LineStringScalar, PolygonScalar

@convert_django_field.register(PointField)
def convert_point_field(field, registry=None):
    return PointScalar()

@convert_django_field.register(LineStringField)
def convert_linestring_field(field, registry=None):
    return LineStringScalar()

@convert_django_field.register(PolygonField)
def convert_polygon_field(field, registry=None):
    return PolygonScalar()
