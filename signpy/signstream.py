"""Build the SignPy Streamlit application."""

import base64
from pathlib import Path
from typing import Any

import numpy as np
import plotly.graph_objects as go
import streamlit as st
from PIL import Image

from signpy.capture import sign_capture
from signpy.constants import REFERENCE_DYNAMIC, REFERENCE_KINDS, REFERENCE_STATIC
from signpy.paths import PATH_LOGO, PATH_LSF_ALPHABET
from signpy.references import (
    Reference,
    delete_reference,
    list_references,
    load_reference,
    save_reference,
)
from signpy.scoring import (
    HAND_CONNECTIONS,
    MAX_DYNAMIC_FRAMES,
    evaluate_dynamic,
    evaluate_static,
    frames_from_payload,
    hand_from_frame,
    keyframes,
    normalize_frames,
    normalize_hand,
)

IMPORT_MODE_WEBCAM = "Webcam"
IMPORT_MODE_VIDEO = "Video importee"
IMPORT_MODE_IMAGES = "Images importees"
IMPORT_MAX_SIZE = 20_000_000


def _capture_payload(key: str, **args: Any) -> tuple[int, dict | None]:
    """Read the capture component and deduplicate already processed captures."""
    payload = sign_capture(key=key, **args)
    statuses = ("capture", "image_batch")
    if payload is None or payload.get("status") not in statuses:
        return -1, None
    capture_id = int(payload.get("captureId", -1))
    processed = st.session_state.setdefault("processed_captures", set())
    token = (key, capture_id)
    if token in processed:
        return capture_id, None
    processed.add(token)
    return capture_id, payload


def _hand_figure(shape: np.ndarray, title: str) -> go.Figure:
    """Draw one normalized hand shape as a plotly skeleton."""
    figure = go.Figure()
    x_values, y_values = shape[:, 0], shape[:, 1]
    for start, end in HAND_CONNECTIONS:
        figure.add_trace(
            go.Scatter(
                x=[x_values[start], x_values[end]],
                y=[y_values[start], y_values[end]],
                mode="lines",
                line={"color": "#00cc88", "width": 3},
                hoverinfo="skip",
                showlegend=False,
            )
        )
    figure.add_trace(
        go.Scatter(
            x=x_values,
            y=y_values,
            mode="markers",
            marker={"size": 7, "color": "#ff4b4b"},
            showlegend=False,
        )
    )
    figure.update_layout(
        title=title,
        margin={"l": 10, "r": 10, "t": 40, "b": 10},
        height=320,
        xaxis={"visible": False, "range": [-2.2, 2.2]},
        yaxis={"visible": False, "range": [2.4, -2.4]},
    )
    return figure


def _show_reference(reference: Reference) -> None:
    """Show the reference to reproduce: one shape or the movement keyframes."""
    st.subheader("Le signe a reproduire")
    if reference.kind == REFERENCE_STATIC:
        figure = _hand_figure(reference.samples[0], reference.name)
        st.plotly_chart(figure, use_container_width=True)
        return
    frames = keyframes(reference.samples[0])
    for row_start in range(0, len(frames), 2):
        row = st.columns(2)
        chunk = frames[row_start : row_start + 2]
        for column, frame in zip(row, chunk, strict=False):
            column.plotly_chart(_hand_figure(frame, ""), use_container_width=True)


def practice_page() -> None:
    """Render the practice page: see the sign, reproduce it, get scored."""
    st.header("S'exercer")
    names = list_references()
    if not names:
        st.info(
            "Aucune référence enregistrée pour l'instant. Ouvre l'onglet Références "
            "en haut de l'écran, enregistre un signe face à la caméra, puis reviens ici."
        )
        return
    selected = st.selectbox("Signe à travailler", names)
    reference = load_reference(selected)
    if reference is None or not reference.samples:
        st.warning(f"La référence {selected!r} est illisible, enregistre-la à nouveau.")
        return
    st.caption(f"Type : {reference.kind} - {len(reference.samples)} échantillon(s)")

    reference_column, capture_column = st.columns((2, 3), vertical_alignment="top")

    with capture_column:
        st.subheader("Ta reproduction")
        st.write("Signe devant la caméra puis clique sur Evaluer dans le composant.")
        capture_id, payload = _capture_payload(key=f"practice-{selected}")
        if payload is not None:
            frames = frames_from_payload(payload)
            if not frames:
                st.warning("Aucune main détectée pendant la capture.")
            else:
                normalized = normalize_frames(frames)
                if reference.kind == REFERENCE_STATIC:
                    results = [evaluate_static(normalized[-1], s) for s in reference.samples]
                else:
                    sequence = normalized[-MAX_DYNAMIC_FRAMES:]
                    results = [evaluate_dynamic(sequence, s) for s in reference.samples]
                score, feedback = max(results, key=lambda result: result[0])
                st.session_state.setdefault("results", {})[capture_id] = (
                    selected,
                    score,
                    feedback,
                )
                scores = st.session_state.setdefault("scores", {})
                scores.setdefault(selected, []).append(score)

    with reference_column:
        _show_reference(reference)
        _show_last_result(selected)


