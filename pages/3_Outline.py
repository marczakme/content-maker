import streamlit as st
from storage import outline_get, outline_set

st.set_page_config(page_title="Outline", layout="wide")
st.header("3) Outline")

data = outline_get()
outline = st.text_area(
    "Outline artykułu (nagłówki + fakty do użycia)",
    value=data.get("outline", ""),
    height=420,
    placeholder="H2: ...\n- fakt...\nH3: ...\n- fakt...",
)

if st.button("Save outline", type="primary"):
    outline_set(outline)
    st.success("Zapisano outline (persist w data/outline.json).")
