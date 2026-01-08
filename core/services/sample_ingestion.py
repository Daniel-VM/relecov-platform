from typing import Tuple

from core import models


def ingest_sample(sample_payload: dict, request_user=None) -> Tuple[models.Sample, bool]:
    # Get samples unique id
    raw_unique_id = sample_payload.get("sample_unique_id")
    normalized_id = raw_unique_id.strip()

    # Handle schema relationship explicitly
    schema_obj = None
    schema_name = sample_payload.get("schema_name")
    schema_version = sample_payload.get("schema_version")
    if not schema_name or not schema_version:
        raise ValueError("schema_name and schema_version are required")
    schema_obj = (
        models.Schema.objects.filter(
            schema_name=schema_name, schema_version=schema_version
        ).last()
    )
    if schema_obj is None:
        raise ValueError(
            f"Schema not found for name={schema_name} version={schema_version}"
        )

    # Build defaults with any simple fields provided, without failing if they are absent.
    defaults = {}
    sample_field_names = {
        f.name
        for f in models.Sample._meta.get_fields()
        if getattr(f, "is_relation", False) is False
    }
    excluded_defaults = {"id", "sample_unique_id", "created_at"}
    # TODO: here we ignore foreingkey fields such as lineage, schema_obj, etc.
    for key, value in sample_payload.items():
        if key in excluded_defaults or key not in sample_field_names:
            continue  # Ignore unknown fields (e.g., metadata, future keys).
        if value is None:
            continue  # avoid overwriting with None
        if isinstance(value, str):
            trimmed = value.strip()
            if not trimmed:
                continue  # avoid overwriting with empty strings
            defaults[key] = trimmed
        else:
            defaults[key] = value

    # Get-or-create on sample_unique_id
    sample_obj, created = models.Sample.objects.get_or_create(
        sample_unique_id=normalized_id,
        defaults=defaults,
    )

    # Attach the authenticated user if provided and not already set.
    if request_user and getattr(sample_obj, "user_id", None) is None:
        sample_obj.user = request_user
        sample_obj.save(update_fields=["user"])

    # If schema is provided and the sample lacks it, attach it without overwriting existing data.
    if schema_obj and sample_obj.schema_obj_id is None:
        sample_obj.schema_obj = schema_obj
        sample_obj.save(update_fields=["schema_obj"])

    return sample_obj, created
