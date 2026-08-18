import React, { useState, useEffect } from "react";
import "./App.css";

// Import Page components
import Dashboard from "./pages/Dashboard";
import TripPlanner from "./pages/TripPlanner";
import TripHistory from "./pages/TripHistory";
import Profile from "./pages/Profile";
import AIAssistant from "./pages/AIAssistant";

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [activeTab, setActiveTab] = useState("dashboard");
  const [trips, setTrips] = useState([]);
  const [currentTrip, setCurrentTrip] = useState(null);
  
  // Auth Form State
  const [authMode, setAuthMode] = useState("login"); // 'login' or 'register'
  const [authForm, setAuthForm] = useState({
    username: "",
    password: "",
    name: "",
    driverId: "",
    truckNumber: "",
    carrierName: "",
  });
  const [authError, setAuthError] = useState(null);
  const [authLoading, setAuthLoading] = useState(false);

  // Check user authentication status on mount
  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const response = await fetch("http://127.0.0.1:8000/api/user/");
      const data = await response.json();
      if (data.isAuthenticated) {
        setIsAuthenticated(true);
        setUser({
          username: data.username,
          name: data.name,
          ...data.profile,
        });
        fetchHistory();
      }
    } catch (err) {
      console.error("Auth verify error:", err);
    }
  };

  const fetchHistory = async () => {
    try {
      const response = await fetch("http://127.0.0.1:8000/api/trips/");
      if (response.ok) {
        const data = await response.json();
        setTrips(data);
      }
    } catch (err) {
      console.error("Failed to load historical trips:", err);
    }
  };

  const handleAuthChange = (e) => {
    setAuthForm({
      ...authForm,
      [e.target.name]: e.target.value,
    });
  };

  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    setAuthError(null);
    setAuthLoading(true);

    const endpoint = authMode === "login" ? "login" : "register";
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/${endpoint}/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(authForm),
      });

      const data = await response.json();

      if (!response.ok) {
        setAuthError(data.error || "Authentication failed");
        return;
      }

      setIsAuthenticated(true);
      setUser({
        username: data.username,
        name: data.name,
        ...data.profile,
      });
      
      // Clear forms
      setAuthForm({
        username: "",
        password: "",
        name: "",
        driverId: "",
        truckNumber: "",
        carrierName: "",
      });

      // Load trips history
      const tripsResponse = await fetch("http://127.0.0.1:8000/api/trips/");
      if (tripsResponse.ok) {
        const tripsData = await tripsResponse.json();
        setTrips(tripsData);
      }
      
      setActiveTab("dashboard");
    } catch (err) {
      setAuthError("Cannot establish connection to authentication server. Verify Django backend is running.");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await fetch("http://127.0.0.1:8000/api/logout/", { method: "POST" });
    } catch (err) {
      console.error("Logout issue:", err);
    }
    setIsAuthenticated(false);
    setUser(null);
    setTrips([]);
    setCurrentTrip(null);
    setActiveTab("dashboard");
  };

  const handleProfileUpdated = (data) => {
    setUser({
      ...user,
      name: data.name,
      ...data.profile,
    });
  };

  const handleTripGenerated = () => {
    fetchHistory();
    // Fetch latest generated trip to save context for the AI query assistant
    fetch("http://127.0.0.1:8000/api/trips/")
      .then((res) => res.json())
      .then((data) => {
        setTrips(data);
        if (data.length > 0) {
          // Set active trip context to the most recently generated one
          setCurrentTrip(data[0].details || data[0]);
        }
      });
  };

  // Auth Screen Render
  if (!isAuthenticated) {
    return (
      <div className="auth-wrapper">
        <div className="auth-card">
          <div className="auth-header">
            <span style={{ fontSize: "40px" }}>🚛</span>
            <h1 style={{ marginTop: "10px" }}>Smart Truck ELD Planner</h1>
            <p>Compliance, HOS simulation, and financial routing logs</p>
          </div>

          {authError && (
            <div style={{ background: "rgba(239, 68, 68, 0.1)", border: "1px solid var(--color-danger)", color: "#fca5a5", padding: "12px", borderRadius: "var(--radius-sm)", marginBottom: "15px", fontSize: "14px" }}>
              ⚠️ {authError}
            </div>
          )}

          <form onSubmit={handleAuthSubmit}>
            <div className="form-group">
              <label>Username</label>
              <input
                type="text"
                name="username"
                value={authForm.username}
                onChange={handleAuthChange}
                required
              />
            </div>
            
            <div className="form-group">
              <label>Password</label>
              <input
                type="password"
                name="password"
                value={authForm.password}
                onChange={handleAuthChange}
                required
              />
            </div>

            {authMode === "register" && (
              <>
                <div className="form-group">
                  <label>Full Name</label>
                  <input
                    type="text"
                    name="name"
                    value={authForm.name}
                    onChange={handleAuthChange}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Driver license/ID</label>
                  <input
                    type="text"
                    name="driverId"
                    value={authForm.driverId}
                    onChange={handleAuthChange}
                  />
                </div>
                <div className="form-group">
                  <label>Truck Number</label>
                  <input
                    type="text"
                    name="truckNumber"
                    value={authForm.truckNumber}
                    onChange={handleAuthChange}
                  />
                </div>
                <div className="form-group">
                  <label>Carrier Name</label>
                  <input
                    type="text"
                    name="carrierName"
                    value={authForm.carrierName}
                    onChange={handleAuthChange}
                  />
                </div>
              </>
            )}

            <button type="submit" disabled={authLoading} className="btn-primary" style={{ width: "100%", marginTop: "15px" }}>
              {authLoading ? "Authenticating..." : authMode === "login" ? "Login" : "Register"}
            </button>
          </form>

          <div className="auth-toggle">
            {authMode === "login" ? (
              <p>
                Don't have a profile yet? <span onClick={() => setAuthMode("register")}>Register here</span>
              </p>
            ) : (
              <p>
                Already registered? <span onClick={() => setAuthMode("login")}>Login here</span>
              </p>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Sidebar Layout Navigation Render
  return (
    <div className="app-container">
      {/* Sidebar navigation */}
      <aside className="sidebar">
        <div className="logo-section">
          <span className="logo-icon">🚛</span>
          <h2>TruckELD Planner</h2>
        </div>

        <nav>
          <ul className="sidebar-menu">
            <li 
              className={`menu-item ${activeTab === "dashboard" ? "active" : ""}`}
              onClick={() => setActiveTab("dashboard")}
            >
              <span>📊</span>
              <span>Dashboard</span>
            </li>
            <li 
              className={`menu-item ${activeTab === "planner" ? "active" : ""}`}
              onClick={() => setActiveTab("planner")}
            >
              <span>🧭</span>
              <span>Trip Planner</span>
            </li>
            <li 
              className={`menu-item ${activeTab === "history" ? "active" : ""}`}
              onClick={() => setActiveTab("history")}
            >
              <span>🗂️</span>
              <span>Trip Logs</span>
            </li>
            <li 
              className={`menu-item ${activeTab === "ai" ? "active" : ""}`}
              onClick={() => setActiveTab("ai")}
            >
              <span>🤖</span>
              <span>Compliance AI</span>
            </li>
            <li 
              className={`menu-item ${activeTab === "profile" ? "active" : ""}`}
              onClick={() => setActiveTab("profile")}
            >
              <span>⚙️</span>
              <span>Profile Settings</span>
            </li>
          </ul>
        </nav>

        <div className="sidebar-footer">
          <div className="driver-info-mini">
            <span className="name">{user?.name || "Driver"}</span>
            <span className="truck">Truck: {user?.truckNumber || "N/A"}</span>
          </div>
          <button className="logout-btn" onClick={handleLogout}>
            Logout Session
          </button>
        </div>
      </aside>

      {/* Page Routing Views */}
      <main className="main-content">
        {activeTab === "dashboard" && (
          <Dashboard 
            trips={trips} 
            profile={user} 
            onNavigate={(tab) => setActiveTab(tab)} 
          />
        )}
        {activeTab === "planner" && (
          <TripPlanner 
            profile={user} 
            onTripGenerated={handleTripGenerated} 
          />
        )}
        {activeTab === "history" && (
          <TripHistory 
            trips={trips} 
            onRefresh={fetchHistory} 
          />
        )}
        {activeTab === "profile" && (
          <Profile 
            profile={user} 
            onProfileUpdated={handleProfileUpdated} 
          />
        )}
        {activeTab === "ai" && (
          <AIAssistant 
            currentTrip={currentTrip} 
          />
        )}
      </main>
    </div>
  );
}

export default App;