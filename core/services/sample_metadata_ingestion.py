from core import models


def ingest_sample_metadata(sample_obj, schema_obj, payload):
    stored_count = 0
    for field, value in payload.items():
        if field in ("schema_name", "schema_version"):
            continue
        if value is None:
            continue
        if isinstance(value, (dict, list)):
            raise ValueError(f"Complex field '{field}' is not supported yet")
        property_obj = models.SchemaProperties.objects.filter(
            schemaID=schema_obj, property__iexact=field
        ).last()
        if property_obj is None:
            raise ValueError(f"Field '{field}' is not defined in schema properties")
        models.MetadataValues.objects.create(
            value=str(value),
            analysis_date=payload.get("analysis_date")
            or payload.get("lineage_analysis_date"),
            sample=sample_obj,
            schema_property=property_obj,
        )
        stored_count += 1
    return stored_count
