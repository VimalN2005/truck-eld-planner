import math
import requests

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status


# -----------------------------------
# GET LOCATION COORDINATES
# -----------------------------------
def get_coordinates(location):

    url = "https://nominatim.openstreetmap.org/search"

    params = {
        "q": location,
        "format": "json",
        "limit": 1
    }

    headers = {
        "User-Agent": "TruckTripPlanner/1.0"
    }

    response = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=15
    )

    response.raise_for_status()

    data = response.json()

    if not data:
        return None

    return {
        "lat": float(data[0]["lat"]),
        "lon": float(data[0]["lon"])
    }


# -----------------------------------
# GET ROUTE INFORMATION + MAP GEOMETRY
# -----------------------------------
def get_route(start, end):

    url = (
        f"https://router.project-osrm.org/route/v1/driving/"
        f"{start['lon']},{start['lat']};"
        f"{end['lon']},{end['lat']}"
    )

    params = {
        "overview": "full",
        "geometries": "geojson"
    }

    response = requests.get(
        url,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    if data.get("code") != "Ok":
        return None

    routes = data.get("routes", [])

    if not routes:
        return None

    route = routes[0]

    distance_miles = route["distance"] / 1609.344
    duration_hours = route["duration"] / 3600

    # OSRM gives coordinates as:
    # [longitude, latitude]
    #
    # Leaflet needs:
    # [latitude, longitude]

    route_coordinates = [
        [point[1], point[0]]
        for point in route["geometry"]["coordinates"]
    ]

    return {
        "distance_miles": round(distance_miles, 1),
        "duration_hours": round(duration_hours, 1),
        "coordinates": route_coordinates
    }


# -----------------------------------
# HOS CALCULATION ENGINE + ELD LOG
# -----------------------------------
def calculate_hos(total_driving_hours, cycle_used):

    DAILY_DRIVING_LIMIT = 11
    CYCLE_LIMIT = 70
    OFF_DUTY_REST = 10
    BREAK_DURATION = 0.5

    # Avoid division / calculation issues
    if total_driving_hours <= 0:
        driving_days = 0
    else:
        driving_days = math.ceil(
            total_driving_hours / DAILY_DRIVING_LIMIT
        )

    # Simplified estimate
    required_breaks = math.floor(
        total_driving_hours / 8
    )

    available_cycle_hours = max(
        0,
        CYCLE_LIMIT - cycle_used
    )

    # Cycle status
    if total_driving_hours <= available_cycle_hours:
        cycle_status = "Within available cycle hours"
    else:
        cycle_status = (
            "Cycle limit may require a 34-hour restart"
        )

    # -----------------------------------
    # DAILY SCHEDULE + ELD LOG
    # -----------------------------------

    remaining_hours = total_driving_hours
    daily_schedule = []

    for day in range(1, driving_days + 1):

        driving_hours = min(
            DAILY_DRIVING_LIMIT,
            remaining_hours
        )

        # Break if driving is 8 or more hours
        break_required = driving_hours >= 8

        break_hours = (
            BREAK_DURATION
            if break_required
            else 0
        )

        eld_log = {
            "offDutyHours": OFF_DUTY_REST,
            "drivingHours": round(driving_hours, 1),
            "breakHours": break_hours,
            "onDutyHours": 0
        }

        daily_schedule.append({
            "day": day,
            "drivingHours": round(driving_hours, 1),
            "status": "Planned",
            "eldLog": eld_log
        })

        remaining_hours -= driving_hours

    return {
        "dailyDrivingLimit": DAILY_DRIVING_LIMIT,

        "totalDrivingRequired": round(
            total_driving_hours,
            1
        ),

        "estimatedDrivingDays": driving_days,

        "requiredBreaks": required_breaks,

        "availableCycleHours": round(
            available_cycle_hours,
            1
        ),

        "cycleStatus": cycle_status,

        "dailySchedule": daily_schedule
    }


# -----------------------------------
# CREATE TRIP API
# -----------------------------------
@api_view(["POST"])
def create_trip(request):

    # -----------------------------------
    # GET REQUEST DATA
    # -----------------------------------

    current_location = request.data.get(
        "currentLocation"
    )

    pickup_location = request.data.get(
        "pickupLocation"
    )

    dropoff_location = request.data.get(
        "dropoffLocation"
    )

    cycle_used = request.data.get(
        "cycleUsed"
    )

    # -----------------------------------
    # VALIDATION
    # -----------------------------------

    if not current_location:
        return Response(
            {
                "error": "Current location is required"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    if not pickup_location:
        return Response(
            {
                "error": "Pickup location is required"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    if not dropoff_location:
        return Response(
            {
                "error": "Dropoff location is required"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    if cycle_used is None or cycle_used == "":
        return Response(
            {
                "error": "Cycle hours are required"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    try:

        # -----------------------------------
        # VALIDATE CYCLE HOURS
        # -----------------------------------

        cycle_used = float(cycle_used)

        if cycle_used < 0 or cycle_used > 70:

            return Response(
                {
                    "error":
                    "Cycle hours must be between 0 and 70"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # -----------------------------------
        # GET LOCATION COORDINATES
        # -----------------------------------

        current_coords = get_coordinates(
            current_location
        )

        if not current_coords:
            return Response(
                {
                    "error":
                    f"Could not find location: {current_location}"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        pickup_coords = get_coordinates(
            pickup_location
        )

        if not pickup_coords:
            return Response(
                {
                    "error":
                    f"Could not find location: {pickup_location}"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        dropoff_coords = get_coordinates(
            dropoff_location
        )

        if not dropoff_coords:
            return Response(
                {
                    "error":
                    f"Could not find location: {dropoff_location}"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # -----------------------------------
        # CALCULATE ROUTES
        # -----------------------------------

        route1 = get_route(
            current_coords,
            pickup_coords
        )

        route2 = get_route(
            pickup_coords,
            dropoff_coords
        )

        if not route1 or not route2:

            return Response(
                {
                    "error":
                    "Could not calculate route"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # -----------------------------------
        # TOTAL DISTANCE
        # -----------------------------------

        total_distance = (
            route1["distance_miles"]
            + route2["distance_miles"]
        )

        # -----------------------------------
        # TOTAL DRIVING TIME
        # -----------------------------------

        total_duration = (
            route1["duration_hours"]
            + route2["duration_hours"]
        )

        # -----------------------------------
        # HOS CALCULATION
        # -----------------------------------

        hos_data = calculate_hos(
            total_duration,
            cycle_used
        )

        # -----------------------------------
        # FINAL RESPONSE
        # -----------------------------------

        return Response(
            {
                "message":
                "Trip plan generated successfully!",

                "trip": {

                    # LOCATIONS
                    "currentLocation":
                    current_location,

                    "pickupLocation":
                    pickup_location,

                    "dropoffLocation":
                    dropoff_location,

                    # COORDINATES FOR LEAFLET MAP
                    "currentCoordinates":
                    current_coords,

                    "pickupCoordinates":
                    pickup_coords,

                    "dropoffCoordinates":
                    dropoff_coords,

                    # CYCLE
                    "cycleUsed":
                    cycle_used,

                    "availableCycleHours":
                    round(
                        70 - cycle_used,
                        1
                    ),

                    # ROUTE 1
                    "currentToPickup":
                    route1,

                    # ROUTE 2
                    "pickupToDropoff":
                    route2,

                    # TOTALS
                    "totalDistanceMiles":
                    round(
                        total_distance,
                        1
                    ),

                    "totalDrivingHours":
                    round(
                        total_duration,
                        1
                    ),

                    # HOS + ELD
                    "hos":
                    hos_data
                }
            },
            status=status.HTTP_200_OK
        )

    except requests.exceptions.Timeout:

        return Response(
            {
                "error":
                "Location or routing service timed out. Please try again."
            },
            status=status.HTTP_504_GATEWAY_TIMEOUT
        )

    except requests.exceptions.RequestException:

        return Response(
            {
                "error":
                "Unable to connect to location or routing service"
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    except ValueError:

        return Response(
            {
                "error":
                "Cycle hours must be a valid number"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    except Exception as error:

        print("Unexpected error:", error)

        return Response(
            {
                "error":
                "An unexpected error occurred"
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )