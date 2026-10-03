"""Build the SignPy Streamlit application."""

import plotly.graph_objects as go
import streamlit as st
from PIL import Image

from signpy.capture import sign_capture
from signpy.constants import REFERENCE_DYNAMIC, REFERENCE_KINDS, REFERENCE_STATIC
from signpy.paths import PATH_LOGO
from signpy.references import (
    Reference,
    delete_reference,
    list_references,
    load_reference,
    save_reference,
)
from signpy.scoring import (
    MAX_DYNAMIC_FRAMES,
    evaluate_dynamic,
    evaluate_static,
    frames_from_payload,
    normalize_frames,
)


def _capture_payload(key: str) -> tuple[int, dict | None]:
    """Read the capture component and deduplicate already processed captures."""
    payload = sign_capture(key=key)
    if payload is None or payload.get("status") != "capture":
        return -1, None
    capture_id = int(payload.get("captureId", -1))
    processed = st.session_state.setdefault("processed_captures", set())
    token = (key, capture_id)
    if token in processed:
        return capture_id, None
    processed.add(token)
    return capture_id, payload


def practice_page() -> None:
    """Render the practice page: sign in front of the camera and get scored."""
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
    st.write("Signe devant la caméra puis clique sur Evaluer dans le composant.")

    capture_id, payload = _capture_payload(key=f"practice-{selected}")
    if payload is None:
        _show_last_result(selected)
        return

    frames = frames_from_payload(payload)
    if not frames:
        st.warning("Aucune main détectée pendant la capture.")
        _show_last_result(selected)
        return

    normalized = normalize_frames(frames)
    if reference.kind == REFERENCE_STATIC:
        results = [evaluate_static(normalized[-1], sample) for sample in reference.samples]
    else:
        sequence = normalized[-MAX_DYNAMIC_FRAMES:]
        results = [evaluate_dynamic(sequence, sample) for sample in reference.samples]
    score, feedback = max(results, key=lambda result: result[0])

    st.session_state.setdefault("results", {})[capture_id] = (selected, score, feedback)
    scores = st.session_state.setdefault("scores", {})
    scores.setdefault(selected, []).append(score)
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


def record_page() -> None:
    """Render the reference recording page."""
    st.header("Références")
    st.write("Signe lentement et proprement devant la caméra puis clique sur Evaluer.")
    name = st.text_input("Nom du signe", placeholder="exemple : B, bonjour, merci")
    kind = st.radio("Type de signe", REFERENCE_KINDS)
    if kind == REFERENCE_DYNAMIC:
        st.caption("Le signe est enregistré comme une séquence de mouvements.")
    else:
        st.caption("Seule la dernière image de la capture est conservée.")
    _, payload = _capture_payload(key="record")
    if payload is None:
        return
    clean_name = name.strip()
    if not clean_name:
        st.warning("Donne un nom au signe avant d'enregistrer.")
        return
    frames = frames_from_payload(payload)
    if not frames:
        st.warning("Aucune main détectée pendant la capture.")
        return
    normalized = normalize_frames(frames)
    if kind == REFERENCE_STATIC:
        sample = normalized[-1]
    else:
        sample = normalized[-MAX_DYNAMIC_FRAMES:]
    reference = load_reference(clean_name) or Reference(name=clean_name, kind=kind)
    reference.kind = kind
    reference.add_sample(sample)
    save_reference(reference)
    st.success(f"Référence {clean_name!r} enregistrée ({len(reference.samples)} échantillon(s)).")

    st.divider()
    st.subheader("Supprimer une référence")
    names = list_references()
    if not names:
        return
    doomed = st.selectbox("Référence à supprimer", names)
    if st.button("Supprimer", type="primary"):
        delete_reference(doomed)
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
        yaxis=dict(title="Score", range=[0, 100]),
        xaxis=dict(title="Tentative"),
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
