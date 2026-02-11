from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

try:
    import cv2  # type: ignore
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover - optional dependency fallback
    cv2 = None
    np = None


def _file_size_ok(path: Path, min_bytes: int = 5_000) -> bool:
    return path.exists() and path.stat().st_size >= min_bytes


def _quick_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _opencv_validate(selfie_path: Path, accident_path: Path) -> dict[str, Any]:
    selfie = cv2.imread(str(selfie_path))
    accident = cv2.imread(str(accident_path))
    if selfie is None or accident is None:
        return {
            "face_ok": False,
            "accident_image_ok": False,
            "suspicious": True,
            "verification_score": 0.0,
            "flags": ["image_load_failed"],
        }

    def blur_score(image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())

    def is_blank(image):
        return float(np.std(image)) < 5.0

    flags: list[str] = []
    detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = detector.detectMultiScale(cv2.cvtColor(selfie, cv2.COLOR_BGR2GRAY), scaleFactor=1.1, minNeighbors=4)
    face_ok = len(faces) > 0
    if not face_ok:
        flags.append("no_face_detected")

    accident_blur = blur_score(accident)
    selfie_blur = blur_score(selfie)
    accident_not_blank = not is_blank(accident)
    if not accident_not_blank:
        flags.append("accident_blank")
    if accident_blur < 25:
        flags.append("accident_too_blurry")

    same_hash = _quick_hash(selfie_path) == _quick_hash(accident_path)
    if same_hash:
        flags.append("selfie_and_accident_same_file")

    accident_image_ok = accident_not_blank and accident_blur >= 25 and not same_hash
    suspicious = (not face_ok) or (not accident_image_ok)
    score = (0.5 if face_ok else 0.0) + (0.35 if accident_image_ok else 0.0) + (0.15 if selfie_blur >= 25 else 0.0)

    return {
        "face_ok": face_ok,
        "accident_image_ok": accident_image_ok,
        "suspicious": suspicious,
        "verification_score": round(score * 100, 1),
        "flags": flags,
    }


def _heuristic_validate(selfie_path: Path, accident_path: Path) -> dict[str, Any]:
    """Fallback validator when OpenCV is unavailable in local environment."""
    flags: list[str] = ["opencv_unavailable_using_heuristics"]
    selfie_ok = _file_size_ok(selfie_path)
    accident_ok = _file_size_ok(accident_path)
    if not selfie_ok:
        flags.append("selfie_too_small")
    if not accident_ok:
        flags.append("accident_too_small")

    same_hash = _quick_hash(selfie_path) == _quick_hash(accident_path)
    if same_hash:
        flags.append("selfie_and_accident_same_file")

    face_ok = selfie_ok and not same_hash
    accident_image_ok = accident_ok and not same_hash
    suspicious = not (face_ok and accident_image_ok)
    score = 80.0 if not suspicious else 25.0

    return {
        "face_ok": face_ok,
        "accident_image_ok": accident_image_ok,
        "suspicious": suspicious,
        "verification_score": score,
        "flags": flags,
    }


def validate_images(selfie_path: Path, accident_path: Path) -> dict[str, Any]:
    if cv2 is None or np is None:
        return _heuristic_validate(selfie_path, accident_path)
    return _opencv_validate(selfie_path, accident_path)
