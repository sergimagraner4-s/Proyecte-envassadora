const API_URL = "http://localhost:8000/api";
let pollingInterval = null;

// DOM Elements
const elStatusBadge = document.getElementById('statusBadge');
const valBPM = document.getElementById('valBPM');
const valProduction = document.getElementById('valProduction');
const valErrorsHour = document.getElementById('valErrorsHour');
const valErrorsTotal = document.getElementById('valErrorsTotal');
const consoleLog = document.getElementById('consoleLog');
const btnStart = document.getElementById('btnStart');
const btnStop = document.getElementById('btnStop');

// Utility: Clock
function updateClock() {
    const now = new Date();
    document.getElementById('clock').innerText = now.toLocaleTimeString();
}
setInterval(updateClock, 1000);
updateClock();

// Utility: Logger
function log(msg) {
    const div = document.createElement('div');
    div.className = 'log-entry';
    div.innerText = `> ${new Date().toLocaleTimeString()} - ${msg}`;
    consoleLog.prepend(div);
    if (consoleLog.children.length > 50) {
        consoleLog.lastChild.remove();
    }
}

// API Calls
async function fetchStatus() {
    try {
        const response = await fetch(`${API_URL}/status`);
        if (!response.ok) throw new Error("Network response was not ok");
        const data = await response.json();
        updateUI(data);
    } catch (err) {
        console.error("Fetch error:", err);
        elStatusBadge.innerText = "OFFLINE";
        elStatusBadge.className = "status-badge"; // Reset classes
    }
}

async function sendControl(command) {
    try {
        const response = await fetch(`${API_URL}/control`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: command })
        });
        const data = await response.json();
        log(`Comando enviado: ${command.toUpperCase()} -> Estado: ${data.status}`);
        fetchStatus(); // Immediate update
    } catch (err) {
        log(`Error enviando comando: ${err}`);
    }
}

// UI Updates
function updateUI(data) {
    const status = data.status;
    const m = data.metrics;

    // Status Badge
    elStatusBadge.innerText = status;
    elStatusBadge.className = "status-badge " + status.toLowerCase();

    // Metrics
    valBPM.innerText = m.bpm;
    valProduction.innerText = m.correct_last_hour;
    valErrorsHour.innerText = m.errors_last_hour;
    valErrorsTotal.innerText = m.total_errors;

    // Button states
    if (status === "RUNNING") {
        btnStart.classList.add('active'); // Styling for visual feedback if needed
    }
}

// Event Listeners
btnStart.addEventListener('click', () => sendControl('start'));
btnStop.addEventListener('click', () => sendControl('stop'));

// Init
log("Conectando con el sistema central...");
fetchStatus();
pollingInterval = setInterval(fetchStatus, 1000); // Poll every second
