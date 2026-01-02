import streamlit as st
import pandas as pd
from storage import read_keywords, write_keywords, KEYWORDS_PATH

st.set_page_config(page_title="Keywords", layout="wide")
st.header("4) Keywords")

df = read_keywords()
st.caption("Fraza + docelowa liczba wystąpień. Możesz edytować tabelę i zapisać.")

edited = st.data_editor(
    df,
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        "phrase": st.column_config.TextColumn("phrase", required=True),
        "target_count": st.column_config.NumberColumn("target_count", min_value=0, step=1),
        "notes": st.column_config.TextColumn("notes"),
    },
)

col1, col2 = st.columns(2)
with col1:
    if st.button("Save keywords", type="primary"):
        write_keywords(pd.DataFrame(edited))
        st.success(f"Zapisano: {KEYWORDS_PATH}")

with col2:
    st.download_button(
        "Download keywords.csv",
        data=pd.DataFrame(edited).to_csv(index=False).encode("utf-8"),
        file_name="keywords.csv",
        mime="text/csv",
    )

uploaded = st.file_uploader("Import keywords.csv", type=["csv"])
if uploaded is not None:
    new_df = pd.read_csv(uploaded)
    write_keywords(new_df)
    st.success("Zaimportowano keywords.csv. Odśwież stronę jeśli nie widać zmian.")
