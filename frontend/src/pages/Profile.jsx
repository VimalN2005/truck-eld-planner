import React, { useState } from "react";

export default function Profile({ profile, onProfileUpdated }) {
  const [formData, setFormData] = useState({
    name: profile?.name || "",
    driverId: profile?.driverId || "",
    truckNumber: profile?.truckNumber || "",
    carrierName: profile?.carrierName || "",
    currentCycleUsed: profile?.currentCycleUsed || 0.0,
    truckMpg: profile?.truckMpg || 6.5,
    fuelPricePreset: profile?.fuelPricePreset || 4.00,
  });

  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: name === "currentCycleUsed" || name === "truckMpg" || name === "fuelPricePreset" ? parseFloat(value) || 0 : value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setSuccess(false);
    setError(null);

    try {
      const response = await fetch("http://127.0.0.1:8000/api/profile/", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          // Cookies authentication is handled automatically by the browser since session cookies are sent
        },
        body: JSON.stringify(formData),
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.error || "Failed to update profile settings");
        return;
      }

      setSuccess(true);
      if (onProfileUpdated) {
        onProfileUpdated(data);
      }
    } catch (err) {
      setError("Connection issue while saving profile updates. Ensure Django server is online.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ maxWidth: "650px" }}>
      <div style={{ marginBottom: "25px" }}>
        <h1 style={{ fontSize: "28px", fontWeight: "700", marginBottom: "4px" }}>
          Driver Profile Settings
        </h1>
        <p style={{ color: "var(--text-secondary)" }}>
          Configure your carrier credentials and default truck specifications.
        </p>
      </div>

      {success && (
        <div style={{ background: "rgba(16, 185, 129, 0.1)", border: "1px solid var(--color-success)", color: "#a7f3d0", padding: "12px 18px", borderRadius: "var(--radius-md)", marginBottom: "20px" }}>
          ✓ Profile settings updated successfully!
        </div>
      )}

      {error && (
        <div className="error-banner">
          <span>⚠️</span>
          <p>{error}</p>
        </div>
      )}

      <form className="trip-form-card" onSubmit={handleSubmit}>
        <h3 style={{ marginBottom: "15px", borderBottom: "1px solid var(--border-color)", paddingBottom: "8px" }}>
          Carrier & Driver Info
        </h3>
        
        <div className="form-row">
          <div className="form-group">
            <label>Driver Full Name</label>
            <input
              type="text"
              name="name"
              value={formData.name}
              onChange={handleChange}
              required
            />
          </div>
          <div className="form-group">
            <label>Driver License/ID</label>
            <input
              type="text"
              name="driverId"
              value={formData.driverId}
              onChange={handleChange}
            />
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Truck Number</label>
            <input
              type="text"
              name="truckNumber"
              value={formData.truckNumber}
              onChange={handleChange}
            />
          </div>
          <div className="form-group">
            <label>Carrier Company Name</label>
            <input
              type="text"
              name="carrierName"
              value={formData.carrierName}
              onChange={handleChange}
            />
          </div>
        </div>

        <h3 style={{ marginTop: "25px", marginBottom: "15px", borderBottom: "1px solid var(--border-color)", paddingBottom: "8px" }}>
          ELD & Fuel Defaults
        </h3>

        <div className="form-row">
          <div className="form-group">
            <label>Current Cycle Used (Hours)</label>
            <input
              type="number"
              name="currentCycleUsed"
              min="0"
              max="70"
              step="0.1"
              value={formData.currentCycleUsed}
              onChange={handleChange}
            />
          </div>
          <div className="form-group">
            <label>Default Truck MPG</label>
            <input
              type="number"
              name="truckMpg"
              step="0.1"
              min="4"
              max="15"
              value={formData.truckMpg}
              onChange={handleChange}
            />
          </div>
          <div className="form-group">
            <label>Default Fuel Price ($/gal)</label>
            <input
              type="number"
              name="fuelPricePreset"
              step="0.01"
              min="2.00"
              max="8.00"
              value={formData.fuelPricePreset}
              onChange={handleChange}
            />
          </div>
        </div>

        <button 
          type="submit" 
          disabled={saving} 
          className="btn-primary" 
          style={{ width: "100%", marginTop: "15px" }}
        >
          {saving ? "Saving Updates..." : "Save Profile Settings"}
        </button>
      </form>
    </div>
  );
}
