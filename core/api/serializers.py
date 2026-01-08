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


class SampleIngestResponseSerializer(serializers.Serializer):
    sample_unique_id = serializers.CharField()
    sequencing_sample_id = serializers.CharField(allow_null=True, allow_blank=True)
    created = serializers.BooleanField()


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


# TODO: Add or remove response filters.
class SampleListItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = core.models.Sample
        fields = [
            "sample_unique_id",
            "sequencing_sample_id",
            "collecting_institution",
            "created_at",
            "schema_obj",
            "user",
        ]


#### Old serializers TODO: refactor or remove ####

class CreateMetadataValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = core.models.MetadataValues
        fields = "__all__"
class SampleStateHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = core.models.SampleStateHistory
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
