
import asyncio
import sqlite3
import random
import time
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal

# --- Configuration ---
DB_NAME = "KirkNGR_6007.db"
MACHINE_NAME = "KirkNGR 6007"
SIMULATION_INTERVAL = 1.0  # seconds between simulation ticks

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Events table: stores production and error events
    c.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            event_type TEXT,  -- 'production', 'error', 'state_change'
            details TEXT
        )
    ''')
    conn.commit()
    conn.close()

def log_event(event_type: str, details: str = ""):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO events (timestamp, event_type, details) VALUES (?, ?, ?)",
              (datetime.now(), event_type, details))
    conn.commit()
    conn.close()

# --- Global State ---
class MachineState:
    status: Literal["STOPPED", "RUNNING", "ERROR"] = "STOPPED"
    target_bpm: int = 70  # Target bags per minute
    # Simulation internals
    _last_tick: float = 0

state = MachineState()

# --- Simulation Logic ---
async def simulation_loop():
    """Background task to simulate machine operation."""
    while True:
        if state.status == "RUNNING":
            now = time.time()
            
            # Simulate bags production
            # 70 BPM = 70/60 bags per second ~= 1.16 bags per second
            # We check if a 'bag' would have been produced in this interval
            # Simplified: Random chance based on BPM and interval
            
            chance_to_produce = (state.target_bpm / 60.0) * SIMULATION_INTERVAL
            
            # Allow for slight variations (jitter)
            jitter = random.uniform(0.9, 1.1)
            
            if random.random() < (chance_to_produce * jitter):
                 log_event("production", "1")
            
            # Simulate errors (Low probability: e.g., 1 every 2 minutes approx)
            # 1 every 120 seconds -> probability per second ~ 1/120
            if random.random() < (1.0 / 120.0 * SIMULATION_INTERVAL):
                error_types = ["Jam detected", "Seal failure", "Temperature warning"]
                err = random.choice(error_types)
                log_event("error", err)
                # Optional: Stop machine on error? 
                # For this demo, we'll log it but keep running unless critical, 
                # or maybe just let the user see the count increase.
                
        await asyncio.sleep(SIMULATION_INTERVAL)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    asyncio.create_task(simulation_loop())
    yield
    # Shutdown
    print("Shutting down...")

app = FastAPI(lifespan=lifespan)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Models ---
class ControlCommand(BaseModel):
    command: Literal["start", "stop"]

# --- Endpoints ---

@app.get("/api/status")
def get_status():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    now = datetime.now()
    one_hour_ago = now - timedelta(hours=1)
    
    # 1. Correct packaging last hour
    c.execute("SELECT COUNT(*) FROM events WHERE event_type='production' AND timestamp > ?", (one_hour_ago,))
    correct_last_hour = c.fetchone()[0]
    
    # 2. Bags per minute (Rolling 1 minute)
    one_minute_ago = now - timedelta(minutes=1)
    c.execute("SELECT COUNT(*) FROM events WHERE event_type='production' AND timestamp > ?", (one_minute_ago,))
    production_last_minute = c.fetchone()[0]
    current_bpm = production_last_minute # Since we look back exactly 1 minute, the count IS the rate.
    
    # 3. Total errors per hour
    c.execute("SELECT COUNT(*) FROM events WHERE event_type='error' AND timestamp > ?", (one_hour_ago,))
    errors_last_hour = c.fetchone()[0]
    
    # 4. Total errors since start (all time in DB)
    c.execute("SELECT COUNT(*) FROM events WHERE event_type='error'")
    total_errors = c.fetchone()[0]
    
    conn.close()
    
    return {
        "machine_name": MACHINE_NAME,
        "status": state.status,
        "metrics": {
            "correct_last_hour": correct_last_hour,
            "bpm": current_bpm,
            "errors_last_hour": errors_last_hour,
            "total_errors": total_errors
        }
    }

@app.post("/api/control")
def control_machine(cmd: ControlCommand):
    if cmd.command == "start":
        state.status = "RUNNING"
        log_event("state_change", "STARTED")
    elif cmd.command == "stop":
        state.status = "STOPPED"
        log_event("state_change", "STOPPED")
    return {"status": state.status}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
