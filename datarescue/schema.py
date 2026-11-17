"""Validate the declared schema without inferring semantics."""
import json
from pathlib import Path


def validate_schema(schema: dict) -> None:
    if not isinstance(schema, dict) or not isinstance(schema.get("fields"), dict) or not schema["fields"]:
        raise ValueError("Schema requires nonempty fields")
    for name, field in schema["fields"].items():
        if not isinstance(name, str) or not name or not isinstance(field, dict):
            raise ValueError("Fields require names and definitions")
        if field.get("type") not in ("enum", "string", "date"):
            raise ValueError("Unsupported schema type")
        if "description" in field and not isinstance(field["description"], str):
            raise ValueError("Description must be text")
        if field["type"] == "enum":
            values = field.get("values")
            if not isinstance(values, list) or not values or not all(isinstance(v, str) for v in values) or len(set(values)) != len(values):
                raise ValueError("Enum requires nonempty unique strings")


def _unique_object(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate schema key")
        result[key] = value
    return result


def load_schema(path: str | Path) -> dict:
    schema = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    validate_schema(schema)
    return schema
