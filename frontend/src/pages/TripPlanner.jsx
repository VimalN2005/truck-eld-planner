import React, { useState } from "react";
import TripMap from "../components/TripMap";
import ELDLog from "../components/ELDLog";

const API_BASE_URL = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
  ? "http://127.0.0.1:8000"
  : "https://truck-eld-planner.onrender.com";

export default function TripPlanner({ profile, onTripGenerated }) {
  const [trip, setTrip] = useState({
    currentLocation: "",
    pickupLocation: "",
    dropoffLocation: "",
    cycleUsed: profile?.currentCycleUsed || "",
    truckMpg: profile?.truckMpg || 6.5,
    fuelPrice: profile?.fuelPricePreset || 4.00,
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const handleChange = (e) => {
    setTrip({
      ...trip,
      [e.target.name]: e.target.value,
    });
  };

  const handleReset = () => {
    setTrip({
      currentLocation: "",
      pickupLocation: "",
      dropoffLocation: "",
      cycleUsed: profile?.currentCycleUsed || "",
      truckMpg: profile?.truckMpg || 6.5,
      fuelPrice: profile?.fuelPricePreset || 4.00,
    });
    setResult(null);
    setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/trip/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          currentLocation: trip.currentLocation,
          pickupLocation: trip.pickupLocation,
          dropoffLocation: trip.dropoffLocation,
          cycleUsed: trip.cycleUsed,
          saveTrip: true, // Auto-save generated trips if user logged in
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.error || "Failed to generate trip plan");
        return;
      }

      setResult(data.trip);
      if (onTripGenerated) {
        onTripGenerated(); // Trigger reload of history lists
      }
    } catch (err) {
      setError("Unable to connect to routing server. Please check your internet connection and verify the backend is running on port 8000.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="planner-layout">
      <div style={{ marginBottom: "10px" }}>
        <h1 style={{ fontSize: "28px", fontWeight: "700", marginBottom: "4px" }}>
          ELD Trip & Compliance Planner
        </h1>
        <p style={{ color: "var(--text-secondary)" }}>
          Simulate logs, calculate costs, and verify compliance with FMCSA rules.
        </p>
      </div>

      {error && (
        <div className="error-banner">
          <span style={{ fontSize: "20px" }}>⚠️</span>
          <div>
            <strong>Calculation Error</strong>
            <p style={{ fontSize: "14px", marginTop: "2px" }}>{error}</p>
          </div>
        </div>
      )}

      {/* Inputs Form Card */}
      {!result && !loading && (
        <form className="trip-form-card" onSubmit={handleSubmit}>
          <div className="form-row">
            <div className="form-group">
              <label>Current Location</label>
              <input
                type="text"
                name="currentLocation"
                placeholder="City, State (e.g. New York, NY)"
                value={trip.currentLocation}
                onChange={handleChange}
                required
              />
            </div>
            <div className="form-group">
              <label>Pickup Location</label>
              <input
                type="text"
                name="pickupLocation"
                placeholder="City, State (e.g. Chicago, IL)"
                value={trip.pickupLocation}
                onChange={handleChange}
                required
              />
            </div>
            <div className="form-group">
              <label>Dropoff Location</label>
              <input
                type="text"
                name="dropoffLocation"
                placeholder="City, State (e.g. Los Angeles, CA)"
                value={trip.dropoffLocation}
                onChange={handleChange}
                required
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Current Cycle Used (Hours)</label>
              <input
                type="number"
                name="cycleUsed"
                placeholder="0 - 70"
                min="0"
                max="70"
                step="0.1"
                value={trip.cycleUsed}
                onChange={handleChange}
                required
              />
            </div>
            <div className="form-group">
              <label>Truck MPG Presets</label>
              <input
                type="number"
                name="truckMpg"
                step="0.1"
                min="4"
                max="15"
                value={trip.truckMpg}
                onChange={handleChange}
              />
            </div>
            <div className="form-group">
              <label>Fuel Price Preset ($/gal)</label>
              <input
                type="number"
                name="fuelPrice"
                step="0.01"
                min="2.00"
                max="8.00"
                value={trip.fuelPrice}
                onChange={handleChange}
              />
            </div>
          </div>

          <button type="submit" className="btn-primary" style={{ width: "100%", marginTop: "10px" }}>
            Generate Compliance & Trip Plan →
          </button>
        </form>
      )}

      {loading && (
        <div className="loading-box">
          <div className="spinner"></div>
          <strong>Generating route coordinates, calculating HOS limits and optimizing trip finances...</strong>
          <p style={{ color: "var(--text-muted)", fontSize: "14px" }}>This might take a moment as we query geocoding parameters.</p>
        </div>
      )}

      {/* Trip Calculation Results */}
      {result && (
        <div style={{ display: "flex", flexDirection: "column", gap: "30px" }}>
          
          {/* Actions Bar */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "var(--bg-secondary)", padding: "16px 24px", borderRadius: "var(--radius-lg)", border: "1px solid var(--border-color)" }}>
            <div>
              <strong style={{ fontSize: "16px" }}>Route Loaded</strong>
              <p style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
                {result.currentLocation} → {result.pickupLocation} → {result.dropoffLocation}
              </p>
            </div>
            <button onClick={handleReset} className="btn-secondary" style={{ padding: "8px 16px", fontSize: "14px" }}>
              Plan New Trip
            </button>
          </div>

          {/* Stats Summary Dashboard */}
          <div className="stats-grid">
            <div className="stat-card">
              <span className="label">Total Distance</span>
              <span className="value">{result.totalDistanceMiles} mi</span>
              <span className="desc">OSRM computed path</span>
            </div>
            <div className="stat-card">
              <span className="label">Driving Time</span>
              <span className="value">{result.totalDrivingHours} hrs</span>
              <span className="desc">Total wheel hours</span>
            </div>
            <div className="stat-card">
              <span className="label">Estimated Days</span>
              <span className="value">{result.hos.estimatedDrivingDays} days</span>
              <span className="desc">Including required rests</span>
            </div>
            <div className="stat-card">
              <span className="label">Cycle Remaining</span>
              <span className="value" style={{ color: result.hos.availableCycleHours < 15 ? "var(--color-danger)" : "var(--color-success)" }}>
                {result.hos.availableCycleHours} hrs
              </span>
              <span className="desc">Available HOS balance</span>
            </div>
          </div>

          {/* Map Section */}
          <TripMap trip={result} />

          {/* Financial Dashboard */}
          <div className="trip-form-card">
            <h3>Trip Cost & Fuel Estimation</h3>
            <div className="financial-grid">
              <div className="financial-item">
                <span>Fuel Required</span>
                <strong>{result.fuelRequired} gal</strong>
              </div>
              <div className="financial-item">
                <span>Estimated Fuel Cost</span>
                <strong>${result.fuelCost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>
              </div>
              <div className="financial-item">
                <span>Driver Compensation ($0.65/mi)</span>
                <strong>${result.driverCost.toLocaleString(undefined, { minimumFractionDigits: 2 })}</strong>
              </div>
              <div className="financial-item">
                <span>Maintenance & Misc</span>
                <strong>${(result.maintenanceCost + result.tollsMisc).toLocaleString(undefined, { minimumFractionDigits: 2 })}</strong>
              </div>
            </div>
            <div style={{ marginTop: "20px", paddingTop: "15px", borderTop: "1px solid var(--border-color)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "15px", fontWeight: "600", color: "var(--text-secondary)" }}>Total Estimated Cost</span>
              <strong style={{ fontSize: "24px", color: "var(--color-success)" }}>
                ${result.totalTripCost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </strong>
            </div>
          </div>

          {/* Hours of Service Panel */}
          <div className="trip-form-card">
            <h3>Hours of Service Compliance Analysis</h3>
            
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px", marginTop: "15px" }}>
              <div className="financial-item">
                <span>Daily Driving Cap</span>
                <strong>{result.hos.dailyDrivingLimit} hrs</strong>
              </div>
              <div className="financial-item">
                <span>Mandatory Break threshold</span>
                <strong>8.0 driving hrs</strong>
              </div>
              <div className="financial-item">
                <span>Estimated Breaks</span>
                <strong>{result.hos.requiredBreaks} (30 mins each)</strong>
              </div>
              <div className="financial-item">
                <span>Compliance Warning Status</span>
                <strong style={{ color: result.hos.cycleStatus.includes("restart") ? "var(--color-warning)" : "var(--color-success)" }}>
                  {result.hos.cycleStatus.includes("restart") ? "RESTART REQ" : "COMPLIANT"}
                </strong>
              </div>
            </div>

            <p style={{ marginTop: "15px", color: "var(--text-secondary)", fontSize: "14px" }}>
              <strong>Status Note:</strong> {result.hos.cycleStatus}
            </p>

            {/* Daily Schedule logs */}
            <div className="schedule-list">
              {result.hos.dailySchedule.map((day) => (
                <div key={day.day} className="day-schedule-card">
                  <div className="day-header">
                    <h4>Day {day.day} schedule</h4>
                    <span className={`badge ${day.type === "RESTART" ? "badge-restart" : "badge-work"}`}>
                      {day.type === "RESTART" ? "MANDATORY REST" : "TRANSIT DUTY"}
                    </span>
                  </div>

                  {day.type === "RESTART" ? (
                    <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>
                      ⚠️ {day.message}
                    </p>
                  ) : (
                    <div>
                      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "10px", fontSize: "13px" }}>
                        <div>
                          <span style={{ color: "var(--text-muted)" }}>Driving</span>
                          <strong style={{ display: "block", color: "var(--color-primary)", fontSize: "16px", marginTop: "2px" }}>{day.drivingHours} hrs</strong>
                        </div>
                        <div>
                          <span style={{ color: "var(--text-muted)" }}>On Duty</span>
                          <strong style={{ display: "block", color: "var(--color-warning)", fontSize: "16px", marginTop: "2px" }}>{day.onDutyHours} hrs</strong>
                        </div>
                        <div>
                          <span style={{ color: "var(--text-muted)" }}>Off Duty</span>
                          <strong style={{ display: "block", color: "var(--text-secondary)", fontSize: "16px", marginTop: "2px" }}>{day.eldLog.offDutyHours} hrs</strong>
                        </div>
                        <div>
                          <span style={{ color: "var(--text-muted)" }}>Sleeper</span>
                          <strong style={{ display: "block", color: "var(--text-secondary)", fontSize: "16px", marginTop: "2px" }}>{day.eldLog.sleeperHours} hrs</strong>
                        </div>
                        <div>
                          <span style={{ color: "var(--text-muted)" }}>Break</span>
                          <strong style={{ display: "block", color: "var(--text-secondary)", fontSize: "16px", marginTop: "2px" }}>{day.breakHours} hrs</strong>
                        </div>
                      </div>

                      {/* Display beautiful visual ELD grid log */}
                      <ELDLog dayLog={day} />
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
