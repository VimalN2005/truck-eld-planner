from django.db import models
from django.contrib.auth.models import User

class DriverProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    driver_id = models.CharField(max_length=50, blank=True, default="")
    truck_number = models.CharField(max_length=50, blank=True, default="")
    carrier_name = models.CharField(max_length=100, blank=True, default="")
    current_cycle_used = models.FloatField(default=0.0)
    truck_mpg = models.FloatField(default=6.5)
    fuel_price_preset = models.FloatField(default=4.00)

    def __str__(self):
        return f"{self.user.username}'s Profile"

class Trip(models.Model):
    driver = models.ForeignKey(DriverProfile, on_delete=models.CASCADE, related_name="trips", null=True, blank=True)
    current_location = models.CharField(max_length=255)
    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255)
    cycle_used = models.FloatField()
    total_distance = models.FloatField()
    total_driving_hours = models.FloatField()
    fuel_required = models.FloatField(default=0.0)
    fuel_cost = models.FloatField(default=0.0)
    total_trip_cost = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Store complete coordinate pathways, HOS schedules and log breakdowns
    details = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.current_location} -> {self.pickup_location} -> {self.dropoff_location}"
