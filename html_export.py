import re
from datetime import datetime

def escape_html(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def text_to_basic_html(text: str, title: str | None = None) -> str:
    lines = (text or "").splitlines()
    out = []
    if title:
        out.append(f"<h1>{escape_html(title)}</h1>")

    buf = []
    def flush_paragraph():
        nonlocal buf
        if buf:
            p = " ".join([x.strip() for x in buf if x.strip()])
            if p:
                out.append(f"<p>{escape_html(p)}</p>")
        buf = []

    for raw in lines:
        line = raw.strip()
        if not line:
            flush_paragraph()
            continue

        m = re.match(r"^(H[1-3]|###+|##|#)\s*[:\-]?\s*(.*)$", line, flags=re.IGNORECASE)
        if m:
            flush_paragraph()
            token = m.group(1).upper()
            content = m.group(2).strip()
            if token in ["#","H1","H2"]:
                out.append(f"<h2>{escape_html(content)}</h2>")
            elif token in ["##","H3"]:
                out.append(f"<h3>{escape_html(content)}</h3>")
            else:
                out.append(f"<h4>{escape_html(content)}</h4>")
        else:
            buf.append(line)

    flush_paragraph()
    meta = f"<!-- generated_at: {datetime.utcnow().isoformat()}Z -->"
    return meta + "\n" + "\n".join(out)
