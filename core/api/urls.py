# Generic imports
from django.urls import path

# Local imports
import core.api.views

app_name = "relecov_api"

# TODO: remove "api" layer from path once stable
urlpatterns = [
    path("samples", core.api.views.samples, name="samples"),
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
    #path(
    #    "createBioinfoData",
    #    core.api.views.create_metadata_value,
    #    name="create_metadata_value",
    #),
    # path(
    #     "createSampleData",
    #     core.api.views.create_sample_data,
    #     name="create_sample_data",
    # ),
    path("updateState", core.api.views.update_state, name="update_state"),
]
