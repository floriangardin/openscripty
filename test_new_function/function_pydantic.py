from pydantic import BaseModel
from pydantic import Field
import math


class Point(BaseModel):
    """
    A point with a longitude and latitude
    """
    long: float = Field(description="The longitude of the point")
    lat: float = Field(description="The latitude of the point")

class PointWithDistance(Point):
    """
    A point with a longitude and latitude and the distance to the equator in km
    """
    distance: float = Field(description="The distance to the equator in km")

def run(point: Point, options: dict) -> PointWithDistance:
    '''
    This function takes a long,lat point and return the distance to the equator in km
    Args:
        point: A point with a longitude and latitude
        unit: The unit of the distance, can be "km" or "m"
    Returns:
        distance: The distance to the equator in unit
    '''
    multiplier = 1 if options.get("unit") == "km" else 1000
    R = 6371  # Mean Earth radius in kilometers
    return PointWithDistance(long=point.long, lat=point.lat, distance=abs(point.lat) * math.pi / 180 * R * multiplier)



if __name__ == "__main__":
    result = pydantic_auto_convert(run)({"point": {"long": 1, "lat": 2}, "options": {"unit": "km"}})
    print(result)