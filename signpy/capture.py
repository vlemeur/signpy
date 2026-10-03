"""Expose the browser-side sign capture Streamlit component."""

from typing import Any

import streamlit.components.v1 as components

from signpy.paths import PATH_SIGN_CAPTURE

_component_func = components.declare_component("sign_capture", path=str(PATH_SIGN_CAPTURE))


def sign_capture(key: str) -> dict[str, Any] | None:
    """Render the webcam capture component and return its latest payload.

    The component runs MediaPipe hand landmark detection in the browser and
    only sends landmark coordinates back. It returns ``None`` until the user
    clicks the evaluate button in the component.
    """
    payload = _component_func(key=key, default=None)
    if payload is None:
        return None
    if not isinstance(payload, dict):
        msg = "Unexpected payload from the sign capture component."
        raise TypeError(msg)
    return payload
