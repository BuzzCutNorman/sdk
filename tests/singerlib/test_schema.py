from __future__ import annotations

import pytest

from singer_sdk.singerlib import Schema, resolve_schema_references

STRING_SCHEMA = Schema(type="string", maxLength=32, default="")
STRING_DICT = {"type": "string", "maxLength": 32, "default": ""}
INTEGER_SCHEMA = Schema(type="integer", maximum=1000000, default=0)
INTEGER_DICT = {"type": "integer", "maximum": 1000000, "default": 0}
ARRAY_SCHEMA = Schema(type="array", items=INTEGER_SCHEMA)
ARRAY_DICT = {"type": "array", "items": INTEGER_DICT}
OBJECT_SCHEMA = Schema(
    type="object",
    properties={
        "a_string": STRING_SCHEMA,
        "an_array": ARRAY_SCHEMA,
    },
    additionalProperties=True,
    required=["a_string"],
)
OBJECT_DICT = {
    "type": "object",
    "properties": {
        "a_string": STRING_DICT,
        "an_array": ARRAY_DICT,
    },
    "additionalProperties": True,
    "required": ["a_string"],
}


@pytest.mark.parametrize(
    "schema,expected",
    [
        pytest.param(
            STRING_SCHEMA,
            STRING_DICT,
            id="string_to_dict",
        ),
        pytest.param(
            INTEGER_SCHEMA,
            INTEGER_DICT,
            id="integer_to_dict",
        ),
        pytest.param(
            ARRAY_SCHEMA,
            ARRAY_DICT,
            id="array_to_dict",
        ),
        pytest.param(
            OBJECT_SCHEMA,
            OBJECT_DICT,
            id="object_to_dict",
        ),
    ],
)
def test_schema_to_dict(schema, expected):
    assert schema.to_dict() == expected


@pytest.mark.parametrize(
    "pydict,expected",
    [
        pytest.param(
            STRING_DICT,
            STRING_SCHEMA,
            id="schema_from_string_dict",
        ),
        pytest.param(
            INTEGER_DICT,
            INTEGER_SCHEMA,
            id="schema_from_integer_dict",
        ),
        pytest.param(
            ARRAY_DICT,
            ARRAY_SCHEMA,
            id="schema_from_array_dict",
        ),
        pytest.param(
            OBJECT_DICT,
            OBJECT_SCHEMA,
            id="schema_from_object_dict",
        ),
    ],
)
def test_schema_from_dict(pydict, expected):
    assert Schema.from_dict(pydict) == expected


