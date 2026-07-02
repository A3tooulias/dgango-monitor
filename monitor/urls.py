from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("thresholds/", views.thresholds_page, name="thresholds-page"),
    path("api/ingest/", views.IngestReadingView.as_view(), name="api-ingest"),
    path("api/devices/", views.DeviceListView.as_view(), name="api-devices"),
    path("api/devices/<int:device_id>/readings/", views.DeviceReadingsView.as_view(), name="api-device-readings"),
    path("api/thresholds/", views.ThresholdRuleListCreateView.as_view(), name="api-thresholds"),
    path("api/thresholds/<int:pk>/", views.ThresholdRuleDetailView.as_view(), name="api-threshold-detail"),
]
