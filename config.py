import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "openai/gpt-oss-120b")

TICK_SECONDS = int(os.getenv("TICK_SECONDS", 6))
SEVERE_ANOMALY_ODDS = int(os.getenv("SEVERE_ANOMALY_ODDS", 50))

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))