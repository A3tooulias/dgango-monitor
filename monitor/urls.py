from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("thresholds/", views.thresholds_page, name="thresholds-page"),

    path("api/ingest/", views.IngestReadingView.as_view(), name="api-ingest"),
    path("api/ecowitt/", views.EcowittIngestView.as_view(), name="api-ecowitt"),
    path("api/devices/", views.DeviceListView.as_view(), name="api-devices"),
    path("api/devices/<int:device_id>/readings/", views.DeviceReadingsView.as_view(), name="api-device-readings"),

    path("api/risk-levels/", views.RiskLevelListView.as_view(), name="api-risk-levels"),
    path("api/risk-levels/<int:pk>/", views.RiskLevelDetailView.as_view(), name="api-risk-level-detail"),

    path("api/heat-table/", views.HeatIndexRowListCreateView.as_view(), name="api-heat-table"),
    path("api/heat-table/<int:pk>/", views.HeatIndexRowDetailView.as_view(), name="api-heat-table-detail"),
    path("api/heat-table/load-moderate/", views.LoadModerateTableView.as_view(), name="api-heat-table-preset"),
    path("api/settings/", views.SystemSettingsView.as_view(), name="api-settings"),
    path("api/map-data/", views.MapDataView.as_view(), name="api-map-data"),
    path("api/geocode-search/", views.GeocodeSearchView.as_view(), name="api-geocode-search"),
]
