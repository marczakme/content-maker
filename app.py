import os
import re
import zipfile
from io import BytesIO
from datetime import datetime

import streamlit as st
import pandas as pd

from storage import (
    guidelines_get, guidelines_set,
    outline_get, outline_set,
    read_keywords, write_keywords,
    GUIDELINES_PATH, OUTLINE_PATH, KEYWORDS_PATH,
    GENERATED_DIR, REPORTS_DIR,
    get_last_modified,
)
from llm_providers import chat_llm
from html_export import text_to_basic_html
from keyword_validator import validate_keywords

st.set_page_config(page_title="Content Studio", layout="wide")
st.title("Content Studio")

# ----------------------------
# Helpers
# ----------------------------
def parse_keywords_lines(txt: str) -> list[str]:
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
        k = x.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(x)
    return out

def mark_saved(key: str):
    st.session_state[key] = True

def autosave_guidelines():
    guidelines_set(st.session_state.guidelines_prompt)
    mark_saved("guidelines_saved")

def autosave_outline():
    outline_set(st.session_state.outline_text)
    mark_saved("outline_saved")

def autosave_keywords():
    phrases = parse_keywords_lines(st.session_state.keywords_text)
    write_keywords(phrases)
    mark_saved("keywords_saved")

# ----------------------------
# Load persisted values into session_state (first run)
# ----------------------------
if "loaded_once" not in st.session_state:
    g = guidelines_get()
    o = outline_get()
    kdf = read_keywords()

    st.session_state.guidelines_prompt = g.get("prompt", "")
    st.session_state.outline_text = o.get("outline", "")
    st.session_state.keywords_text = "\n".join(kdf["phrase"].tolist()) if not kdf.empty else ""

    st.session_state.loaded_once = True

# ----------------------------
# Top bar: model + progress
# ----------------------------
colA, colB, colC = st.columns([1.2, 1.2, 2.6])

with colA:
    provider_ui = st.selectbox("Model", ["OpenAI", "Gemini", "Qwen"], index=0)
    provider = provider_ui.lower()

with colB:
    temperature = st.slider("Temperature", 0.0, 0.9, 0.3, 0.05)

with colC:
    # completion checks
    has_guidelines = bool((st.session_state.guidelines_prompt or "").strip())
    has_outline = bool((st.session_state.outline_text or "").strip())
    kw_list = parse_keywords_lines(st.session_state.keywords_text)
    has_keywords = len(kw_list) > 0

    steps_done = sum([has_guidelines, has_outline, has_keywords])
    total_steps = 3
    progress = steps_done / total_steps

    st.progress(progress)
    st.caption(
        f"Postęp: {steps_done}/{total_steps} — "
        f"{'✅ Guidelines' if has_guidelines else '⬜ Guidelines'} | "
        f"{'✅ Outline' if has_outline else '⬜ Outline'} | "
        f"{'✅ Keywords' if has_keywords else '⬜ Keywords'}"
    )

st.divider()

# ----------------------------
# Single window sections
# ----------------------------
left, right = st.columns([1.15, 1.0])

with left:
    st.subheader("1) Guidelines (autosave)")
    st.text_area(
        "Wytyczne: jak piszemy, jaka długość, ton, zakazy, zasady SEO itd.",
        key="guidelines_prompt",
        height=220,
        on_change=autosave_guidelines,
        placeholder="Wklej tu swój prompt / guidelines…",
    )
    g_saved = st.session_state.get("guidelines_saved", False)
    g_time = get_last_modified(GUIDELINES_PATH)
    st.caption(f"{'✅ Zapisano' if g_saved else '💾 Zapis automatyczny aktywny'}"
               + (f" | Ostatnia zmiana: {g_time}" if g_time else ""))

    st.subheader("2) Outline (autosave)")
    st.text_area(
        "Outline: nagłówki + fakty do wykorzystania (Twoje wytyczne).",
        key="outline_text",
        height=260,
        on_change=autosave_outline,
        placeholder="H2: ...\n- fakt...\nH3: ...\n- fakt...",
    )
    o_saved = st.session_state.get("outline_saved", False)
    o_time = get_last_modified(OUTLINE_PATH)
    st.caption(f"{'✅ Zapisano' if o_saved else '💾 Zapis automatyczny aktywny'}"
               + (f" | Ostatnia zmiana: {o_time}" if o_time else ""))

    st.subheader("3) Keywords (autosave)")
    st.text_area(
        "Frazy (jedna na linię). Bez targetów. Użycie naturalne.",
        key="keywords_text",
        height=240,
        on_change=autosave_keywords,
        placeholder="pozycjonowanie strony\nwyszukiwarka google\n...",
    )
    k_saved = st.session_state.get("keywords_saved", False)
    k_time = get_last_modified(KEYWORDS_PATH)
    st.caption(f"Liczba fraz: **{len(kw_list)}** | "
               f"{'✅ Zapisano' if k_saved else '💾 Zapis automatyczny aktywny'}"
               + (f" | Ostatnia zmiana: {k_time}" if k_time else ""))

