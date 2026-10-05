# OVCA Decision Engine

Evidence browser and patient-driven regimen ranker for high-grade serous ovarian carcinoma (HGSC).

Decision principle: **overall-survival benefit first → evidence-strength qualifier → PFS-only tier collapsed below → adverse-effect profile decides among survivors → prior-therapy ledger removes or demotes drugs already used.**

## Layout

| Path | What it is |
|---|---|
| `index.html` | Single-page app. View 1: ranker (patient profile → tiered regimen list). View 2: evidence browser (7 setting tabs, filters, PubMed-linked references). No build step; loads `data/*.json` at runtime. |
| `data/trials.json` | 67 trial rows across 7 settings + 95 references, exported from the Obsidian note `OVCA_HGSC_Algorithm_v1.2` (GO_MCP series). Values checked against full text 2026-09-14. |
| `data/regimens.json` | 43 regimen × setting records (HGSC). Each points at its trial rows, its toxicity entry (arm-specific where the trial mixes arms), its label drugs, and carries the OS classification, evidence strength, tier, biomarker/line gates, label-derived risk rules and ledger rules. This is the file to edit when a judgement changes. |
| `data/tox.json` | Grade ≥3 rate, signature AEs, discontinuation and dose-reduction rates per trial, extracted from the `GO_summaries/` structured extracts. Unreported fields are the literal `"not_reported"`. |
| `data/labels.json` | Dose-modification / discontinuation rules per drug from FDA USPI §2 via DailyMed (label date and setid recorded). |
| `data/rechallenge.json` | Re-challenge evidence per drug class, with a verification report against the spec's from-memory values. |
| `SPEC.md` | Data schema and build spec (v0.1). |

## Ranking logic (v0.1)

1. **Gate** by histology (HGSC only), setting, biomarker (BRCA / HRD / FRα / HER2 / PD-L1 CPS), stage, residual disease, PFI, prior-line count and prior bevacizumab, as each pivotal trial and label require.
2. **Tier** by OS evidence: 1 replicated OS · 2 single phase 3 OS · 3 subgroup / crossover-confounded OS · 4 PFS-only · 5 no efficacy difference (toxicity-chosen alternatives) · 6 no phase 3 · 7 do not use. Tier rules can move a regimen for a profile (e.g. TC + bev → tier 3 for stage IV; olaparib + bev → tier 7 for HRD-negative).
3. **Exclude** on label contraindications and trial exclusions matched to the patient's baseline-risk flags; **demote** on the prior-therapy ledger (PFI <6 removes platinum re-challenge; prior PARPi turns PARPi maintenance into OReO re-challenge; same class stopped for toxicity excludes).
4. **Order within a tier** by net risk flags (cautions minus fits), then grade ≥3 any-cause rate ascending; `not_reported` rows follow the numeric ones and say so.
5. Tiers 1–3 open by default; tiers 4–5 open automatically when 1–3 are empty for the profile.

Every card shows why it sits where it sits, and links each trial to its row in the evidence browser.

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