def _show_last_result(selected: str) -> None:
    """Show the most recent result recorded for the selected reference."""
    results = st.session_state.get("results", {})
    matching = [item for item in results.values() if item[0] == selected]
    if not matching:
        return
    _, score, feedback = matching[-1]
    st.metric("Score", f"{score} / 100")
    st.progress(score / 100)
    if feedback:
        st.info("Doigts à corriger en priorité : " + ", ".join(feedback))


def _save_capture(reference_name: str, kind: str, payload: dict, frame_index: int) -> str | None:
    """Store a capture payload as a reference sample and return an error message."""
    frames = frames_from_payload(payload)
    if not frames:
        return "Aucune main détectée pendant la capture."
    normalized = normalize_frames(frames)
    if kind == REFERENCE_STATIC:
        sample = normalized[min(frame_index, len(normalized) - 1)]
    else:
        sample = normalized[-MAX_DYNAMIC_FRAMES:]
    reference = load_reference(reference_name) or Reference(name=reference_name, kind=kind)
    reference.kind = kind
    reference.add_sample(sample)
    save_reference(reference)
    return None


def _save_image_batch(payload: dict) -> tuple[int, list[str]]:
    """Store one static reference per analyzed image, named after its file.

    Returns the number of saved references and the names of the images where
    no hand was detected.
    """
    saved = 0
    missed = []
    for image in payload.get("images", []):
        name = str(image.get("name", "")).strip() or "sans-nom"
        hand = hand_from_frame(image)
        if hand is None:
            missed.append(name)
            continue
        reference = load_reference(name) or Reference(name=name, kind=REFERENCE_STATIC)
        reference.kind = REFERENCE_STATIC
        reference.add_sample(normalize_hand(hand))
        save_reference(reference)
        saved += 1
    return saved, missed


def _image_entries(uploads: list) -> list[dict[str, str]] | None:
    """Build component entries from uploaded images, or None if too large."""
    entries = []
    for uploaded in uploads:
        if uploaded.size > IMPORT_MAX_SIZE:
            st.warning(f"{uploaded.name} est trop volumineux ({uploaded.size / 1e6:.0f} Mo).")
            return None
        data_url = "data:image/jpeg;base64," + base64.b64encode(uploaded.getvalue()).decode()
        entries.append({"name": Path(uploaded.name).stem, "url": data_url})
    return entries


def _alphabet_entries() -> list[dict[str, str]]:
    """Build component entries from the bundled LSF alphabet images."""
    entries = []
    for image_path in sorted(PATH_LSF_ALPHABET.glob("*.jpg")):
        data_url = "data:image/jpeg;base64," + base64.b64encode(image_path.read_bytes()).decode()
        entries.append({"name": image_path.stem, "url": data_url})
    return entries


