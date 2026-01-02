import os
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
# Safe init (NEVER crash on missing session_state keys)
# ----------------------------
def _ensure_state():
    # keys that MUST exist always
    st.session_state.setdefault("task_prompt", "")
    st.session_state.setdefault("guidelines_prompt", "")
    st.session_state.setdefault("outline_text", "")
    st.session_state.setdefault("keywords_text", "")
    st.session_state.setdefault("loaded_once", False)

    if st.session_state["loaded_once"]:
        return

    # load persisted values (guidelines/outline/keywords)
    g = guidelines_get()
    o = outline_get()
    kdf = read_keywords()

    st.session_state["guidelines_prompt"] = g.get("prompt", "") or ""
    st.session_state["outline_text"] = o.get("outline", "") or ""
    st.session_state["keywords_text"] = "\n".join(kdf["phrase"].tolist()) if not kdf.empty else ""

    # task_prompt is per task -> default empty
    st.session_state["task_prompt"] = st.session_state.get("task_prompt", "") or ""

    st.session_state["loaded_once"] = True

_ensure_state()

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
    seen = set()
    out = []
    for x in lines:
        k = x.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(x)
    return out

def autosave_guidelines():
    guidelines_set(st.session_state.get("guidelines_prompt", ""))
    st.session_state["guidelines_saved"] = True

def autosave_outline():
    outline_set(st.session_state.get("outline_text", ""))
    st.session_state["outline_saved"] = True

def autosave_keywords():
    phrases = parse_keywords_lines(st.session_state.get("keywords_text", ""))
    write_keywords(phrases)
    st.session_state["keywords_saved"] = True

