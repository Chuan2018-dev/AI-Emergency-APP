from __future__ import annotations

from datetime import datetime
from pathlib import Path
import pickle

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from .config import DATASET_PATH, MODEL_PATH


class SeverityModel:
    def __init__(self) -> None:
        self.model = None

    @staticmethod
    def _build_pipeline() -> Pipeline:
        pre = ColumnTransformer(
            transformers=[
                ("desc", TfidfVectorizer(max_features=1000, ngram_range=(1, 2)), "description"),
                ("cat", OneHotEncoder(handle_unknown="ignore"), ["emergency_type"]),
                ("num", "passthrough", ["hour_of_day", "risk_score"]),
            ]
        )
        return Pipeline([("pre", pre), ("clf", LogisticRegression(max_iter=400))])

    def train_and_save(self) -> None:
        df = pd.read_csv(DATASET_PATH)
        X = df[["emergency_type", "description", "hour_of_day", "risk_score"]]
        y = df["severity"]

        pipe = self._build_pipeline()
        pipe.fit(X, y)
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        with Path(MODEL_PATH).open("wb") as f:
            pickle.dump(pipe, f)

    def load(self) -> None:
        if not Path(MODEL_PATH).exists():
            self.train_and_save()
        with Path(MODEL_PATH).open("rb") as f:
            self.model = pickle.load(f)

    def predict(self, emergency_type: str, description: str, risk_score: float = 0.5) -> tuple[str, float]:
        if self.model is None:
            self.load()
        hour = datetime.utcnow().hour
        row = pd.DataFrame(
            [
                {
                    "emergency_type": emergency_type,
                    "description": description,
                    "hour_of_day": hour,
                    "risk_score": risk_score,
                }
            ]
        )
        pred = self.model.predict(row)[0]
        proba = max(self.model.predict_proba(row)[0])
        return str(pred), float(round(proba, 3))

    def evaluate(self) -> dict:
        """Return model performance metrics for chapter 4 reporting."""
        df = pd.read_csv(DATASET_PATH)
        X = df[["emergency_type", "description", "hour_of_day", "risk_score"]]
        y = df["severity"]

        x_train, x_test, y_train, y_test = train_test_split(
            X, y, test_size=0.3, random_state=42, stratify=y
        )
        model = self._build_pipeline()
        model.fit(x_train, y_train)
        pred = model.predict(x_test)

        labels = sorted(y.unique().tolist())
        cm = confusion_matrix(y_test, pred, labels=labels)

        return {
            "accuracy": round(float(accuracy_score(y_test, pred)), 4),
            "precision": round(float(precision_score(y_test, pred, average="weighted", zero_division=0)), 4),
            "recall": round(float(recall_score(y_test, pred, average="weighted", zero_division=0)), 4),
            "f1_score": round(float(f1_score(y_test, pred, average="weighted", zero_division=0)), 4),
            "labels": labels,
            "confusion_matrix": cm.tolist(),
            "sample_size": int(len(df)),
        }
