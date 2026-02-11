import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
UPLOAD_DIR = BASE_DIR / "uploads"
DB_PATH = BASE_DIR / "emergency.db"
MODEL_PATH = BASE_DIR.parent / "data" / "model.pkl"
DATASET_PATH = BASE_DIR.parent / "data" / "severity_dataset.csv"
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
TOKEN_EXPIRE_HOURS = int(os.getenv("TOKEN_EXPIRE_HOURS", "24"))
RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "3"))
SUSPICIOUS_VERIFICATION_THRESHOLD = float(os.getenv("SUSPICIOUS_VERIFICATION_THRESHOLD", "35"))

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
