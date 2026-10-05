#!/usr/bin/env python3
"""Fetch DailyMed SPL XML for named products and dump the dosage-modification text.

Usage: fetch_labels.py <outdir>  — writes <outdir>/<key>.json with setid/version/title and
the text of the Dosage & Administration section (LOINC 34068-7) plus any subsection whose
title mentions modification/discontinuation. Nothing here is interpreted; rules are written
by hand into data/labels.json after reading the dumped text, with section references.
"""
import json, re, sys, os, urllib.request, xml.etree.ElementTree as ET

API = "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls"
NS = {"v3": "urn:hl7-org:v3"}
WANT = {
    # key: (search drug_name, preferred title regex)
    "irinotecan": ("irinotecan", r"CAMPTOSAR"),
    "oxaliplatin": ("oxaliplatin", r"OXALIPLATIN.*INJECTION.*\[(SANDOZ|TEVA|HOSPIRA|FRESENIUS|ACCORD)"),
    "capecitabine": ("capecitabine", r"XELODA"),
    "fluorouracil": ("fluorouracil", r"FLUOROURACIL INJECTION.*\[(ACCORD|FRESENIUS|SPECTRUM|TEVA|HIKMA|GLAND)"),
    "nivolumab": ("nivolumab", r"^OPDIVO \("),
    "ipilimumab": ("ipilimumab", r"^YERVOY"),
    "lenvatinib": ("lenvatinib", r"^LENVIMA"),
    "letrozole": ("letrozole", r"^FEMARA"),
    "anastrozole": ("anastrozole", r"^ARIMIDEX"),
    "palbociclib": ("palbociclib", r"^IBRANCE"),
    "trastuzumab": ("trastuzumab", r"^HERCEPTIN \("),
    "durvalumab": ("durvalumab", r"^IMFINZI"),
    "bleomycin": ("bleomycin", r"BLEOMYCIN"),
    "etoposide": ("etoposide", r"ETOPOSIDE INJECTION"),
    "ifosfamide": ("ifosfamide", r"IFOSFAMIDE"),
    "vinblastine": ("vinblastine", r"VINBLASTINE"),
    "leuprolide": ("leuprolide", r"LUPRON DEPOT"),
}

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "ovca-decision-engine/0.2"})
    with urllib.request.urlopen(req, timeout=60) as r: return r.read()

def pick(drug, pat):
    page = 1
    while page <= 6:
        j = json.loads(get(f"{API}.json?drug_name={drug}&pagesize=25&page={page}"))
        for d in j["data"]:
            if re.search(pat, d["title"], re.I): return d
        if page >= j["metadata"]["total_pages"]: break
        page += 1
    return None

def text(el):
    return re.sub(r"\s+", " ", " ".join(el.itertext())).strip()

def sections(root):
    out = []
    for sec in root.iter("{urn:hl7-org:v3}section"):
        code = sec.find("v3:code", NS); title = sec.find("v3:title", NS)
        c = code.get("code") if code is not None else ""
        t = text(title) if title is not None else ""
        out.append((c, t, sec))
    return out

def main():
    outdir = sys.argv[1]; os.makedirs(outdir, exist_ok=True)
    only = set(sys.argv[2:])
    for key, (drug, pat) in WANT.items():
        if only and key not in only: continue
        try:
            d = pick(drug, pat)
            if not d: print(key, "NOT FOUND"); continue
            xml = get(f"{API}/{d['setid']}.xml")
            root = ET.fromstring(xml)
            eff = root.find("v3:effectiveTime", NS)
            rec = {"key": key, "title": d["title"], "setid": d["setid"], "spl_version": d["spl_version"],
                   "published": d["published_date"], "effectiveTime": eff.get("value") if eff is not None else "", "sections": []}
            for c, t, sec in sections(root):
                if c == "34068-7" or re.search(r"modif|discontinu|dosage and administration|recommended dos", t, re.I) or c in ("34070-3",):
                    rec["sections"].append({"code": c, "title": t, "text": text(sec)})
            json.dump(rec, open(os.path.join(outdir, key + ".json"), "w"), indent=1)
            print(key, d["title"], d["setid"], len(rec["sections"]))
        except Exception as e:
            print(key, "ERROR", e)

if __name__ == "__main__":
    main()
