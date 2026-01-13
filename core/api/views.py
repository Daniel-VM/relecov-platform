# Generic imports
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import (
    authentication_classes,
    permission_classes,
    api_view,
)
from rest_framework import status
from rest_framework.response import Response
from drf_spectacular.utils import (
    extend_schema,
    OpenApiExample,
    inline_serializer,
    OpenApiResponse,
    extend_schema_view,
)
from rest_framework import serializers
from django.http import QueryDict

# Local imports
import core.urls
import core.models
import core.utils.samples
import core.api.serializers
import core.api.utils.samples
import core.api.utils.metadata_values
import core.api.utils.public_db
import core.api.utils.variants
import core.api.utils.common_functions
import core.config
from core.services import sample_ingestion
from core.services import sample_listing
from core.services import sample_detail
from core.services import sample_metadata
from core.services import sample_metadata_ingestion

@extend_schema_view(
    post=extend_schema(
        request=core.api.serializers.SampleIngestSerializer,
        responses={
            200: core.api.serializers.SampleIngestResponseSerializer,
            201: core.api.serializers.SampleIngestResponseSerializer,
            400: core.api.serializers.ErrorSerializer,
            404: core.api.serializers.ErrorSerializer,
            409: core.api.serializers.ErrorSerializer,
        },
    ),
    get=extend_schema(
        request=core.api.serializers.SampleFilterSerializer,
        responses={
            200: core.api.serializers.SampleListItemSerializer(many=True),
            401: core.api.serializers.ErrorSerializer,
            404: core.api.serializers.ErrorSerializer,
        },
    ),
)
@authentication_classes([SessionAuthentication, BasicAuthentication])
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def samples(request):
    if request.method == "POST":
        # Few checks
        if not request.user.is_staff:
            return Response(
                {"error": "Admin privileges required"},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = core.api.serializers.SampleIngestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create/Ingest Sample
        try:
            sample_obj, created = sample_ingestion.ingest_sample(
                serializer.validated_data, request_user=request.user
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        # If created, add initial state history
        if created:
            state_obj = core.models.SampleState.objects.filter(
                state__exact="Defined"
            ).last()
            if state_obj is None:
                return Response(
                    {"error": "Sample state 'Defined' not configured"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                result = core.api.utils.common_functions.add_sample_state_history(
                    sample_obj, state_id=state_obj.pk, error_name="No error"
                )
            except ValueError as exc:
                return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            if isinstance(result, Response):
                return result
        
        # Prepare POST response
        response_serializer = core.api.serializers.SampleIngestResponseSerializer(
            data={
                "sample_unique_id": sample_obj.sample_unique_id,
                "sequencing_sample_id": sample_obj.sequencing_sample_id,
                "created": created,
            }
        )
        response_serializer.is_valid(raise_exception=True)

        # Return
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    # GET samples with filters
    data = request.data or request.query_params
    filter_serializer = core.api.serializers.SampleFilterSerializer(data=data)
    filter_serializer.is_valid(raise_exception=True)
    try:
        queryset = sample_listing.list_samples(filter_serializer.validated_data)
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    if not queryset.exists():
        return Response({"error": "No samples found"}, status=status.HTTP_404_NOT_FOUND)
    response_serializer = core.api.serializers.SampleListItemSerializer(
        queryset, many=True
    )
    return Response(response_serializer.data, status=status.HTTP_200_OK)

@extend_schema(
    responses={
        200: core.api.serializers.SampleDetailSerializer,
        401: core.api.serializers.ErrorSerializer,
        403: core.api.serializers.ErrorSerializer,
        404: core.api.serializers.ErrorSerializer,
    },
)
@authentication_classes([SessionAuthentication, BasicAuthentication])
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sample_detail_view(request, sample_unique_id):
    sample_obj = sample_detail.get_sample_detail(sample_unique_id)
    if sample_obj is None:
        return Response({"error": "Sample not found"}, status=status.HTTP_404_NOT_FOUND)
    response_serializer = core.api.serializers.SampleDetailSerializer(sample_obj)
    return Response(response_serializer.data, status=status.HTTP_200_OK)

# FIXME: It requires bioinfo post endpoint before testing
@extend_schema_view(
    get=extend_schema(
        parameters=[
            inline_serializer(
                name="SampleMetadataQuery",
                fields={
                    "classification": serializers.ListField(
                        child=serializers.CharField(), required=False
                    ),
                    "property": serializers.ListField(
                        child=serializers.CharField(), required=False
                    ),
                },
            )
        ],
        responses={
            200: core.api.serializers.SampleMetadataItemSerializer(many=True),
            401: core.api.serializers.ErrorSerializer,
            403: core.api.serializers.ErrorSerializer,
            404: core.api.serializers.ErrorSerializer,
            400: core.api.serializers.ErrorSerializer,
        },
    ),
    post=extend_schema(
        request=core.api.serializers.SampleMetadataIngestSerializer,
        responses={
            201: core.api.serializers.SampleMetadataIngestResponseSerializer,
            400: core.api.serializers.ErrorSerializer,
            401: core.api.serializers.ErrorSerializer,
            403: core.api.serializers.ErrorSerializer,
            404: core.api.serializers.ErrorSerializer,
        },
    ),
)
@authentication_classes([SessionAuthentication, BasicAuthentication])
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def sample_metadata_view(request, sample_unique_id):
    sample_obj = sample_detail.get_sample_detail(sample_unique_id)
    if sample_obj is None:
        return Response({"error": "Sample not found"}, status=status.HTTP_404_NOT_FOUND)

    # GET method
    if request.method == "GET":
        classifications = request.query_params.getlist("classification")
        properties = request.query_params.getlist("property")
        if len(classifications) == 1 and "," in classifications[0]:
            classifications = [
                item.strip() for item in classifications[0].split(",") if item.strip()
            ]
        if len(properties) == 1 and "," in properties[0]:
            properties = [
                item.strip() for item in properties[0].split(",") if item.strip()
            ]

        filter_data = {}
        if classifications:
            filter_data["classification"] = classifications
        if properties:
            filter_data["property"] = properties

        if filter_data:
            filter_serializer = core.api.serializers.SampleMetadataFilterSerializer(
                data=filter_data
            )
            filter_serializer.is_valid(raise_exception=True)
            classifications = filter_serializer.validated_data.get("classification")
            properties = filter_serializer.validated_data.get("property")

        metadata_list = sample_metadata.list_sample_metadata(
            sample_obj,
            classifications=classifications or None,
            properties=properties or None,
        )
        response_serializer = core.api.serializers.SampleMetadataItemSerializer(
            metadata_list, many=True
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    # POST method
    if not request.user.is_staff:
        return Response(
            {"error": "Admin privileges required"},
            status=status.HTTP_403_FORBIDDEN,
        )
    serializer = core.api.serializers.SampleMetadataIngestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    payload = serializer.validated_data["payload"]

    schema_name = serializer.validated_data.get("schema_name")
    schema_version = serializer.validated_data.get("schema_version")
    if schema_name and schema_version:
        schema_obj = core.models.Schema.objects.filter(
            schema_name=schema_name, schema_version=schema_version
        ).last()
        if schema_obj is None:
            return Response(
                {"error": "Schema not found for provided name/version"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if sample_obj.schema_obj_id and sample_obj.schema_obj_id != schema_obj.id:
            return Response(
                {"error": "Schema does not match sample schema"},
                status=status.HTTP_400_BAD_REQUEST,
            )
    else:
        schema_obj = sample_obj.schema_obj
        if schema_obj is None:
            return Response(
                {"error": "Sample has no schema assigned"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    try:
        stored_count = sample_metadata_ingestion.ingest_sample_metadata(
            sample_obj, schema_obj, payload
        )
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    if stored_count:
        state_obj = core.models.SampleState.objects.filter(state__exact="Bioinfo").last()
        if state_obj is None:
            return Response(
                {"error": "Sample state 'Bioinfo' not configured"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            result = core.api.utils.common_functions.add_sample_state_history(
                sample_obj, state_id=state_obj.pk, error_name="No error"
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if isinstance(result, Response):
            return result

    response_serializer = core.api.serializers.SampleMetadataIngestResponseSerializer(
        data={"sample_unique_id": sample_unique_id, "stored_count": stored_count}
    )
    response_serializer.is_valid(raise_exception=True)
    return Response(response_serializer.data, status=status.HTTP_201_CREATED)

######################### TODO: refactor or remove ###########
# TODO: add validate step. relecov tool.
@extend_schema(
    examples=[
        OpenApiExample(
            "Example",
            description="Variant example",
            value={
                "analysis_authors": "",
                "author_submitter": "",
                "authors": "",
                "experiment_alias": "",
                "experiment_title": "",
                "fastq_r1_md5": "b5242d60471e5a5a97b35531dbbe8c30",
                "fastq_r2_md5": "57525c5a1ec992098e652aa01b366d69",
                "gisaid_id": "EPI_ISL_8625444",
                "microbiology_lab_sample_id": "20183102",
                "r1_fastq_filepath": "/media/data/relecov/",
                "r2_fastq_filepath": "/media/data/relecov/",
                "schema_name": "relecov",
                "schema_version": "",
                "sequence_file_R1_fastq": "20183102_R1.fastq.gz",
                "sequence_file_R2_fastq": "20183102_R2.fastq.gz",
                "sequencing_sample_id": "20183102",
                "study_alias": "",
                "study_id": "",
                "study_title": "",
                "study_type": "Whole Genome Sequencing",
                "submitting_lab_sample_id": "LAB_856232",
            },
        )
    ],
    request=inline_serializer(
        name="createSample",
        fields={
            "analysis_authors": serializers.CharField(required=False),
            "author_submitter": serializers.CharField(required=False),
            "authors": serializers.CharField(required=False),
            "experiment_alias": serializers.CharField(required=False),
            "experiment_title": serializers.CharField(required=False),
            "fastq_r1_md5": serializers.CharField(),
            "fastq_r2_md5": serializers.CharField(),
            "gisaid_id": serializers.CharField(required=False),
            "microbiology_lab_sample_id": serializers.CharField(),
            "r1_fastq_filepath": serializers.CharField(),
            "r2_fastq_filepath": serializers.CharField(),
            "schema_name": serializers.CharField(),
            "schema_version": serializers.CharField(),
            "sequence_file_R1_fastq": serializers.CharField(),
            "sequence_file_R2_fastq": serializers.CharField(),
            "sequencing_sample_id": serializers.CharField(),
            "study_alias": serializers.CharField(required=False),
            "study_id": serializers.CharField(required=False),
            "study_title": serializers.CharField(required=False),
            "study_type": serializers.CharField(required=False),
            "submitting_lab_sample_id": serializers.CharField(),
        },
    ),
    description="More descriptive text",
    responses={
        201: OpenApiResponse(description="Successful upload information"),
        400: OpenApiResponse(description="Bad request"),
        500: OpenApiResponse(description="Internal Server Error"),
    },
)
@authentication_classes([SessionAuthentication, BasicAuthentication])
@api_view(["POST"])
@permission_classes([IsAuthenticated])
# FIXME: When input data has not ENA value, it returns 404, but samples were successfully added to database.
#          - Proposal: emit a warning message instead
def create_sample_data(request):
    if request.method == "POST":
        data = request.data
        if isinstance(data, QueryDict):
            data = data.dict()
        schema_obj = core.api.utils.common_functions.get_schema_version_if_exists(data)
        if schema_obj is None:
            error = {"ERROR": "schema name and version is not defined"}
            return Response(error, status=status.HTTP_400_BAD_REQUEST)
        schema_id = schema_obj.get_schema_id()

        # check if sample id field and collecting_institution are in the request
        if "sequencing_sample_id" not in data or "collecting_institution" not in data:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # check if sample is already defined
        sample_obj = core.utils.samples.get_sample_obj_from_sample_name(
            data["sequencing_sample_id"]
        )
        if sample_obj:
            error = "Sample already defined"
            error_name_value = core.models.ErrorName.objects.filter(
                error_name=error
            ).first()
            if error_name_value:
                core.api.utils.common_functions.add_sample_state_history(
                    sample_obj,
                    state_id=None,
                    error_name=error,
                )
            return Response(error, status=status.HTTP_400_BAD_REQUEST)

        # get the user to assign the sample based on the collecting_institution
        # value. If lab is not define user field is set t
        split_data = core.api.utils.samples.split_sample_data(data)
        # Add schema id to store in database
        split_data["sample"]["schema_obj"] = schema_id
        sample_serializer = core.api.serializers.CreateSampleSerializer(
            data=split_data["sample"]
        )
        if not sample_serializer.is_valid():
            return Response(
                sample_serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )
        sample_obj = sample_serializer.save()
        sample_id = sample_obj.get_sample_id()

        # Add initial state history (after creating the sample)
        is_first_entry = not core.models.SampleStateHistory.objects.filter(
            sample=sample_obj
        ).exists()
        if is_first_entry:
            error_name_value = (
                core.models.ErrorName.objects.filter(pk=1)
                .values_list("error_name", flat=True)
                .first()
            )
            core.api.utils.common_functions.add_sample_state_history(
                sample_obj,
                state_id=split_data["sample"]["state"],
                error_name=error_name_value,
            )

        # Save ENA info if included
        if len(split_data["ena"]) > 0:
            state_id = (
                core.models.SampleState.objects.filter(state__exact="Ena")
                .last()
                .get_state_id()
            )
            result = core.api.utils.public_db.store_pub_databases_data(
                split_data["ena"], "ena", schema_obj, sample_id
            )
            if "ERROR" in result:
                error = "Failed to store data"
                core.api.utils.common_functions.add_sample_state_history(
                    sample_obj,
                    state_id=state_id,
                    error_name=error,
                )
                return Response(result, status=status.HTTP_206_PARTIAL_CONTENT)
            # check that the ena_sample_accession is not empty or "Not Provided"
            # TODO: should this be optional? Errors suggest that the sample was not recorded.
            if (
                split_data["ena"]["ena_sample_accession"] != "Not Provided"
                and split_data["ena"]["ena_sample_accession"] != ""
                and split_data["ena"]["ena_sample_accession"] is not None
            ):
                # Save entry in update state table for valid ena_sample_accession
                try:
                    core.api.utils.common_functions.add_sample_state_history(
                        sample_obj,
                        state_id=state_id,
                        error_name="No error",
                    )
                except ValueError:
                    error = "Failed to update sample state history due to invalid state or missing data"
                    core.api.utils.common_functions.add_sample_state_history(
                        sample_obj,
                        state_id=state_id,
                        error_name=error,
                    )
                    return Response(
                        {"ERROR": error}, status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                error = "Accession empty or not provided"
                core.api.utils.common_functions.add_sample_state_history(
                    sample_obj,
                    state_id=state_id,
                    error_name=error,
                )
                return Response({"ERROR": error}, status=status.HTTP_400_BAD_REQUEST)

        # Save GISAID info if included
        if len(split_data["gisaid"]) > 0:
            state_id = (
                core.models.SampleState.objects.filter(state__exact="Gisaid")
                .last()
                .get_state_id()
            )
            if "EPI_ISL" in split_data["gisaid"]["gisaid_accession_id"]:
                result = core.api.utils.public_db.store_pub_databases_data(
                    split_data["gisaid"], "gisaid", schema_obj, sample_id
                )
                if "ERROR" in result:
                    error = "Failed to store data"
                    core.api.utils.common_functions.add_sample_state_history(
                        sample_obj,
                        state_id=state_id,
                        error_name=error,
                    )
                    return Response(result, status=status.HTTP_400_BAD_REQUEST)
                # Save entry in update state table
                sample_obj.update_state("Gisaid")
                try:
                    core.api.utils.common_functions.add_sample_state_history(
                        sample_obj,
                        state_id=state_id,
                        error_name="No error",
                    )
                except ValueError as e:
                    error = "Failed to update sample state history due to invalid state or missing data"
                    core.api.utils.common_functions.add_sample_state_history(
                        sample_obj,
                        state_id=state_id,
                        error_name=error,
                    )
                    return Response(
                        {"ERROR": str(e)}, status=status.HTTP_400_BAD_REQUEST
                    )

        # Save AUTHOR info if included
        if len(split_data["author"]) > 0:
            result = core.api.utils.public_db.store_pub_databases_data(
                split_data["author"], "author", schema_obj, sample_id
            )
            if "ERROR" in result:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response("Successful upload information", status=status.HTTP_201_CREATED)


@extend_schema(
    examples=[
        OpenApiExample(
            "Example",
            description="Variant example",
            value={
                "analysis_date": "20220705",
                "assembly": "None",
                "assembly_params": "None",
                "bioinformatics_protocol_software_name": "nf-core/viralrecon",
                "bioinformatics_protocol_software_version": "2.4.1",
                "commercial_open_source_both": "Open Source",
                "consensus_genome_length": "29884",
                "consensus_params": "-p vcf -f",
                "consensus_sequence_filename": "2018086.consensus.fa",
                "consensus_sequence_filepath": "/data/COD-2100/20220720",
                "consensus_sequence_md5": "8853df0702f68d4e50bb3aab59a59df9",
                "consensus_sequence_name": "21578522",
                "consensus_sequence_software_name": "BCFTOOLS_CONSENSUS",
                "consensus_sequence_software_version": "1.14",
                "dehosting_method_software_name": "KRAKEN2_KRAKEN2",
                "dehosting_method_software_version": "2.1.2",
                "depth_of_coverage_threshold": ">10x",
                "depth_of_coverage_value": "1804.46",
                "if_consensus_other": "None",
                "if_enrichment_panel_assay_is_other_specify": "Not Provided",
                "if_enrichment_protocol_is_other_specify": "Not Provided",
                "if_lineage_identification_other": "None",
                "if_mapping_other": "None",
                "if_preprocessing_other": "None",
                "lineage_algorithm_software_version": "PUSHER-v1.9",
                "lineage_analysis_constellation_version": "v0.1.10",
                "lineage_analysis_date": "2022-07-05",
                "lineage_analysis_scorpio_version": "0.3.17",
                "lineage_analysis_software_name": "pangolin",
                "lineage_analysis_software_version": "4.0.6",
                "lineage_name": "B.1.1.7",
                "long_table_path": "",
                "mapping_params": "--seed 1",
                "mapping_software_name": "BOWTIE2_ALIGN",
                "mapping_software_version": "2.4.4",
                "number_of_base_pairs_sequenced": "9024968",
                "number_of_samples_in_run": "60",
                "number_of_variants_in_consensus": "34",
                "number_of_variants_with_effect": "22",
                "per_Ns": "1.63",
                "per_genome_greater_10x": "99.66",
                "per_reads_host": "0.23",
                "per_reads_virus": "99.7446",
                "per_unmapped": "0.0223003",
                "preprocessing_params": "--cut_front --cut_tail --trim_poly_x --cut_mean_quality 30 --qualified_quality_phred 30 --unqualified_percent_limit 10 --length_required 50",
                "preprocessing_software_name": "FASTP",
                "preprocessing_software_version": "0.23.2",
                "qc_filtered": "573984",
                "reference_genome_accession": "NC_045512.2",
                "schema_name": "RELECOV schema",
                "schema_version": "1.0.0",
                "sequence_file_R1_fastq": "2018086_R1.fastq.gz",
                "sequence_file_R1_md5": "eab8b05ef27f4f5cba5cddf6ad627de2",
                "sequence_file_R2_fastq": "2018086_R2.fastq.gz",
                "sequence_file_R2_md5": "d82a37aa970df2b8bf8f547ca7c18ac8",
                "sequencing_sample_id": "254866",
                "variant_calling_params": "--ignore-overlaps --count-orphans --no-BAQ --max-depth 0 --min-BQ 0';-t 0.25 -q 20 -m 10",
                "variant_calling_software_name": "IVAR_VARIANTS",
                "variant_calling_software_version": "1.3.1",
                "variant_name": "Alpha (B.1.1.7-like)",
            },
        )
    ],
    request=inline_serializer(
        name="create_metadata_value",
        fields={
            "analysis_date": serializers.CharField(),
            "assembly": serializers.CharField(),
            "assembly_params": serializers.CharField(),
            "bioinformatics_protocol_software_name": serializers.CharField(),
            "bioinformatics_protocol_software_version": serializers.CharField(),
            "commercial_open_source_both": serializers.CharField(),
            "consensus_genome_length": serializers.CharField(),
            "consensus_params": serializers.CharField(),
            "consensus_sequence_filename": serializers.CharField(),
            "consensus_sequence_filepath": serializers.CharField(),
            "consensus_sequence_md5": serializers.CharField(),
            "consensus_sequence_name": serializers.CharField(),
            "consensus_sequence_software_name": serializers.CharField(),
            "consensus_sequence_software_version": serializers.CharField(),
            "dehosting_method_software_name": serializers.CharField(),
            "dehosting_method_software_version": serializers.CharField(),
            "depth_of_coverage_threshold": serializers.CharField(),
            "depth_of_coverage_value": serializers.CharField(),
            "if_assembly_other": serializers.CharField(required=False),
            "if_bioinformatic_protocol_is_other_specify": serializers.CharField(
                required=False
            ),
            "if_consensus_other": serializers.CharField(required=False),
            "if_lineage_identification_other": serializers.CharField(required=False),
            "if_mapping_other": serializers.CharField(required=False),
            "if_preprocessing_other": serializers.CharField(required=False),
            "lineage_algorithm_software_version": serializers.CharField(),
            "lineage_analysis_constellation_version": serializers.CharField(),
            "lineage_analysis_date": serializers.CharField(),
            "lineage_analysis_scorpio_version": serializers.CharField(),
            "lineage_analysis_software_name": serializers.CharField(),
            "lineage_analysis_software_version": serializers.CharField(),
            "lineage_name": serializers.CharField(),
            "long_table_path": serializers.CharField(),
            "mapping_params": serializers.CharField(),
            "mapping_software_name": serializers.CharField(),
            "mapping_software_version": serializers.CharField(),
            "ns_per_100_kbp": serializers.CharField(),
            "number_of_base_pairs_sequenced": serializers.CharField(),
            "number_of_variants_in_consensus": serializers.CharField(),
            "number_of_variants_with_effect": serializers.CharField(),
            "per_Ns": serializers.CharField(),
            "per_genome_greater_10x": serializers.CharField(),
            "per_reads_host": serializers.CharField(),
            "per_reads_virus": serializers.CharField(),
            "per_unmapped": serializers.CharField(),
            "preprocessing_params": serializers.CharField(),
            "preprocessing_software_name": serializers.CharField(),
            "preprocessing_software_version": serializers.CharField(),
            "qc_filtered": serializers.CharField(),
            "reference_genome_accession": serializers.CharField(),
            "schema_name": serializers.CharField(),
            "schema_version": serializers.CharField(),
            "sequence_file_R1_fastq": serializers.CharField(),
            "sequence_file_R1_md5": serializers.CharField(),
            "sequence_file_R2_fastq": serializers.CharField(),
            "sequence_file_R2_md5": serializers.CharField(),
            "sequencing_sample_id": serializers.CharField(),
            "variant_calling_params": serializers.CharField(),
            "variant_calling_software_name": serializers.CharField(),
            "variant_calling_software_version": serializers.CharField(),
            "variant_name": serializers.CharField(),
        },
    ),
    description="More descriptive text",
    responses={
        201: OpenApiResponse(description="Successful C information"),
        400: OpenApiResponse(description="Bad request"),
        500: OpenApiResponse(description="Internal Server Error"),
    },
)
@authentication_classes([SessionAuthentication, BasicAuthentication])
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_metadata_value(request):
    if request.method == "POST":
        data = request.data

    if isinstance(data, QueryDict):
        data = data.dict()
    # check schema (name and version)
    schema_obj = core.api.utils.common_functions.get_schema_version_if_exists(data)
    if schema_obj is None:
        error = {"ERROR": "schema name and version is not defined"}
        return Response(error, status=status.HTTP_400_BAD_REQUEST)
    if "sequencing_sample_id" not in data:
        return Response(
            {"ERROR": core.config.ERROR_SAMPLE_NAME_NOT_INCLUDED},
            status=status.HTTP_400_BAD_REQUEST,
        )
    sample_obj = core.utils.samples.get_sample_obj_from_sample_name(
        data["sequencing_sample_id"]
    )
    if sample_obj is None:
        return Response(
            {"ERROR": core.config.ERROR_SAMPLE_NOT_DEFINED},
            status=status.HTTP_400_BAD_REQUEST,
        )

    analysis_defined = core.api.utils.metadata_values.get_analysis_defined(sample_obj)
    # TODO: This field should be updated in order to make it more general
    analysis_date = data.get("lineage_analysis_date", None)
    if analysis_date is not None:
        if analysis_date in list(analysis_defined):
            return Response(
                {"ERROR": core.config.ERROR_ANALYSIS_ALREADY_DEFINED},
                status=status.HTTP_400_BAD_REQUEST,
            )
    # FIXME: 'analysis_date' create errors when it is none. A custom serializer that allows both specific date format and "not-provided" value should be added.
    stored_data = core.api.utils.metadata_values.store_metadata_values(
        data, schema_obj, analysis_date
    )
    if "ERROR" in stored_data:
        return Response(stored_data, status=status.HTTP_400_BAD_REQUEST)

    # Update state of sample:
    state_id = (
        core.models.SampleState.objects.filter(state__exact="Bioinfo")
        .last()
        .get_state_id()
    )
    try:
        core.api.utils.common_functions.add_sample_state_history(
            sample_obj, state_id=state_id, error_name="No error"
        )
    except ValueError as e:
        error = "Failed to store data"
        core.api.utils.common_functions.add_sample_state_history(
            sample_obj,
            state_id=state_id,
            error_name=error,
        )
        return Response({"ERROR": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(status=status.HTTP_201_CREATED)


@extend_schema(
    examples=[
        OpenApiExample(
            "Example",
            description="Variant example",
            value={
                "sample_name": "sample_name_12345",
                "variants": [
                    {
                        "Chromosome": "NC_045512.2",
                        "Variant": {"pos": "11287", "alt": "G", "ref": "GTCTGGTTTT"},
                        "Filter": "PASS",
                        "VariantInSample": {
                            "dp": "1322",
                            "ref_dp": "1312",
                            "alt_dp": "1197",
                            "af": "0.91",
                        },
                        "Gene": "orf1ab",
                        "Effect": "conservative_inframe_deletion",
                        "VariantAnnotation": {
                            "hgvs_c": "c.11023_11031delTCTGGTTTT",
                            "hgvs_p": "p.Ser3675_Phe3677del",
                            "hgvs_p_1_letter": "p.S3675_F3677del",
                        },
                    },
                    {
                        "Chromosome": "NC_045512.2",
                        "Variant": {"pos": "13386", "alt": "A", "ref": "G"},
                        "Filter": "PASS",
                        "VariantInSample": {
                            "dp": "14750",
                            "ref_dp": "8029",
                            "alt_dp": "6307",
                            "af": "0.43",
                        },
                        "Gene": "orf1ab",
                        "Effect": "missense_variant",
                        "VariantAnnotation": {
                            "hgvs_c": "c.13121G>A",
                            "hgvs_p": "p.Gly4374Asp",
                            "hgvs_p_1_letter": "p.G4374D",
                        },
                    },
                ],
            },
        )
    ],
    description="Store variants found for the sample",
    responses={
        201: OpenApiResponse(description="Successful upload information"),
        400: OpenApiResponse(description="Bad request"),
        500: OpenApiResponse(description="Internal Server Error"),
    },
    request=inline_serializer(
        name="VariantUpload",
        fields={
            "sample_name": serializers.CharField(),
            "Variants": inline_serializer(
                name="variant",
                fields={
                    "Chromosome": serializers.CharField(),
                    "variant": inline_serializer(
                        name="variant",
                        fields={
                            "pos": serializers.CharField(),
                            "alt": serializers.CharField(),
                            "ref": serializers.CharField(),
                        },
                    ),
                    "Filter": serializers.CharField(),
                    "VariantInSample": inline_serializer(
                        name="VariantInSample",
                        fields={
                            "dp": serializers.CharField(),
                            "ref_dp": serializers.CharField(),
                            "alt_dp": serializers.CharField(),
                            "af": serializers.CharField(),
                        },
                    ),
                    "Gene": serializers.CharField(),
                    "Effect": serializers.CharField(),
                    "VariantAnnotation": inline_serializer(
                        name="VariantAnnotation",
                        fields={
                            "hgvs_c": serializers.CharField(),
                            "hgvs_p": serializers.CharField(),
                            "hgvs_p_1_letter": serializers.CharField(),
                        },
                        allow_null=True,
                    ),
                },
            ),
        },
    ),
)

@extend_schema(
    examples=[
        OpenApiExample(
            name="update sample state",
            value={"sample_name": "sample_number_12345", "state": "Bioinfo"},
        )
    ],
    request=inline_serializer(
        name="UpdateState",
        fields={
            "sample_name": serializers.CharField(),
            "state": serializers.CharField(),
        },
        allow_null=True,
    ),
    responses={
        201: OpenApiResponse(description="Successful. sample state updated"),
        400: OpenApiResponse(description="Bad Request"),
        500: OpenApiResponse(description="Internal Server Error"),
    },
)
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
@api_view(["PUT"])
def update_state(request):
    if request.method == "PUT":
        data = request.data
        if isinstance(data, QueryDict):
            data = data.dict()

        # Attach the user making the request
        data["user"] = request.user.pk

        # Fetch the sample object by its name
        sample_obj = core.utils.samples.get_sample_obj_from_sample_name(
            data["sample_name"]
        )

        # Catch errors during the execution
        errors = []
        if sample_obj is None:
            return Response(
                core.config.ERROR_SAMPLE_NOT_DEFINED, status=status.HTTP_400_BAD_REQUEST
            )

        # Validate the new state exists
        new_state_obj = core.models.SampleState.objects.filter(
            state=data["state"]
        ).last()

        # Catch errors during the execution
        if not new_state_obj:
            errors.append(
                {
                    "error_name": "The specified state does not exist",
                    "http_status": status.HTTP_400_BAD_REQUEST,
                }
            )

        # Add new sample state in history records
        try:
            core.api.utils.common_functions.add_sample_state_history(
                sample_obj=sample_obj,
                state_id=new_state_obj.pk if new_state_obj else None,
                error_name="No errors",
            )
        except ValueError as e:
            error = "Failed to update sample state history due to invalid state or missing data"
            core.api.utils.common_functions.add_sample_state_history(
                sample_obj,
                state_id=new_state_obj.pk if new_state_obj else None,
                error_name=error,
            )
            return Response({"ERROR": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Return response of error encountered while updating sample state
        if len(errors) > 0:
            return Response(
                errors[0]["error_name"],
                status=errors[0]["http_status"],
            )
        else:
            return Response(
                "Successful: sample state updated and history recorded.",
                status=status.HTTP_201_CREATED,
            )
    else:
        return Response(status=status.HTTP_400_BAD_REQUEST)