with right:
    st.subheader("4) Generowanie")
    title = st.text_input("Tytuł (H1 w HTML)", placeholder="np. Jak działa pozycjonowanie stron?")
    run_validation = st.checkbox("Walidator keywords po generowaniu", value=True)

    can_generate = has_guidelines and has_outline
    if not can_generate:
        st.warning("Uzupełnij Guidelines i Outline, żeby generować treść.")

    generate_btn = st.button("Generate", type="primary", disabled=not can_generate)

    if generate_btn:
        guidelines = (st.session_state.guidelines_prompt or "").strip()
        outline = (st.session_state.outline_text or "").strip()
        phrases = kw_list

        kw_block = "\n".join([f"- {p}" for p in phrases]) if phrases else "None"

        system = "You are an expert SEO content writer. Follow instructions strictly. Output structured text with headings and paragraphs."
        user = f"""
GUIDELINES (must follow):
{guidelines}

OUTLINE (must follow, include facts):
{outline}

KEYWORDS (use naturally where appropriate):
{kw_block}

OUTPUT RULES:
- Write in Polish unless guidelines say otherwise
- Use headings matching outline (H2/H3)
- Use readable paragraphs (not one-liners)
- Do NOT mention that you are an AI
- Return plain text with headings marked as "H2: ..." / "H3: ..."
""".strip()

        with st.spinner(f"Generuję ({provider_ui})..."):
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
        html_name = f"{ts}_{provider}.html"
        html_path = os.path.join(GENERATED_DIR, html_name)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        st.session_state.last_text = text
        st.session_state.last_html = html
        st.session_state.last_html_path = html_path
        st.success(f"✅ Zapisano HTML: data/generated/{html_name}")

        if run_validation and phrases:
            hits = validate_keywords(text, phrases)
            report_df = pd.DataFrame([{
                "phrase": h.phrase,
                "found": h.found,
                "count_estimate": h.count,
            } for h in hits])

            # nice ordering: missing first
            report_df = report_df.sort_values(["found", "count_estimate", "phrase"], ascending=[True, True, True]).reset_index(drop=True)

            rep_name = f"{ts}_{provider}_keyword_report.csv"
            rep_path = os.path.join(REPORTS_DIR, rep_name)
            report_df.to_csv(rep_path, index=False)

            st.session_state.last_report_df = report_df
            st.session_state.last_report_path = rep_path
            st.success(f"✅ Zapisano raport: data/reports/{rep_name}")

    st.divider()
    st.subheader("5) Wynik i eksport")

    if "last_html" in st.session_state:
        st.caption("Podgląd HTML (fragment) + pobrania plików:")

        st.download_button(
            "Download last HTML",
            data=st.session_state.last_html.encode("utf-8"),
            file_name=os.path.basename(st.session_state.last_html_path),
            mime="text/html",
        )

        if "last_report_df" in st.session_state:
            st.download_button(
                "Download last keyword report (CSV)",
                data=st.session_state.last_report_df.to_csv(index=False).encode("utf-8"),
                file_name=os.path.basename(st.session_state.last_report_path),
                mime="text/csv",
            )

        # ZIP of all generated HTML
        html_files = sorted([f for f in os.listdir(GENERATED_DIR) if f.lower().endswith(".html")], reverse=True)
        selected = st.multiselect("ZIP: wybierz pliki HTML", html_files, default=html_files[:10])

        if selected:
            buf = BytesIO()
            with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
                for name in selected:
                    z.write(os.path.join(GENERATED_DIR, name), arcname=name)
            buf.seek(0)

            st.download_button(
                "Download ZIP (HTML)",
                data=buf.getvalue(),
                file_name="generated_html.zip",
                mime="application/zip",
            )

        with st.expander("Podgląd tekstu + raport walidatora", expanded=False):
            st.text_area("Generated text", st.session_state.get("last_text", ""), height=240)
            if "last_report_df" in st.session_state:
                st.caption("Walidator: fuzzy dopasowanie ‘z odmianami’ (heurystycznie przez rdzenie).")
                st.dataframe(st.session_state.last_report_df, width="stretch")
            else:
                st.info("Brak raportu walidatora (albo wyłączony, albo brak keywords).")
    else:
        st.info("Wygeneruj treść, żeby zobaczyć eksport i raport.")
