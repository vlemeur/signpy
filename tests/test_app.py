"""Regression tests for the Streamlit application pages."""

from pathlib import Path

import numpy as np
from PIL import Image
from streamlit.testing.v1 import AppTest

import signpy.signstream as signstream
from signpy import references as references_module
from signpy.constants import REFERENCE_STATIC
from signpy.paths import PATH_LOGO, PATH_LSF_ALPHABET, PATH_SIGN_CAPTURE
from signpy.references import Reference, load_reference, save_reference
from signpy.scoring import normalize_hand

APP = Path(__file__).resolve().parents[1] / "signpy" / "signstream.py"


def _fake_hand(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    hand = rng.normal(size=(21, 3))
    hand[0] = (0.0, 0.0, 0.0)
    hand[9] = (0.0, -1.0, 0.0)
    return hand


def _capture_payload(capture_id: int = 3) -> dict:
    hand = _fake_hand()
    return {
        "status": "capture",
        "captureId": capture_id,
        "fps": 30,
        "frames": [
            {
                "timeMs": 0,
                "hands": [
                    {
                        "handedness": "Right",
                        "landmarks": [
                            {"x": float(x), "y": float(y), "z": float(z)} for x, y, z in hand
                        ],
                    }
                ],
            }
        ],
    }


def test_packaged_logo() -> None:
    with Image.open(PATH_LOGO) as logo:
        logo.verify()


def test_component_frontend_is_packaged() -> None:
    index_html = (PATH_SIGN_CAPTURE / "index.html").read_text()
    assert "tasks-vision@" in index_html
    assert "vision_bundle.mjs" in index_html
    assert "streamlit:componentReady" in index_html
    assert 'sendToStreamlit("streamlit:componentReady", { apiVersion: 1 })' in index_html
    assert "getUserMedia" in index_html


def test_practice_page_without_references(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(references_module, "PATH_REFERENCES", tmp_path)
    app = AppTest.from_file(str(APP)).run(timeout=30)
    assert not app.exception
    assert app.header[0].value == "S'exercer"
    assert app.info[0].value == (
        "Aucune référence enregistrée pour l'instant. Ouvre l'onglet Références "
        "en haut de l'écran, enregistre un signe face à la caméra, puis reviens ici."
    )


def test_record_page() -> None:
    app = AppTest.from_string("from signpy.signstream import record_page\nrecord_page()").run(
        timeout=30
    )
    assert not app.exception
    assert app.header[0].value == "Références"


def test_progress_page_without_scores() -> None:
    app = AppTest.from_string("from signpy.signstream import progress_page\nprogress_page()").run(
        timeout=30
    )
    assert not app.exception
    assert app.header[0].value == "Progression"
    assert app.info[0].value == "Pas encore de score. Va sur la page S'exercer pour commencer."


def test_progress_page_with_scores() -> None:
    app = AppTest.from_string("from signpy.signstream import progress_page\nprogress_page()")
    app.session_state["scores"] = {"B": [40, 70], "C": [10]}
    app.run(timeout=30)
    assert not app.exception
    assert len(app.metric) == 2
    assert app.metric[0].value == "Meilleur score : 70"


def test_practice_page_scores_a_capture(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(references_module, "PATH_REFERENCES", tmp_path)
    shape = normalize_hand(_fake_hand())
    save_reference(Reference(name="B", kind=REFERENCE_STATIC, samples=[shape]))
    monkeypatch.setattr(signstream, "sign_capture", lambda key: _capture_payload())

    app = AppTest.from_string("from signpy.signstream import practice_page\npractice_page()")
    app.run(timeout=30)
    assert not app.exception
    assert app.selectbox[0].value == "B"
    assert app.metric[0].value == "100 / 100"
    assert app.session_state["scores"] == {"B": [100]}

    app.run(timeout=30)
    assert app.session_state["scores"] == {"B": [100]}


def test_record_page_stores_a_capture(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(references_module, "PATH_REFERENCES", tmp_path)
    state = {"payload": _capture_payload()}
    monkeypatch.setattr(signstream, "sign_capture", lambda key, **args: state["payload"])

    app = AppTest.from_string("from signpy.signstream import record_page\nrecord_page()")
    app.run(timeout=30)
    assert not app.exception
    assert app.warning[0].value == "Donne un nom au signe avant d'enregistrer."

    state["payload"] = _capture_payload(capture_id=4)
    app.text_input[0].set_value("B").run(timeout=30)
    assert app.success[0].value == "Référence 'B' enregistrée."
    reference = load_reference("B")
    assert reference is not None
    assert reference.kind == REFERENCE_STATIC
    assert len(reference.samples) == 1


def test_record_page_video_mode_imports_a_capture(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(references_module, "PATH_REFERENCES", tmp_path)
    monkeypatch.setattr(signstream, "sign_capture", lambda key, **args: None)

    app = AppTest.from_string("from signpy.signstream import record_page\nrecord_page()")
    app.run(timeout=30)
    app.radio(key="record-mode").set_value(signstream.IMPORT_MODE_VIDEO).run(timeout=30)
    assert not app.exception
    assert len(app.file_uploader) == 1
    assert app.info[0].value.startswith("Choisis un court clip vidéo")

    state = {"payload": _capture_payload(capture_id=7)}
    monkeypatch.setattr(signstream, "sign_capture", lambda key, **args: state["payload"])
    app.text_input[0].set_value("B").run(timeout=30)
    app.file_uploader[0].set_value(("clip.mp4", b"fake video bytes", "video/mp4")).run(timeout=30)
    assert not app.exception
    assert app.success[0].value == "Référence 'B' importée depuis la vidéo."
    reference = load_reference("B")
    assert reference is not None
    assert reference.kind == REFERENCE_STATIC
    assert len(reference.samples) == 1


def _image_batch_payload() -> dict:
    hand = _fake_hand()
    entry = {
        "handedness": "Right",
        "landmarks": [{"x": float(x), "y": float(y), "z": float(z)} for x, y, z in hand],
    }
    return {
        "status": "image_batch",
        "captureId": 9,
        "images": [{"name": "A", "hands": [entry]}, {"name": "C", "hands": []}],
    }


def test_record_page_images_mode_saves_references(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(references_module, "PATH_REFERENCES", tmp_path)
    alphabet = tmp_path / "alphabet"
    alphabet.mkdir()
    (alphabet / "A.jpg").write_bytes(b"fake image")
    (alphabet / "B.jpg").write_bytes(b"fake image")
    monkeypatch.setattr(signstream, "PATH_LSF_ALPHABET", alphabet)
    state = {"payload": None}
    monkeypatch.setattr(signstream, "sign_capture", lambda key, **args: state["payload"])

    app = AppTest.from_string("from signpy.signstream import record_page\nrecord_page()")
    app.run(timeout=30)
    app.radio(key="record-mode").set_value(signstream.IMPORT_MODE_IMAGES).run(timeout=30)
    assert not app.exception
    assert app.info[0].value.startswith("Charge l'alphabet dactylologique LSF fourni")

    app.button[0].set_value(True).run(timeout=30)
    assert not app.exception
    assert "2 image(s) chargée(s)" in app.caption[-1].value

    state["payload"] = _image_batch_payload()
    app.run(timeout=30)
    assert not app.exception
    assert app.success[0].value == "1 référence(s) importée(s) depuis les images."
    assert app.warning[0].value == "Aucune main détectée dans : C"
    reference = load_reference("A")
    assert reference is not None
    assert reference.kind == REFERENCE_STATIC
    assert len(reference.samples) == 1

    app.run(timeout=30)
    reference = load_reference("A")
    assert reference is not None
    assert len(reference.samples) == 1


def test_lsf_alphabet_is_packaged() -> None:
    images = list(PATH_LSF_ALPHABET.glob("*.jpg"))
    assert len(images) == 26
    assert {path.stem for path in images} == set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    assert (PATH_LSF_ALPHABET / "CREDITS.md").is_file()
