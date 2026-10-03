"""Score captured hand landmarks against recorded references."""

from typing import Any

import numpy as np

WRIST = 0
MIDDLE_MCP = 9
HAND_LANDMARKS = 21

FINGERS: dict[str, tuple[int, int]] = {
    "pouce": (1, 4),
    "index": (5, 8),
    "majeur": (9, 12),
    "annulaire": (13, 16),
    "auriculaire": (17, 20),
}

MAX_DISTANCE = 0.5
MIN_DYNAMIC_FRAMES = 5
MAX_DYNAMIC_FRAMES = 90


def normalize_hand(landmarks: np.ndarray) -> np.ndarray:
    """Center a hand on its wrist and scale it by the middle finger MCP distance.

    ``landmarks`` has shape ``(21, 3)``. The result is invariant to the hand
    position, its distance to the camera and mirroring along the x axis.
    """
    if landmarks.shape != (HAND_LANDMARKS, 3):
        msg = f"Expected {HAND_LANDMARKS} landmarks, got shape {landmarks.shape}."
        raise ValueError(msg)
    wrist = landmarks[WRIST]
    scale = np.linalg.norm(landmarks[MIDDLE_MCP] - wrist)
    if scale < 1e-6:
        msg = "Hand scale is too small: the wrist and middle MCP landmarks overlap."
        raise ValueError(msg)
    centered = landmarks - wrist
    centered[:, 0] = -centered[:, 0]
    return centered / scale


def handshape_distance(shape_a: np.ndarray, shape_b: np.ndarray) -> float:
    """Return the mean per-landmark distance between two normalized hands."""
    return float(np.linalg.norm(shape_a - shape_b, axis=1).mean())


def score_from_distance(distance: float) -> int:
    """Map an average landmark distance to a score between 0 and 100."""
    return int(round(100.0 * max(0.0, 1.0 - distance / MAX_DISTANCE)))


def finger_feedback(shape_a: np.ndarray, shape_b: np.ndarray) -> list[str]:
    """Name the fingers whose landmarks deviate the most between two shapes."""
    distances = np.linalg.norm(shape_a - shape_b, axis=1)
    deviations = {
        name: float(distances[start : end + 1].mean()) for name, (start, end) in FINGERS.items()
    }
    ordered = sorted(deviations, key=lambda name: deviations[name], reverse=True)
    return [name for name in ordered if deviations[name] > MAX_DISTANCE / 2.0]


def dtw_distance(sequence_a: np.ndarray, sequence_b: np.ndarray) -> float:
    """Return the normalized Dynamic Time Warping distance between two sequences.

    Each sequence has shape ``(n_frames, 21, 3)`` of normalized hands. The
    result is the optimal alignment cost divided by the alignment length, so it
    is comparable to a per-frame handshape distance.
    """
    frame_count_a, frame_count_b = len(sequence_a), len(sequence_b)
    cost = np.empty((frame_count_a, frame_count_b))
    for index_a in range(frame_count_a):
        diffs = sequence_b - sequence_a[index_a]
        cost[index_a] = np.linalg.norm(diffs, axis=2).mean(axis=1)
    accumulated = np.full((frame_count_a + 1, frame_count_b + 1), np.inf)
    accumulated[0, 0] = 0.0
    for index_a in range(1, frame_count_a + 1):
        for index_b in range(1, frame_count_b + 1):
            step = cost[index_a - 1, index_b - 1]
            accumulated[index_a, index_b] = step + min(
                accumulated[index_a - 1, index_b],
                accumulated[index_a, index_b - 1],
                accumulated[index_a - 1, index_b - 1],
            )
    return float(accumulated[frame_count_a, frame_count_b] / (frame_count_a + frame_count_b))


def frames_from_payload(payload: dict[str, Any]) -> list[np.ndarray]:
    """Extract the first detected hand of each frame from a capture payload."""
    frames = []
    for frame in payload.get("frames", []):
        hands = frame.get("hands") or []
        if not hands:
            continue
        landmarks = hands[0].get("landmarks") or []
        if len(landmarks) != HAND_LANDMARKS:
            continue
        frames.append(
            np.array([[point["x"], point["y"], point["z"]] for point in landmarks], dtype=float)
        )
    return frames


def normalize_frames(frames: list[np.ndarray]) -> np.ndarray:
    """Normalize every frame of a capture and return shape ``(n, 21, 3)``."""
    return np.array([normalize_hand(frame) for frame in frames])


def evaluate_static(sample: np.ndarray, reference: np.ndarray) -> tuple[int, list[str]]:
    """Score one normalized hand against one normalized reference hand."""
    distance = handshape_distance(sample, reference)
    return score_from_distance(distance), finger_feedback(sample, reference)


def evaluate_dynamic(sequence: np.ndarray, reference: np.ndarray) -> tuple[int, list[str]]:
    """Score a normalized sequence against a normalized reference sequence."""
    best_distance = min(
        dtw_distance(sequence, candidate) for candidate in _split_overlong(reference)
    )
    return score_from_distance(best_distance), []


def _split_overlong(sequence: np.ndarray) -> list[np.ndarray]:
    """Split sequences longer than the capture window into overlapping chunks."""
    if len(sequence) <= MAX_DYNAMIC_FRAMES:
        return [sequence]
    step = MAX_DYNAMIC_FRAMES // 2
    return [
        sequence[start : start + MAX_DYNAMIC_FRAMES]
        for start in range(0, len(sequence), step)
        if start + MIN_DYNAMIC_FRAMES <= len(sequence)
    ]
