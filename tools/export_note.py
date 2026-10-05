#!/usr/bin/env python3
"""Export a GO_MCP histotype algorithm note (markdown) to data/trials_<hist>.json.

Usage: export_note.py <note.md> <hist_key> <out.json> [--overrides overrides.json]

The note is parsed, not interpreted: every table cell is kept verbatim (markdown
bold retained). Only two derived fields are added per row:
  out        outcome class (os / pfs / ns / harm / single / pending) from heuristics,
             overridable per trial in the overrides file
  level      histotype evidence level parsed from the "<Hist> data" cell
References are resolved from the 📄 PDF wikilink or explicit [n] markers.
"""
import json, re, sys

def split_row(line):
    # split a markdown table row on unescaped pipes
    cells, cur, i = [], "", 0
    while i < len(line):
        ch = line[i]
        if ch == "\\" and i + 1 < len(line) and line[i+1] == "|":
            cur += "|"; i += 2; continue
        if ch == "|":
            cells.append(cur.strip()); cur = ""; i += 1; continue
        cur += ch; i += 1
    cells.append(cur.strip())
    if cells and cells[0] == "": cells = cells[1:]
    if cells and cells[-1] == "": cells = cells[:-1]
    return cells

WIKI = re.compile(r"\[\[([^\]|]+?)(?:\|([^\]]*))?\]\]")

def strip_links(s):
    # [[target|📝]] -> drop entirely ; [[target]] -> target
    def rep(m):
        alias = m.group(2)
        if alias is not None: return ""  # icons
        return m.group(1)
    return re.sub(r"\s{2,}", " ", WIKI.sub(rep, s)).strip(" ·;")

def parse_refs(text):
    refs, pdfs = [], {}
    for line in text.splitlines():
        m = re.match(r"^(\d+)\.\s+(.*)$", line.strip())
        if not m: continue
        n = int(m.group(1)); body = m.group(2)
        pm = re.search(r"PMID:\s*(\d+)", body)
        pdf = WIKI.findall(body)
        pdfname = pdf[-1][0] if pdf else ""
        # citation = text up to PMID
        cite = body.split("PMID:")[0].strip(" |")
        # split "Authors. Title. *Journal*. year;vol:pages."
        jm = re.search(r"\*([^*]+)\*\.\s*([^|]*)$", cite)
        journal = jm.group(1).strip() if jm else ""
        detail = jm.group(2).strip().rstrip(".") if jm else ""
        head = cite[:jm.start()].strip() if jm else cite
        refs.append([n, head, journal, detail, pm.group(1) if pm else ""])
        if pdfname: pdfs[pdfname] = n
    return refs, pdfs

def row_refs(cell, pdfs):
    out = []
    for target, alias in WIKI.findall(cell):
        if target in pdfs and pdfs[target] not in out: out.append(pdfs[target])
    for n in re.findall(r"\[(\d+)\]", cell):
        n = int(n)
        if n not in out: out.append(n)
    return out

LEVELS = [
    (r"(occc|oec|moc|histotype|clear.cell|mucinous|endometrioid)-only|only trial|only study|only phase|only randomi|only cohort|only series", "histotype_only"),
    (r"pooled", "pooled"),
    (r"subgroup reported|subgroup\b", "subgroup"),
    (r"included, not broken out|included\b", "included"),
    (r"❌|excluded", "excluded"),
]
def level_of(cell):
    head = cell[:160].lower()
    for pat, lv in LEVELS:
        if re.search(pat, head): return lv
    return "unspecified"

OUTCOMES = {
    "os": {"label": "Histotype OS benefit", "c": "var(--os)"},
    "pfs": {"label": "Histotype PFS benefit only", "c": "var(--pfs)"},
    "signal": {"label": "Subgroup signal, unconfirmed", "c": "var(--pfs)"},
    "ns": {"label": "Histotype result NS / negative", "c": "var(--ns)"},
    "harm": {"label": "Harm", "c": "var(--harm)"},
    "single": {"label": "Single-arm, histotype-level", "c": "var(--single)"},
    "obs": {"label": "Observational / retrospective", "c": "var(--fg-3)"},
    "no_subgroup": {"label": "Included, not broken out", "c": "var(--fg-3)"},
    "excluded": {"label": "Histotype excluded", "c": "var(--harm)"},
    "pending": {"label": "Unpublished", "c": "var(--fg-3)"},
}

