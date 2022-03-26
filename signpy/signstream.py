"""Build the main application"""
from pathlib import Path

import pandas as pd
import streamlit as st
from hydralit import HydraApp, HydraHeadApp
from PIL import Image

# Loading logo for favicon
PATH_LOGO = Path(__file__).parent.parent / "static" / "sign-language.png"
logo = Image.open(fp=PATH_LOGO)


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


class OtherTab(HydraHeadApp):
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
        title="Metroscope",
        layout="wide",
        favicon=logo,
        navbar_animation=False,
        hide_streamlit_markers=True,  # will remove native streamlit menu
        navbar_mode="sticky",  # will jump down and up during page transitions, but more space efficient
        navbar_sticky=True,  # should stay on top
    )

    app.add_app(is_home=True, title="SignPy", icon="📷", app=SignInput())
    app.add_app(title="OtherTab", icon="🧑‍🎄", app=OtherTab())
    app.add_loader_app(loader_app=NoLoader())
    app.run()
