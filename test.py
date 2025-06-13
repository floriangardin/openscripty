import json

from typing_extensions import TypedDict, Any
from pydantic import BaseModel, Field
from agents import Agent, FunctionTool, RunContextWrapper, function_tool


class SubLocation(BaseModel):
    lat: float = Field(..., description="The latitude of the location")
    long: float = Field(..., description="The longitude of the location")

class Location(BaseModel):
    sub_location: SubLocation

def fetch_weather(arg1: int, location: 'Location') -> str:
    
    """Fetch the weather for a given location.

    Args:
        location: The location to fetch the weather for.
    """
    # In real life, we'd fetch the weather from a weather API
    return "sunny"

import inspect
from typing import get_type_hints

print(get_type_hints(fetch_weather))

from pdb import set_trace
set_trace()


"""
Let the AI generate the script code : 
- You should wrap your main code in a function named `run`
- Each parameters of the `run` function must be typed with standard python types OR pydantic models
- For each pydantic model you use you have to define it first in the script code (before `run` function definition)
"""