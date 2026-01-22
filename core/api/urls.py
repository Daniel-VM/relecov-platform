# Generic imports
from django.urls import path

# Local imports
import core.api.views

app_name = "relecov_api"

# TODO: remove "api" layer from path once stable
urlpatterns = [
    path("samples", core.api.views.samples, name="samples"),
    path(
        "samples/metadata",
        core.api.views.sample_metadata_property_view,
        name="sample_metadata_property",
    ),
    path(
        "samples/metadata/search",
        core.api.views.sample_metadata_search_view,
        name="sample_metadata_search",
    ),
    path(
        "samples/history",
        core.api.views.sample_history_view,
        name="sample_history",
    ),
    path(
        "samples/<str:sample_unique_id>/history",
        core.api.views.sample_history_detail_view,
        name="sample_history_detail",
    ),
    path(
        "samples/<str:sample_unique_id>",
        core.api.views.sample_detail_view,
        name="sample_detail",
    ),
    path(
        "samples/<str:sample_unique_id>/metadata",
        core.api.views.sample_metadata_view,
        name="sample_metadata",
    ),
]
