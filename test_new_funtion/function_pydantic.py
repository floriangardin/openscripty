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

def run(point: Point) -> float:
    '''
    This function takes a long,lat point and return the distance to the equator in km
    Args:
        point: A point with a longitude and latitude
    Returns:
        distance: The distance to the equator in km
    '''
    R = 6371  # Mean Earth radius in kilometers
    return 2, PointWithDistance(long=point.long, lat=point.lat, distance=abs(point.lat) * math.pi / 180 * R)

from typing import Any
class Wrapper(BaseModel):
    wrapped: Any

if __name__ == "__main__":
    import json
    result = run(Point(long=1, lat=2))
    print(json.dumps(Wrapper(wrapped=result).model_dump()['wrapped']))