import streamlit as st
import pandas as pd
import os
from datetime import datetime

from storage import guidelines_get, outline_get, read_keywords, GENERATED_DIR
from llm_providers import chat_llm
from html_export import text_to_basic_html

st.set_page_config(page_title="Generate", layout="wide")
st.header("5) Generate")

provider = st.session_state.get("provider", "openai")

guidelines = guidelines_get().get("prompt", "").strip()
outline = outline_get().get("outline", "").strip()
kw_df = read_keywords()

if not guidelines:
    st.warning("Brak Guidelines. Uzupełnij w zakładce 2) Guidelines.")
if not outline:
    st.warning("Brak Outline. Uzupełnij w zakładce 3) Outline.")

title = st.text_input("Tytuł artykułu (do H1 w HTML)", placeholder="np. Sterylizator kosmetyczny – jak wybrać?")
temperature = st.slider("Temperature", 0.0, 0.9, 0.3, 0.05)

kw_block = "\n".join([f"- {r.phrase} (target: {int(r.target_count)})" for r in kw_df.itertuples()]) if not kw_df.empty else "None"

system = "You are an expert SEO content writer. Follow instructions strictly. Output structured text with headings and paragraphs."
user = f"""
GUIDELINES (must follow):
{guidelines if guidelines else "None"}

OUTLINE (must follow, include facts):
{outline if outline else "None"}

KEYWORDS (use with target counts, naturally):
{kw_block}

OUTPUT RULES:
- Write in Polish unless guidelines say otherwise
- Use clear headings that match outline (H2/H3)
- Use short, readable paragraphs (not one-liners)
- Do NOT mention that you are an AI
- Do not add final notes or summary unless outline includes it
- Return plain text with headings marked as "H2: ..." / "H3: ..."

Now write the article.
""".strip()

if st.button("Generate article", type="primary", disabled=not (guidelines and outline)):
    with st.spinner(f"Generuję ({provider.upper()})..."):
        text = chat_llm(
            provider=provider,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )

    html = text_to_basic_html(text, title=title.strip() if title else None)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"{ts}_{provider}.html"
    path = os.path.join(GENERATED_DIR, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    st.session_state.last_generated_path = path
    st.session_state.last_generated_html = html
    st.session_state.last_generated_text = text

    st.success(f"Zapisano: {path}")

if "last_generated_text" in st.session_state:
    st.subheader("Preview (tekst)")
    st.text_area("Generated text", st.session_state.last_generated_text, height=280)

    st.subheader("Preview (HTML)")
    st.code(st.session_state.last_generated_html, language="html")

    st.download_button(
        "Download last HTML",
        data=st.session_state.last_generated_html.encode("utf-8"),
        file_name=os.path.basename(st.session_state.last_generated_path),
        mime="text/html",
    )
