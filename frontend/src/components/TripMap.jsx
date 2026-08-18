import React, { useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

// Leaflet marker icon fix
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png",
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
});

// A component to automatically adjust map bounds to fit the route markers
function FitBounds({ coords }) {
  const map = useMap();
  useEffect(() => {
    if (coords && coords.length > 0) {
      const validCoords = coords.filter(c => c && c[0] && c[1]);
      if (validCoords.length > 0) {
        const bounds = L.latLngBounds(validCoords);
        map.fitBounds(bounds, { padding: [50, 50] });
      }
    }
  }, [coords, map]);
  return null;
}

export default function TripMap({ trip }) {
  if (!trip || !trip.currentCoordinates || !trip.pickupCoordinates || !trip.dropoffCoordinates) {
    return <div className="error-banner">Invalid coordinates for Map render.</div>;
  }

  const {
    currentLocation,
    pickupLocation,
    dropoffLocation,
    currentCoordinates,
    pickupCoordinates,
    dropoffCoordinates,
    currentToPickup,
    pickupToDropoff
  } = trip;

  // Compile all points to fit map bounds
  const points = [
    [currentCoordinates.lat, currentCoordinates.lon],
    [pickupCoordinates.lat, pickupCoordinates.lon],
    [dropoffCoordinates.lat, dropoffCoordinates.lon]
  ];

  return (
    <div className="map-card">
      <h2>Trip Route Map</h2>
      <MapContainer
        center={[currentCoordinates.lat, currentCoordinates.lon]}
        zoom={6}
        scrollWheelZoom={true}
        className="trip-map"
      >
        <TileLayer
          attribution='&copy; <a href="https://openstreetmap.org">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Current Location Marker */}
        <Marker position={[currentCoordinates.lat, currentCoordinates.lon]}>
          <Popup>
            <div>
              <strong>🚛 Current Location (Start)</strong>
              <p>{currentLocation}</p>
            </div>
          </Popup>
        </Marker>

        {/* Pickup Location Marker */}
        <Marker position={[pickupCoordinates.lat, pickupCoordinates.lon]}>
          <Popup>
            <div>
              <strong>📦 Pickup Location</strong>
              <p>{pickupLocation}</p>
            </div>
          </Popup>
        </Marker>

        {/* Dropoff Location Marker */}
        <Marker position={[dropoffCoordinates.lat, dropoffCoordinates.lon]}>
          <Popup>
            <div>
              <strong>🏁 Dropoff Location (Destination)</strong>
              <p>{dropoffLocation}</p>
            </div>
          </Popup>
        </Marker>

        {/* Current to Pickup route - Rendered in Blue */}
        {currentToPickup?.coordinates && (
          <Polyline
            positions={currentToPickup.coordinates}
            color="#3b82f6"
            weight={4}
            opacity={0.8}
          >
            <Popup>Current to Pickup: {currentToPickup.distance_miles} miles</Popup>
          </Polyline>
        )}

        {/* Pickup to Dropoff route - Rendered in Emerald Green */}
        {pickupToDropoff?.coordinates && (
          <Polyline
            positions={pickupToDropoff.coordinates}
            color="#10b981"
            weight={5}
            opacity={0.9}
          >
            <Popup>Pickup to Dropoff: {pickupToDropoff.distance_miles} miles</Popup>
          </Polyline>
        )}

        <FitBounds coords={points} />
      </MapContainer>
    </div>
  );
}
