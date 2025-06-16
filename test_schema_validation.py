from pydantic import TypeAdapter, create_model
from pydantic.json_schema import GenerateJsonSchema
"""
Validate the inputs against the openapi schema
"""
inputs_openapi_schema = {
    "$defs": {
      "Point": {
        "description": "A point with a longitude and latitude",
        "properties": {
          "long": {
            "description": "The longitude of the point",
            "title": "Long",
            "type": "number"
          },
          "lat": {
            "description": "The latitude of the point",
            "title": "Lat",
            "type": "number"
          }
        },
        "required": [
          "long",
          "lat"
        ],
        "title": "Point",
        "type": "object",
        "additionalProperties": False
      }
    },
    "properties": {
      "point": {
        "$ref": "#/$defs/Point"
      }
    },
    "required": [
      "point"
    ],
    "title": "run_args",
    "type": "object",
    "additionalProperties": False
}

# Convert OpenAPI schema to Pydantic model
Point = create_model(
    'Point',
    long=(float, ...),
    lat=(float, ...)
)

InputSchema = create_model(
    'InputSchema',
    point=(Point, ...)
)

inputs = {"point": {"long": 1, "lat": 2}}
adapter = TypeAdapter(InputSchema)
adapter.validate_python(inputs)
    