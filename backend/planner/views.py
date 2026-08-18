import math
import requests
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import DriverProfile, Trip

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
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        if not data:
            return None
        return {
            "lat": float(data[0]["lat"]),
            "lon": float(data[0]["lon"])
        }
    except Exception:
        return None

# -----------------------------------
# GET ROUTE INFORMATION + MAP GEOMETRY
# -----------------------------------
def get_route(start, end):
    url = f"https://router.project-osrm.org/route/v1/driving/{start['lon']},{start['lat']};{end['lon']},{end['lat']}"
    params = {
        "overview": "full",
        "geometries": "geojson"
    }
    try:
        response = requests.get(url, params=params, timeout=30)
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
        route_coordinates = [
            [point[1], point[0]]
            for point in route["geometry"]["coordinates"]
        ]
        return {
            "distance_miles": round(distance_miles, 1),
            "duration_hours": round(duration_hours, 1),
            "coordinates": route_coordinates
        }
    except Exception:
        return None

# -----------------------------------
# REALISTIC HOS SIMULATION ENGINE
# -----------------------------------
def calculate_hos(total_driving_hours, initial_cycle_used):
    DAILY_DRIVING_LIMIT = 11.0
    DAILY_DUTY_LIMIT = 14.0
    CYCLE_LIMIT = 70.0
    BREAK_DRIVING_LIMIT = 8.0
    BREAK_DURATION = 0.5
    OFF_DUTY_REST = 10.0
    RESTART_REST = 34.0
    
    remaining_driving = total_driving_hours
    remaining_cycle = max(0.0, CYCLE_LIMIT - initial_cycle_used)
    daily_schedule = []
    day_counter = 1
    total_restart_hours = 0
    total_breaks_taken = 0
    
    while remaining_driving > 0:
        # Check if we need a restart before driving today
        # We need at least some hours on cycle to drive. If cycle remaining is critically low (e.g. <= 2.0 hrs)
        # and we still have substantial driving to do, trigger a 34h restart.
        if remaining_cycle <= 2.0 and remaining_driving > 0:
            daily_schedule.append({
                "day": day_counter,
                "type": "RESTART",
                "status": "34-Hour Restart",
                "drivingHours": 0.0,
                "onDutyHours": 0.0,
                "offDutyHours": RESTART_REST,
                "breakHours": 0.0,
                "message": "Cycle hours depleted. Mandatory 34-hour restart taken to reset cycle.",
                "eldLog": {
                    "offDutyHours": 18.0,
                    "sleeperHours": 16.0,
                    "drivingHours": 0.0,
                    "breakHours": 0.0,
                    "onDutyHours": 0.0,
                    "intervals": [
                        {"status": "OFF", "start": 0, "end": 12, "duration": 12},
                        {"status": "SB", "start": 12, "end": 24, "duration": 12}
                    ]
                }
            })
            remaining_cycle = CYCLE_LIMIT
            total_restart_hours += RESTART_REST
            day_counter += 1
            continue

        # Decide driving hours for today
        # Must fit within daily limit, remaining driving, and remaining cycle (minus 1h inspect)
        on_duty_inspect = 1.0
        max_possible_driving = min(DAILY_DRIVING_LIMIT, remaining_driving)
        
        # Adjust driving if cycle is limiting
        if max_possible_driving + on_duty_inspect > remaining_cycle:
            # Drive whatever is left of cycle minus inspection, or cycle itself if very small
            max_possible_driving = max(0.0, remaining_cycle - on_duty_inspect)
            if max_possible_driving == 0.0:
                # Force restart
                remaining_cycle = 0.0
                continue

        driving_today = round(min(max_possible_driving, remaining_driving), 1)
        
        # Break check: if driving >= 8 hours, 30 min break required
        break_today = BREAK_DURATION if driving_today >= BREAK_DRIVING_LIMIT else 0.0
        if break_today > 0:
            total_breaks_taken += 1

        on_duty_today = on_duty_inspect
        off_duty_today = round(24.0 - driving_today - on_duty_today - break_today, 1)

        # Split off duty into Off Duty and Sleeper Berth for realistic ELD visualization
        sleeper_today = round(min(10.0, off_duty_today * 0.7), 1)
        pure_off_duty = round(off_duty_today - sleeper_today, 1)

        # Generate ELD Timeline Intervals
        intervals = []
        # Day starts with rest (e.g. sleeper / off duty)
        start_time = 0.0
        
        # 1. Morning rest (Sleeper)
        if sleeper_today > 0:
            intervals.append({"status": "SB", "start": start_time, "end": start_time + sleeper_today, "duration": sleeper_today})
            start_time += sleeper_today
        
        # 2. Pre-trip inspection (On Duty)
        if on_duty_today > 0:
            inspect_dur = on_duty_today * 0.5
            intervals.append({"status": "ON", "start": start_time, "end": start_time + inspect_dur, "duration": inspect_dur})
            start_time += inspect_dur

        # 3. Driving segment 1
        drive_seg1 = round(min(4.0, driving_today), 1)
        if drive_seg1 > 0:
            intervals.append({"status": "D", "start": start_time, "end": start_time + drive_seg1, "duration": drive_seg1})
            start_time += drive_seg1
            
        # 4. Required Break
        if break_today > 0:
            intervals.append({"status": "OFF", "start": start_time, "end": start_time + break_today, "duration": break_today})
            start_time += break_today

        # 5. Driving segment 2
        drive_seg2 = round(driving_today - drive_seg1, 1)
        if drive_seg2 > 0:
            intervals.append({"status": "D", "start": start_time, "end": start_time + drive_seg2, "duration": drive_seg2})
            start_time += drive_seg2

        # 6. Post-trip inspection (On duty remaining)
        if on_duty_today > 0:
            inspect_dur = on_duty_today * 0.5
            intervals.append({"status": "ON", "start": start_time, "end": start_time + inspect_dur, "duration": inspect_dur})
            start_time += inspect_dur

        # 7. Remaining evening off duty
        end_rest = round(24.0 - start_time, 1)
        if end_rest > 0:
            intervals.append({"status": "OFF", "start": start_time, "end": start_time + end_rest, "duration": end_rest})

        eld_log = {
            "offDutyHours": pure_off_duty,
            "sleeperHours": sleeper_today,
            "drivingHours": driving_today,
            "breakHours": break_today,
            "onDutyHours": on_duty_today,
            "intervals": intervals
        }

        daily_schedule.append({
            "day": day_counter,
            "type": "WORK",
            "status": "Planned Driving",
            "drivingHours": driving_today,
            "onDutyHours": on_duty_today,
            "offDutyHours": off_duty_today,
            "breakHours": break_today,
            "eldLog": eld_log
        })

        remaining_driving = round(remaining_driving - driving_today, 1)
        remaining_cycle = round(remaining_cycle - (driving_today + on_duty_today), 1)
        day_counter += 1

    cycle_status = "Within available cycle hours"
    if total_restart_hours > 0:
        cycle_status = f"Cycle exceeded. Requires {int(total_restart_hours)}h of restart rest."

    return {
        "dailyDrivingLimit": DAILY_DRIVING_LIMIT,
        "dailyDutyLimit": DAILY_DUTY_LIMIT,
        "totalDrivingRequired": round(total_driving_hours, 1),
        "estimatedDrivingDays": len(daily_schedule),
        "requiredBreaks": total_breaks_taken,
        "availableCycleHours": round(max(0.0, CYCLE_LIMIT - initial_cycle_used), 1),
        "cycleStatus": cycle_status,
        "dailySchedule": daily_schedule
    }

