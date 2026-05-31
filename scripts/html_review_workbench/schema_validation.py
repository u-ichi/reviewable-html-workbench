"""Minimal JSON schema validation used by fixture tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ValidationError:
    path: str
    message: str


def validate(instance: Any, schema: dict[str, Any]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    _validate_value(instance, schema, "$", errors)
    return errors


def _validate_value(value: Any, schema: dict[str, Any], path: str, errors: list[ValidationError]) -> None:
    negated_schema = schema.get("not")
    if isinstance(negated_schema, dict) and not validate(value, negated_schema):
        errors.append(ValidationError(path, "matched forbidden schema"))

    if "const" in schema and value != schema["const"]:
        errors.append(ValidationError(path, f"expected const {schema['const']!r}"))

    if "enum" in schema and value not in schema["enum"]:
        errors.append(ValidationError(path, f"expected one of {schema['enum']!r}"))

    expected_type = schema.get("type")
    if expected_type is not None and not _matches_type(value, expected_type):
        errors.append(ValidationError(path, f"expected type {expected_type!r}"))
        return

    if isinstance(value, str):
        min_length = schema.get("minLength")
        if isinstance(min_length, int) and len(value) < min_length:
            errors.append(ValidationError(path, f"expected length >= {min_length}"))

    if isinstance(value, int) and not isinstance(value, bool):
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if isinstance(minimum, (int, float)) and value < minimum:
            errors.append(ValidationError(path, f"expected value >= {minimum}"))
        if isinstance(maximum, (int, float)) and value > maximum:
            errors.append(ValidationError(path, f"expected value <= {maximum}"))

    if isinstance(value, list):
        min_items = schema.get("minItems")
        if isinstance(min_items, int) and len(value) < min_items:
            errors.append(ValidationError(path, f"expected at least {min_items} items"))
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                _validate_value(item, item_schema, f"{path}[{index}]", errors)

    if isinstance(value, dict):
        required = schema.get("required", [])
        if isinstance(required, list):
            for key in required:
                if key not in value:
                    errors.append(ValidationError(f"{path}.{key}", "missing required property"))

        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            for key, property_schema in properties.items():
                if key in value and isinstance(property_schema, dict):
                    _validate_value(value[key], property_schema, f"{path}.{key}", errors)

            if schema.get("additionalProperties") is False:
                extra_keys = sorted(set(value) - set(properties))
                for key in extra_keys:
                    errors.append(ValidationError(f"{path}.{key}", "unexpected property"))


def _matches_type(value: Any, expected_type: str | list[str]) -> bool:
    if isinstance(expected_type, list):
        return any(_matches_type(value, item) for item in expected_type)

    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return (isinstance(value, (int, float)) and not isinstance(value, bool))
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "null":
        return value is None
    return False
