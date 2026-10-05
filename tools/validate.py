#!/usr/bin/env python3
"""Cross-reference check for every data file: trials named by regimens exist in the matching
trials file, tox_ref trials resolve in tox.json / tox_histotypes.json, drugs resolve in labels,
"base" ids resolve in the HGSC regimen file, and histotype 'out' classes are in the outcomes map."""
import json, sys, os
D = os.path.join(os.path.dirname(__file__), "..", "data")
load = lambda f: json.load(open(os.path.join(D, f), encoding="utf-8"))

hgsc = load("regimens.json"); hgsc_ids = {g["id"]: g for g in hgsc["regimens"]}
tox = load("tox.json"); toxh = load("tox_histotypes.json")
tox_trials = [e["trial"] for k, v in list(tox.items()) + list(toxh.items()) if isinstance(v, list) for e in v]
labels = {**{k: v for k, v in load("labels.json").items() if k != "_meta"}, **{k: v for k, v in load("labels_histotypes.json").items() if k != "_meta"}}
hgsc_trials = load("trials.json")
hgsc_names = {r["name"] for s in hgsc_trials["sections"] if "groups" in s for g in s["groups"] for r in g["rows"]}

errors = 0
def err(m):
    global errors; errors += 1; print("ERR", m)

def check(regfile, trialfile, histkey):
    reg = load(regfile); tr = load(trialfile)
    names = {r["name"] for s in tr["sections"] for r in s.get("rows", [])}
    outs = set(tr["outcomes"])
    for s in tr["sections"]:
        for r in s.get("rows", []):
            if r["out"] not in outs: err(f"{trialfile}: {r['name']} out={r['out']} not in outcomes")
            if not r["refs"]: print("warn", trialfile, s["id"], r["name"], "has no refs")
    ids = set()
    for g in reg["regimens"]:
        if g["id"] in ids: err(f"{regfile}: duplicate id {g['id']}")
        ids.add(g["id"])
        if g.get("histology") != histkey: err(f"{regfile}: {g['id']} histology={g.get('histology')}")
        if not (g.get("setting") or g.get("settings")): err(f"{regfile}: {g['id']} has no setting")
        if "base" in g and g["base"] not in hgsc_ids: err(f"{regfile}: {g['id']} base {g['base']} not in regimens.json")
        for t in g["trials"]:
            if t not in names: err(f"{regfile}: {g['id']} trial '{t}' not in {trialfile}")
        tr_ = (g.get("tox_ref") or {}).get("trial")
        if tr_ and not any(x == tr_ or x.startswith(tr_) for x in tox_trials): err(f"{regfile}: {g['id']} tox_ref trial '{tr_}' not in tox files")
        drugs = g.get("drugs") if "drugs" in g else hgsc_ids.get(g.get("base"), {}).get("drugs", [])
        for d in drugs:
            if d not in labels: err(f"{regfile}: {g['id']} drug '{d}' has no label record")
        if "tier" not in g or g["tier"] not in range(1, 8): err(f"{regfile}: {g['id']} tier missing/invalid")
        if g["tier"] <= 3: err(f"{regfile}: {g['id']} tier {g['tier']} — histotype files should not claim OS tiers")
    print(f"{regfile}: {len(reg['regimens'])} records, {len(names)} trial names, ok")

check("regimens_occc.json", "trials_occc.json", "OCCC")
check("regimens_oec.json", "trials_oec.json", "endometrioid")
check("regimens_moc.json", "trials_moc.json", "mucinous")
print("errors:", errors)
sys.exit(1 if errors else 0)
