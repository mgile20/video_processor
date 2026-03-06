import os

from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from cv2.data import haarcascades

from app.common.app_context import AppContext

face_cascade = cv2.CascadeClassifier(haarcascades + "haarcascade_frontalface_default.xml")

app_context = AppContext()


def detect_face_dnn(img: str | Path | cv2.typing.MatLike):
    if not isinstance(img, cv2.typing.MatLike):
        img = cv2.imread(img)

    net = cv2.dnn.readNetFromCaffe(app_context.paths.model_proto, app_context.paths.model_weight)
    h, w = img.shape[:2]
    blob = cv2.dnn.blobFromImage(cv2.resize(img, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0))
    net.setInput(blob)
    detections = net.forward()

    all_found = []
    # 1. Collect every detection and its coordinates
    for i in range(0, detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
        (x1, y1, x2, y2) = box.astype("int")
        all_found.append({"conf": confidence, "box": (x1, y1, x2, y2)})

    # 2. Filter for > 0.5
    high_conf = [d for d in all_found if d["conf"] > 0.5]

    # 3. Decision Logic
    targets = []
    if high_conf:
        print(f"Found {len(high_conf)} faces with confidence > 0.5")
        targets = high_conf
    elif all_found:
        # Sort by confidence descending and take the top 1
        best_match = max(all_found, key=lambda x: x["conf"])
        print(f"No high confidence faces. Defaulting to best match: {best_match['conf']:.2f}")
        targets = [best_match]

    return targets, all_found


def overlay_face_box(img: str | Path | cv2.typing.MatLike):
    if not isinstance(img, cv2.typing.MatLike):
        img = cv2.imread(img)

    targets, _ = detect_face_dnn(img)

    overlay = img.copy()
    for t in targets:
        x1, y1, x2, y2 = t["box"]
        # Draw solid rectangle on overlay
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 255, 0), -1)

        # Add label to original image
        label = f"{t['conf']:.2f}"
        cv2.putText(img, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 2)

    # 5. Blend for transparency
    result = cv2.addWeighted(overlay, 0.4, img, 0.6, 0)
    return result


def sanitize_np_types(obj):
    if isinstance(obj, dict):
        return {k: sanitize_np_types(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [sanitize_np_types(v) for v in obj]
    elif isinstance(obj, np.ndarray):
        return [sanitize_np_types(i) for i in obj.tolist()]
    elif isinstance(obj, np.integer):
        return int(obj)  # Forces NumPy int32/64 to standard Python int
    elif isinstance(obj, np.floating):
        return float(obj)  # Forces NumPy float32/64 to standard Python float
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj
