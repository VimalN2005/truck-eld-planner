import React from "react";

export default function ELDLog({ dayLog }) {
  if (!dayLog || !dayLog.eldLog || !dayLog.eldLog.intervals) {
    return null;
  }

  const { intervals } = dayLog.eldLog;

  // Row Y positions
  const getY = (status) => {
    switch (status) {
      case "OFF": return 15;
      case "SB": return 45;
      case "D": return 75;
      case "ON": return 105;
      default: return 15;
    }
  };

  // Build SVG path
  let pathD = "";
  if (intervals.length > 0) {
    const startY = getY(intervals[0].status);
    pathD = `M 0 ${startY}`;
    
    intervals.forEach((interval, idx) => {
      const endX = (interval.end / 24) * 480;
      const targetY = getY(interval.status);
      
      // Horizontal line to end of current segment
      pathD += ` H ${endX}`;
      
      // Vertical line to next segment if it exists
      if (idx < intervals.length - 1) {
        const nextTargetY = getY(intervals[idx + 1].status);
        pathD += ` V ${nextTargetY}`;
      }
    });
  }

  // Generate 24 grid lines
  const gridLines = [];
  for (let i = 1; i < 24; i++) {
    gridLines.push((i / 24) * 480);
  }

  return (
    <div className="eld-chart-card" style={{ display: "flex", flexDirection: "column", gap: "15px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h4 style={{ color: "#f9fafb" }}>Daily ELD Log Grid - Day {dayLog.day}</h4>
        <span style={{ fontSize: "12px", color: "#9ca3af" }}>
          D: {dayLog.eldLog.drivingHours}h | ON: {dayLog.eldLog.onDutyHours}h | OFF: {dayLog.eldLog.offDutyHours}h | SB: {dayLog.eldLog.sleeperHours}h
        </span>
      </div>

      <div className="eld-chart-container">
        {/* Y Axis Labels */}
        <div className="eld-y-axis">
          <div>OFF DUTY</div>
          <div>SLEEPER</div>
          <div>DRIVING</div>
          <div>ON DUTY</div>
        </div>

        {/* SVG Graph wrapper */}
        <div className="eld-svg-wrapper">
          <svg className="eld-timeline-svg" viewBox="0 0 480 120" preserveAspectRatio="none">
            {/* Horizontal Grid lines */}
            <line x1="0" y1="15" x2="480" y2="15" stroke="#334155" strokeWidth="0.5" />
            <line x1="0" y1="45" x2="480" y2="45" stroke="#334155" strokeWidth="0.5" />
            <line x1="0" y1="75" x2="480" y2="75" stroke="#334155" strokeWidth="0.5" />
            <line x1="0" y1="105" x2="480" y2="105" stroke="#334155" strokeWidth="0.5" />

            {/* Vertical Hour lines */}
            {gridLines.map((x, idx) => (
              <line 
                key={idx} 
                x1={x} 
                y1="0" 
                x2={x} 
                y2="120" 
                stroke="#334155" 
                strokeWidth={idx % 4 === 3 ? "1" : "0.5"} 
                strokeDasharray={idx % 4 === 3 ? "" : "2,2"} 
              />
            ))}

            {/* The actual ELD log route path line */}
            {pathD && (
              <path 
                d={pathD} 
                fill="none" 
                stroke="#10b981" 
                strokeWidth="2.5" 
                strokeLinecap="round" 
                strokeLinejoin="miter" 
              />
            )}
          </svg>
        </div>
      </div>
      
      {/* Hour markers */}
      <div className="eld-hour-labels" style={{ marginTop: "-10px" }}>
        <span>M</span>
        <span>1</span>
        <span>2</span>
        <span>3</span>
        <span>4</span>
        <span>5</span>
        <span>6</span>
        <span>7</span>
        <span>8</span>
        <span>9</span>
        <span>10</span>
        <span>11</span>
        <span>N</span>
        <span>1</span>
        <span>2</span>
        <span>3</span>
        <span>4</span>
        <span>5</span>
        <span>6</span>
        <span>7</span>
        <span>8</span>
        <span>9</span>
        <span>10</span>
        <span>11</span>
        <span>M</span>
      </div>

      {/* Recap and Remarks columns */}
      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "20px", marginTop: "10px", borderTop: "1px solid var(--border-color)", paddingTop: "15px" }}>
        {/* Left Column: Remarks */}
        <div>
          <h5 style={{ color: "var(--text-primary)", marginBottom: "8px", fontSize: "14px" }}>Remarks (Duty Status Changes)</h5>
          {dayLog.eldLog.remarks && dayLog.eldLog.remarks.length > 0 ? (
            <ul style={{ listStyle: "none", paddingLeft: 0, maxHeight: "150px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "6px" }}>
              {dayLog.eldLog.remarks.map((rem, idx) => (
                <li key={idx} style={{ fontSize: "12px", color: "var(--text-secondary)", borderLeft: "2px solid var(--color-primary)", paddingLeft: "8px" }}>
                  {rem}
                </li>
              ))}
            </ul>
          ) : (
            <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>No duty changes logged.</p>
          )}
        </div>
        
        {/* Right Column: Recap */}
        {dayLog.eldLog.recap && (
          <div>
            <h5 style={{ color: "var(--text-primary)", marginBottom: "8px", fontSize: "14px" }}>HOS 70h/8-Day Cycle Recap</h5>
            <table style={{ width: "100%", fontSize: "12px", borderCollapse: "collapse", border: "1px solid var(--border-color)" }}>
              <tbody>
                <tr style={{ borderBottom: "1px solid var(--border-color)" }}>
                  <td style={{ padding: "6px 8px", color: "var(--text-secondary)", background: "var(--bg-tertiary)" }}>On Duty Today:</td>
                  <td style={{ padding: "6px 8px", fontWeight: "600", textAlign: "right", background: "var(--bg-tertiary)" }}>{dayLog.eldLog.recap.onDutyToday} hrs</td>
                </tr>
                <tr style={{ borderBottom: "1px solid var(--border-color)" }}>
                  <td style={{ padding: "6px 8px", color: "var(--text-secondary)" }}>Duty Last 7 Days (A):</td>
                  <td style={{ padding: "6px 8px", fontWeight: "600", textAlign: "right" }}>{dayLog.eldLog.recap.rolling7DaysTotal} hrs</td>
                </tr>
                <tr>
                  <td style={{ padding: "6px 8px", color: "var(--text-secondary)", background: "var(--bg-tertiary)" }}>Available Tomorrow (70 - A):</td>
                  <td style={{ padding: "6px 8px", fontWeight: "700", color: "var(--color-success)", textAlign: "right", background: "var(--bg-tertiary)" }}>{dayLog.eldLog.recap.availableTomorrow} hrs</td>
                </tr>
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
