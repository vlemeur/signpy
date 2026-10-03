"""Tests for landmark normalization, scoring and reference storage."""

import numpy as np
import pytest

from signpy import references as references_module
from signpy import scoring
from signpy.constants import REFERENCE_DYNAMIC, REFERENCE_STATIC
from signpy.references import Reference
from signpy.scoring import (
    HAND_LANDMARKS,
    MAX_DISTANCE,
    dtw_distance,
    evaluate_dynamic,
    evaluate_static,
    finger_feedback,
    frames_from_payload,
    handshape_distance,
    normalize_frames,
    normalize_hand,
    score_from_distance,
)


def _fake_hand(spread: float = 1.0, seed: int = 0) -> np.ndarray:
    """Build a plausible hand shape of 21 landmarks."""
    rng = np.random.default_rng(seed)
    hand = rng.normal(size=(HAND_LANDMARKS, 3)) * spread
    hand[0] = (0.0, 0.0, 0.0)
    hand[9] = (0.0, -1.0, 0.0)
    return hand


def test_normalize_hand_is_translation_and_scale_invariant() -> None:
    hand = _fake_hand()
    shifted = hand + np.array([3.0, -2.0, 0.5])
    scaled = shifted * 2.5
    np.testing.assert_allclose(normalize_hand(hand), normalize_hand(scaled))


def test_normalize_hand_mirrors_x_axis() -> None:
    hand = _fake_hand()
    mirrored = hand.copy()
    mirrored[:, 0] = -mirrored[:, 0]
    normalized = normalize_hand(hand)
    normalized_mirrored = normalize_hand(mirrored)
    np.testing.assert_allclose(normalized[:, 0], -normalized_mirrored[:, 0])
    np.testing.assert_allclose(normalized[:, 1:], normalized_mirrored[:, 1:])


def test_evaluate_is_chirality_invariant() -> None:
    hand = _fake_hand()
    angle = np.deg2rad(35.0)
    rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
    hand[:, :2] = hand[:, :2] @ rotation.T
    mirrored_hand = hand.copy()
    mirrored_hand[:, 0] = -mirrored_hand[:, 0]
    sample = normalize_hand(hand)
    reference = normalize_hand(mirrored_hand)
    score, feedback = evaluate_static(sample, reference)
    assert score == 100
    assert feedback == []


def test_normalize_hand_is_in_plane_rotation_invariant() -> None:
    hand = _fake_hand()
    angle = np.deg2rad(35.0)
    rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
    rotated = hand.copy()
    rotated[:, :2] = rotated[:, :2] @ rotation.T
    np.testing.assert_allclose(normalize_hand(hand), normalize_hand(rotated), rtol=1e-5, atol=1e-5)


def test_normalize_hand_aligns_wrist_to_middle_direction() -> None:
    normalized = normalize_hand(_fake_hand())
    direction = normalized[9, :2]
    np.testing.assert_allclose(direction / np.linalg.norm(direction), [0.0, -1.0], atol=1e-9)


def test_normalize_hand_rejects_degenerate_shapes() -> None:
    with pytest.raises(ValueError, match="Expected"):
        normalize_hand(np.zeros((5, 3)))
    degenerate = _fake_hand()
    degenerate[9] = degenerate[0]
    with pytest.raises(ValueError, match="too small"):
        normalize_hand(degenerate)


def test_handshape_distance_is_zero_for_identical_shapes() -> None:
    shape = normalize_hand(_fake_hand())
    assert handshape_distance(shape, shape) == pytest.approx(0.0)


def test_score_from_distance_bounds() -> None:
    assert score_from_distance(0.0) == 100
    assert score_from_distance(MAX_DISTANCE) == 0
    assert score_from_distance(10.0) == 0


def test_score_curve_is_forgiving_for_close_shapes() -> None:
    assert score_from_distance(MAX_DISTANCE / 2) == 75
    assert score_from_distance(MAX_DISTANCE / 4) == 94


def test_finger_feedback_names_the_wrong_finger() -> None:
    reference = normalize_hand(_fake_hand())
    sample = reference.copy()
    sample[5:9] += 1.0
    feedback = finger_feedback(sample, reference)
    assert feedback[0] == "index"


def test_dtw_distance_is_zero_for_identical_sequences() -> None:
    sequence = normalize_frames([_fake_hand(seed=seed) for seed in range(8)])
    assert dtw_distance(sequence, sequence) == pytest.approx(0.0, abs=1e-9)


