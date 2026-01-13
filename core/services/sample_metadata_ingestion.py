from core import models


def _get_sample_payload_fields():
    from core.api.serializers import SampleIngestSerializer

    sample_field_names = {field.name for field in models.Sample._meta.get_fields()}
    sample_payload_fields = set(sample_field_names)
    serializer = SampleIngestSerializer()
    for field_name, field in serializer.fields.items():
        source = field.source if field.source != "*" else field_name
        if source in sample_field_names:
            sample_payload_fields.add(field_name)
    return sample_payload_fields


def ingest_sample_metadata(sample_obj, schema_obj, payload):
    sample_payload_fields = _get_sample_payload_fields()

    stored_count = 0
    for field, value in payload.items():
        if field in ("schema_name", "schema_version"):
            continue
        if field in sample_payload_fields:
            # Skip sample fields; they should be stored via sample ingest only.
            continue
        if value is None:
            continue
        if isinstance(value, (dict, list)):
            # TODO: support complex fields using MetadataGroup; for now skip them.
            # Example (pseudo):
            # - create MetadataGroup for each object in list
            # - store each sub-property in MetadataValues with group_id
            continue
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
