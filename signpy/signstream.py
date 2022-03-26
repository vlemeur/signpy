"""Build the main application"""
import threading
from pathlib import Path

import cv2
import imutils
import numpy as np
import pandas as pd
import streamlit as st
from hydralit import HydraApp, HydraHeadApp  # type: ignore
from PIL import Image
from streamlit_webrtc import ClientSettings, VideoTransformerBase, webrtc_streamer

# Loading logo
PATH_REPO = Path(__file__).parent.parent
PATH_LOGO = PATH_REPO / "static" / "sign-language.png"
PATH_MODELS = PATH_REPO / "pickles"
PATH_STYLE = PATH_MODELS / "style-transfer"

logo = Image.open(fp=PATH_LOGO)

style_models_name = [
    "Candy",
    "Composition_vii",
    "Feathers",
    "La_muse",
    "Mosaic",
    "Starry_night",
    "The_scream",
    "The_wave",
    "Udnie",
]
style_models_file = [
    "candy.t7",
    "composition_vii.t7",
    "feathers.t7",
    "la_muse.t7",
    "mosaic.t7",
    "starry_night.t7",
    "the_scream.t7",
    "the_wave.t7",
    "udnie.t7",
]
style_models_dict = {name: PATH_STYLE / file for name, file in zip(style_models_name, style_models_file)}


def remove_top_whitespace() -> None:
    """Hack to remove whitespace on the top of the page and display more information.
    Found here: https://discuss.streamlit.io/t/reduce-white-space-top-of-the-page/21737"""
    st.markdown(
        """
            <style>
                .css-18e3th9 {
                        padding-top: 0rem;
                        padding-bottom: 10rem;
                        padding-left: 5rem;
                        padding-right: 5rem;
                    }
                .css-1d391kg {
                        padding-top: 3.5rem;
                        padding-right: 1rem;
                        padding-bottom: 3.5rem;
                        padding-left: 1rem;
                    }
            </style>
            """,
        unsafe_allow_html=True,
    )


def get_model_from_path(style_model_path: Path):
    model = cv2.dnn.readNetFromTorch(str(style_model_path))
    return model


def style_transfer(image, model):
    (h, w) = image.shape[:2]
    # image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR) #PIL Jpeg to Opencv image

    blob = cv2.dnn.blobFromImage(image, 1.0, (w, h), (103.939, 116.779, 123.680), swapRB=False, crop=False)
    model.setInput(blob)
    output = model.forward()

    output = output.reshape((3, output.shape[2], output.shape[3]))
    output[0] += 103.939
    output[1] += 116.779
    output[2] += 123.680
    output /= 255.0
    output = output.transpose(1, 2, 0)
    output = np.clip(output, 0.0, 1.0)
    output = imutils.resize(output, width=500)
    return output


def webcam_input(style_model_name):
    st.header("Webcam Live Feed")
    WIDTH = st.sidebar.select_slider("QUALITY (May reduce the speed)", list(range(150, 501, 50)))

    class NeuralStyleTransferTransformer(VideoTransformerBase):
        _width = WIDTH
        _model_name = style_model_name
        _model = None

        def __init__(self) -> None:
            self._model_lock = threading.Lock()

            self._width = WIDTH
            self._update_model()

        def set_width(self, width):
            update_needed = self._width != width
            self._width = width
            if update_needed:
                self._update_model()

        def update_model_name(self, model_name):
            update_needed = self._model_name != model_name
            self._model_name = model_name
            if update_needed:
                self._update_model()

        def _update_model(self):
            style_model_path = style_models_dict[self._model_name]
            with self._model_lock:
                self._model = get_model_from_path(style_model_path)

        def transform(self, frame):
            image = frame.to_ndarray(format="bgr24")

            if self._model is None:
                return image

            orig_h, orig_w = image.shape[0:2]

            # cv2.resize used in a forked thread may cause memory leaks
            input = np.asarray(Image.fromarray(image).resize((self._width, int(self._width * orig_h / orig_w))))

            with self._model_lock:
                transferred = style_transfer(input, self._model)

            result = Image.fromarray((transferred * 255).astype(np.uint8))
            return np.asarray(result.resize((orig_w, orig_h)))

    ctx = webrtc_streamer(
        client_settings=ClientSettings(
            rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
            media_stream_constraints={"video": True, "audio": False},
        ),
        video_transformer_factory=NeuralStyleTransferTransformer,
        key="neural-style-transfer",
    )
    if ctx.video_transformer:
        ctx.video_transformer.set_width(WIDTH)
        ctx.video_transformer.update_model_name(style_model_name)


class SignInput(HydraHeadApp):
    """Sign Py main tab

    Parameters
    ----------
    HydraHeadApp : HydraHeadApp
        Template class from Hydralit to create tabs.
    """

    def run(self):
        pd.options.plotting.backend = "plotly"
        remove_top_whitespace()

        # Sidebar
        st.sidebar.image(image=logo, caption="SignPy", width=150)
        st.sidebar.info("Welcome to Python sign recognition app")
        st.sidebar.info("1. TO BE CONTINUED")
        st.sidebar.info("2. TO BE CONTINUED")

        # Splitting the page into 5 panels, 2 being used for padding
        column_1, _, _, _, column_3 = st.columns((16, 1, 10, 1, 18))

        with column_1:
            st.header("1. Input ??")

        with column_3:
            st.header("2. Input ??")


class TranfertLearning(HydraHeadApp):
    """Optional Tab

    Parameters
    ----------
    HydraHeadApp : HydraHeadApp
        Template class from Hydralit to create tabs.
    """

    def run(self):
        pd.options.plotting.backend = "plotly"
        remove_top_whitespace()

        # Sidebar
        st.sidebar.image(image=logo, caption="Sign py", width=150)
        st.sidebar.info("Bienvenue dans une section sans aucune utilité")
        style_model_name = st.sidebar.selectbox("Choose the style model: ", style_models_name)
        webcam_input(style_model_name)


class NoLoader:  # pylint:disable=too-few-public-methods
    """Simple class to override the default loader to remove loading animation and movements."""

    def run(self, app_target):  # pylint:disable=no-self-use
        """Empty loader, just runs the target.

        Parameters
        ----------
        app_target : HydraApp
            App to run.
        """
        app_target.run()


if __name__ == "__main__":
    app = HydraApp(
        title="SignPy",
        layout="wide",
        favicon=logo,
        navbar_animation=False,
        hide_streamlit_markers=True,  # will remove native streamlit menu
        navbar_mode="sticky",  # will jump down and up during page transitions, but more space efficient
        navbar_sticky=True,  # should stay on top
    )

    app.add_app(is_home=True, title="SignPy", icon="📷", app=SignInput())
    app.add_app(title="Transfert", icon="🧑‍🎄", app=TranfertLearning())
    app.add_loader_app(loader_app=NoLoader())
    app.run()
