# Generic imports
from rest_framework import serializers

# Local imports
import core.models


class SampleIngestSerializer(serializers.ModelSerializer):
    # Extra fields not in the Sample model but needed for lookups/forward-compat.
    schema_name = serializers.CharField(
        required=True, allow_blank=False, allow_null=False, write_only=True
    )
    schema_version = serializers.CharField(
        required=True, allow_blank=False, allow_null=False, write_only=True
    )
    authors = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, write_only=True
    )
    sequence_file_path_r1 = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        source="r1_fastq_filepath",
    )
    sequence_file_path_r2 = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        source="r2_fastq_filepath",
    )

    class Meta:
        model = core.models.Sample
        fields = [
            "sample_unique_id",
            "sequencing_sample_id",
            "authors",
            "collecting_institution",
            "collecting_lab_sample_id",
            "microbiology_lab_sample_id",
            "submitting_lab_sample_id",
            "schema_name",
            "schema_version",
            "sequencing_date",
            "sequence_file_R1_md5",
            "sequence_file_R2_md5",
            "sequence_file_path_r1",
            "sequence_file_path_r2",
        ]

class SampleStateHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = core.models.SampleStateHistory
        fields = "__all__"

class SampleIngestResponseSerializer(serializers.Serializer):
    sample_unique_id = serializers.CharField()
    sequencing_sample_id = serializers.CharField(allow_null=True, allow_blank=True)
    created = serializers.BooleanField()
    status = serializers.CharField()


class ErrorSerializer(serializers.Serializer):
    error = serializers.CharField()


# TODO: Add or remove request filters.
class SampleFilterSerializer(serializers.Serializer):
    sample_unique_id = serializers.CharField(required=False, allow_blank=False)
    sequencing_sample_id = serializers.CharField(required=False, allow_blank=False)
    collecting_institution = serializers.CharField(required=False, allow_blank=False)
    collecting_lab_sample_id = serializers.CharField(required=False, allow_blank=False)
    microbiology_lab_sample_id = serializers.CharField(required=False, allow_blank=False)
    submitting_lab_sample_id = serializers.CharField(required=False, allow_blank=False)
    schema_name = serializers.CharField(required=False, allow_blank=False)
    schema_version = serializers.CharField(required=False, allow_blank=False)
    created_at_from = serializers.DateTimeField(required=False)
    created_at_to = serializers.DateTimeField(required=False)
    sequencing_date_from = serializers.DateTimeField(required=False)
    sequencing_date_to = serializers.DateTimeField(required=False)

    def validate(self, attrs):
        allowed_keys = set(self.fields.keys())
        provided_keys = set(self.initial_data.keys())
        unknown_keys = provided_keys - allowed_keys
        if unknown_keys:
            raise serializers.ValidationError(
                {"error": f"Unknown filter(s): {', '.join(sorted(unknown_keys))}"}
            )
        return attrs


# TODO: Add or remove response filters.
class SampleListItemSerializer(serializers.ModelSerializer):
    schema_name = serializers.CharField(source="schema_obj.schema_name", read_only=True)
    schema_version = serializers.CharField(
        source="schema_obj.schema_version", read_only=True
    )

    class Meta:
        model = core.models.Sample
        fields = [
            "sample_unique_id",
            "sequencing_sample_id",
            #"collecting_institution",
            "created_at",
            "schema_name",
            "schema_version",
        ]


# TODO: Decide response fields for sample detail.
class SampleDetailSerializer(serializers.ModelSerializer):
    schema_name = serializers.CharField(source="schema_obj.schema_name", read_only=True)
    schema_version = serializers.CharField(
        source="schema_obj.schema_version", read_only=True
    )

    class Meta:
        model = core.models.Sample
        fields = [
            "sample_unique_id",
            "sequencing_sample_id",
            "microbiology_lab_sample_id",
            "collecting_lab_sample_id",
            "submitting_lab_sample_id",
            "collecting_institution",
            "sequence_file_R1_md5",
            "sequence_file_R2_md5",
            "r1_fastq_filepath",
            "r2_fastq_filepath",
            "sequencing_date",
            "created_at",
            "schema_name",
            "schema_version",
        ]


class SampleMetadataFilterSerializer(serializers.Serializer):
    classification = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=False
    )
    property = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=False
    )


# FIXME: point to metadata values model instead
class SampleMetadataItemSerializer(serializers.Serializer):
    property = serializers.CharField()
    value = serializers.CharField(allow_null=True, allow_blank=True)

    def to_representation(self, instance):
        if isinstance(instance, dict):
            property_name = instance.get("property")
            value = instance.get("value")
        else:
            property_name = getattr(instance, "property", None)
            value = getattr(instance, "value", None)
        return {property_name: value}


class SampleMetadataIngestSerializer(serializers.Serializer):
    schema_name = serializers.CharField(required=False, allow_blank=False)
    schema_version = serializers.CharField(required=False, allow_blank=False)

    def validate(self, attrs):
        schema_name = attrs.get("schema_name")
        schema_version = attrs.get("schema_version")
        if (schema_name and not schema_version) or (schema_version and not schema_name):
            raise serializers.ValidationError(
                {"error": "schema_name and schema_version must be provided together"}
            )
        attrs["payload"] = self.initial_data
        return attrs


class SampleMetadataIngestResponseSerializer(serializers.Serializer):
    sample_unique_id = serializers.CharField()
    stored_count = serializers.IntegerField()
    status = serializers.CharField()


#### Old serializers TODO: refactor or remove ####

class CreateMetadataValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = core.models.MetadataValues
        fields = "__all__"


class CreateSampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = core.models.Sample
        fields = "__all__"


class CreateEffectSerializer(serializers.ModelSerializer):
    class Meta:
        model = core.models.Effect
        fields = "__all__"


class CreateVariantInSampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = core.models.VariantInSample
        fields = "__all__"


class CreateVariantAnnotationSerializer(serializers.ModelSerializer):
    class Meta:
        model = core.models.VariantAnnotation
        fields = "__all__"


class CreateFilterSerializer(serializers.ModelSerializer):
    class Meta:
        model = core.models.Filter
        fields = "__all__"


class CreateVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = core.models.Variant
        fields = "__all__"


class CreateLineageValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = core.models.LineageValues
        fields = "__all__"


class CreatePublicDatabaseValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = core.models.PublicDatabaseValues
        fields = "__all__"


class UpdateStateSampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = core.models.Sample
        fields = "__all__"