def classify(row):
    """Histotype-level outcome class from the evidence-level cell; reviewed per trial through overrides."""
    lv = row["level"]
    if lv == "excluded": return "excluded"
    if lv == "included": return "no_subgroup"
    if row["observational"]: return "obs"
    reg = row["cols"].get("regimen", "")
    if " vs " not in reg and " v " not in reg and "±" not in reg: return "single"
    return "ns"

HEADMAP = {
    "trial": "trial", "regimen (exp vs control)": "regimen", "regimen": "regimen",
    "population": "pop", "prior systemic therapy": "pop", "n": "n",
    "pfs": "pfs", "dfs / rfs": "pfs", "rfs / pfs": "pfs", "os": "os", "hr": "hr", "orr": "orr",
    "pfi": "pfi", "recurrent fraction": "recurrent_fraction",
    "toxicity / notes": "tox", "source": "source",
}
def head_key(h):
    h = h.strip().lower()
    if h in HEADMAP: return HEADMAP[h]
    if h.endswith(" data"): return "hist"
    return re.sub(r"[^a-z0-9]+", "_", h).strip("_")

def parse_trial_cell(cell):
    italic = cell.startswith("*") and not cell.startswith("**")
    star = cell.startswith("**") or cell.startswith("***")
    c = cell.replace("**", "").replace("⭐", "").strip("*").strip()
    c = re.sub(r"\s*\[[\d,\s–-]+\]", "", c)      # trailing [n] reference markers
    c = re.sub(r"\s*↔.*$", "", c)                 # cross-table arrows
    m = re.match(r"^(.*?)\s*\(([^()]*(?:\([^()]*\)[^()]*)*)\)(.*)$", c)
    if m:
        name, cite, tail = m.group(1).strip(), m.group(2).strip(), m.group(3).strip(" ,;*")
        if tail: name = f"{name}, {tail}" if not tail.startswith(",") else name + tail
    else:
        name, cite = c, ""
    return name.strip(" ,"), cite, star, italic

def parse_callouts(block):
    notes = []
    for m in re.finditer(r"^> \[!(\w+)\]\s*(.*)\n((?:>.*\n?)*)", block, re.M):
        kind = {"warning": "warn", "danger": "warn", "caution": "warn"}.get(m.group(1).lower(), "info")
        body = "\n".join(l[2:] if l.startswith("> ") else l[1:] for l in m.group(3).splitlines())
        notes.append({"kind": kind, "title": m.group(2).strip(), "md": strip_links(body).strip()})
    return notes

