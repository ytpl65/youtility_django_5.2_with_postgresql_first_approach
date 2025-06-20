from graphene import Scalar
from django.contrib.gis.geos import GEOSGeometry, Point, LineString, Polygon

class PointScalar(Scalar):
    @staticmethod
    def serialize(point):
        if point is None:
            return None
        return {
            'latitude': point.y,
            'longitude': point.x
        }

    @staticmethod
    def parse_literal(node):
        if node is None:
            return None
        return Point(
            float(node.get('longitude')),
            float(node.get('latitude')),
            srid=4326
        )

    @staticmethod
    def parse_value(value):
        if value is None:
            return None
        return Point(
            float(value.get('longitude')),
            float(value.get('latitude')),
            srid=4326
        )

class LineStringScalar(Scalar):
    @staticmethod
    def serialize(linestring):
        if linestring is None:
            return None
        return [{'latitude': point[1], 'longitude': point[0]} 
                for point in linestring.coords]

    @staticmethod
    def parse_literal(node):
        if node is None:
            return None
        points = [(point['longitude'], point['latitude']) for point in node]
        return LineString(points, srid=4326)

    @staticmethod
    def parse_value(value):
        if value is None:
            return None
        points = [(point['longitude'], point['latitude']) for point in value]
        return LineString(points, srid=4326)

class PolygonScalar(Scalar):
    @staticmethod
    def serialize(polygon):
        if polygon is None:
            return None
        # Return array of coordinate arrays for each ring
        return [[{'latitude': point[1], 'longitude': point[0]} 
                for point in ring.coords] 
                for ring in polygon]

    @staticmethod
    def parse_literal(node):
        if node is None:
            return None
        # Convert first ring (exterior ring) to polygon
        points = [(point['longitude'], point['latitude']) for point in node[0]]
        return Polygon(points, srid=4326)

    @staticmethod
    def parse_value(value):
        if value is None:
            return None
        # Convert first ring (exterior ring) to polygon
        points = [(point['longitude'], point['latitude']) for point in value[0]]
        return Polygon(points, srid=4326)