# Task prompt is intentionally NOT persisted by default (per task)
def clear_task_prompt():
    st.session_state["task_prompt"] = ""

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
    task_ok = bool((st.session_state.get("task_prompt", "") or "").strip())
    has_guidelines = bool((st.session_state.get("guidelines_prompt", "") or "").strip())
    has_outline = bool((st.session_state.get("outline_text", "") or "").strip())
    kw_list = parse_keywords_lines(st.session_state.get("keywords_text", ""))
    has_keywords = len(kw_list) > 0

    # now we have 4 steps
    steps_done = sum([task_ok, has_guidelines, has_outline, has_keywords])
    total_steps = 4
    st.progress(steps_done / total_steps)

    st.caption(
        f"Postęp: {steps_done}/{total_steps} — "
        f"{'✅ Task' if task_ok else '⬜ Task'} | "
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
    # ✅ NEW STEP 1
    st.subheader("1) Task prompt (per tekst)")
    st.caption(
        "To jest prompt zadaniowy dla **konkretnego** tekstu. "
        "Opisujesz tu: cel tekstu, odbiorcę, format, długość, ton, wymagania. "
        "Jest włączany do generowania razem z Guidelines/Outline/Keywords."
    )
    st.text_area(
        "Task prompt",
        key="task_prompt",
        height=180,
        placeholder=(
            "Np.\n"
            "- Napisz artykuł ekspercki 2500–3500 słów\n"
            "- Ton: naturalny, bez AI-owych schematów\n"
            "- Uwzględnij praktyczne przykłady i definicje\n"
            "- Unikaj marketingowych obietnic\n"
        ),
    )
    c1, c2 = st.columns([1, 2])
    with c1:
        st.button("Wyczyść task prompt", on_click=clear_task_prompt)
    with c2:
        st.caption("Task prompt nie zapisuje się na stałe (celowo), żeby nie mieszać z innymi zadaniami.")

    st.subheader("2) Guidelines (autosave)")
    st.text_area(
        "Wytyczne stałe: jak piszemy, jaka długość, ton, zakazy, zasady SEO itd.",
        key="guidelines_prompt",
        height=210,
        on_change=autosave_guidelines,
        placeholder="Wklej tu stałe guidelines…",
    )
    g_time = get_last_modified(GUIDELINES_PATH)
    st.caption("💾 Autosave aktywny" + (f" | Ostatnia zmiana: {g_time}" if g_time else ""))

    st.subheader("3) Outline (autosave)")
    st.text_area(
        "Outline: nagłówki + fakty do wykorzystania (Twoje wytyczne).",
        key="outline_text",
        height=260,
        on_change=autosave_outline,
        placeholder="H2: ...\n- fakt...\nH3: ...\n- fakt...",
    )
    o_time = get_last_modified(OUTLINE_PATH)
    st.caption("💾 Autosave aktywny" + (f" | Ostatnia zmiana: {o_time}" if o_time else ""))

    st.subheader("4) Keywords (autosave)")
    st.text_area(
        "Frazy (jedna na linię). Bez targetów. Użycie naturalne.",
        key="keywords_text",
        height=240,
        on_change=autosave_keywords,
        placeholder="pozycjonowanie strony\nwyszukiwarka google\n...",
    )
    k_time = get_last_modified(KEYWORDS_PATH)
    st.caption(f"Liczba fraz: **{len(kw_list)}** | 💾 Autosave aktywny" + (f" | Ostatnia zmiana: {k_time}" if k_time else ""))

with right:
    st.subheader("5) Generowanie")
    title = st.text_input("Tytuł (H1 w HTML)", placeholder="np. Jak działa pozycjonowanie stron?")
    run_validation = st.checkbox("Walidator keywords po generowaniu", value=True)

    can_generate = task_ok and has_guidelines and has_outline
    if not task_ok:
        st.warning("Uzupełnij Task prompt (krok 1), żeby generować treść.")
    elif not (has_guidelines and has_outline):
        st.warning("Uzupełnij Guidelines i Outline, żeby generować treść.")

    if st.button("Generate", type="primary", disabled=not can_generate):
        task_prompt = (st.session_state.get("task_prompt", "") or "").strip()
        guidelines = (st.session_state.get("guidelines_prompt", "") or "").strip()
        outline = (st.session_state.get("outline_text", "") or "").strip()
        phrases = kw_list

        kw_block = "\n".join([f"- {p}" for p in phrases]) if phrases else "None"

        system = (
            "You are an expert SEO content writer. Follow instructions strictly. "
            "Output structured text with headings and paragraphs."
        )

        # ✅ Task prompt becomes the FIRST and strongest instruction block
        user = f"""
TASK (what to produce, for this specific text):
{task_prompt}

GUIDELINES (global rules, must follow):
{guidelines}

OUTLINE (must follow, include facts):
{outline}

KEYWORDS (use naturally where appropriate):
{kw_block}

OUTPUT RULES:
- Write in Polish unless task/guidelines say otherwise
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

        # Optional: include task prompt as comment in HTML for traceability
        html = text_to_basic_html(text, title=title.strip() if title else None)
        html = f"<!-- task_prompt:\n{task_prompt}\n-->\n" + html

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_name = f"{ts}_{provider}.html"
        html_path = os.path.join(GENERATED_DIR, html_name)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        st.session_state["last_text"] = text
        st.session_state["last_html"] = html
        st.session_state["last_html_path"] = html_path
        st.success(f"✅ Zapisano HTML: data/generated/{html_name}")

        if run_validation and phrases:
            hits = validate_keywords(text, phrases)
            report_df = pd.DataFrame([{
                "phrase": h.phrase,
                "found": h.found,
                "count_estimate": h.count,
            } for h in hits]).sort_values(
                ["found", "count_estimate", "phrase"],
                ascending=[True, True, True]
            ).reset_index(drop=True)

            rep_name = f"{ts}_{provider}_keyword_report.csv"
            rep_path = os.path.join(REPORTS_DIR, rep_name)
            report_df.to_csv(rep_path, index=False)

            st.session_state["last_report_df"] = report_df
            st.session_state["last_report_path"] = rep_path

    st.divider()
    st.subheader("6) Eksport")

    if "last_html" in st.session_state:
        st.download_button(
            "Download last HTML",
            data=st.session_state["last_html"].encode("utf-8"),
            file_name=os.path.basename(st.session_state["last_html_path"]),
            mime="text/html",
        )

        if "last_report_df" in st.session_state:
            st.download_button(
                "Download last keyword report (CSV)",
                data=st.session_state["last_report_df"].to_csv(index=False).encode("utf-8"),
                file_name=os.path.basename(st.session_state["last_report_path"]),
                mime="text/csv",
            )

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
            st.text_area("Generated text", st.session_state.get("last_text", ""), height=220)
            if "last_report_df" in st.session_state:
                st.dataframe(st.session_state["last_report_df"], width="stretch")
            else:
                st.info("Brak raportu walidatora (wyłączony lub brak keywords).")
    else:
        st.info("Wygeneruj treść, żeby pojawiły się opcje eksportu.")
