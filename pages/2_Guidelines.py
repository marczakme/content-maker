import streamlit as st
from storage import guidelines_get, guidelines_set

st.set_page_config(page_title="Guidelines", layout="wide")
st.header("2) Guidelines")

data = guidelines_get()
prompt = st.text_area(
    "Prompt / zasady tworzenia treści (zawsze używane)",
    value=data.get("prompt", ""),
    height=320,
    placeholder="Opisz jak tworzymy treść: styl, długość, ton, zakazy, struktura…",
)

if st.button("Save guidelines", type="primary"):
    guidelines_set(prompt)
    st.success("Zapisano guidelines (persist w data/guidelines.json).")
