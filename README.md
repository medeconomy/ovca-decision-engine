# OVCA Decision Engine

Evidence browser and patient-driven regimen ranker for high-grade serous ovarian carcinoma (HGSC).

Decision principle: **overall-survival benefit first → evidence-strength qualifier → PFS-only tier collapsed below → adverse-effect profile decides among survivors → prior-therapy ledger removes or demotes drugs already used.**

## Layout

| Path | What it is |
|---|---|
| `index.html` | Single-page app. View 1: ranker (patient profile → tiered regimen list). View 2: evidence browser (7 setting tabs, filters, PubMed-linked references). No build step; loads `data/*.json` at runtime. |
| `data/trials.json` | 67 trial rows across 7 settings + 95 references, exported from the Obsidian note `OVCA_HGSC_Algorithm_v1.2` (GO_MCP series). Values checked against full text 2026-09-14. |
| `data/tox.json` | Grade ≥3 rate, signature AEs, discontinuation and dose-reduction rates per trial, extracted from the `GO_summaries/` structured extracts. Unreported fields are the literal `"not_reported"`. |
| `data/labels.json` | Dose-modification / discontinuation rules per drug from FDA USPI §2 via DailyMed (label date and setid recorded). |
| `data/rechallenge.json` | Re-challenge evidence per drug class, with a verification report against the spec's from-memory values. |
| `SPEC.md` | Data schema and build spec (v0.1). |

## Running locally

Any static server works; `fetch()` is blocked on `file://`.

```
python3 -m http.server 8000
# open http://localhost:8000/
```

## Provenance rules

1. Every HR / median in `data/` traces to a vault extract or a PubMed record; nothing is written from memory.
2. Label rules come from DailyMed SPL text, never reconstructed.
3. `"not_reported"` means the source does not report it. No estimation.

## Scope

v0.1 gates to HGSC. Other ovarian histologies (clear cell, endometrioid, mucinous, germ cell, sex cord–stromal, low-grade serous) have their own algorithm notes in the vault and are not ranked here; HGSC OS claims are not extrapolated to them.

Not clinical advice. Built for one gynecologic oncologist's own decision support; every recommendation carries its source so it can be checked.
