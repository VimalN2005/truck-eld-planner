 import { useState } from "react";
import "./App.css";

function App() {
  const [trip, setTrip] = useState({
    currentLocation: "",
    pickupLocation: "",
    dropoffLocation: "",
    cycleUsed: "",
  });

  const handleChange = (e) => {
    setTrip({
      ...trip,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    console.log("Trip Details:", trip);
    alert("Trip details submitted successfully!");
  };

  return (
    <div className="app">
      <div className="container">
        <div className="header">
          <h1>Truck Trip Planner</h1>
          <p>Plan routes, manage Hours of Service, and generate ELD logs.</p>
        </div>

        <form className="trip-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Current Location</label>
            <input
              type="text"
              name="currentLocation"
              placeholder="Enter current location"
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
              placeholder="Enter pickup location"
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
              placeholder="Enter dropoff location"
              value={trip.dropoffLocation}
              onChange={handleChange}
              required
            />
          </div>

          <div className="form-group">
            <label>Current Cycle Used (Hours)</label>
            <input
              type="number"
              name="cycleUsed"
              placeholder="Example: 25"
              min="0"
              max="70"
              value={trip.cycleUsed}
              onChange={handleChange}
              required
            />
          </div>

          <button type="submit">Generate Trip Plan →</button>
        </form>
      </div>
    </div>
  );
}

export default App;