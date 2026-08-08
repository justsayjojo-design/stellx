# satellite_ops_engine.py

import json
import os
import random
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from openai import OpenAI

# -----------------------------
# Config
# -----------------------------
from config import OPENAI_API_KEY, OPENAI_MODEL, TICK_SECONDS, SEVERE_ANOMALY_ODDS

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=OPENAI_API_KEY
)

app = FastAPI(title="Satellite Ops Engine", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# State
# -----------------------------
@dataclass
class SatelliteState:
    battery: int = 82
    storage: float = 35.0
    images: int = 1500
    orbit: int = 1

    def snapshot(self) -> Dict[str, Any]:
        return asdict(self)


# -----------------------------
# Request models
# -----------------------------
class FaultInjectionRequest(BaseModel):
    fault_type: str = Field(
        default="auto",
        description=(
            "auto, battery_critical, cpu_overheat, comm_loss, storage_full, "
            "solar_failure, sensor_glitch, multi_fault"
        ),
    )


# -----------------------------
# Core engine
# -----------------------------
class TelemetryEngine:
    def __init__(self) -> None:
        self.state = SatelliteState()

    def _utc_now(self) -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _base_packet(self) -> Dict[str, Any]:
        """
        Mostly healthy telemetry, with gentle drift.
        """
        sunlight = random.random() < 0.78

        if sunlight:
            solar = random.randint(950, 1400)
            self.state.battery = min(100, self.state.battery + random.randint(0, 2))
            battery_temp = round(random.uniform(20, 31), 1)
        else:
            solar = random.randint(0, 80)
            self.state.battery = max(70, self.state.battery - random.randint(0, 2))
            battery_temp = round(random.uniform(10, 22), 1)

        power = random.randint(280, 560)
        cpu_temp = round(random.uniform(36, 54), 1)

        comm = random.choices(
            ["Connected", "Weak"],
            weights=[95, 5],
        )[0]

        if comm == "Connected":
            signal = random.randint(-62, -43)
        else:
            signal = random.randint(-92, -63)

        mode = random.choices(
            ["Nominal", "Earth Observation", "Data Transmission", "Calibration", "Standby"],
            weights=[58, 18, 12, 7, 5],
        )[0]

        task_map = {
            "Nominal": "Health Monitoring",
            "Earth Observation": "Capturing Earth Images",
            "Data Transmission": "Downlink Telemetry",
            "Calibration": "Sensor Calibration",
            "Standby": "Idle",
        }

        task = task_map[mode]
        camera = "Active" if mode == "Earth Observation" else "Idle"

        if camera == "Active":
            new_images = random.randint(2, 6)
            self.state.images += new_images
            self.state.storage = min(85.0, self.state.storage + new_images * 0.03)

        if mode == "Data Transmission":
            self.state.storage = max(8.0, self.state.storage - random.uniform(0.8, 2.2))

        if random.random() < 0.04:
            self.state.orbit += 1

        fault = "None"
        health = random.choices(["Excellent", "Good"], weights=[40, 60])[0]

        return {
            "timestamp": self._utc_now(),
            "Battery Percentage": self.state.battery,
            "Solar Panel Output": solar,
            "Power Consumption": power,
            "Battery Temperature": battery_temp,
            "CPU Temperature": cpu_temp,
            "Communication Status": comm,
            "Signal Strength": signal,
            "Storage Used": round(self.state.storage, 1),
            "Camera Status": camera,
            "Images Captured": self.state.images,
            "Current Task": task,
            "Mission Mode": mode,
            "Orbit Number": self.state.orbit,
            "Active Fault": fault,
            "Overall Satellite Health": health,
            "Injection Mode": "normal",
        }

    def _severe_anomaly_packet(self, fault_type: str = "auto") -> Dict[str, Any]:
        """
        Force a serious anomaly for fault injection or rare random severe failure.
        """
        if fault_type == "auto":
            fault_type = random.choice(
                [
                    "battery_critical",
                    "cpu_overheat",
                    "comm_loss",
                    "storage_full",
                    "solar_failure",
                    "sensor_glitch",
                    "multi_fault",
                ]
            )

        packet = self._base_packet()

        if fault_type == "battery_critical":
            packet.update(
                {
                    "Battery Percentage": random.randint(2, 9),
                    "Solar Panel Output": random.randint(0, 35),
                    "Battery Temperature": round(random.uniform(-2, 6), 1),
                    "Power Consumption": random.randint(540, 760),
                    "Active Fault": "Critical Battery Failure",
                    "Overall Satellite Health": "Critical",
                    "Mission Mode": "Safe Mode",
                    "Current Task": "Emergency Power Conservation",
                    "Communication Status": "Weak",
                    "Signal Strength": random.randint(-98, -70),
                    "Camera Status": "Idle",
                    "Injection Mode": "severe_anomaly",
                }
            )

        elif fault_type == "cpu_overheat":
            packet.update(
                {
                    "CPU Temperature": round(random.uniform(72, 94), 1),
                    "Power Consumption": random.randint(560, 820),
                    "Active Fault": "CPU Overheating",
                    "Overall Satellite Health": "Critical",
                    "Mission Mode": "Safe Mode",
                    "Current Task": "Thermal Protection",
                    "Camera Status": "Idle",
                    "Injection Mode": "severe_anomaly",
                }
            )

        elif fault_type == "comm_loss":
            packet.update(
                {
                    "Communication Status": "Lost",
                    "Signal Strength": 0,
                    "Active Fault": "Communication Loss",
                    "Overall Satellite Health": "Critical",
                    "Mission Mode": "Autonomous Recovery",
                    "Current Task": "Beacon Retry + Link Recovery",
                    "Camera Status": "Idle",
                    "Injection Mode": "severe_anomaly",
                }
            )

        elif fault_type == "storage_full":
            packet.update(
                {
                    "Storage Used": round(random.uniform(96.0, 99.9), 1),
                    "Active Fault": "Storage Nearly Full",
                    "Overall Satellite Health": "Critical",
                    "Mission Mode": "Data Purge",
                    "Current Task": "Delete/Downlink Old Payload Data",
                    "Camera Status": "Idle",
                    "Injection Mode": "severe_anomaly",
                }
            )

        elif fault_type == "solar_failure":
            packet.update(
                {
                    "Solar Panel Output": random.randint(0, 12),
                    "Battery Percentage": random.randint(10, 22),
                    "Battery Temperature": round(random.uniform(-4, 8), 1),
                    "Active Fault": "Solar Input Failure",
                    "Overall Satellite Health": "Critical",
                    "Mission Mode": "Safe Mode",
                    "Current Task": "Minimize Load / Preserve Battery",
                    "Camera Status": "Idle",
                    "Injection Mode": "severe_anomaly",
                }
            )

        elif fault_type == "sensor_glitch":
            packet.update(
                {
                    "CPU Temperature": round(random.uniform(45, 70), 1),
                    "Signal Strength": random.choice([0, -999, -88, -76]),
                    "Active Fault": "Sensor Glitch",
                    "Overall Satellite Health": "Warning",
                    "Mission Mode": "Diagnostics",
                    "Current Task": "Validate Sensor Pipeline",
                    "Injection Mode": "severe_anomaly",
                }
            )

        elif fault_type == "multi_fault":
            packet.update(
                {
                    "Battery Percentage": random.randint(5, 15),
                    "Solar Panel Output": random.randint(0, 20),
                    "CPU Temperature": round(random.uniform(72, 96), 1),
                    "Communication Status": "Lost",
                    "Signal Strength": 0,
                    "Storage Used": round(random.uniform(96.0, 99.9), 1),
                    "Camera Status": "Idle",
                    "Active Fault": "Multiple Critical Failures",
                    "Overall Satellite Health": "Critical",
                    "Mission Mode": "Emergency Safe Mode",
                    "Current Task": "Power Down Non-Essential Subsystems",
                    "Injection Mode": "severe_anomaly",
                }
            )

        return packet

    def next_packet(self) -> Dict[str, Any]:
        """
        Mostly healthy packet, with a very rare severe anomaly.
        """
        if random.randint(1, SEVERE_ANOMALY_ODDS) == 1:
            return self._severe_anomaly_packet("auto")
        return self._base_packet()

    def inject_fault(self, fault_type: str = "auto") -> Dict[str, Any]:
        return self._severe_anomaly_packet(fault_type)

    def _local_fallback_plan(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Used only if the OpenAI call fails.
        """
        fault = telemetry.get("Active Fault", "None")
        health = telemetry.get("Overall Satellite Health", "Good")

        if fault == "None" and health in ["Excellent", "Good"]:
            return {
                "headline": "Nominal operations",
                "risk_level": "low",
                "what_happened": "Satellite is stable and within expected limits.",
                "next_action": "Continue nominal mission operations.",
                "satellite_instruction": "Maintain current mode and keep collecting routine telemetry.",
                "precautions": ["Keep monitoring battery, CPU temperature, and link quality."],
                "operator_notes": ["No immediate intervention needed."],
            }

        return {
            "headline": f"Anomaly detected: {fault}",
            "risk_level": "critical" if health == "Critical" else "high",
            "what_happened": "The spacecraft is outside nominal conditions.",
            "next_action": "Move to safe mode and prioritize recovery.",
            "satellite_instruction": "Reduce load, preserve power, and attempt recovery steps in sequence.",
            "precautions": [
                "Avoid non-essential payload activity.",
                "Confirm telemetry downlink before issuing new commands.",
                "Check power, thermal, and communication subsystems first.",
            ],
            "operator_notes": ["Escalate if the fault persists for multiple cycles."],
        }

    def build_plan(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ask OpenAI to turn telemetry into a human-style ops brief.
        """
        prompt = f"""
You are a senior spacecraft operations director monitoring satellite telemetry in real-time.

Telemetry Data received:
{json.dumps(telemetry, indent=2)}

Task:
Convert this telemetry data into a highly descriptive, human-style operations brief.
CRITICAL INSTRUCTION: Do NOT just list raw numbers, charts, or repeat the JSON fields as is. Instead, write like a human explaining the situation in real time to the operator team.
For example, if an anomaly is present, explain it like: "We have a critical battery situation; the voltage is dropping below safe thresholds while we are in eclipse, meaning our primary battery heater is struggling. We must transition immediately to Emergency Safe Mode."
If everything is nominal, explain it in a reassuring, professional tone like: "The satellite is in a stable state. All subsystems, including the battery, CPU temperature, and solar panels, are operating within normal ranges. Signal strength remains solid."

Specifically, in your JSON response:
- "headline": A crisp status title (e.g. "Nominal operations" or "CRITICAL: Severe CPU Overheating").
- "risk_level": "low", "elevated", "high", or "critical".
- "what_happened": Write a vivid, real-time explanation of the current status of the satellite in natural, conversational, yet professional human language. Detail the narrative of what is happening under the hood.
- "next_action": The immediate concrete action/command to issue, explained in human English.
- "satellite_instruction": The exact recovery instruction or procedure the satellite must follow.
- "precautions": A list of precautionary steps for the human ground team to take.
- "operator_notes": Strategic notes for the operations staff on what to watch next.
""".strip()

        schema = {
            "type": "object",
            "properties": {
                "headline": {"type": "string"},
                "risk_level": {
                    "type": "string",
                    "enum": ["low", "elevated", "high", "critical"],
                },
                "what_happened": {"type": "string"},
                "next_action": {"type": "string"},
                "satellite_instruction": {"type": "string"},
                "precautions": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "operator_notes": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": [
                "headline",
                "risk_level",
                "what_happened",
                "next_action",
                "satellite_instruction",
                "precautions",
                "operator_notes",
            ],
            "additionalProperties": False,
        }

        try:
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "satellite_ops_brief",
                        "strict": True,
                        "schema": schema,
                    }
                }
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"OpenAI completion error, using local fallback plan: {e}")
            return self._local_fallback_plan(telemetry)

    def tick(self) -> Dict[str, Any]:
        telemetry = self.next_packet()
        plan = self.build_plan(telemetry)
        return {
            "telemetry": telemetry,
            "plan": plan,
        }

    def tick_with_fault(self, fault_type: str) -> Dict[str, Any]:
        telemetry = self.inject_fault(fault_type)
        plan = self.build_plan(telemetry)
        return {
            "telemetry": telemetry,
            "plan": plan,
        }


