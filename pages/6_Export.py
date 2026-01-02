import streamlit as st
import os
import zipfile
from io import BytesIO
from storage import GENERATED_DIR

st.set_page_config(page_title="Export", layout="wide")
st.header("6) Export")

if not os.path.exists(GENERATED_DIR):
    st.info("Brak wygenerowanych plików.")
    st.stop()

files = sorted([f for f in os.listdir(GENERATED_DIR) if f.lower().endswith(".html")], reverse=True)

st.write(f"Znaleziono plików HTML: **{len(files)}**")
selected = st.multiselect("Wybierz pliki do ZIP", files, default=files[:10])

if selected:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name in selected:
            path = os.path.join(GENERATED_DIR, name)
            z.write(path, arcname=name)
    buf.seek(0)

    st.download_button(
        "Download ZIP",
        data=buf.getvalue(),
        file_name="generated_html.zip",
        mime="application/zip",
    )

st.divider()
st.subheader("Pojedyncze pliki")
for name in files[:25]:
    path = os.path.join(GENERATED_DIR, name)
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    st.download_button(
        f"Download {name}",
        data=html.encode("utf-8"),
        file_name=name,
        mime="text/html",
        key=name,
    )
