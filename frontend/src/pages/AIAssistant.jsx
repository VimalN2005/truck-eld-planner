import React, { useState, useRef, useEffect } from "react";

const API_BASE_URL = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
  ? "http://127.0.0.1:8000"
  : "https://truck-eld-planner.onrender.com";

export default function AIAssistant({ currentTrip }) {
  const [messages, setMessages] = useState([
    {
      sender: "assistant",
      text: "Hello! I am your compliance and HOS assistant. I can inspect your calculated route compliance risks, fuel efficiency, or restart schedules. Ask me anything!",
    },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || sending) return;

    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { sender: "user", text: userMessage }]);
    setSending(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/ai/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: userMessage,
          trip: currentTrip, // Provide active trip calculation data for intelligent feedback
        }),
      });

      const data = await response.json();
      setMessages((prev) => [
        ...prev,
        { sender: "assistant", text: data.reply || "Sorry, I am having trouble understanding that query." },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { sender: "assistant", text: "Error communicating with AI assistant backend. Make sure the server is online." },
      ]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div style={{ maxWidth: "750px" }}>
      <div style={{ marginBottom: "20px" }}>
        <h1 style={{ fontSize: "28px", fontWeight: "700", marginBottom: "4px" }}>
          Smart Trip compliance Assistant 🤖
        </h1>
        <p style={{ color: "var(--text-secondary)" }}>
          {currentTrip ? (
            <span style={{ color: "var(--color-success)" }}>
              ✓ Analyzing active route: {currentTrip.currentLocation.split(",")[0]} → {currentTrip.dropoffLocation.split(",")[0]}
            </span>
          ) : (
            "Plan a trip to enable custom compliance risk analysis."
          )}
        </p>
      </div>

      <div className="chat-container">
        <div className="chat-history">
          {messages.map((msg, index) => (
            <div key={index} className={`chat-bubble ${msg.sender}`}>
              {msg.text}
            </div>
          ))}
          {sending && (
            <div className="chat-bubble assistant" style={{ fontStyle: "italic", opacity: 0.7 }}>
              Assistant is analyzing compliance safety limits...
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <form className="chat-input-area" onSubmit={handleSend}>
          <input
            type="text"
            className="chat-input"
            placeholder="Ask: 'Will I need a restart?' or 'What is the risk level?'"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={sending}
          />
          <button type="submit" className="chat-send-btn" disabled={sending}>
            Send
          </button>
        </form>
      </div>
      
      {/* Suggestions panel */}
      <div style={{ marginTop: "20px" }}>
        <span style={{ fontSize: "13px", fontWeight: "600", color: "var(--text-secondary)" }}>Suggested Questions:</span>
        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", marginTop: "8px" }}>
          {["Will I need a restart?", "What is my risk level?", "Tell me about fuel costs", "Show trip durations"].map((q) => (
            <button
              key={q}
              onClick={() => setInput(q)}
              style={{
                width: "auto",
                background: "var(--bg-secondary)",
                border: "1px solid var(--border-color)",
                color: "var(--text-secondary)",
                fontSize: "12px",
                padding: "6px 12px",
                borderRadius: "50px",
                cursor: "pointer",
                marginTop: "0"
              }}
            >
              {q}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