def parse_sections(text, pdfs):
    # split at headings level 2 and 5
    parts = re.split(r"^(#{2,5} .*)$", text, flags=re.M)
    sections, mol = [], None
    i = 1
    while i < len(parts):
        head, body = parts[i].strip(), parts[i+1]; i += 2
        title = re.sub(r"^#+\s*", "", head)
        if title.startswith("References"): break
        sid = None
        m = re.match(r"^(\d[A-C]?)\.\s*(.*)", title)
        if title.lower().startswith("molecular profile"): sid = "mol"
        elif m: sid = "t" + m.group(1).lower()
        if not sid: continue
        intro_lines = []
        for l in body.splitlines():
            if l.startswith("|") or l.startswith(">") or l.startswith("#"): break
            if l.strip() and not l.startswith("---"): intro_lines.append(l.strip())
        intro = strip_links(" ".join(intro_lines))
        # tables
        tables = []; captions = []
        lines = body.splitlines(); j = 0; last_para = ""
        while j < len(lines):
            if lines[j].startswith("|") and j+1 < len(lines) and re.match(r"^\|\s*-", lines[j+1]):
                hdr = split_row(lines[j]); j += 2; rows = []
                while j < len(lines) and lines[j].startswith("|"):
                    rows.append(split_row(lines[j])); j += 1
                tables.append((hdr, rows)); captions.append(last_para if re.match(r"^\*\*", last_para) else ""); last_para = ""
            else:
                if lines[j].strip() and not lines[j].startswith(">") and not lines[j].startswith("---"): last_para = strip_links(lines[j].strip())
                j += 1
        if captions and intro_lines and captions[0] and captions[0] == strip_links(intro_lines[-1]):
            intro = strip_links(" ".join(intro_lines[:-1]))
        sec = {"id": sid, "title": title, "intro": intro}
        notes = parse_callouts(body)
        if sid == "mol":
            sec["mol"] = []
            for hdr, rows in tables:
                keys = [head_key(h) for h in hdr]
                sec["mol"].append({"caption": captions[len(sec["mol"])], "columns": hdr, "rows": [
                    {"cells": [strip_links(c) for c in r], "refs": row_refs(r[-1], pdfs)} for r in rows]})
            sec["notes"] = notes
            # drop the heading-only "A."/"B." text? keep intro
        else:
            if not tables:
                # subsection container (e.g. "## 2." with 2A/2B) -> keep as pre-notes on the next sections
                sec["container"] = True; sec["notes"] = notes
                sections.append(sec); continue
            hdr, rows = tables[0]
            keys = [head_key(h) for h in hdr]
            sec["columns"] = {k: h for k, h in zip(keys, hdr)}
            out_rows = []
            for r in rows:
                if len(r) != len(keys):
                    sys.stderr.write(f"[warn] {sid}: {len(r)} cells vs {len(keys)} headers: {r[0][:60]}\n")
                cols = {k: (r[idx] if idx < len(r) else "") for idx, k in enumerate(keys)}
                name, cite, star, italic = parse_trial_cell(cols.pop("trial"))
                src = cols.pop("source", "")
                refs = row_refs(src + " " + cols.get("tox", ""), pdfs)
                cols = {k: strip_links(v) for k, v in cols.items()}
                row = {"name": name, "cite": cite, "star": star, "observational": italic, "cols": cols, "refs": refs}
                row["level"] = level_of(cols.get("hist", ""))
                row["out"] = classify(row)
                out_rows.append(row)
            sec["rows"] = out_rows
            sec["notes"] = notes
        sections.append(sec)
    return sections

def main():
    src, hist, dst = sys.argv[1:4]
    overrides = {}
    if "--overrides" in sys.argv:
        overrides = json.load(open(sys.argv[sys.argv.index("--overrides") + 1]))
    text = open(src, encoding="utf-8").read()
    fm = {}
    if text.startswith("---"):
        fmtxt, text = text.split("\n---\n", 1)
        for l in fmtxt.splitlines()[1:]:
            if ":" in l: k, v = l.split(":", 1); fm[k.strip()] = v.strip().strip('"')
    refs, pdfs = parse_refs(text.split("## References", 1)[1] if "## References" in text else "")
    sections = parse_sections(text, pdfs)
    for s in sections:
        for r in s.get("rows", []):
            key = r["name"]
            if key in overrides.get("out", {}): r["out"] = overrides["out"][key]
            if key in overrides.get("tags", {}): r["tags"] = overrides["tags"][key]
            r.setdefault("tags", [])
    data = {"outcomes": OUTCOMES, "_meta": {"source": f"{fm.get('title','')} — vault note version {fm.get('version','')}, updated {fm.get('updated','')}",
                      "histology": hist, "extracted": "2026-10-05",
                      "note": "Cells are verbatim from the vault note (markdown bold retained). 'out' and 'level' are derived; 'out' overrides are listed in tools/overrides_<hist>.json."},
            "sections": sections, "references": refs}
    json.dump(data, open(dst, "w"), ensure_ascii=False, indent=1)
    n = sum(len(s.get("rows", [])) for s in sections)
    print(f"{hist}: {len(sections)} sections, {n} rows, {len(refs)} refs")

if __name__ == "__main__":
    main()