@pytest.mark.parametrize(
    "schema,refs,expected",
    [
        pytest.param(
            {
                "type": "object",
                "definitions": {"string_type": {"type": "string"}},
                "properties": {"name": {"$ref": "#/definitions/string_type"}},
            },
            None,
            {
                "type": "object",
                "definitions": {"string_type": {"type": "string"}},
                "properties": {"name": {"type": "string"}},
            },
            id="resolve_schema_references",
        ),
        pytest.param(
            {
                "type": "object",
                "properties": {
                    "name": {"$ref": "references.json#/definitions/string_type"},
                },
            },
            {"references.json": {"definitions": {"string_type": {"type": "string"}}}},
            {
                "type": "object",
                "properties": {"name": {"type": "string"}},
            },
            id="resolve_schema_references_with_refs",
        ),
        pytest.param(
            {
                "type": "object",
                "definitions": {"string_type": {"type": "string"}},
                "patternProperties": {".+": {"$ref": "#/definitions/string_type"}},
            },
            None,
            {
                "type": "object",
                "definitions": {"string_type": {"type": "string"}},
                "patternProperties": {".+": {"type": "string"}},
            },
            id="resolve_schema_references_with_pattern_properties",
        ),
        pytest.param(
            {
                "type": "object",
                "properties": {
                    "dogs": {"type": "array", "items": {"$ref": "doggie.json#/dogs"}},
                },
            },
            {
                "doggie.json": {
                    "dogs": {
                        "type": "object",
                        "properties": {
                            "breed": {"type": "string"},
                            "name": {"type": "string"},
                        },
                    },
                },
            },
            {
                "type": "object",
                "properties": {
                    "dogs": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "breed": {"type": "string"},
                                "name": {"type": "string"},
                            },
                        },
                    },
                },
            },
            id="resolve_schema_references_with_items",
        ),
        pytest.param(
            {
                "type": "object",
                "properties": {
                    "thing": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "$ref": "references.json#/definitions/string_type",
                            },
                        },
                    },
                },
            },
            {"references.json": {"definitions": {"string_type": {"type": "string"}}}},
            {
                "type": "object",
                "properties": {
                    "thing": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                    },
                },
            },
            id="resolve_schema_nested_references",
        ),
        pytest.param(
            {
                "type": "object",
                "properties": {
                    "name": {"$ref": "references.json#/definitions/string_type"},
                },
            },
            {
                "references.json": {
                    "definitions": {"string_type": {"$ref": "second_reference.json"}},
                },
                "second_reference.json": {"type": "string"},
            },
            {"type": "object", "properties": {"name": {"type": "string"}}},
            id="resolve_schema_indirect_references",
        ),
        pytest.param(
            {
                "type": "object",
                "properties": {
                    "name": {
                        "$ref": "references.json#/definitions/string_type",
                        "still_here": "yep",
                    },
                },
            },
            {"references.json": {"definitions": {"string_type": {"type": "string"}}}},
            {
                "type": "object",
                "properties": {"name": {"type": "string", "still_here": "yep"}},
            },
            id="resolve_schema_preserves_existing_fields",
        ),
        pytest.param(
            {
                "anyOf": [
                    {"$ref": "references.json#/definitions/first_type"},
                    {"$ref": "references.json#/definitions/second_type"},
                ],
            },
            {
                "references.json": {
                    "definitions": {
                        "first_type": {"type": "string"},
                        "second_type": {"type": "integer"},
                    },
                },
            },
            {"anyOf": [{"type": "string"}, {"type": "integer"}]},
            id="resolve_schema_any_of",
        ),
        pytest.param(
            {
                "allOf": [
                    {"$ref": "references.json#/definitions/first_type"},
                    {"$ref": "references.json#/definitions/second_type"},
                ],
            },
            {
                "references.json": {
                    "definitions": {
                        "first_type": {"type": "string"},
                        "second_type": {"type": "integer"},
                    },
                },
            },
            {"allOf": [{"type": "string"}, {"type": "integer"}]},
            id="resolve_schema_all_of",
        ),
        pytest.param(
            {
                "oneOf": [
                    {"$ref": "references.json#/definitions/first_type"},
                    {"$ref": "references.json#/definitions/second_type"},
                ],
                "title": "A Title",
            },
            {
                "references.json": {
                    "definitions": {
                        "first_type": {"type": "string", "title": "First Type"},
                        "second_type": {"type": "integer", "title": "Second Type"},
                    }
                },
            },
            {
                "oneOf": [
                    {"type": "string", "title": "First Type"},
                    {"type": "integer", "title": "Second Type"},
                ],
                "title": "A Title",
            },
            id="resolve_schema_one_of",
        ),
        pytest.param(
            {
                "type": "object",
                "properties": {
                    "product_price": {
                        "oneOf": [
                            {"$ref": "components#/schemas/LegacyProductPrice"},
                            {"$ref": "components#/schemas/ProductPrice"},
                        ],
                        "title": "Product Price",
                    },
                },
            },
            {
                "components": {
                    "schemas": {
                        "LegacyProductPrice": {
                            "type": "object",
                            "properties": {"price": {"type": "number"}},
                            "title": "Legacy Product Price",
                        },
                        "ProductPrice": {
                            "oneOf": [
                                {
                                    "$ref": "components#/schemas/ProductPriceFixed",
                                },
                                {
                                    "$ref": "components#/schemas/ProductPriceFree",
                                },
                            ],
                        },
                        "ProductPriceFixed": {
                            "type": "object",
                            "properties": {"price": {"type": "number"}},
                            "title": "Product Price Fixed",
                        },
                        "ProductPriceFree": {
                            "type": "object",
                            "properties": {"price": {"type": "number", "const": 0}},
                            "title": "Product Price Free",
                        },
                    }
                },
            },
            {
                "type": "object",
                "properties": {
                    "product_price": {
                        "oneOf": [
                            {
                                "type": "object",
                                "properties": {"price": {"type": "number"}},
                                "title": "Legacy Product Price",
                            },
                            {
                                "oneOf": [
                                    {
                                        "type": "object",
                                        "properties": {"price": {"type": "number"}},
                                        "title": "Product Price Fixed",
                                    },
                                    {
                                        "type": "object",
                                        "properties": {
                                            "price": {"type": "number", "const": 0}
                                        },
                                        "title": "Product Price Free",
                                    },
                                ],
                            },
                        ],
                        "title": "Product Price",
                    },
                },
            },
            id="resolve_nested_one_of",
        ),
        pytest.param(
            {
                "type": "object",
                "properties": {
                    "filter": {
                        "$ref": "components#/schemas/Filter",
                    },
                },
            },
            {
                "components": {
                    "schemas": {
                        "Filter": {
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "title": "Name",
                                },
                                "clauses": {
                                    "type": "array",
                                    "items": {
                                        "$ref": "components#/schemas/Filter",
                                    },
                                    "title": "Clauses",
                                },
                            },
                        },
                    },
                },
            },
            {
                "type": "object",
                "properties": {
                    "filter": {
                        "properties": {
                            "name": {
                                "type": "string",
                                "title": "Name",
                            },
                            "clauses": {
                                "type": "array",
                                "items": {},
                                "title": "Clauses",
                            },
                        },
                    },
                },
            },
            id="resolve_schema_references_with_circular_references",
        ),
        pytest.param(
            {
                "type": "object",
                "properties": {
                    "min_compute_units": {"$ref": "components#/schemas/ComputeUnit"},
                    "max_compute_units": {"$ref": "components#/schemas/ComputeUnit"},
                },
            },
            {
                "components": {
                    "schemas": {
                        "ComputeUnit": {"type": "number"},
                    },
                },
            },
            {
                "type": "object",
                "properties": {
                    "min_compute_units": {"type": "number"},
                    "max_compute_units": {"type": "number"},
                },
            },
            id="resolve_schema_multiple_properties_with_same_reference",
        ),
    ],
)
def test_resolve_schema_references(schema, refs, expected):
    """Test resolving schema references."""
    assert resolve_schema_references(schema, refs) == expected


def test_schema_from_dict_simple():
    simple_schema = {
        "title": "Longitude and Latitude Values",
        "description": "A geographical coordinate.",
        "required": ["latitude", "longitude"],
        "type": "object",
        "properties": {
            "latitude": {"type": "number", "minimum": -90, "maximum": 90},
            "longitude": {"type": "number", "minimum": -180, "maximum": 180},
        },
    }

    schema_plus = Schema.from_dict(simple_schema)
    assert schema_plus.to_dict() == simple_schema
    assert schema_plus.required == ["latitude", "longitude"]
    assert isinstance(schema_plus.properties["latitude"], Schema)
    latitude = schema_plus.properties["latitude"]
    assert latitude.type == "number"


def test_schema_from_dict_with_items():
    schema = {
        "description": "A representation of a person, company, organization, or place",
        "type": "object",
        "properties": {"fruits": {"type": "array", "items": {"type": "string"}}},
    }
    schema_plus = Schema.from_dict(schema)
    assert schema_plus.to_dict() == schema
    assert isinstance(schema_plus.properties["fruits"], Schema)
    fruits = schema_plus.properties["fruits"]
    assert isinstance(fruits.items, Schema)
    assert fruits.items.type == "string"