engine = TelemetryEngine()


# -----------------------------
# Dashboard UI
# -----------------------------
@app.get("/", response_class=HTMLResponse)
def get_dashboard() -> HTMLResponse:
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stellx Space Operations - Mission Control</title>
    <!-- Fonts & Icons -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- Chart.js CDN -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    
    <style>
        :root {
            --bg-base: #080a10;
            --bg-surface: rgba(18, 22, 35, 0.7);
            --bg-surface-glow: rgba(30, 41, 68, 0.4);
            --border-glow: rgba(59, 130, 246, 0.2);
            --text-primary: #f3f4f6;
            --text-secondary: #9ca3af;
            --color-nominal: #10b981;
            --color-warning: #f59e0b;
            --color-critical: #ef4444;
            --color-accent: #6366f1;
            --font-main: 'Inter', sans-serif;
            --font-mono: 'JetBrains Mono', monospace;
            --glow-nominal: 0 0 15px rgba(16, 185, 129, 0.35);
            --glow-warning: 0 0 15px rgba(245, 158, 11, 0.35);
            --glow-critical: 0 0 20px rgba(239, 68, 68, 0.5);
            --glow-accent: 0 0 15px rgba(99, 102, 241, 0.4);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            background-color: var(--bg-base);
            background-image: 
                radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.15) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(239, 68, 68, 0.08) 0px, transparent 50%),
                radial-gradient(at 50% 50%, rgba(16, 185, 129, 0.05) 0px, transparent 70%);
            color: var(--text-primary);
            font-family: var(--font-main);
            min-height: 100vh;
            overflow-x: hidden;
            display: flex;
            flex-direction: column;
        }

        /* Top Navigation Header */
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1.25rem 2rem;
            background: rgba(10, 12, 20, 0.8);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.07);
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .brand i {
            font-size: 1.75rem;
            color: var(--color-accent);
            text-shadow: var(--glow-accent);
        }

        .brand-title {
            font-weight: 700;
            font-size: 1.25rem;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            background: linear-gradient(135deg, #fff 0%, var(--text-secondary) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .brand-badge {
            font-size: 0.75rem;
            font-family: var(--font-mono);
            background: rgba(99, 102, 241, 0.15);
            border: 1px solid rgba(99, 102, 241, 0.3);
            color: #a5b4fc;
            padding: 0.15rem 0.5rem;
            border-radius: 4px;
        }

        .controls {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .btn {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: var(--text-primary);
            padding: 0.6rem 1.25rem;
            border-radius: 6px;
            font-size: 0.875rem;
            font-weight: 500;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            transition: all 0.25s ease;
        }

        .btn:hover {
            background: rgba(255, 255, 255, 0.1);
            border-color: rgba(255, 255, 255, 0.2);
            transform: translateY(-1px);
        }

        .btn-primary {
            background: var(--color-accent);
            border-color: rgba(255, 255, 255, 0.1);
            text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
            box-shadow: var(--glow-accent);
        }

        .btn-primary:hover {
            background: #4f46e5;
            box-shadow: 0 0 25px rgba(99, 102, 241, 0.6);
        }

        .btn-danger {
            background: var(--color-critical);
            border-color: rgba(255, 255, 255, 0.1);
            box-shadow: var(--glow-critical);
        }

        .btn-danger:hover {
            background: #dc2626;
            box-shadow: 0 0 25px rgba(239, 68, 68, 0.7);
        }

        .btn-simulating {
            background: var(--color-nominal) !important;
            box-shadow: var(--glow-nominal) !important;
        }

        .select-fault {
            background: #0f1322;
            border: 1px solid rgba(255, 255, 255, 0.15);
            color: var(--text-primary);
            padding: 0.6rem 1rem;
            border-radius: 6px;
            font-size: 0.875rem;
            cursor: pointer;
            outline: none;
            transition: border-color 0.2s;
        }

        .select-fault:focus {
            border-color: var(--color-accent);
        }

        /* Dashboard Grid Layout */
        .dashboard-container {
            flex: 1;
            display: grid;
            grid-template-columns: 1.1fr 1fr;
            gap: 1.5rem;
            padding: 2rem;
            max-width: 1600px;
            margin: 0 auto;
            width: 100%;
        }

        @media (max-width: 1200px) {
            .dashboard-container {
                grid-template-columns: 1fr;
            }
        }

        /* Glassmorphism Panel card styling */
        .panel {
            background: var(--bg-surface);
            border: 1px solid var(--border-glow);
            border-radius: 12px;
            padding: 1.5rem;
            backdrop-filter: blur(16px);
            display: flex;
            flex-direction: column;
            gap: 1.25rem;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
            transition: border-color 0.3s ease, box-shadow 0.3s ease;
        }

        .panel:hover {
            border-color: rgba(99, 102, 241, 0.3);
        }

        .panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            padding-bottom: 0.75rem;
        }

        .panel-title {
            font-size: 1.1rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .panel-title i {
            color: var(--color-accent);
        }

        /* Satellite Status Header bar */
        .status-overview {
            grid-column: 1 / -1;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
        }

        .status-metric {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            padding: 0.8rem 1.2rem;
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }

        .status-label {
            font-size: 0.75rem;
            text-transform: uppercase;
            color: var(--text-secondary);
            letter-spacing: 0.05em;
        }

        .status-value {
            font-size: 1.15rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        /* State Badges */
        .badge-health {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.2rem 0.6rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            border: 1px solid transparent;
        }

        .badge-health.nominal {
            background: rgba(16, 185, 129, 0.15);
            color: var(--color-nominal);
            border-color: rgba(16, 185, 129, 0.3);
            box-shadow: var(--glow-nominal);
            animation: pulse-green 2s infinite alternate;
        }

        .badge-health.warning {
            background: rgba(245, 158, 11, 0.15);
            color: var(--color-warning);
            border-color: rgba(245, 158, 11, 0.3);
            box-shadow: var(--glow-warning);
            animation: pulse-orange 2s infinite alternate;
        }

        .badge-health.critical {
            background: rgba(239, 68, 68, 0.15);
            color: var(--color-critical);
            border-color: rgba(239, 68, 68, 0.3);
            box-shadow: var(--glow-critical);
            animation: pulse-red 1.5s infinite;
        }

        /* Metrics grid */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 1.25rem;
        }

        @media (max-width: 580px) {
            .metrics-grid {
                grid-template-columns: 1fr;
            }
        }

        .metric-card {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 10px;
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            position: relative;
            overflow: hidden;
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .card-title {
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-secondary);
        }

        .card-icon {
            font-size: 1.1rem;
            color: var(--color-accent);
        }

        .card-body {
            display: flex;
            align-items: baseline;
            gap: 0.25rem;
        }

        .card-value {
            font-size: 1.75rem;
            font-weight: 700;
            color: #fff;
        }

        .card-unit {
            font-size: 0.85rem;
            color: var(--text-secondary);
        }

        .card-status {
            font-size: 0.75rem;
            font-family: var(--font-mono);
            display: flex;
            align-items: center;
            gap: 0.3rem;
        }

        /* Linear Progress Bars */
        .progress-container {
            width: 100%;
            height: 6px;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 9999px;
            overflow: hidden;
            margin-top: 0.25rem;
        }

        .progress-bar {
            height: 100%;
            border-radius: 9999px;
            transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
            background: var(--color-accent);
        }

        /* Circular Progress styling for Battery */
        .circle-progress-container {
            display: flex;
            justify-content: center;
            align-items: center;
            position: relative;
            width: 90px;
            height: 90px;
        }

        .circle-progress-svg {
            transform: rotate(-90deg);
            width: 90px;
            height: 90px;
        }

        .circle-bg {
            fill: none;
            stroke: rgba(255, 255, 255, 0.06);
            stroke-width: 8;
        }

        .circle-bar {
            fill: none;
            stroke: var(--color-nominal);
            stroke-width: 8;
            stroke-linecap: round;
            stroke-dasharray: 251.2;
            stroke-dashoffset: 0;
            transition: stroke-dashoffset 0.5s ease, stroke 0.5s ease;
        }

        .circle-text {
            position: absolute;
            font-size: 1.25rem;
            font-weight: 700;
            color: #fff;
        }

        .battery-card-body {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
        }

        /* AI Narrative Terminal Panel */
        .terminal-panel {
            min-height: 480px;
        }

        .terminal-container {
            background: #06080e;
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            font-family: var(--font-mono);
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.8);
        }

        .terminal-header {
            background: #0d111d;
            padding: 0.6rem 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }

        .terminal-dots {
            display: flex;
            gap: 0.35rem;
        }

        .dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }

        .dot-red { background: #ef4444; }
        .dot-yellow { background: #f59e0b; }
        .dot-green { background: #10b981; }

        .terminal-title {
            font-size: 0.7rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }

        .terminal-body {
            flex: 1;
            padding: 1.25rem;
            overflow-y: auto;
            font-size: 0.85rem;
            line-height: 1.6;
            display: flex;
            flex-direction: column;
            gap: 1rem;
            max-height: 520px;
        }

        .log-section {
            border-left: 2px solid rgba(255, 255, 255, 0.1);
            padding-left: 0.75rem;
        }

        .log-section.critical {
            border-color: var(--color-critical);
        }

        .log-section.warning {
            border-color: var(--color-warning);
        }

        .log-section.nominal {
            border-color: var(--color-nominal);
        }

        .log-header {
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            margin-bottom: 0.35rem;
            color: var(--text-secondary);
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }

        .log-narrative {
            color: #d1d5db;
        }

        .log-item {
            display: flex;
            gap: 0.5rem;
            align-items: flex-start;
            margin-bottom: 0.25rem;
        }

        .log-item i {
            color: var(--color-accent);
            margin-top: 0.2rem;
            font-size: 0.75rem;
        }

        .log-item.precaution i {
            color: var(--color-warning);
        }

        /* Historical Charts Panel */
        .chart-panel {
            grid-column: 1 / -1;
        }

        .chart-wrapper {
            position: relative;
            height: 280px;
            width: 100%;
        }

        /* Animations */
        @keyframes pulse-green {
            0% { box-shadow: 0 0 5px rgba(16, 185, 129, 0.2); }
            100% { box-shadow: 0 0 20px rgba(16, 185, 129, 0.5); }
        }

        @keyframes pulse-orange {
            0% { box-shadow: 0 0 5px rgba(245, 158, 11, 0.2); }
            100% { box-shadow: 0 0 20px rgba(245, 158, 11, 0.5); }
        }

        @keyframes pulse-red {
            0% { transform: scale(1); box-shadow: 0 0 10px rgba(239, 68, 68, 0.3); }
            50% { transform: scale(1.02); box-shadow: 0 0 25px rgba(239, 68, 68, 0.7); }
            100% { transform: scale(1); box-shadow: 0 0 10px rgba(239, 68, 68, 0.3); }
        }

        .flash-highlight {
            animation: flash-animation 0.5s ease-out;
        }

        @keyframes flash-animation {
            0% { background: rgba(99, 102, 241, 0.2); }
            100% { background: rgba(255, 255, 255, 0.02); }
        }
        
        .pulse-severe {
            animation: severe-pulse-border 1.5s infinite;
        }
        
        @keyframes severe-pulse-border {
            0% { border-color: rgba(239, 68, 68, 0.3); }
            50% { border-color: rgba(239, 68, 68, 0.85); box-shadow: 0 0 15px rgba(239, 68, 68, 0.2); }
            100% { border-color: rgba(239, 68, 68, 0.3); }
        }

        /* Footer */
        footer {
            padding: 1.5rem;
            text-align: center;
            font-size: 0.75rem;
            color: var(--text-secondary);
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            background: rgba(10, 12, 20, 0.6);
            margin-top: auto;
        }
    </style>
</head>
<body>

    <header>
        <div class="brand">
            <i class="fa-solid fa-satellite"></i>
            <div class="brand-title">Stellx Space Systems</div>
            <span class="brand-badge">TELEMETRY DECRYPTOR v1.2</span>
        </div>
        <div class="controls">
            <!-- Simulation Trigger -->
            <button id="btn-simulation" class="btn btn-primary" onclick="toggleSimulation()">
                <i class="fa-solid fa-play"></i> Run Simulation
            </button>
            <!-- Fault Injection selector -->
            <div style="display: flex; gap: 0.5rem; align-items: center; border-left: 1px solid rgba(255, 255, 255, 0.1); padding-left: 1rem;">
                <select id="fault-type" class="select-fault">
                    <option value="auto">Auto / Random Fault</option>
                    <option value="battery_critical">Critical Battery Failure</option>
                    <option value="cpu_overheat">CPU Thermal Overload</option>
                    <option value="comm_loss">Total Communication Loss</option>
                    <option value="storage_full">Solid-State Storage Full</option>
                    <option value="solar_failure">Solar Panel Deployment Fail</option>
                    <option value="sensor_glitch">Telemetry Sensor Glitch</option>
                    <option value="multi_fault">Multiple System Failure</option>
                </select>
                <button id="btn-inject" class="btn btn-danger" onclick="injectFault()">
                    <i class="fa-solid fa-triangle-exclamation"></i> Inject Fault
                </button>
            </div>
        </div>
    </header>

    <div class="dashboard-container">
        <!-- Status Overview Banner (Full Width in Grid) -->
        <div class="status-overview">
            <div class="status-metric">
                <span class="status-label">Satellite Status</span>
                <span class="status-value">
                    <span id="badge-overall-health" class="badge-health nominal">Excellent</span>
                </span>
            </div>
            <div class="status-metric">
                <span class="status-label">Active Fault</span>
                <span id="txt-active-fault" class="status-value" style="color: var(--color-nominal)">None</span>
            </div>
            <div class="status-metric">
                <span class="status-label">Mission Mode</span>
                <span id="txt-mission-mode" class="status-value">Nominal</span>
            </div>
            <div class="status-metric">
                <span class="status-label">Current Task</span>
                <span id="txt-current-task" class="status-value">Health Monitoring</span>
            </div>
            <div class="status-metric">
                <span class="status-label">Orbit Number</span>
                <span id="txt-orbit-number" class="status-value">1</span>
            </div>
        </div>

        <!-- Left Column: Metrics Grid -->
        <div class="panel" id="metrics-panel">
            <div class="panel-header">
                <h2 class="panel-title"><i class="fa-solid fa-chart-simple"></i> Live Telemetry Packet</h2>
                <span id="txt-timestamp" style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--text-secondary);">Offline</span>
            </div>
            
            <div class="metrics-grid">
                <!-- Battery Card -->
                <div class="metric-card" id="card-battery">
                    <div class="card-header">
                        <span class="card-title">Power Reserves</span>
                        <i class="fa-solid fa-battery-three-quarters card-icon"></i>
                    </div>
                    <div class="battery-card-body">
                        <div class="card-body">
                            <span class="card-value" id="val-battery">--</span>
                            <span class="card-unit">%</span>
                        </div>
                        <!-- Radial Progress Ring -->
                        <div class="circle-progress-container">
                            <svg class="circle-progress-svg">
                                <circle class="circle-bg" cx="45" cy="45" r="40"></circle>
                                <circle class="circle-bar" id="ring-battery" cx="45" cy="45" r="40"></circle>
                            </svg>
                            <span class="circle-text" id="ring-battery-text">--%</span>
                        </div>
                    </div>
                </div>

                <!-- Storage Card -->
                <div class="metric-card" id="card-storage">
                    <div class="card-header">
                        <span class="card-title">Storage Used</span>
                        <i class="fa-solid fa-hard-drive card-icon"></i>
                    </div>
                    <div class="card-body" style="flex-direction: column; width: 100%;">
                        <div style="display: flex; justify-content: space-between; align-items: baseline; width: 100%;">
                            <div>
                                <span class="card-value" id="val-storage">--</span>
                                <span class="card-unit">%</span>
                            </div>
                            <span class="card-status" id="lbl-storage-images">-- imgs</span>
                        </div>
                        <div class="progress-container">
                            <div class="progress-bar" id="bar-storage" style="width: 0%"></div>
                        </div>
                    </div>
                </div>

                <!-- Solar Panel Output -->
                <div class="metric-card" id="card-solar">
                    <div class="card-header">
                        <span class="card-title">Solar Array</span>
                        <i class="fa-solid fa-solar-panel card-icon"></i>
                    </div>
                    <div class="card-body" style="flex-direction: column; width: 100%;">
                        <div>
                            <span class="card-value" id="val-solar">--</span>
                            <span class="card-unit">W</span>
                        </div>
                        <div class="progress-container">
                            <div class="progress-bar" id="bar-solar" style="width: 0%; background: #fbbf24;"></div>
                        </div>
                    </div>
                </div>

                <!-- Power Consumption -->
                <div class="metric-card" id="card-power">
                    <div class="card-header">
                        <span class="card-title">Power Load</span>
                        <i class="fa-solid fa-bolt card-icon"></i>
                    </div>
                    <div class="card-body" style="flex-direction: column; width: 100%;">
                        <div>
                            <span class="card-value" id="val-power">--</span>
                            <span class="card-unit">W</span>
                        </div>
                        <div class="progress-container">
                            <div class="progress-bar" id="bar-power" style="width: 0%; background: #60a5fa;"></div>
                        </div>
                    </div>
                </div>

                <!-- Temperatures (Battery & CPU) -->
                <div class="metric-card" id="card-temp-battery">
                    <div class="card-header">
                        <span class="card-title">Battery Temp</span>
                        <i class="fa-solid fa-thermometer card-icon"></i>
                    </div>
                    <div class="card-body">
                        <span class="card-value" id="val-temp-battery">--</span>
                        <span class="card-unit">°C</span>
                    </div>
                    <span class="card-status" id="lbl-temp-battery-status"><i class="fa-solid fa-check-circle" style="color: var(--color-nominal)"></i> Stable</span>
                </div>

                <div class="metric-card" id="card-temp-cpu">
                    <div class="card-header">
                        <span class="card-title">CPU Temp</span>
                        <i class="fa-solid fa-microchip card-icon"></i>
                    </div>
                    <div class="card-body">
                        <span class="card-value" id="val-temp-cpu">--</span>
                        <span class="card-unit">°C</span>
                    </div>
                    <span class="card-status" id="lbl-temp-cpu-status"><i class="fa-solid fa-check-circle" style="color: var(--color-nominal)"></i> Optimal</span>
                </div>

                <!-- Communication Status -->
                <div class="metric-card" id="card-comm" style="grid-column: 1 / -1;">
                    <div class="card-header">
                        <span class="card-title">Comms Uplink</span>
                        <i class="fa-solid fa-signal card-icon"></i>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                        <div class="card-body" style="margin: 0;">
                            <span class="card-value" id="val-comm">--</span>
                        </div>
                        <div style="text-align: right;">
                            <span class="card-value" id="val-signal" style="font-size: 1.35rem;">--</span>
                            <span class="card-unit">dBm</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Right Column: AI Operations Director -->
        <div class="panel terminal-panel" id="ai-panel">
            <div class="panel-header">
                <h2 class="panel-title"><i class="fa-solid fa-brain"></i> AI Operations Director</h2>
                <div id="badge-ai-status" class="badge-health" style="background: rgba(99, 102, 241, 0.1); color: var(--color-accent); border-color: rgba(99, 102, 241, 0.2);">Standby</div>
            </div>
            
            <div class="terminal-container">
                <div class="terminal-header">
                    <div class="terminal-dots">
                        <div class="dot dot-red"></div>
                        <div class="dot dot-yellow"></div>
                        <div class="dot dot-green"></div>
                    </div>
                    <div class="terminal-title">Mission Director Briefing</div>
                </div>
                <div class="terminal-body" id="terminal-content">
                    <div style="color: var(--text-secondary); text-align: center; margin: auto; font-family: var(--font-mono);">
                        <i class="fa-solid fa-satellite-dish" style="font-size: 2.5rem; margin-bottom: 1rem; color: rgba(255,255,255,0.15)"></i>
                        <p>Awaiting Simulation Launch...</p>
                        <p style="font-size: 0.75rem; margin-top: 0.5rem; color: #4b5563;">Turn on the simulation loop to parse real-time AI actions.</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Bottom Chart: Full Width -->
        <div class="panel chart-panel">
            <div class="panel-header">
                <h2 class="panel-title"><i class="fa-solid fa-chart-line"></i> Subsystem Trends (Live Update)</h2>
            </div>
            <div class="chart-wrapper">
                <canvas id="telemetryChart"></canvas>
            </div>
        </div>
    </div>

    <footer>
        <p>&copy; Stellx Operations. Secure Telemetry Stream. Powered by OpenAI & FastAPI.</p>
    </footer>

    <script>
        // Global variables
        let isSimulating = false;
        let simulationInterval = null;
        let telemetryHistory = {
            labels: [],
            battery: [],
            cpuTemp: [],
            signal: []
        };
        let telemetryChart = null;

        // Initialize Chart
        function initChart() {
            const ctx = document.getElementById('telemetryChart').getContext('2d');
            telemetryChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: telemetryHistory.labels,
                    datasets: [
                        {
                            label: 'Battery Percentage (%)',
                            borderColor: '#10b981',
                            backgroundColor: 'rgba(16, 185, 129, 0.05)',
                            borderWidth: 2,
                            data: telemetryHistory.battery,
                            yAxisID: 'y-percent',
                            tension: 0.25,
                            fill: true
                        },
                        {
                            label: 'CPU Temp (°C)',
                            borderColor: '#6366f1',
                            backgroundColor: 'rgba(99, 102, 241, 0.05)',
                            borderWidth: 2,
                            data: telemetryHistory.cpuTemp,
                            yAxisID: 'y-temp',
                            tension: 0.25,
                            fill: true
                        },
                        {
                            label: 'Signal Strength (dBm)',
                            borderColor: '#f59e0b',
                            backgroundColor: 'transparent',
                            borderWidth: 1.5,
                            borderDash: [5, 5],
                            data: telemetryHistory.signal,
                            yAxisID: 'y-dbm',
                            tension: 0.1
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            grid: {
                                color: 'rgba(255, 255, 255, 0.05)'
                            },
                            ticks: {
                                color: '#9ca3af',
                                font: {
                                    family: "'JetBrains Mono', monospace",
                                    size: 10
                                }
                            }
                        },
                        'y-percent': {
                            type: 'linear',
                            position: 'left',
                            min: 0,
                            max: 100,
                            grid: {
                                color: 'rgba(255, 255, 255, 0.05)'
                            },
                            ticks: {
                                color: '#10b981'
                            }
                        },
                        'y-temp': {
                            type: 'linear',
                            position: 'right',
                            min: 0,
                            max: 110,
                            grid: {
                                drawOnChartArea: false
                            },
                            ticks: {
                                color: '#6366f1'
                            }
                        },
                        'y-dbm': {
                            type: 'linear',
                            position: 'right',
                            min: -110,
                            max: 0,
                            grid: {
                                drawOnChartArea: false
                            },
                            ticks: {
                                color: '#f59e0b'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            labels: {
                                color: '#f3f4f6',
                                font: {
                                    family: "'Inter', sans-serif",
                                    size: 11
                                }
                            }
                        }
                    }
                }
            });
        }

        // Toggle simulation loop
        function toggleSimulation() {
            const btn = document.getElementById('btn-simulation');
            if (isSimulating) {
                // Pause
                clearInterval(simulationInterval);
                isSimulating = false;
                btn.innerHTML = '<i class="fa-solid fa-play"></i> Run Simulation';
                btn.classList.remove('btn-simulating');
                document.getElementById('badge-ai-status').textContent = 'Paused';
                document.getElementById('badge-ai-status').className = 'badge-health';
            } else {
                // Run
                isSimulating = true;
                btn.innerHTML = '<i class="fa-solid fa-pause"></i> Pause Simulation';
                btn.classList.add('btn-simulating');
                document.getElementById('badge-ai-status').textContent = 'Listening';
                document.getElementById('badge-ai-status').className = 'badge-health nominal';
                
                // Trigger first load immediately
                fetchTelemetryNext();
                // Then poll every 6 seconds
                simulationInterval = setInterval(fetchTelemetryNext, 6000);
            }
        }

        // Fetch Next nominal packet
        async function fetchTelemetryNext() {
            try {
                const response = await fetch('/telemetry/next');
                const data = await response.json();
                updateDashboard(data);
            } catch (err) {
                console.error("Error fetching telemetry:", err);
                appendTerminalError("Network fault: Failed to pull telemetry stream.");
            }
        }

        // Inject fault request
        async function injectFault() {
            const faultSelect = document.getElementById('fault-type');
            const faultType = faultSelect.value;
            const btnInject = document.getElementById('btn-inject');
            
            btnInject.disabled = true;
            btnInject.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Injecting...';
            
            try {
                const response = await fetch('/telemetry/fault-injection', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ fault_type: faultType })
                });
                
                const data = await response.json();
                updateDashboard(data);
                
                // Temporarily apply pulsing border glow to metric panels to show injection flash
                const metricsPanel = document.getElementById('metrics-panel');
                metricsPanel.classList.add('pulse-severe');
                setTimeout(() => metricsPanel.classList.remove('pulse-severe'), 6000);
                
            } catch (err) {
                console.error("Error injecting fault:", err);
                appendTerminalError("Command uplink failed: Anomaly injection rejected by spacecraft.");
            } finally {
                btnInject.disabled = false;
                btnInject.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Inject Fault';
            }
        }

        // Update Dashboard Elements
        function updateDashboard(data) {
            const tel = data.telemetry;
            const plan = data.plan;

            // Highlight updated cards briefly
            flashCards();

            // Set Timestamp
            const ts = new Date(tel.timestamp);
            document.getElementById('txt-timestamp').textContent = ts.toLocaleTimeString();

            // Header state values
            const healthBadge = document.getElementById('badge-overall-health');
            const healthStr = tel["Overall Satellite Health"];
            healthBadge.textContent = healthStr;
            
            if (healthStr === "Excellent" || healthStr === "Good") {
                healthBadge.className = "badge-health nominal";
            } else if (healthStr === "Warning" || healthStr === "Fair") {
                healthBadge.className = "badge-health warning";
            } else {
                healthBadge.className = "badge-health critical";
            }

            // Active fault text
            const faultTxt = document.getElementById('txt-active-fault');
            faultTxt.textContent = tel["Active Fault"];
            if (tel["Active Fault"] !== "None") {
                faultTxt.style.color = "var(--color-critical)";
                faultTxt.style.fontWeight = "700";
            } else {
                faultTxt.style.color = "var(--color-nominal)";
                faultTxt.style.fontWeight = "600";
            }

            document.getElementById('txt-mission-mode').textContent = tel["Mission Mode"];
            document.getElementById('txt-current-task').textContent = tel["Current Task"];
            document.getElementById('txt-orbit-number').textContent = tel["Orbit Number"];

            // Radial Battery Circle
            const batteryVal = tel["Battery Percentage"];
            document.getElementById('val-battery').textContent = batteryVal;
            document.getElementById('ring-battery-text').textContent = batteryVal + "%";
            
            const ring = document.getElementById('ring-battery');
            const circumference = 2 * Math.PI * 40; // 251.2
            const offset = circumference - (batteryVal / 100) * circumference;
            ring.style.strokeDashoffset = offset;
            if (batteryVal < 20) {
                ring.style.stroke = "var(--color-critical)";
            } else if (batteryVal < 50) {
                ring.style.stroke = "var(--color-warning)";
            } else {
                ring.style.stroke = "var(--color-nominal)";
            }

            // Linear progress bars
            const storageVal = tel["Storage Used"];
            document.getElementById('val-storage').textContent = storageVal;
            document.getElementById('lbl-storage-images').textContent = tel["Images Captured"] + " imgs";
            document.getElementById('bar-storage').style.width = storageVal + "%";
            
            const solarVal = tel["Solar Panel Output"];
            document.getElementById('val-solar').textContent = solarVal;
            // Solar Max is ~1500W
            document.getElementById('bar-solar').style.width = Math.min(100, (solarVal / 1500) * 100) + "%";
            
            const powerVal = tel["Power Consumption"];
            document.getElementById('val-power').textContent = powerVal;
            // Power Max load ~900W
            document.getElementById('bar-power').style.width = Math.min(100, (powerVal / 900) * 100) + "%";

            // Temps
            const batTemp = tel["Battery Temperature"];
            document.getElementById('val-temp-battery').textContent = batTemp;
            const batTempLbl = document.getElementById('lbl-temp-battery-status');
            if (batTemp < 0 || batTemp > 40) {
                batTempLbl.innerHTML = '<i class="fa-solid fa-triangle-exclamation" style="color: var(--color-critical)"></i> Abnormal';
            } else {
                batTempLbl.innerHTML = '<i class="fa-solid fa-check-circle" style="color: var(--color-nominal)"></i> Stable';
            }

            const cpuTemp = tel["CPU Temperature"];
            document.getElementById('val-temp-cpu').textContent = cpuTemp;
            const cpuTempLbl = document.getElementById('lbl-temp-cpu-status');
            if (cpuTemp > 68) {
                cpuTempLbl.innerHTML = '<i class="fa-solid fa-triangle-exclamation" style="color: var(--color-critical)"></i> Overheat';
            } else if (cpuTemp > 55) {
                cpuTempLbl.innerHTML = '<i class="fa-solid fa-warning" style="color: var(--color-warning)"></i> High';
            } else {
                cpuTempLbl.innerHTML = '<i class="fa-solid fa-check-circle" style="color: var(--color-nominal)"></i> Optimal';
            }

            // Comms
            document.getElementById('val-comm').textContent = tel["Communication Status"];
            document.getElementById('val-signal').textContent = tel["Signal Strength"];

            // Update Chart
            updateChartData(tel.timestamp, batteryVal, cpuTemp, tel["Signal Strength"]);

            // Update AI narrative panel
            renderAINarrative(plan);
        }

        // Flash metric cards on new data
        function flashCards() {
            const cards = document.querySelectorAll('.metric-card');
            cards.forEach(card => {
                card.classList.add('flash-highlight');
                setTimeout(() => card.classList.remove('flash-highlight'), 500);
            });
        }

        // Render AI narrative console
        function renderAINarrative(plan) {
            const container = document.getElementById('terminal-content');
            container.innerHTML = ''; // clear initial content

            const risk = plan.risk_level || "low";
            let statusClass = "nominal";
            let riskGlowColor = "var(--color-nominal)";
            
            if (risk === "critical") {
                statusClass = "critical";
                riskGlowColor = "var(--color-critical)";
            } else if (risk === "high" || risk === "elevated") {
                statusClass = "warning";
                riskGlowColor = "var(--color-warning)";
            }

            // 1. Headline section
            const headlineSec = document.createElement('div');
            headlineSec.className = `log-section ${statusClass}`;
            headlineSec.innerHTML = `
                <div class="log-header">
                    <i class="fa-solid fa-crosshairs"></i> Operations Briefing: ${plan.headline}
                </div>
                <div style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 0.5rem;">
                    Risk Assessment: <span style="color: ${riskGlowColor}; font-weight: 700; text-transform: uppercase;">${risk}</span>
                </div>
            `;
            container.appendChild(headlineSec);

            // 2. What Happened (Human narrative)
            const whatSec = document.createElement('div');
            whatSec.className = `log-section ${statusClass}`;
            whatSec.innerHTML = `
                <div class="log-header"><i class="fa-solid fa-bullhorn"></i> Narrative Situation</div>
                <div class="log-narrative">${plan.what_happened}</div>
            `;
            container.appendChild(whatSec);

            // 3. Next Action / Satellite Instruction
            const instructionSec = document.createElement('div');
            instructionSec.className = `log-section ${statusClass}`;
            instructionSec.innerHTML = `
                <div class="log-header"><i class="fa-solid fa-code-branch"></i> Core Telecommand Directives</div>
                <div class="log-item">
                    <i class="fa-solid fa-arrow-right"></i>
                    <div><strong>Immediate Action:</strong> ${plan.next_action}</div>
                </div>
                <div class="log-item">
                    <i class="fa-solid fa-terminal"></i>
                    <div><strong>Onboard Logic:</strong> ${plan.satellite_instruction}</div>
                </div>
            `;
            container.appendChild(instructionSec);

            // 4. Precautions
            if (plan.precautions && plan.precautions.length > 0) {
                const precSec = document.createElement('div');
                precSec.className = `log-section ${statusClass}`;
                let precHTML = `<div class="log-header"><i class="fa-solid fa-shield-halved"></i> Ground Operator Precautions</div>`;
                plan.precautions.forEach(prec => {
                    precHTML += `
                        <div class="log-item precaution">
                            <i class="fa-solid fa-circle-exclamation"></i>
                            <div>${prec}</div>
                        </div>
                    `;
                });
                precSec.innerHTML = precHTML;
                container.appendChild(precSec);
            }

            // 5. Operator Notes
            if (plan.operator_notes && plan.operator_notes.length > 0) {
                const noteSec = document.createElement('div');
                noteSec.className = "log-section";
                let notesHTML = `<div class="log-header"><i class="fa-solid fa-clipboard-list"></i> Operations Log Notes</div>`;
                plan.operator_notes.forEach(note => {
                    notesHTML += `
                        <div class="log-item">
                            <i class="fa-solid fa-angle-right"></i>
                            <div>${note}</div>
                        </div>
                    `;
                });
                noteSec.innerHTML = notesHTML;
                container.appendChild(noteSec);
            }
        }

        // Append terminal error
        function appendTerminalError(message) {
            const container = document.getElementById('terminal-content');
            const errDiv = document.createElement('div');
            errDiv.className = "log-section critical";
            errDiv.innerHTML = `
                <div class="log-header" style="color: var(--color-critical);"><i class="fa-solid fa-circle-xmark"></i> Operational Link Error</div>
                <div class="log-narrative" style="color: var(--color-critical); font-weight: 500;">${message}</div>
            `;
            container.prepend(errDiv);
        }

        // Update Chart Data Points
        function updateChartData(timeStr, battery, cpu, signal) {
            const labelTime = new Date(timeStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
            
            telemetryHistory.labels.push(labelTime);
            telemetryHistory.battery.push(battery);
            telemetryHistory.cpuTemp.push(cpu);
            telemetryHistory.signal.push(signal);

            // Cap items at 18
            if (telemetryHistory.labels.length > 18) {
                telemetryHistory.labels.shift();
                telemetryHistory.battery.shift();
                telemetryHistory.cpuTemp.shift();
                telemetryHistory.signal.shift();
            }

            if (telemetryChart) {
                telemetryChart.update();
            }
        }

        // Initialize elements on load
        window.addEventListener('DOMContentLoaded', () => {
            initChart();
        });
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)


