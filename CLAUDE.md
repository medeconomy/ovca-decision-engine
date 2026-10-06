# OVCA Decision Engine — project notes for Claude Code

Static single-page app for Jay (吳晉睿, gynecologic oncologist, NTUH): an **evidence browser** of ovarian cancer trials and a **regimen ranker** driven by a patient profile. Data comes from Jay's Obsidian GO_MCP algorithm notes. Live at https://medeconomy.github.io/ovca-decision-engine/ (GitHub Pages from `main`, repo `medeconomy/ovca-decision-engine`, public).

Decision principle: **overall survival first, then toxicity against the patient's own risks, then the prior-therapy ledger.**

Read `HANDOFF.md` for current state and open items, `SPEC.md` for the schema and the numbered decisions (1–19), `README.md` for the layout and ranking logic.

## Working with Jay

- **Discuss design before building.** For anything that changes what the ranker shows or how a tier is assigned, propose first and wait for his answer. Small fixes and data corrections can go straight in.
- **Never write the label "一句話"** in anything (he finds it AI-sounding). A one-sentence lead is fine without the label.
- Commit as `Jay Wu <cjwu00@gmail.com>`. Push to `main` deploys.
- Not clinical advice; every number on screen must be traceable (see Provenance).

## Architecture

- `index.html` — the whole app (HTML + CSS + one `<script>`), no build step. Loads `data/*.json` with `fetch()`, so serve over HTTP, not `file://`.
- `HIST` holds one entry per histology: `{trials, regimens, meta, generic}`. `HIST_ORDER` / `HIST_LABEL` list them: HGSC, OCCC, endometrioid, mucinous, GCT, SCST. `NONEPI` = {GCT, SCST}.
- Ranker pipeline: `readPatient` → `gateOK` → `effectiveTier` → `assess` (risk_rules / prefer_when / ledger_rules / exclude_default / caution_default / response_scheme) → `sortKey` (tier, cautions − fits, G≥3) → `rank` renders tiers.
- `syncSettings(h)` swaps the Setting options per histology: epithelial share the default list; GCT/SCST use `_meta.settings` from their regimen file. Call it before reading or setting `f_setting`.
- `classifyResponse(key, p)` maps surgery timing + residual + end-of-chemo imaging + CA-125 onto each maintenance trial's own NED/CR/PR category (`data/response_schemes.json`). Epithelial only.
- Histotype regimen records may carry `base` (an HGSC regimen id) and inherit drugs, tox_ref, pfs, risk_rules, ledger_rules, response_scheme from it (`inheritBase`).
- Tiers: 1 OS replicated · 2 OS single phase 3 · 3 OS subgroup/confounded · 4 PFS only · 5 no difference (toxicity decides) · 6 no phase 3 · 7 do not use. Histotype pools are judged on **histotype-level** evidence, so tiers 1–3 are empty there — except GCT BEP (tier 2, `evidence_basis: male_rct_extrapolated`). `_meta.tiers` in a pool overrides the tier labels.

## Commands

```
python3 -m http.server 8765           # serve (any static server)
python3 tools/validate.py             # cross-reference check: must print "errors: 0"
npm install && node tools/smoke.js    # headless scenarios + browser tabs + phone width; exit 1 on any page error
python3 tools/export_note.py <note.md> <hist> data/trials_<hist>.json --overrides tools/overrides/<hist>.json
python3 tools/fetch_labels.py <outdir> [keys...]   # DailyMed SPL §2/§4 text dump; rules are then written by hand
```

Run `validate.py` and `smoke.js` before every commit that touches `data/` or `index.html`. The smoke output lists every card per scenario, so a ranking change shows up as a diff — say which changes are intended.

## Data files

| File | Content |
|---|---|
| `data/trials.json` | HGSC evidence page (67 rows, 95 refs) |
| `data/trials_{occc,oec,moc,gct,scst}.json` | Exports of the histotype notes (`export_note.py`) |
| `data/regimens.json` | 43 HGSC regimen × setting records |
| `data/regimens_{occc,oec,moc,gct,scst}.json` | 38 / 42 / 32 / 21 / 19 records |
| `data/tox.json`, `tox_histotypes.json` | Per-trial grade ≥3 and signature AEs |
| `data/labels.json`, `labels_histotypes.json` | DailyMed label rules per drug (setid + date recorded) |
| `data/response_schemes.json` | Verbatim NED/CR/PR definitions and subgroup HRs per maintenance trial |
| `data/rechallenge.json` | Re-challenge evidence per drug class |

## Provenance (non-negotiable)

1. Every HR / median / rate traces to a vault extract, a PubMed record or a protocol/SAP PDF; nothing from memory.
2. Label rules come from DailyMed SPL text, never reconstructed.
3. `"not_reported"` means the source does not report it. No estimation.
4. An all-histology trial that did not report a histotype is "included, not broken out" — its HR is never shown as a histotype result.

## Source material (Jay's Mac)

- Obsidian vault `AIObsi`; notes in `20_Area/Medicine/GO_MCP/GO_Algorithm/`: `OVCA_HGSC_Algorithm_v1.2`, `OVCA_ClearCell_Algorithm_v1.1`, `OVCA_Endometrioid_Algorithm_v1.1`, `OVCA_Mucinous_Algorithm_v1.1`, `OVCA_GermCell_Algorithm_v1.1`, `OVCA_SexCordStromal_Algorithm_v1.0`. Structured extracts in `20_Area/Medicine/GO_MCP/GO_summaries/`.
- Trial PDFs in the `GO_PDFs` folder, including the PRIMA, NOVA and PRIME protocols/SAPs (`2019_PRIMA_Protocol_NCT02655016.pdf`, `2016_NOVA_Protocol_NCT01847274.pdf`, `2023_Li_PRIME_*`).
- Fetching papers: do not bypass bot detection, CAPTCHAs or paywalls, and never use pirate mirrors. NEJM supplements return 403 to scripts — use ClinicalTrials.gov document uploads or Europe PMC, or ask Jay to download manually.

## Gotchas

- Nested template literals inside `${}` have broken the script before (`molTables`); prefer string concatenation there. Syntax check: extract the `<script>` block and run `node --check`.
- `.fld[hidden]` must stay `display:none!important`, because `.fld[data-hist].show` sets `display:flex`.
- Form fields with `data-hist="..."` show only for those histologies; epithelial biomarkers carry the epithelial list.
- The PFI <6-month platinum rule in `assess` is epithelial; GCT/SCST set `pfi_months` to null.
