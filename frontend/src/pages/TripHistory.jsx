import React, { useState, useEffect } from "react";
import TripMap from "../components/TripMap";
import ELDLog from "../components/ELDLog";

export default function TripHistory({ trips, onRefresh }) {
  const [selectedTrip, setSelectedTrip] = useState(null);

  useEffect(() => {
    if (onRefresh) {
      onRefresh();
    }
  }, []);

  const handleClose = () => {
    setSelectedTrip(null);
  };

  return (
    <div>
      <div style={{ marginBottom: "25px" }}>
        <h1 style={{ fontSize: "28px", fontWeight: "700", marginBottom: "4px" }}>
          Trip logs & History
        </h1>
        <p style={{ color: "var(--text-secondary)" }}>
          Review and audit your past calculated compliance routes.
        </p>
      </div>

      {trips.length === 0 ? (
        <div className="trip-form-card" style={{ textAlign: "center", padding: "40px 20px" }}>
          <span style={{ fontSize: "36px" }}>📁</span>
          <h3 style={{ marginTop: "15px", marginBottom: "8px" }}>No trip history available</h3>
          <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>
            Create and save a compliance plan in the Trip Planner to build your logs.
          </p>
        </div>
      ) : (
        <div className="trip-form-card">
          <div className="trips-table-container">
            <table className="trips-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Route (Start → Pickup → Destination)</th>
                  <th>Distance</th>
                  <th>Driving</th>
                  <th>Total Cost</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {trips.map((trip) => (
                  <tr key={trip.id}>
                    <td>{trip.createdAt}</td>
                    <td>
                      <strong style={{ display: "block" }}>
                        {trip.pickupLocation.split(",")[0]} → {trip.dropoffLocation.split(",")[0]}
                      </strong>
                      <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                        Start: {trip.currentLocation.split(",")[0]}
                      </span>
                    </td>
                    <td>{trip.totalDistanceMiles} mi</td>
                    <td>{trip.totalDrivingHours} hrs</td>
                    <td style={{ color: "var(--color-success)", fontWeight: "600" }}>
                      ${trip.totalTripCost.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td>
                      <button 
                        onClick={() => setSelectedTrip(trip.details || trip)}
                        className="btn-primary" 
                        style={{ width: "auto", padding: "6px 12px", fontSize: "12px", marginTop: "0" }}
                      >
                        View Logs
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Details Modal Overlay */}
      {selectedTrip && (
        <div className="modal-overlay">
          <div className="modal-content">
            <button onClick={handleClose} className="close-modal">
              &times;
            </button>
            
            <div style={{ marginBottom: "25px", borderBottom: "1px solid var(--border-color)", paddingBottom: "15px" }}>
              <span className="badge badge-status" style={{ marginBottom: "10px", display: "inline-block" }}>
                SAVED LOG DETAILS
              </span>
              <h2>
                {selectedTrip.currentLocation.split(",")[0]} to {selectedTrip.dropoffLocation.split(",")[0]}
              </h2>
              <p style={{ color: "var(--text-secondary)", fontSize: "13px", marginTop: "4px" }}>
                Route stops: {selectedTrip.currentLocation} → {selectedTrip.pickupLocation} → {selectedTrip.dropoffLocation}
              </p>
            </div>

            {/* Stats Summary Dashboard */}
            <div className="stats-grid" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
              <div className="stat-card" style={{ padding: "16px" }}>
                <span className="label" style={{ fontSize: "11px" }}>Total Distance</span>
                <span className="value" style={{ fontSize: "20px" }}>{selectedTrip.totalDistanceMiles} mi</span>
              </div>
              <div className="stat-card" style={{ padding: "16px" }}>
                <span className="label" style={{ fontSize: "11px" }}>Driving Time</span>
                <span className="value" style={{ fontSize: "20px" }}>{selectedTrip.totalDrivingHours} hrs</span>
              </div>
              <div className="stat-card" style={{ padding: "16px" }}>
                <span className="label" style={{ fontSize: "11px" }}>HOS Days</span>
                <span className="value" style={{ fontSize: "20px" }}>{selectedTrip.hos?.estimatedDrivingDays} days</span>
              </div>
              <div className="stat-card" style={{ padding: "16px" }}>
                <span className="label" style={{ fontSize: "11px" }}>Total Cost</span>
                <span className="value" style={{ fontSize: "20px", color: "var(--color-success)" }}>
                  ${selectedTrip.totalTripCost?.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </span>
              </div>
            </div>

            {/* Financial Details */}
            <div style={{ background: "var(--bg-secondary)", padding: "20px", borderRadius: "var(--radius-lg)", border: "1px solid var(--border-color)", margin: "20px 0" }}>
              <h4 style={{ marginBottom: "12px" }}>Financial Operating Metrics</h4>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "15px" }}>
                <div>
                  <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Fuel Required</span>
                  <strong style={{ display: "block", fontSize: "15px", marginTop: "2px" }}>{selectedTrip.fuelRequired} gal</strong>
                </div>
                <div>
                  <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Fuel Expense</span>
                  <strong style={{ display: "block", fontSize: "15px", marginTop: "2px" }}>${selectedTrip.fuelCost?.toLocaleString()}</strong>
                </div>
                <div>
                  <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Driver Compensation</span>
                  <strong style={{ display: "block", fontSize: "15px", marginTop: "2px" }}>${selectedTrip.driverCost?.toLocaleString()}</strong>
                </div>
                <div>
                  <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Maintenance & Misc</span>
                  <strong style={{ display: "block", fontSize: "15px", marginTop: "2px" }}>
                    ${(selectedTrip.maintenanceCost + selectedTrip.tollsMisc)?.toLocaleString()}
                  </strong>
                </div>
              </div>
            </div>

            {/* Route Map */}
            <TripMap trip={selectedTrip} />

            {/* HOS Schedules & ELD charts */}
            <div style={{ marginTop: "30px" }}>
              <h3 style={{ marginBottom: "15px" }}>Hours of Service logs</h3>
              <p style={{ color: "var(--text-secondary)", fontSize: "14px", marginBottom: "20px" }}>
                <strong>Compliance Verdict:</strong> {selectedTrip.hos?.cycleStatus}
              </p>

              <div className="schedule-list">
                {selectedTrip.hos?.dailySchedule.map((day) => (
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
                            <strong style={{ display: "block", color: "var(--color-primary)", fontSize: "16px" }}>{day.drivingHours} hrs</strong>
                          </div>
                          <div>
                            <span style={{ color: "var(--text-muted)" }}>On Duty</span>
                            <strong style={{ display: "block", color: "var(--color-warning)", fontSize: "16px" }}>{day.onDutyHours} hrs</strong>
                          </div>
                          <div>
                            <span style={{ color: "var(--text-muted)" }}>Off Duty</span>
                            <strong style={{ display: "block", color: "var(--text-secondary)", fontSize: "16px" }}>{day.eldLog.offDutyHours} hrs</strong>
                          </div>
                          <div>
                            <span style={{ color: "var(--text-muted)" }}>Sleeper</span>
                            <strong style={{ display: "block", color: "var(--text-secondary)", fontSize: "16px" }}>{day.eldLog.sleeperHours} hrs</strong>
                          </div>
                          <div>
                            <span style={{ color: "var(--text-muted)" }}>Break</span>
                            <strong style={{ display: "block", color: "var(--text-secondary)", fontSize: "16px" }}>{day.breakHours} hrs</strong>
                          </div>
                        </div>

                        <ELDLog dayLog={day} />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
