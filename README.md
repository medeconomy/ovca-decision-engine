# OVCA Decision Engine

Evidence browser and patient-driven regimen ranker for ovarian carcinoma: high-grade serous (HGSC), clear cell (OCCC), endometrioid (OEC) and mucinous (MOC).

Decision principle: **overall-survival benefit first → evidence-strength qualifier → PFS-only tier collapsed below → adverse-effect profile decides among survivors → prior-therapy ledger removes or demotes drugs already used.**

## Layout

| Path | What it is |
|---|---|
| `index.html` | Single-page app. View 1: ranker (patient profile → tiered regimen list; the histology field picks the regimen pool). View 2: evidence browser (histology switch → setting tabs, filters, PubMed-linked references). No build step; loads `data/*.json` at runtime. |
| `data/trials.json` | 67 trial rows across 7 settings + 95 references, exported from the Obsidian note `OVCA_HGSC_Algorithm_v1.2` (GO_MCP series). Values checked against full text 2026-09-14. |
| `data/trials_occc.json`, `trials_oec.json`, `trials_moc.json` | Generic exports of `OVCA_ClearCell_Algorithm_v1.1` (49 rows, 64 refs), `OVCA_Endometrioid_Algorithm_v1.1` (61 rows, 96 refs) and `OVCA_Mucinous_Algorithm_v1.1` (36 rows, 66 refs) by `tools/export_note.py`. Every table cell is kept verbatim; two fields are derived — `level` (histotype evidence level, from the "Clear cell / OEC / MOC data" cell) and `out` (the *histotype-level* reading of the trial: histotype OS/PFS benefit, subgroup signal, NS/negative, single-arm, observational, included-not-broken-out, excluded). Per-trial `out` corrections live in `tools/overrides/`. |
| `data/regimens_occc.json`, `regimens_oec.json`, `regimens_moc.json` | 38 / 42 / 32 regimen × setting records per histotype. A record with `base` inherits drugs, toxicity reference, PFS text, label risk rules and ledger rules from the named HGSC record (a regimen's toxicity does not change with histology); its own tier, OS reading, `evidence_basis`, gates and qualifiers override. |
| `data/trials_gct.json`, `trials_scst.json` | Exports of `OVCA_GermCell_Algorithm_v1.1` (61 rows, 71 refs) and `OVCA_SexCordStromal_Algorithm_v1.0` (56 rows, 60 refs). Male germ cell trials carry the badge "Extrapolated (male GCT)". |
| `data/regimens_gct.json`, `regimens_scst.json` | 21 / 19 regimen × setting records with their own settings list (`_meta.settings`), tier labels and patient fields (subtype, age group, surgical staging, tumour markers; ER/PR and resectability for SCST). |
| `data/tox_histotypes.json` | Toxicity entries for the trials that appear only in the histotype notes (JGOG3017, MOCCA, MoST-CIRCUIT, INOVA, LARA, PEACOCC, DART, GOG-0241, GOG-157, KEYNOTE-158, PARAGON, LACOG 1018). |
| `data/labels_histotypes.json` | DailyMed label rules for the agents that appear only in the histotype pools (irinotecan, oxaliplatin, capecitabine, fluorouracil, nivolumab, ipilimumab, durvalumab, lenvatinib, letrozole, anastrozole, palbociclib, trastuzumab; sintilimab recorded as having no FDA label). Fetched by `tools/fetch_labels.py`. |
| `data/regimens.json` | 43 regimen × setting records (HGSC). Each points at its trial rows, its toxicity entry (arm-specific where the trial mixes arms), its label drugs, and carries the OS classification, evidence strength, tier, biomarker/line gates, label-derived risk rules and ledger rules. This is the file to edit when a judgement changes. |
| `data/tox.json` | Grade ≥3 rate, signature AEs, discontinuation and dose-reduction rates per trial, extracted from the `GO_summaries/` structured extracts. Unreported fields are the literal `"not_reported"`. |
| `data/labels.json` | Dose-modification / discontinuation rules per drug from FDA USPI §2 via DailyMed (label date and setid recorded). |
| `data/response_schemes.json` | Per-trial definitions of NED / CR / PR at the end of the platinum (verbatim from the full texts) and the response-category subgroup HRs the ranker quotes. |
| `data/rechallenge.json` | Re-challenge evidence per drug class, with a verification report against the spec's from-memory values. |
| `SPEC.md` | Data schema and build spec (v0.1) with the decisions taken. |
| `tools/` | `export_note.py` (vault note → trials JSON), `fetch_labels.py` (DailyMed SPL → label text dump), `validate.py` (cross-reference check: every trial, tox_ref, drug and base id must resolve), `overrides/*.json`. |

## Ranking logic (v0.2)

1. **Gate** by histology (picks the regimen pool), setting, biomarker (BRCA / HRD / FRα / HER2 / PD-L1 CPS), stage, residual disease, PFI, prior-line count and prior bevacizumab, as each pivotal trial and label require.
2. **Tier** by OS evidence: 1 replicated OS · 2 single phase 3 OS · 3 subgroup / crossover-confounded OS · 4 PFS-only · 5 no efficacy difference (toxicity-chosen alternatives) · 6 no phase 3 · 7 do not use. Tier rules can move a regimen for a profile (e.g. TC + bev → tier 3 for stage IV; olaparib + bev → tier 7 for HRD-negative). **For the non-HGSC histotypes the tier is judged on histotype-level evidence**, so tiers 1–3 are empty by construction: tier 5 = randomised histotype (or stratified clear cell/mucinous) comparison with no difference (JGOG3017, JGOG-3016, iPocc, GOG-157 subgroups, ICON1/ACTION death counts); tier 6 = included-not-broken-out, single-arm, observational or biomarker-extrapolated (BRCA → PARPi, MMRd → pembrolizumab, HER2 → T-DXd, ER/PR → endocrine); tier 7 = negative histotype result (MOCCA, KEYNOTE-100 endometrioid 0/28), harm, or histotype excluded from the trial. Each card carries an `evidence_basis` badge and the ranking banner says how to read it.
3. **Exclude** on label contraindications and trial exclusions matched to the patient's baseline-risk flags; **demote** on the prior-therapy ledger (PFI <6 removes platinum re-challenge; prior PARPi turns PARPi maintenance into OReO re-challenge; same class stopped for toxicity excludes).
4. **Order within a tier** by net risk flags (cautions minus fits), then grade ≥3 rate ascending — any-cause where printed, otherwise the treatment-related figure (labelled as such; a lower bound), and rows with neither last.
5. Tiers 1–3 open by default; tiers 4–5 open automatically when 1–3 are empty for the profile, and tier 6 when 1–5 are empty (the histotype pools).
6. **End-of-chemotherapy status** (first-line and recurrence maintenance): surgery timing, residual after that surgery, imaging and CA-125 at the end of the platinum are translated into each maintenance trial's own category — PAOLA-1 NED/CR/PR, SOLO1 CR/PR, ATHENA-MONO "no disease after surgery" — with the matching subgroup HR (`data/response_schemes.json`). Adjuvant, first-line chemotherapy and neoadjuvant hide the fields that have no meaning there.
7. **Histotype-specific inputs**: endometrioid adds grade, molecular class (POLEmut / MMRd / NSMP / p53abn), WT1 and ER/PR — a WT1-positive tumour triggers a notice to switch to HGSC, and MMRd gates pembrolizumab; mucinous adds invasion pattern (expansile / infiltrative) and a primary-confirmed flag — unconfirmed primaries get a warning because most locally diagnosed mucinous ovarian cancers were metastatic on central review.

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

v0.3 ranks HGSC, clear cell, endometrioid and mucinous carcinoma, and malignant germ cell and sex cord–stromal tumours. HGSC OS claims are never extrapolated to the other histotypes: an all-histology trial that admitted a histotype without reporting it is shown with its trial-wide figures but labelled "included, not broken out", and biomarker-driven extrapolations (BRCA, MMRd, HER2, ER/PR) say so on the card. Germ cell tumours have no randomised ovarian trial: BEP sits in tier 2 on male germ cell RCTs, marked as extrapolated, and everything else ranks on ovarian single-arm, paediatric or registry data. Sex cord–stromal tumours have two small randomised trials without a survival difference (GOG-0264, ALIENOR), so their arms are tier 5. Low-grade serous carcinoma has no note yet; carcinosarcoma has only the uterine note.

Not clinical advice. Built for one gynecologic oncologist's own decision support; every recommendation carries its source so it can be checked.

## License

Code (`index.html`): MIT. Data files under `data/`: CC BY 4.0 (see `data/LICENSE`).

Live: https://medeconomy.github.io/ovca-decision-engine/ (GitHub Pages from `main`).