def test_dtw_distance_prefers_shifted_alignment() -> None:
    base = normalize_frames([_fake_hand(seed=seed) for seed in range(10)])
    shifted = base[3:]
    assert dtw_distance(base, shifted) < handshape_distance(base[0], shifted[0])


def test_evaluate_static_scores_identical_shapes_perfectly() -> None:
    shape = normalize_hand(_fake_hand())
    score, feedback = evaluate_static(shape, shape)
    assert score == 100
    assert feedback == []


def test_evaluate_dynamic_scores_identical_sequences_perfectly() -> None:
    sequence = normalize_frames([_fake_hand(seed=seed) for seed in range(6)])
    score, _ = evaluate_dynamic(sequence, sequence)
    assert score == 100


def _payload(frames: list[list[list[float]] | None]) -> dict:
    """Build a capture payload; None marks a frame without a hand."""
    return {
        "status": "capture",
        "captureId": 1,
        "fps": 30,
        "frames": [
            {
                "timeMs": index,
                "hands": (
                    []
                    if frame is None
                    else [
                        {
                            "handedness": "Right",
                            "landmarks": [{"x": x, "y": y, "z": z} for x, y, z in frame],
                        }
                    ]
                ),
            }
            for index, frame in enumerate(frames)
        ],
    }


def test_frames_from_payload_keeps_only_valid_hands() -> None:
    hand = _fake_hand()
    short = hand[:5]
    frames = frames_from_payload(_payload([hand.tolist(), None, short.tolist(), hand.tolist()]))
    assert len(frames) == 2
    assert frames[0].shape == (HAND_LANDMARKS, 3)


def test_frames_from_payload_on_empty_capture() -> None:
    assert frames_from_payload({"status": "empty", "captureId": 1}) == []


def test_reference_roundtrip(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(references_module, "PATH_REFERENCES", tmp_path)
    reference = Reference(name="bonjour", kind=REFERENCE_DYNAMIC)
    reference.add_sample(normalize_frames([_fake_hand(seed=seed) for seed in range(4)]))
    references_module.save_reference(reference)

    assert references_module.list_references() == ["bonjour"]
    loaded = references_module.load_reference("bonjour")
    assert loaded is not None
    assert loaded.name == "bonjour"
    assert loaded.kind == REFERENCE_DYNAMIC
    assert len(loaded.samples) == 1
    np.testing.assert_allclose(loaded.samples[0], reference.samples[0])

    references_module.delete_reference("bonjour")
    assert references_module.list_references() == []
    assert references_module.load_reference("bonjour") is None


def test_reference_static_score_against_samples(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(references_module, "PATH_REFERENCES", tmp_path)
    shape = normalize_hand(_fake_hand())
    reference = Reference(name="B", kind=REFERENCE_STATIC, samples=[shape])
    assert reference.best_static_score(shape) == 100

    with pytest.raises(ValueError, match="not static"):
        Reference(name="B", kind=REFERENCE_DYNAMIC, samples=[shape]).best_static_score(shape)


def test_keyframes_picks_evenly_spaced_frames() -> None:
    sequence = normalize_frames([_fake_hand(seed=seed) for seed in range(12)])
    picked = scoring.keyframes(sequence, count=4)
    assert len(picked) == 4
    np.testing.assert_allclose(picked[0], sequence[0])
    np.testing.assert_allclose(picked[-1], sequence[-1])


def test_keyframes_keeps_short_sequences() -> None:
    sequence = normalize_frames([_fake_hand(seed=seed) for seed in range(3)])
    assert len(scoring.keyframes(sequence, count=4)) == 3


def test_hand_connections_cover_every_landmark() -> None:
    touched = {index for pair in scoring.HAND_CONNECTIONS for index in pair}
    assert touched == set(range(HAND_LANDMARKS))


def test_hand_from_frame_rejects_invalid_frames() -> None:
    assert scoring.hand_from_frame({"hands": []}) is None
    assert scoring.hand_from_frame({}) is None
    short = {"hands": [{"landmarks": [{"x": 0.0, "y": 0.0, "z": 0.0}] * 5}]}
    assert scoring.hand_from_frame(short) is None


def test_hand_from_frame_extracts_first_hand() -> None:
    hand = _fake_hand()
    frame = {
        "hands": [
            {"handedness": "Right", "landmarks": [{"x": x, "y": y, "z": z} for x, y, z in hand]}
        ]
    }
    extracted = scoring.hand_from_frame(frame)
    assert extracted is not None
    np.testing.assert_allclose(extracted, hand)
