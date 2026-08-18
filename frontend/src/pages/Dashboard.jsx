import React from "react";

export default function Dashboard({ trips, profile, onNavigate }) {
  // Aggregate stats from trips
  const totalTrips = trips.length;
  const totalMiles = trips.reduce((sum, t) => sum + parseFloat(t.totalDistanceMiles || 0), 0);
  const totalHours = trips.reduce((sum, t) => sum + parseFloat(t.totalDrivingHours || 0), 0);
  const remainingCycle = Math.max(0, 70 - (profile?.currentCycleUsed || 0));

  return (
    <div>
      <div style={{ marginBottom: "30px" }}>
        <h1 style={{ fontSize: "28px", fontWeight: "700", marginBottom: "4px" }}>
          Welcome back, {profile?.name || "Driver"} 👋
        </h1>
        <p style={{ color: "var(--text-secondary)" }}>
          Here is your compliance and fleet summary for today.
        </p>
      </div>

      {/* Analytics Dashboard Grid */}
      <div className="stats-grid">
        <div className="stat-card">
          <span className="label">Total Trips</span>
          <span className="value">{totalTrips}</span>
          <span className="desc">Active & Saved trips</span>
        </div>

        <div className="stat-card">
          <span className="label">Total Distance</span>
          <span className="value">{totalMiles.toLocaleString(undefined, { maximumFractionDigits: 1 })} mi</span>
          <span className="desc">Logged transit distance</span>
        </div>

        <div className="stat-card">
          <span className="label">Driving Time</span>
          <span className="value">{totalHours.toLocaleString(undefined, { maximumFractionDigits: 1 })} hrs</span>
          <span className="desc">Active wheel hours</span>
        </div>

        <div className="stat-card">
          <span className="label">Cycle Remaining</span>
          <span className="value" style={{ color: remainingCycle < 15 ? "var(--color-danger)" : "var(--color-success)" }}>
            {remainingCycle} hrs
          </span>
          <span className="desc">Out of 70h cycle limit</span>
        </div>
      </div>

      <div className="dashboard-grid">
        {/* Recent Trips Panel */}
        <div className="dashboard-panel">
          <h3>
            <span>Recent Trips</span>
            <button 
              onClick={() => onNavigate("planner")} 
              style={{ width: "auto", padding: "6px 12px", fontSize: "12px", marginTop: "0" }}
              className="btn-primary"
            >
              + Plan New
            </button>
          </h3>
          
          {trips.length === 0 ? (
            <p style={{ color: "var(--text-muted)", padding: "20px 0" }}>
              No trips calculated yet. Open the Trip Planner to get started!
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "15px" }}>
              {trips.slice(0, 3).map((trip) => (
                <div 
                  key={trip.id} 
                  style={{ 
                    background: "var(--bg-tertiary)", 
                    padding: "16px", 
                    borderRadius: "var(--radius-md)",
                    border: "1px solid var(--border-color)",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center"
                  }}
                >
                  <div>
                    <strong style={{ display: "block", fontSize: "15px", color: "var(--text-primary)" }}>
                      {trip.pickupLocation.split(",")[0]} → {trip.dropoffLocation.split(",")[0]}
                    </strong>
                    <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                      Planned on {trip.createdAt} from {trip.currentLocation.split(",")[0]}
                    </span>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <strong style={{ display: "block", color: "var(--color-primary)" }}>
                      {trip.totalDistanceMiles} mi
                    </strong>
                    <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                      {trip.totalDrivingHours} hrs
                    </span>
                  </div>
                </div>
              ))}
              <button 
                onClick={() => onNavigate("history")}
                style={{ background: "transparent", border: "none", color: "var(--color-primary)", textDecoration: "underline", fontSize: "14px", alignSelf: "flex-start", cursor: "pointer", width: "auto", padding: "0" }}
              >
                View all trip history →
              </button>
            </div>
          )}
        </div>

        {/* HOS Compliance Sidebar */}
        <div className="dashboard-panel">
          <h3>Compliance Cheat Sheet</h3>
          <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "15px" }}>
            <li style={{ display: "flex", gap: "12px" }}>
              <span style={{ fontSize: "20px" }}>🚨</span>
              <div>
                <strong>11-Hour Driving Limit</strong>
                <p style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
                  Must not drive more than 11 hours following 10 consecutive hours off duty.
                </p>
              </div>
            </li>
            <li style={{ display: "flex", gap: "12px" }}>
              <span style={{ fontSize: "20px" }}>⏱️</span>
              <div>
                <strong>14-Hour Duty Window</strong>
                <p style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
                  Must not drive after 14 hours on-duty since starting the shift.
                </p>
              </div>
            </li>
            <li style={{ display: "flex", gap: "12px" }}>
              <span style={{ fontSize: "20px" }}>🛑</span>
              <div>
                <strong>30-Minute Break</strong>
                <p style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
                  Requires 30 mins rest if driving for more than 8 hours since last break.
                </p>
              </div>
            </li>
            <li style={{ display: "flex", gap: "12px" }}>
              <span style={{ fontSize: "20px" }}>🔄</span>
              <div>
                <strong>34-Hour Restart</strong>
                <p style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
                  Taking 34 straight hours of off-duty resets the weekly 70-hour cycle clock.
                </p>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
