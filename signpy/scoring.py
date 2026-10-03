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

HAND_CONNECTIONS: tuple[tuple[int, int], ...] = (
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),
    (0, 5),
    (5, 6),
    (6, 7),
    (7, 8),
    (5, 9),
    (9, 10),
    (10, 11),
    (11, 12),
    (9, 13),
    (13, 14),
    (14, 15),
    (15, 16),
    (13, 17),
    (17, 18),
    (18, 19),
    (19, 20),
    (0, 17),
)

MAX_DISTANCE = 0.5
FEEDBACK_SCORE_CEILING = 90
MIN_DYNAMIC_FRAMES = 5
MAX_DYNAMIC_FRAMES = 90


def normalize_hand(landmarks: np.ndarray) -> np.ndarray:
    """Put a hand in a canonical frame for comparison.

    ``landmarks`` has shape ``(21, 3)``. The result is invariant to the hand
    position, its distance to the camera, mirroring along the x axis and the
    in-plane rotation of the wrist: the hand is centered on its wrist, scaled
    by the wrist to middle-MCP distance, mirrored to the selfie view, and
    rotated so that the wrist to middle-MCP segment points up.
    """
    if landmarks.shape != (HAND_LANDMARKS, 3):
        msg = f"Expected {HAND_LANDMARKS} landmarks, got shape {landmarks.shape}."
        raise ValueError(msg)
    wrist = landmarks[WRIST]
    scale = np.linalg.norm(landmarks[MIDDLE_MCP] - wrist)
    if scale < 1e-6:
        msg = "Hand scale is too small: the wrist and middle MCP landmarks overlap."
        raise ValueError(msg)
    centered = (landmarks - wrist) / scale
    centered[:, 0] = -centered[:, 0]

    direction = centered[MIDDLE_MCP, :2]
    norm = np.linalg.norm(direction)
    if norm > 1e-6:
        angle = -np.pi / 2 - np.arctan2(direction[1], direction[0])
        cos, sin = np.cos(angle), np.sin(angle)
        rotation = np.array([[cos, -sin], [sin, cos]])
        centered[:, :2] = centered[:, :2] @ rotation.T
    return centered


def finger_deviations(shape_a: np.ndarray, shape_b: np.ndarray) -> dict[str, float]:
    """Return the mean 2D landmark deviation of each finger between two shapes.

    Only the x and y axes are compared: MediaPipe depth estimates are too
    noisy to score fairly, especially on drawings.
    """
    distances = np.linalg.norm(shape_a[:, :2] - shape_b[:, :2], axis=1)
    return {
        name: float(distances[start : end + 1].mean()) for name, (start, end) in FINGERS.items()
    }


def finger_deviations_batch(frame: np.ndarray, sequence: np.ndarray) -> np.ndarray:
    """Return per-finger deviations between one frame and a whole sequence.

    ``frame`` has shape ``(21, 3)`` and ``sequence`` has shape
    ``(n_frames, 21, 3)``. The result has shape ``(n_frames, 5)`` with the
    same finger order as ``FINGERS``.
    """
    distances = np.linalg.norm(sequence[:, :, :2] - frame[:, :2], axis=2)
    return np.stack(
        [distances[:, start : end + 1].mean(axis=1) for start, end in FINGERS.values()],
        axis=1,
    )


def handshape_distance(shape_a: np.ndarray, shape_b: np.ndarray) -> float:
    """Return the deviation of the worst finger between two normalized hands.

    A sign is wrong as soon as one finger is wrong, so the distance is the
    largest finger mean deviation instead of an average that would dilute a
    single bad finger among 21 landmarks.
    """
    return max(finger_deviations(shape_a, shape_b).values())


def score_from_distance(distance: float) -> int:
    """Map an average landmark distance to a score between 0 and 100.

    The quadratic curve keeps small natural variations from dragging the
    score down while still separating clearly different handshapes: a
    distance of half ``MAX_DISTANCE`` scores 75, not 50.
    """
    ratio = min(1.0, distance / MAX_DISTANCE)
    return int(round(100.0 * (1.0 - ratio**2)))


