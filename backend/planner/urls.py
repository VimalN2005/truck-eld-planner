from django.urls import path
from .views import (
    create_trip,
    register_user,
    login_user,
    logout_user,
    get_current_user,
    update_driver_profile,
    get_trips,
    get_trip_details,
    ai_assistant_query
)

urlpatterns = [
    path("trip/", create_trip, name="create_trip"),
    path("register/", register_user, name="register"),
    path("login/", login_user, name="login"),
    path("logout/", logout_user, name="logout"),
    path("user/", get_current_user, name="user"),
    path("profile/", update_driver_profile, name="profile"),
    path("trips/", get_trips, name="trips"),
    path("trips/<int:pk>/", get_trip_details, name="trip_details"),
    path("ai/", ai_assistant_query, name="ai_query"),
]