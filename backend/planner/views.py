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

# Helper to format decimal hours to HH:MM format
def format_time(decimal_hours):
    hours = int(decimal_hours)
    minutes = int(round((decimal_hours - hours) * 60))
    if minutes == 60:
        hours += 1
        minutes = 0
    period = "AM"
    if hours >= 12:
        period = "PM"
    display_hours = hours
    if hours > 12:
        display_hours -= 12
    elif hours == 0:
        display_hours = 12
    return f"{display_hours:02d}:{minutes:02d} {period}"

# -----------------------------------
# ASSESSMENT COMPLIANT HOS SIMULATION
# -----------------------------------
def calculate_hos_advanced(current_location, pickup_location, dropoff_location, d1, t1, d2, t2, initial_cycle_used):
    DAILY_DRIVING_LIMIT = 11.0
    DAILY_DUTY_LIMIT = 14.0
    CYCLE_LIMIT = 70.0
    BREAK_DRIVING_LIMIT = 8.0
    BREAK_DURATION = 0.5
    OFF_DUTY_REST = 10.0
    RESTART_REST = 34.0
    
    # 1. Compile events queue
    events = []
    
    # Pre-trip at origin
    events.append({
        "type": "ON_DUTY",
        "hours": 0.5,
        "reason": "Pre-trip Inspection",
        "location": current_location
    })
    
    # Drive leg 1 (Current to Pickup)
    speed1 = d1 / t1 if t1 > 0 else 55.0
    rem_d1 = d1
    odometer = 0.0 # odometer since last fuel stop
    
    while rem_d1 > 0:
        dist_to_fuel = 1000.0 - odometer
        if rem_d1 <= dist_to_fuel:
            drive_hrs = rem_d1 / speed1
            events.append({
                "type": "DRIVE",
                "hours": drive_hrs,
                "miles": rem_d1,
                "start_loc": current_location,
                "end_loc": pickup_location
            })
            odometer += rem_d1
            rem_d1 = 0
        else:
            # Drive to fueling stop
            events.append({
                "type": "DRIVE",
                "hours": dist_to_fuel / speed1,
                "miles": dist_to_fuel,
                "start_loc": current_location,
                "end_loc": "Fuel Station"
            })
            events.append({
                "type": "ON_DUTY",
                "hours": 0.5,
                "reason": "Fueling Stop & Inspection",
                "location": "Fuel Station"
            })
            odometer = 0.0
            rem_d1 -= dist_to_fuel

    # Pickup stop - 1 hour on duty loading (from PDF instructions)
    events.append({
        "type": "ON_DUTY",
        "hours": 1.0,
        "reason": "Pickup & Loading (Stop)",
        "location": pickup_location
    })

    # Drive leg 2 (Pickup to Dropoff)
    speed2 = d2 / t2 if t2 > 0 else 55.0
    rem_d2 = d2
    while rem_d2 > 0:
        dist_to_fuel = 1000.0 - odometer
        if rem_d2 <= dist_to_fuel:
            drive_hrs = rem_d2 / speed2
            events.append({
                "type": "DRIVE",
                "hours": drive_hrs,
                "miles": rem_d2,
                "start_loc": pickup_location,
                "end_loc": dropoff_location
            })
            odometer += rem_d2
            rem_d2 = 0
        else:
            events.append({
                "type": "DRIVE",
                "hours": dist_to_fuel / speed2,
                "miles": dist_to_fuel,
                "start_loc": pickup_location,
                "end_loc": "Fuel Station"
            })
            events.append({
                "type": "ON_DUTY",
                "hours": 0.5,
                "reason": "Fueling Stop & Inspection",
                "location": "Fuel Station"
            })
            odometer = 0.0
            rem_d2 -= dist_to_fuel

    # Dropoff stop - 1 hour on duty unloading (from PDF instructions)
    events.append({
        "type": "ON_DUTY",
        "hours": 1.0,
        "reason": "Dropoff & Unloading (Stop)",
        "location": dropoff_location
    })

    # Post-trip inspection at destination
    events.append({
        "type": "ON_DUTY",
        "hours": 0.5,
        "reason": "Post-trip Inspection",
        "location": dropoff_location
    })

    # 2. Simulate daily operations
    daily_schedule = []
    day_counter = 1
    cycle_remaining = max(0.0, CYCLE_LIMIT - initial_cycle_used)
    
    # Maintain rolling daily duty log for recap table (previous 7 days initialization)
    # We distribute initial_cycle_used over the past 7 days to simulate a realistic starting cycle history.
    daily_duty_history = [round(initial_cycle_used / 7, 1)] * 7

    event_index = 0
    while event_index < len(events):
        # Check if cycle limit is exhausted (need 34h restart)
        # If we have less than 2 hours left in cycle, force a 34h restart day
        if cycle_remaining <= 2.0:
            daily_schedule.append({
                "day": day_counter,
                "type": "RESTART",
                "status": "34-Hour Restart",
                "drivingHours": 0.0,
                "onDutyHours": 0.0,
                "offDutyHours": 24.0,
                "breakHours": 0.0,
                "milesDriven": 0.0,
                "message": "Rolling 70-hour cycle limit reached. 34-hour restart taken to reset cycle hours.",
                "eldLog": {
                    "offDutyHours": 12.0,
                    "sleeperHours": 12.0,
                    "drivingHours": 0.0,
                    "breakHours": 0.0,
                    "onDutyHours": 0.0,
                    "intervals": [
                        {"status": "OFF", "start": 0.0, "end": 12.0, "duration": 12.0},
                        {"status": "SB", "start": 12.0, "end": 24.0, "duration": 12.0}
                    ],
                    "remarks": [
                        "06:00 AM - Initiated mandatory 34-hour restart rest window"
                    ],
                    "recap": {
                        "onDutyToday": 0.0,
                        "rolling7DaysTotal": 0.0,
                        "availableTomorrow": 70.0
                    }
                }
            })
            cycle_remaining = CYCLE_LIMIT
            daily_duty_history.append(0.0)
            day_counter += 1
            continue

        # Simulate standard work day
        # Shift starts at 06:00 AM (Hour 6.0) and ends at 08:00 PM (Hour 20.0) - max 14 hours
        shift_elapsed = 0.0
        driving_today = 0.0
        on_duty_today = 0.0
        break_today = 0.0
        miles_today = 0.0
        
        remarks = []
        intervals = []
        
        # 1. Morning Off Duty/Sleeper rest (00:00 to 06:00 = 6 hours)
        intervals.append({"status": "SB", "start": 0.0, "end": 6.0, "duration": 6.0})
        remarks.append("12:00 AM - Midnight Rest in Sleeper Berth")

        driving_since_break = 0.0

        # Process shift window
        while shift_elapsed < DAILY_DUTY_LIMIT and event_index < len(events):
            event = events[event_index]
            
            # Check limits
            limit_11 = DAILY_DRIVING_LIMIT - driving_today
            limit_14 = DAILY_DUTY_LIMIT - shift_elapsed
            limit_70 = cycle_remaining
            
            if event["type"] == "ON_DUTY":
                rem_h = event["hours"]
                fit_h = min(rem_h, limit_14, limit_70)
                
                if fit_h > 0:
                    start_time_dec = 6.0 + shift_elapsed
                    remarks.append(f"{format_time(start_time_dec)} - {event['reason']} at {event['location']}")
                    
                    on_duty_today += fit_h
                    shift_elapsed += fit_h
                    cycle_remaining -= fit_h
                    
                    intervals.append({"status": "ON", "start": start_time_dec, "end": start_time_dec + fit_h, "duration": fit_h})
                    
                    event["hours"] -= fit_h
                    if event["hours"] <= 0:
                        event_index += 1
                else:
                    break # Shift window or cycle limit hit
                    
            elif event["type"] == "DRIVE":
                rem_h = event["hours"]
                limit_8 = BREAK_DRIVING_LIMIT - driving_since_break
                max_drive = min(rem_h, limit_11, limit_14, limit_70, limit_8)
                
                if max_drive > 0:
                    start_time_dec = 6.0 + shift_elapsed
                    remarks.append(f"{format_time(start_time_dec)} - Driving from {event['start_loc']} to {event['end_loc']}")
                    
                    driving_today += max_drive
                    shift_elapsed += max_drive
                    cycle_remaining -= max_drive
                    driving_since_break += max_drive
                    
                    # Calculate proportional miles driven today
                    leg_speed = event["miles"] / event["hours"] if event["hours"] > 0 else 55.0
                    drive_miles = max_drive * leg_speed
                    miles_today += drive_miles
                    
                    intervals.append({"status": "D", "start": start_time_dec, "end": start_time_dec + max_drive, "duration": max_drive})
                    
                    event["hours"] -= max_drive
                    event["miles"] -= drive_miles
                    if event["hours"] <= 0:
                        event_index += 1
                        
                    # Check if 30-min break is triggered
                    if driving_since_break >= BREAK_DRIVING_LIMIT and shift_elapsed < DAILY_DUTY_LIMIT:
                        break_start = 6.0 + shift_elapsed
                        remarks.append(f"{format_time(break_start)} - Mandatory 30-minute Rest Break")
                        
                        break_today += BREAK_DURATION
                        shift_elapsed += BREAK_DURATION
                        driving_since_break = 0.0
                        
                        intervals.append({"status": "OFF", "start": break_start, "end": break_start + BREAK_DURATION, "duration": BREAK_DURATION})
                else:
                    if limit_8 <= 0:
                        # Force rest break
                        break_start = 6.0 + shift_elapsed
                        remarks.append(f"{format_time(break_start)} - Mandatory 30-minute Rest Break")
                        
                        break_today += BREAK_DURATION
                        shift_elapsed += BREAK_DURATION
                        driving_since_break = 0.0
                        
                        intervals.append({"status": "OFF", "start": break_start, "end": break_start + BREAK_DURATION, "duration": BREAK_DURATION})
                    else:
                        break # Daily limit reached

        # End of shift rest (10 consecutive hours off duty)
        shift_end = 6.0 + shift_elapsed
        if shift_end < 24.0:
            rem_day_rest = 24.0 - shift_end
            intervals.append({"status": "OFF", "start": shift_end, "end": 24.0, "duration": rem_day_rest})
            remarks.append(f"{format_time(shift_end)} - Shift completed. Released for Off-Duty Rest.")
        
        # Calculate totals
        off_duty_today = break_today
        sleeper_today = 6.0 # morning rest
        
        # Split evening rest between off duty and sleeper
        evening_rest = 24.0 - shift_end
        if evening_rest > 0:
            sleeper_today += evening_rest * 0.5
            off_duty_today += evening_rest * 0.5
            
        driving_today = round(driving_today, 1)
        on_duty_today = round(on_duty_today, 1)
        off_duty_today = round(off_duty_today, 1)
        sleeper_today = round(sleeper_today, 1)
        
        # Consolidation of duplicate consecutive intervals to keep graph path drawing clean
        consolidated = []
        for interval in sorted(intervals, key=lambda x: x["start"]):
            if len(consolidated) == 0:
                consolidated.append(interval)
            else:
                last = consolidated[-1]
                if last["status"] == interval["status"] and abs(last["end"] - interval["start"]) < 0.01:
                    last["end"] = interval["end"]
                    last["duration"] = round(last["end"] - last["start"], 1)
                else:
                    consolidated.append(interval)
                    
        # Recap calculations
        duty_today = driving_today + on_duty_today
        daily_duty_history.append(duty_today)
        
        # Rolling 7 days total (previous 7 days from history list)
        rolling_7 = sum(daily_duty_history[-7:])
        available_tomorrow = max(0.0, 70.0 - rolling_7)

        daily_schedule.append({
            "day": day_counter,
            "type": "WORK",
            "status": "Planned Driving",
            "drivingHours": driving_today,
            "onDutyHours": on_duty_today,
            "offDutyHours": off_duty_today,
            "breakHours": break_today,
            "milesDriven": round(miles_today, 1),
            "eldLog": {
                "offDutyHours": off_duty_today,
                "sleeperHours": sleeper_today,
                "drivingHours": driving_today,
                "breakHours": break_today,
                "onDutyHours": on_duty_today,
                "intervals": consolidated,
                "remarks": remarks,
                "recap": {
                    "onDutyToday": round(duty_today, 1),
                    "rolling7DaysTotal": round(rolling_7, 1),
                    "availableTomorrow": round(available_tomorrow, 1)
                }
            }
        })
        
        day_counter += 1

    total_driving_required = t1 + t2
    cycle_status = "Within available cycle hours"
    if any(d["type"] == "RESTART" for d in daily_schedule):
        cycle_status = "Cycle limit reached. Includes 34-hour restart."

    return {
        "dailyDrivingLimit": DAILY_DRIVING_LIMIT,
        "dailyDutyLimit": DAILY_DUTY_LIMIT,
        "totalDrivingRequired": round(total_driving_required, 1),
        "estimatedDrivingDays": len(daily_schedule),
        "requiredBreaks": sum(1 for d in daily_schedule if d["breakHours"] > 0),
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

        current_coords = get_coordinates(current_location)
        if not current_coords:
            return Response({"error": f"Could not find location: {current_location}"}, status=status.HTTP_400_BAD_REQUEST)

        pickup_coords = get_coordinates(pickup_location)
        if not pickup_coords:
            return Response({"error": f"Could not find location: {pickup_location}"}, status=status.HTTP_400_BAD_REQUEST)

        dropoff_coords = get_coordinates(dropoff_location)
        if not dropoff_coords:
            return Response({"error": f"Could not find location: {dropoff_location}"}, status=status.HTTP_400_BAD_REQUEST)

        route1 = get_route(current_coords, pickup_coords)
        route2 = get_route(pickup_coords, dropoff_coords)

        if not route1 or not route2:
            return Response({"error": "Could not calculate route. Ensure locations are reachable."}, status=status.HTTP_400_BAD_REQUEST)

        total_distance = route1["distance_miles"] + route2["distance_miles"]
        total_duration = route1["duration_hours"] + route2["duration_hours"]

        # Advanced HOS simulation incorporating 1h stops & 1000mi fueling limit
        hos_data = calculate_hos_advanced(
            current_location, pickup_location, dropoff_location,
            route1["distance_miles"], route1["duration_hours"],
            route2["distance_miles"], route2["duration_hours"],
            cycle_used
        )

        # Fuel and costs logic
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
        
    if not trip_data:
        if "hello" in message or "hi" in message:
            reply = "Hello! I am your AI compliance assistant. Please plan a trip first so I can analyze your logs, or ask general questions about ELD & HOS rules!"
        elif "rule" in message or "hos" in message:
            reply = "Federal HOS rules include: 11-Hour Driving Limit, 14-Hour Duty Window, 30-Minute Break after 8 hours of driving, 10 consecutive hours Off Duty reset, and the 70-Hour / 8-Day Cycle limit."
        else:
            reply = "I'm ready to assist you. To provide custom recommendations, please enter details and calculate a trip first!"
        return Response({"reply": reply})

    dist = trip_data.get("totalDistanceMiles", 0)
    hours = trip_data.get("totalDrivingHours", 0)
    cycle_used = trip_data.get("cycleUsed", 0)
    available_cycle = trip_data.get("availableCycleHours", 70.0)
    hos = trip_data.get("hos", {})
    schedule = hos.get("dailySchedule", [])
    
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
        status_msg = "requires a 34-hour restart" if requires_restart else "can be completed without any restart"
        reply = (
            f"I've analyzed your trip from {trip_data.get('currentLocation')} to {trip_data.get('dropoffLocation')}. "
            f"The trip covers {dist} miles ({hours} driving hours) and {status_msg}. "
            f"You will spend approximately ${trip_data.get('totalTripCost'):,.2f} in total operation costs. "
            f"How else can I help you optimize this route?"
        )

    return Response({"reply": reply})