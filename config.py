import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "openai/gpt-oss-120b")

TICK_SECONDS = int(os.getenv("TICK_SECONDS", 6))
# Default odds value controls the random check: random.randint(1, SEVERE_ANOMALY_ODDS) == 1
# Setting to 5 makes the chance 1/5 => 20% severe anomaly probability when env var is not set.
SEVERE_ANOMALY_ODDS = int(os.getenv("SEVERE_ANOMALY_ODDS", 5))

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))