@app.get("/telemetry/next")
def get_next_telemetry() -> Dict[str, Any]:
    return engine.tick()


@app.get("/telemetry/packet")
def get_telemetry_packet() -> Dict[str, Any]:
    """
    Lightweight telemetry-only endpoint intended for low-resource clients
    (ESP32, microcontrollers). Returns only the telemetry packet quickly
    without invoking the OpenAI model.
    """
    return engine.next_packet()


@app.post("/telemetry/fault-injection")
def fault_injection(req: FaultInjectionRequest) -> Dict[str, Any]:
    return engine.tick_with_fault(req.fault_type)


@app.post("/telemetry/analyze")
def analyze_telemetry(telemetry: Optional[Dict[str, Any]] = Body(None)) -> Dict[str, Any]:
    """
    Analyze provided telemetry with the GPT-OSS model and return an operations plan.
    If no telemetry payload is provided, a fresh nominal packet will be generated and analyzed.
    Request body (optional): JSON telemetry object matching the telemetry packet format.
    Response: { "telemetry": {...}, "plan": {...} }
    """
    if telemetry is None:
        telemetry = engine.next_packet()

    plan = engine.build_plan(telemetry)
    return {"telemetry": telemetry, "plan": plan}


# -----------------------------
# Console mode
# -----------------------------
def run_console() -> None:
    print("Satellite Ops Engine running...")
    print(f"Tick every {TICK_SECONDS} seconds.")
    print("Press Ctrl+C to stop.\n")

    while True:
        result = engine.tick()
        print(json.dumps(result, indent=2))
        time.sleep(TICK_SECONDS)


if __name__ == "__main__":
    # If executed directly, run the FastAPI app with uvicorn so Render
    # (or other process managers) will serve the HTTP endpoints.
    import uvicorn

    uvicorn.run("satellite_ops_engine:app", host=HOST, port=PORT)