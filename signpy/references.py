"""Store and load user-recorded sign references."""

from dataclasses import dataclass, field

import joblib
import numpy as np

from signpy.constants import PATH_REFERENCES, REFERENCE_STATIC


@dataclass
class Reference:
    """A recorded sign: one or more normalized samples of its shape or movement."""

    name: str
    kind: str
    samples: list[np.ndarray] = field(default_factory=list)

    def add_sample(self, sample: np.ndarray) -> None:
        """Append a normalized sample recorded by the user."""
        self.samples.append(sample)

    def best_static_score(self, sample: np.ndarray) -> int:
        """Return the best static score against the recorded samples."""
        from signpy.scoring import evaluate_static

        if self.kind != REFERENCE_STATIC:
            msg = f"Reference {self.name!r} is not static."
            raise ValueError(msg)
        return max(evaluate_static(sample, candidate)[0] for candidate in self.samples)


def save_reference(reference: Reference) -> None:
    """Persist a reference, replacing any previous recording with the same name."""
    PATH_REFERENCES.mkdir(parents=True, exist_ok=True)
    joblib.dump(reference, PATH_REFERENCES / f"{reference.name}.joblib")


def load_reference(name: str) -> Reference | None:
    """Load a reference by name, or return None if it does not exist."""
    path = PATH_REFERENCES / f"{name}.joblib"
    if not path.exists():
        return None
    reference = joblib.load(path)
    if not isinstance(reference, Reference):
        msg = f"File {path} does not contain a reference."
        raise TypeError(msg)
    return reference


def list_references() -> list[str]:
    """Return the sorted names of every stored reference."""
    if not PATH_REFERENCES.exists():
        return []
    return sorted(path.stem for path in PATH_REFERENCES.glob("*.joblib"))


def delete_reference(name: str) -> None:
    """Delete a stored reference, ignoring missing files."""
    (PATH_REFERENCES / f"{name}.joblib").unlink(missing_ok=True)
