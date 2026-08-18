from django.urls import path
from .views import create_trip

urlpatterns = [
    path("trip/", create_trip, name="create_trip"),
]