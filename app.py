import streamlit as st

st.set_page_config(page_title="Content maker", layout="wide")
st.title("Enzo Content Studio")
st.write("Generator treści na bazie wytycznych, outline i fraz z targetami wystąpień.")

st.info(
    "Kolejność pracy: Configuration → Guidelines → Outline → Keywords → Generate → Export\n\n"
    "To jest osobne narzędzie. Translator działa niezależnie."
)
