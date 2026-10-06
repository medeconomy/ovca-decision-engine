# Handoff — 2026-10-06

Moved from a cloud Claude session to Claude Code. This file is a dated snapshot; `CLAUDE.md` holds the standing rules.

## State

- `main` at the handoff commit; v0.3 (`776a5c2`) added germ cell and sex cord–stromal tumours. `validate.py` → 0 errors; `tools/smoke.js` → OK (14 scenarios, 6 browser pages, phone width 390 px).
- **v0.3 is not live yet.** The GitHub Pages runs for `776a5c2` and the empty re-trigger `018ddbd` failed with "The job was not acquired by Runner of type hosted even after multiple attempts"; a re-run started 2026-10-06 04:20 UTC sat queued. githubstatus.com showed Actions and Pages operational, so this may be account-level. The handoff commit itself starts a new Pages run.
  - Check: `gh run list -L 3` and `curl -s -o /dev/null -w '%{http_code}' https://medeconomy.github.io/ovca-decision-engine/data/regimens_scst.json` (200 = live).
  - If it fails again the same way: look at github.com → Settings → Billing and plans (spending limit / hold) and the repo's Settings → Actions → General (Actions enabled). Do not keep pushing empty commits.

## Waiting on Jay (review of v0.3 judgement calls)

1. **GCT BEP = tier 2 on male data.** Male GCT RCTs lost survival when bleomycin (EP ×3) or cisplatin (carboplatin–etoposide–bleomycin) was dropped; card says "male RCT extrapolated". EP ×3, high-dose PEB, PVB, VAC are tier 7.
2. **Surveillance vs adjuvant chemotherapy** (both histologies) is tier 6 vs tier 6; order is set by subtype, age group and staging (e.g. YST child → surveillance first; dysgerminoma ≥40 with incomplete staging → BEP first).
3. **SCST:** GOG-0264 and ALIENOR arms tier 5 (no survival difference, toxicity decides); repeat cytoreduction tier 6, preferred if resectable, excluded if not.
4. ~~**SCST endocrine** tier 6, gated on ER/PR positive (unknown → excluded with the reason shown).~~ **Decided 2026-10-06:** unknown → caution "test ER/PR first", stays in tier (SPEC 19); applied to the OEC endocrine records too.
5. **SCST has no neoadjuvant setting** in the ranker (evidence stays on browser tab 4).
6. ~~**BEP etoposide schedule**~~ **Decided 2026-10-06:** the NTUH template matches the MD Anderson 3-day BEP (Gershenson 1990) except q3w instead of q4w; the GCT BEP cards now say so (etoposide 300 vs 500 mg/m² per cycle). The vault chemoregimen note had cited Dimopoulos 2004 (different doses); corrected to Gershenson 1990.

## Validation (2026-10-06)

Jay started validating with real cases; a stage IIB HGSC case produced decision 20 (stage gates on 1L maintenance). The unpushed `50d1b3c` (SCST ER/PR unknown → caution; NTUH BEP card source) was pushed with it.

## Not done / possible next steps (none requested yet)

- Low-grade serous carcinoma: no vault note yet. Carcinosarcoma: only the uterine note (`EMCA_Carcinosarcoma_Algorithm_v1.2`). Both show "Not ranked yet".
- PRIMA NEJM supplementary appendix: not fetched (403 to scripts). Jay could download it by hand if wanted; the protocol and SAP already cover the CA-125 and residual rules used.
- SCST level filter in the browser shows a single chip ("Histotype-only trial") because the export classed the rest as unspecified; could be refined via `tools/overrides/scst.json`.
- README "Ranking logic" section is headed v0.2 and does not yet describe the GCT/SCST inputs (SPEC decisions 16–19 do).

## Recent decision history (details in SPEC.md)

- 13–15: response to platinum is setting-dependent; end-of-chemo status entered as surgery timing + residual + imaging + CA-125; NED ≠ CR in RECIST/GCIG, CA-125 decides the label; PRIMA/PRIME/NOVA require CA-125 normal or >90% fall stable ≥7 days, PRIMA/NOVA also residual ≤2 cm (shown as a caution, no size field), PRIMA excludes stage III R0 after primary surgery.
- 16–19: GCT/SCST pools, settings and inputs; GCT tier 2 extrapolated; surveillance ordering; SCST endocrine gating.
