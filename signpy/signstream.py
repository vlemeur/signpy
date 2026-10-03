"""Build the SignPy Streamlit application."""

import pandas as pd
import streamlit as st
from PIL import Image

from signpy.paths import PATH_LOGO


def sign_input() -> None:
    """Render the sign input page."""
    st.sidebar.info("Welcome to Python sign recognition app")
    st.sidebar.info("1. TO BE CONTINUED")
    st.sidebar.info("2. TO BE CONTINUED")

    column_1, _, _, _, column_3 = st.columns((16, 1, 10, 1, 18))
    with column_1:
        st.header("1. Input ??")
    with column_3:
        st.header("2. Input ??")


def other_tab() -> None:
    """Render the optional page."""
    st.sidebar.info("Bienvenue dans une section sans aucune utilité")


def main() -> None:
    """Configure the application and run the selected page."""
    with Image.open(PATH_LOGO) as logo:
        st.set_page_config(page_title="SignPy", layout="wide", page_icon=logo)
        st.sidebar.image(logo, caption="SignPy", width=150)
    pd.options.plotting.backend = "plotly"
    page = st.navigation(
        [
            st.Page(sign_input, title="SignPy", icon="📷", default=True),
            st.Page(other_tab, title="OtherTab", icon="🧑‍🎄"),
        ],
        position="top",
    )
    page.run()


if __name__ == "__main__":
    main()