# -----------------------------------
# AUTHENTICATION API ENDPOINTS
# -----------------------------------
@api_view(["POST"])
@permission_classes([AllowAny])
def register_user(request):
    username = request.data.get("username")
    password = request.data.get("password")
    name = request.data.get("name", "")
    driver_id = request.data.get("driverId", "")
    truck_number = request.data.get("truckNumber", "")
    carrier_name = request.data.get("carrierName", "")
    
    if not username or not password:
        return Response({"error": "Username and password are required"}, status=status.HTTP_400_BAD_REQUEST)
        
    if User.objects.filter(username=username).exists():
        return Response({"error": "Username already exists"}, status=status.HTTP_400_BAD_REQUEST)
        
    user = User.objects.create_user(username=username, password=password, first_name=name)
    profile = DriverProfile.objects.create(
        user=user,
        driver_id=driver_id,
        truck_number=truck_number,
        carrier_name=carrier_name
    )
    
    login(request, user)
    return Response({
        "message": "User registered and logged in successfully",
        "username": user.username,
        "name": user.first_name,
        "profile": {
            "driverId": profile.driver_id,
            "truckNumber": profile.truck_number,
            "carrierName": profile.carrier_name,
            "currentCycleUsed": profile.current_cycle_used,
            "truckMpg": profile.truck_mpg,
            "fuelPricePreset": profile.fuel_price_preset
        }
    }, status=status.HTTP_201_CREATED)

