import streamlit as st
import pandas as pd
from storage import read_keywords, write_keywords, KEYWORDS_PATH

st.set_page_config(page_title="Keywords", layout="wide")
st.header("4) Keywords")

st.caption(
    "Wklej frazy **linia po linii** (bez targetów). "
    "System zapisze je jako listę do użycia w generowaniu i do walidacji."
)

existing = read_keywords()
existing_list = existing["phrase"].tolist() if not existing.empty else []

with st.expander("Aktualnie zapisane frazy", expanded=False):
    st.write(f"Liczba fraz: **{len(existing_list)}**")
    if existing_list:
        st.code("\n".join(existing_list), language="text")
    else:
        st.info("Brak fraz. Wklej listę poniżej i zapisz.")

st.subheader("Wklej nową listę fraz")
paste = st.text_area(
    "Frazy (jedna na linię)",
    height=320,
    placeholder="np.\npozycjonowanie strony\nwyszukiwarka google\n...",
)

col1, col2, col3 = st.columns([1, 1, 1])

def _parse_lines(txt: str) -> list[str]:
    lines = []
    for raw in (txt or "").splitlines():
        s = raw.strip()
        if not s:
            continue
        lines.append(s)
    # unique keep order
    seen = set()
    out = []
    for x in lines:
        key = x.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(x)
    return out

with col1:
    if st.button("Replace (overwrite)", type="primary"):
        phrases = _parse_lines(paste)
        df = pd.DataFrame({"phrase": phrases})
        write_keywords(df)
        st.success(f"Zapisano {len(phrases)} fraz do {KEYWORDS_PATH}. Odśwież stronę, jeśli trzeba.")

with col2:
    if st.button("Merge (append)"):
        phrases_new = _parse_lines(paste)
        merged = existing_list + phrases_new
        # unique keep order
        seen = set()
        out = []
        for x in merged:
            key = x.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(x)
        df = pd.DataFrame({"phrase": out})
        write_keywords(df)
        st.success(f"Dodano/połączono. Teraz jest {len(out)} fraz. Odśwież stronę, jeśli trzeba.")

with col3:
    st.download_button(
        "Download keywords.csv",
        data=pd.DataFrame({"phrase": existing_list}).to_csv(index=False).encode("utf-8"),
        file_name="keywords.csv",
        mime="text/csv",
    )

st.divider()
st.subheader("Import keywords.csv")

uploaded = st.file_uploader("Wgraj plik CSV z kolumną: phrase", type=["csv"])
if uploaded is not None:
    df = pd.read_csv(uploaded)
    write_keywords(df)
    st.success("Zaimportowano keywords.csv (kolumna phrase).")