def finger_feedback(shape_a: np.ndarray, shape_b: np.ndarray) -> list[str]:
    """Name the fingers whose landmarks deviate the most between two shapes.

    A finger is flagged when its deviation exceeds 1.3 times the mean
    deviation across fingers, so the feedback is relative and stays useful
    whatever the score level. At most two fingers are returned.
    """
    deviations = finger_deviations(shape_a, shape_b)
    overall = float(np.mean(list(deviations.values())))
    if overall < 0.01:
        return []
    ordered = sorted(deviations, key=lambda name: deviations[name], reverse=True)
    return [name for name in ordered if deviations[name] > 1.3 * overall][:2]


def dtw_distance(sequence_a: np.ndarray, sequence_b: np.ndarray) -> float:
    """Return the normalized Dynamic Time Warping distance between two sequences.

    Each sequence has shape ``(n_frames, 21, 3)`` of normalized hands. Frames
    are compared with the static handshape distance (worst finger, x and y
    only), and the result is the optimal alignment cost divided by the
    alignment length, so it is comparable to a static handshape distance.
    """
    frame_count_a, frame_count_b = len(sequence_a), len(sequence_b)
    cost = np.empty((frame_count_a, frame_count_b))
    for index_a in range(frame_count_a):
        deviations = finger_deviations_batch(sequence_a[index_a], sequence_b)
        cost[index_a] = deviations.max(axis=1)
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


def hand_from_frame(frame: dict[str, Any]) -> np.ndarray | None:
    """Return the first detected hand of a frame as an array, or None."""
    hands = frame.get("hands") or []
    if not hands:
        return None
    landmarks = hands[0].get("landmarks") or []
    if len(landmarks) != HAND_LANDMARKS:
        return None
    return np.array([[point["x"], point["y"], point["z"]] for point in landmarks], dtype=float)


def frames_from_payload(payload: dict[str, Any]) -> list[np.ndarray]:
    """Extract the first detected hand of each frame from a capture payload."""
    frames = []
    for frame in payload.get("frames", []):
        hand = hand_from_frame(frame)
        if hand is not None:
            frames.append(hand)
    return frames


def normalize_frames(frames: list[np.ndarray]) -> np.ndarray:
    """Normalize every frame of a capture and return shape ``(n, 21, 3)``."""
    return np.array([normalize_hand(frame) for frame in frames])


def _chirality_variants(reference: np.ndarray) -> list[np.ndarray]:
    """Return a reference and its x mirror, so left and right hands match."""
    mirrored = reference.copy()
    mirrored[..., 0] = -mirrored[..., 0]
    return [reference, mirrored]


def evaluate_static(sample: np.ndarray, reference: np.ndarray) -> tuple[int, list[str]]:
    """Score one normalized hand against one normalized reference hand.

    Both chirality variants of the reference are tried so that signing with
    the other hand or mirroring the reference is not penalized.
    """
    candidates = _chirality_variants(reference)
    distances = [handshape_distance(sample, candidate) for candidate in candidates]
    best = int(np.argmin(distances))
    score = score_from_distance(distances[best])
    feedback = [] if score >= FEEDBACK_SCORE_CEILING else finger_feedback(sample, candidates[best])
    return score, feedback


def evaluate_dynamic(sequence: np.ndarray, reference: np.ndarray) -> tuple[int, list[str]]:
    """Score a normalized sequence against a normalized reference sequence.

    Both chirality variants of the reference are tried so that signing with
    the other hand or mirroring the reference is not penalized.
    """
    best_distance = min(
        dtw_distance(sequence, candidate)
        for variant in _chirality_variants(reference)
        for candidate in _split_overlong(variant)
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


def keyframes(sequence: np.ndarray, count: int = 4) -> np.ndarray:
    """Return up to ``count`` evenly spaced frames of a normalized sequence."""
    if len(sequence) <= count:
        return sequence
    indexes = np.linspace(0, len(sequence) - 1, count).round().astype(int)
    return sequence[sorted(set(int(index) for index in indexes))]