def record_page() -> None:
    """Render the reference recording page."""
    st.header("Références")
    st.write("Enregistre un signe de référence : signe lentement et proprement.")
    mode = st.radio(
        "Source",
        [IMPORT_MODE_WEBCAM, IMPORT_MODE_VIDEO, IMPORT_MODE_IMAGES],
        key="record-mode",
    )
    name = st.text_input("Nom du signe", placeholder="exemple : B, bonjour, merci")
    kind = st.radio("Type de signe", REFERENCE_KINDS, key="record-kind")
    if kind == REFERENCE_DYNAMIC:
        st.caption("Le signe est enregistré comme une séquence de mouvements.")
    else:
        st.caption("Une seule image du signe est conservée (la dernière en webcam).")

    clean_name = name.strip()
    if mode == IMPORT_MODE_WEBCAM:
        _, payload = _capture_payload(key="record")
        if payload is None:
            return
        if not clean_name:
            st.warning("Donne un nom au signe avant d'enregistrer.")
            return
        error = _save_capture(clean_name, kind, payload, frame_index=-1)
        if error:
            st.warning(error)
            return
        st.success(f"Référence {clean_name!r} enregistrée.")
    elif mode == IMPORT_MODE_VIDEO:
        uploaded = st.file_uploader(
            "Clip vidéo du signe (dictionnaire en ligne, quelques secondes)",
            type=["mp4", "mov", "webm"],
            key="record-upload",
        )
        if uploaded is None:
            st.info(
                "Choisis un court clip vidéo montrant le signe une fois, "
                "puis clique sur Analyser la video dans le composant."
            )
            return
        if uploaded.size > IMPORT_MAX_SIZE:
            st.warning(f"Clip trop volumineux ({uploaded.size / 1e6:.0f} Mo), 20 Mo maximum.")
            return
        data_url = "data:video/mp4;base64," + base64.b64encode(uploaded.getvalue()).decode()
        _, payload = _capture_payload(key="record-video", import_mode=True, video_url=data_url)
        if payload is None:
            return
        if not clean_name:
            st.warning("Donne un nom au signe avant d'enregistrer.")
            return
        error = _save_capture(clean_name, kind, payload, frame_index=len(payload["frames"]) // 2)
        if error:
            st.warning(error)
            return
        st.success(f"Référence {clean_name!r} importée depuis la vidéo.")
    else:
        alphabet_ready = bool(list(PATH_LSF_ALPHABET.glob("*.jpg")))
        if alphabet_ready and st.button("Importer l'alphabet LSF fourni", key="import-alphabet"):
            st.session_state["image_entries"] = _alphabet_entries()
        uploads = st.file_uploader(
            "Ou tes propres images (configurations de main)",
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="record-images-upload",
        )
        if uploads:
            st.session_state["image_entries"] = _image_entries(uploads)
        entries = st.session_state.get("image_entries") or []
        if not entries:
            st.info(
                "Charge l'alphabet dactylologique LSF fourni en un clic, "
                "ou importe tes propres images de configurations de main, "
                "puis clique sur Analyser les images dans le composant."
            )
            return
        st.caption(
            f"{len(entries)} image(s) chargée(s) : clique sur Analyser les images "
            "dans le composant ci-dessous."
        )
        _, payload = _capture_payload(key="record-images", import_mode=True, image_urls=entries)
        if payload is None:
            return
        st.session_state["image_entries"] = None
        saved, missed = _save_image_batch(payload)
        if saved:
            st.success(f"{saved} référence(s) importée(s) depuis les images.")
        if missed:
            st.warning("Aucune main détectée dans : " + ", ".join(missed))

    st.divider()
    st.subheader("Supprimer une référence")
    names = list_references()
    if not names:
        return
    doomed = st.selectbox("Référence à supprimer", names)
    if st.button("Supprimer", type="primary"):
        delete_reference(doomed)
        st.rerun()
    if st.button("Tout supprimer"):
        for name in names:
            delete_reference(name)
        st.rerun()


def progress_page() -> None:
    """Render the progression page."""
    st.header("Progression")
    scores = st.session_state.get("scores", {})
    if not scores:
        st.info("Pas encore de score. Va sur la page S'exercer pour commencer.")
        return
    figure = go.Figure()
    for name, values in scores.items():
        figure.add_trace(
            go.Scatter(
                x=list(range(1, len(values) + 1)),
                y=values,
                mode="lines+markers",
                name=name,
            )
        )
    figure.update_layout(
        yaxis={"title": "Score", "range": [0, 100]},
        xaxis={"title": "Tentative"},
        legend_title="Signe",
    )
    st.plotly_chart(figure)
    columns = st.columns(len(scores))
    for column, (name, values) in zip(columns, scores.items(), strict=True):
        column.metric(name, f"Meilleur score : {max(values)}")


def main() -> None:
    """Configure the application and run the selected page."""
    with Image.open(PATH_LOGO) as logo:
        st.set_page_config(page_title="SignPy", layout="wide", page_icon=logo)
        st.sidebar.image(logo, caption="SignPy", width=150)
    st.sidebar.info("Enregistre des signes, exerce-toi, suis ta progression.")
    page = st.navigation(
        [
            st.Page(practice_page, title="S'exercer", icon="🎯", default=True),
            st.Page(record_page, title="Références", icon="🎬"),
            st.Page(progress_page, title="Progression", icon="📈"),
        ],
        position="top",
    )
    page.run()


if __name__ == "__main__":
    main()