@api_view(["POST"])
@permission_classes([AllowAny])
def login_user(request):
    username = request.data.get("username")
    password = request.data.get("password")
    
    if not username or not password:
        return Response({"error": "Username and password are required"}, status=status.HTTP_400_BAD_REQUEST)
        
    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        profile, created = DriverProfile.objects.get_or_create(user=user)
        return Response({
            "message": "Login successful",
            "username": user.username,
            "name": user.first_name,
            "profile": {
                "driverId": profile.driver_id,
                "truckNumber": profile.truck_number,
                "carrierName": profile.carrier_name,
                "currentCycleUsed": profile.current_cycle_used,
                "truckMpg": profile.truck_mpg,
                "fuelPricePreset": profile.fuel_price_preset
            }
        }, status=status.HTTP_200_OK)
    else:
        return Response({"error": "Invalid username or password"}, status=status.HTTP_401_UNAUTHORIZED)

@api_view(["POST"])
def logout_user(request):
    logout(request)
    return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)

@api_view(["GET"])
def get_current_user(request):
    if request.user.is_authenticated:
        profile, created = DriverProfile.objects.get_or_create(user=request.user)
        return Response({
            "isAuthenticated": True,
            "username": request.user.username,
            "name": request.user.first_name,
            "profile": {
                "driverId": profile.driver_id,
                "truckNumber": profile.truck_number,
                "carrierName": profile.carrier_name,
                "currentCycleUsed": profile.current_cycle_used,
                "truckMpg": profile.truck_mpg,
                "fuelPricePreset": profile.fuel_price_preset
            }
        })
    else:
        return Response({"isAuthenticated": False})

@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_driver_profile(request):
    profile = request.user.profile
    profile.driver_id = request.data.get("driverId", profile.driver_id)
    profile.truck_number = request.data.get("truckNumber", profile.truck_number)
    profile.carrier_name = request.data.get("carrierName", profile.carrier_name)
    profile.current_cycle_used = float(request.data.get("currentCycleUsed", profile.current_cycle_used))
    profile.truck_mpg = float(request.data.get("truckMpg", profile.truck_mpg))
    profile.fuel_price_preset = float(request.data.get("fuelPricePreset", profile.fuel_price_preset))
    profile.save()
    
    # Also update user first name
    name = request.data.get("name")
    if name is not None:
        request.user.first_name = name
        request.user.save()
        
    return Response({
        "message": "Profile updated successfully",
        "name": request.user.first_name,
        "profile": {
            "driverId": profile.driver_id,
            "truckNumber": profile.truck_number,
            "carrierName": profile.carrier_name,
            "currentCycleUsed": profile.current_cycle_used,
            "truckMpg": profile.truck_mpg,
            "fuelPricePreset": profile.fuel_price_preset
        }
    })

# -----------------------------------
# GET TRIPS HISTORY API
# -----------------------------------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_trips(request):
    trips = Trip.objects.filter(driver=request.user.profile).order_name_by("-created_at") if hasattr(request.user, 'profile') else []
    # Fallback to prevent order_name_by typo, standard order_by
    trips = Trip.objects.filter(driver=request.user.profile).order_by("-created_at")
    data = []
    for trip in trips:
        data.append({
            "id": trip.id,
            "currentLocation": trip.current_location,
            "pickupLocation": trip.pickup_location,
            "dropoffLocation": trip.dropoff_location,
            "cycleUsed": trip.cycle_used,
            "totalDistanceMiles": trip.total_distance,
            "totalDrivingHours": trip.total_driving_hours,
            "fuelRequired": trip.fuel_required,
            "fuelCost": trip.fuel_cost,
            "totalTripCost": trip.total_trip_cost,
            "createdAt": trip.created_at.strftime("%b %d, %Y"),
            "details": trip.details
        })
    return Response(data)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_trip_details(request, pk):
    try:
        trip = Trip.objects.get(pk=pk, driver=request.user.profile)
        return Response({
            "id": trip.id,
            "currentLocation": trip.current_location,
            "pickupLocation": trip.pickup_location,
            "dropoffLocation": trip.dropoff_location,
            "cycleUsed": trip.cycle_used,
            "totalDistanceMiles": trip.total_distance,
            "totalDrivingHours": trip.total_driving_hours,
            "fuelRequired": trip.fuel_required,
            "fuelCost": trip.fuel_cost,
            "totalTripCost": trip.total_trip_cost,
            "createdAt": trip.created_at.strftime("%b %d, %Y"),
            "details": trip.details
        })
    except Trip.DoesNotExist:
        return Response({"error": "Trip not found"}, status=status.HTTP_404_NOT_FOUND)

