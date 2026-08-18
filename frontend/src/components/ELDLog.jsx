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
    <div className="eld-chart-card">
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
      <div className="eld-hour-labels">
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
    </div>
  );
}
