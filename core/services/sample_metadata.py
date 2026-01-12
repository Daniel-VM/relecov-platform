from core import models


def _normalize_list(values):
    if values is None:
        return None
    if isinstance(values, str):
        values = [values]
    cleaned = [item.strip() for item in values if item and item.strip()]
    return cleaned or None


def list_sample_metadata(sample_obj, classifications=None, properties=None):
    queryset = (
        models.MetadataValues.objects.filter(sample=sample_obj)
        .select_related("schema_property", "schema_property__classificationID", "group")
    )
    classifications = _normalize_list(classifications)
    properties = _normalize_list(properties)
    if classifications:
        queryset = queryset.filter(
            schema_property__classificationID__classification_name__in=classifications
        )
    if properties:
        queryset = queryset.filter(schema_property__property__in=properties)

    results = []
    for item in queryset:
        classification_obj = item.schema_property.classificationID
        classification_name = (
            classification_obj.classification_name if classification_obj else None
        )
        results.append(
            {
                "property": item.schema_property.property,
                "value": item.value,
                "classification": classification_name,
                "group_id": item.group_id,
                "group_index": item.group.group_index if item.group_id else None,
            }
        )
    return results