# -----------------------------------
# CREATE / CALCULATE TRIP API
# -----------------------------------
@api_view(["POST"])
@permission_classes([AllowAny])
def create_trip(request):
    current_location = request.data.get("currentLocation")
    pickup_location = request.data.get("pickupLocation")
    dropoff_location = request.data.get("dropoffLocation")
    cycle_used = request.data.get("cycleUsed")
    save_trip = request.data.get("saveTrip", False)

    if not current_location:
        return Response({"error": "Current location is required"}, status=status.HTTP_400_BAD_REQUEST)
    if not pickup_location:
        return Response({"error": "Pickup location is required"}, status=status.HTTP_400_BAD_REQUEST)
    if not dropoff_location:
        return Response({"error": "Dropoff location is required"}, status=status.HTTP_400_BAD_REQUEST)
    if cycle_used is None or cycle_used == "":
        return Response({"error": "Cycle hours are required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        cycle_used = float(cycle_used)
        if cycle_used < 0 or cycle_used > 70:
            return Response({"error": "Cycle hours must be between 0 and 70"}, status=status.HTTP_400_BAD_REQUEST)

        # Location lookup
        current_coords = get_coordinates(current_location)
        if not current_coords:
            return Response({"error": f"Could not find location: {current_location}"}, status=status.HTTP_400_BAD_REQUEST)

        pickup_coords = get_coordinates(pickup_location)
        if not pickup_coords:
            return Response({"error": f"Could not find location: {pickup_location}"}, status=status.HTTP_400_BAD_REQUEST)

        dropoff_coords = get_coordinates(dropoff_location)
        if not dropoff_coords:
            return Response({"error": f"Could not find location: {dropoff_location}"}, status=status.HTTP_400_BAD_REQUEST)

        # Route Calculation
        route1 = get_route(current_coords, pickup_coords)
        route2 = get_route(pickup_coords, dropoff_coords)

        if not route1 or not route2:
            return Response({"error": "Could not calculate route. Ensure endpoints are reachable and valid."}, status=status.HTTP_400_BAD_REQUEST)

        total_distance = route1["distance_miles"] + route2["distance_miles"]
        total_duration = route1["duration_hours"] + route2["duration_hours"]

        # HOS Calculation
        hos_data = calculate_hos(total_duration, cycle_used)

        # Fuel and Cost metrics
        # Default or driver-specific settings
        mpg = 6.5
        fuel_price = 4.00
        if request.user.is_authenticated:
            try:
                profile = request.user.profile
                mpg = profile.truck_mpg
                fuel_price = profile.fuel_price_preset
            except Exception:
                pass

        fuel_required = total_distance / mpg
        fuel_cost = fuel_required * fuel_price
        
        # Operating costs: Driver ($0.65/mile), Tolls/Misc ($0.15/mile), Maintenance ($0.10/mile)
        driver_cost = total_distance * 0.65
        tolls_misc = total_distance * 0.15
        maintenance_cost = total_distance * 0.10
        total_trip_cost = fuel_cost + driver_cost + tolls_misc + maintenance_cost

        trip_result = {
            "currentLocation": current_location,
            "pickupLocation": pickup_location,
            "dropoffLocation": dropoff_location,
            "currentCoordinates": current_coords,
            "pickupCoordinates": pickup_coords,
            "dropoffCoordinates": dropoff_coords,
            "cycleUsed": cycle_used,
            "availableCycleHours": round(70 - cycle_used, 1),
            "currentToPickup": route1,
            "pickupToDropoff": route2,
            "totalDistanceMiles": round(total_distance, 1),
            "totalDrivingHours": round(total_duration, 1),
            "fuelRequired": round(fuel_required, 1),
            "fuelCost": round(fuel_cost, 2),
            "driverCost": round(driver_cost, 2),
            "tollsMisc": round(tolls_misc, 2),
            "maintenanceCost": round(maintenance_cost, 2),
            "totalTripCost": round(total_trip_cost, 2),
            "hos": hos_data
        }

        # Save to DB if authenticated and requested
        if request.user.is_authenticated and save_trip:
            Trip.objects.create(
                driver=request.user.profile,
                current_location=current_location,
                pickup_location=pickup_location,
                dropoff_location=dropoff_location,
                cycle_used=cycle_used,
                total_distance=round(total_distance, 1),
                total_driving_hours=round(total_duration, 1),
                fuel_required=round(fuel_required, 1),
                fuel_cost=round(fuel_cost, 2),
                total_trip_cost=round(total_trip_cost, 2),
                details=trip_result
            )

        return Response({
            "message": "Trip plan generated successfully!",
            "trip": trip_result
        }, status=status.HTTP_200_OK)

    except requests.exceptions.Timeout:
        return Response({"error": "Routing API timed out. Try again."}, status=status.HTTP_504_GATEWAY_TIMEOUT)
    except Exception as e:
        return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# -----------------------------------
# AI SMART ASSISTANT QUERY
# -----------------------------------
@api_view(["POST"])
@permission_classes([AllowAny])
def ai_assistant_query(request):
    message = request.data.get("message", "").lower()
    trip_data = request.data.get("trip")
    
    if not message:
        return Response({"error": "Message is required"}, status=status.HTTP_400_BAD_REQUEST)
        
    # Standard responses if no trip context is available
    if not trip_data:
        if "hello" in message or "hi" in message:
            reply = "Hello! I am your AI compliance assistant. Please plan a trip first so I can analyze your logs, or ask general questions about ELD & HOS rules!"
        elif "rule" in message or "hos" in message:
            reply = "Federal HOS rules include: 11-Hour Driving Limit, 14-Hour Duty Window, 30-Minute Break after 8 hours of driving, 10 consecutive hours Off Duty reset, and the 70-Hour / 8-Day Cycle limit."
        else:
            reply = "I'm ready to assist you. To provide custom recommendations, please enter details and calculate a trip first!"
        return Response({"reply": reply})

    # Trip details are present
    dist = trip_data.get("totalDistanceMiles", 0)
    hours = trip_data.get("totalDrivingHours", 0)
    cycle_used = trip_data.get("cycleUsed", 0)
    available_cycle = trip_data.get("availableCycleHours", 70.0)
    hos = trip_data.get("hos", {})
    schedule = hos.get("dailySchedule", [])
    
    # Analyze if restart was scheduled
    restart_days = [d for d in schedule if d.get("type") == "RESTART"]
    requires_restart = len(restart_days) > 0
    driving_days = hos.get("estimatedDrivingDays", 1)
    
    if "restart" in message:
        if requires_restart:
            reply = f"Yes, you will require a 34-hour restart. Based on your cycle usage ({cycle_used} hrs used, leaving {available_cycle} hrs), the total driving required ({hours} hours) exceeds your limit. A restart is planned on Day {restart_days[0]['day']} to reset your clock."
        else:
            reply = f"No restart is required for this trip! You have {available_cycle} available cycle hours, and the trip requires {hours} hours of driving, meaning you can complete it within your current cycle limit."
            
    elif "risk" in message or "safe" in message:
        if requires_restart:
            reply = f"Risk Level: MEDIUM/HIGH. Although you have a planned 34-hour restart, driving {hours} hours starting with {cycle_used} cycle hours used is demanding. Watch out for fatigue around Day {restart_days[0]['day']}. Keep an eye on your ELD alerts!"
        elif hours > 35:
            reply = "Risk Level: MEDIUM. This is a long-haul trip spanning multiple days. While compliance is maintained without restart resets, regular sleep cycles are highly recommended."
        else:
            reply = "Risk Level: LOW. The route is short and fits easily within your daily 11-hour driving and 14-hour duty limits."
            
    elif "fuel" in message or "cost" in message:
        fuel_cost = trip_data.get("fuelCost", 0)
        fuel_req = trip_data.get("fuelRequired", 0)
        total_cost = trip_data.get("totalTripCost", 0)
        reply = f"The trip requires approximately {fuel_req} gallons of fuel, costing about ${fuel_cost:,.2f}. The estimated total operating cost (including driver pay, maintenance, and tolls) is ${total_cost:,.2f}."
        
    elif "time" in message or "duration" in message or "when" in message:
        reply = f"This trip spans a total of {driving_days} calendar days. It requires {hours} hours of active driving to cover the {dist} miles."
        
    else:
        # Default smart response summarizing the route
        status_msg = "requires a 34-hour restart" if requires_restart else "can be completed without any restart"
        reply = (
            f"I've analyzed your trip from {trip_data.get('currentLocation')} to {trip_data.get('dropoffLocation')}. "
            f"The trip covers {dist} miles ({hours} driving hours) and {status_msg}. "
            f"You will spend approximately ${trip_data.get('totalTripCost'):,.2f} in total operation costs. "
            f"How else can I help you optimize this route?"
        )

    return Response({"reply": reply})