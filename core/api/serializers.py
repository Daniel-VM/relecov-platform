# Generic imports
from rest_framework import serializers

# Local imports
import core.models


class CreateMetadataValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = core.models.MetadataValues
        fields = "__all__"


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

    class Meta:
        model = core.models.Sample
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
