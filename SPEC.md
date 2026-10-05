# OVCA Decision Engine — Data Schema & Build Spec v0.1

Source: Obsidian vault `20_Area/Medicine/GO_MCP/OVCA_Decision_Engine_Spec_v0.1.md` (created 2026-10-05). Copied verbatim; the **Decisions taken** section at the end records what was settled on 2026-10-05 and supersedes §7.

Goal: turn `OVCA_HGSC_Algorithm_v1.2` (interactive HTML) from an evidence browser into a
patient-driven regimen ranker. Input = patient profile; output = ranked regimen list with
exclusions explained.

Decision principle (unchanged): OS benefit first → evidence strength qualifier → PFS-only tier
collapsed below → adverse-effect profile decides among survivors → prior-therapy ledger removes
or demotes drugs already used.

> **Hard rules for the build session**
> 1. Every HR / median in §5 is written from memory and MUST be verified against the vault
>    summary or the PubMed abstract before it is written to the vault.
> 2. Label dose-modification tables (§4) MUST be read from DailyMed (USPI) or EMA SmPC,
>    never reconstructed from memory.
> 3. Unreported fields stay `"not_reported"`. No estimation.

---

## 1. Patient profile (input)

```yaml
patient:
  histology: HGSC | LGSC | OCCC | endometrioid | mucinous | carcinosarcoma | other
  grade: high | low
  stage_figo2014: I | II | III | IV          # IIIC/IVA/IVB if known
  setting: adjuvant | first_line_chemo | first_line_maintenance |
           platinum_sensitive_recurrence | platinum_resistant_recurrence | neoadjuvant
  residual_disease: R0 | R1 | R2 | unknown   # for adjuvant / 1L
  pfi_months: <number> | null               # from last platinum
  markers:
    brca: germline_path | somatic_path | wild_type | unknown
    hrd: positive | negative | unknown       # record assay + cutoff
    fra: high | medium | low | negative | unknown   # PS2+ ≥75% = high (VENTANA FOLR1)
    her2: 3+ | 2+ | 1+ | 0 | unknown
    pdl1_cps: <number> | unknown
    mmr: dMMR | pMMR | unknown
  baseline_risk:                             # feeds §4 exclusion rules
    neuropathy_grade: 0-2
    ild_or_pneumonitis: true | false
    ocular_disease: true | false
    gi_fistula_or_obstruction_risk: true | false
    uncontrolled_htn_or_proteinuria: true | false
    cardiac_lvef_low: true | false
    hepatic_impairment: none | mild | moderate | severe
    renal_crcl: <mL/min>
    cytopenia_baseline: true | false
    ecog: 0-4
  prior_therapy: []                          # see §2
```

Histology gates the evidence set: Table 3B / 3A / maintenance trials are HGSC-dominant;
OCCC, LGSC, mucinous get their own (smaller) pool and must not inherit HGSC OS claims.

---

## 2. Prior-therapy ledger

One row per line. "Used before" is not the tag — the outcome is.

```yaml
prior_therapy:
  - line: 1L
    regimen_id: TC_q3w
    drug_classes: [platinum, taxane]
    start: 2016-05
    end: 2016-08
    cycles: 6
    best_response: CR | PR | SD | PD | biochemical_only
    outcome_tag: progressed_on | progressed_after | stopped_toxicity | completed_maintenance | ongoing
    pfi_months: 16                           # only for platinum-containing lines
    limiting_toxicity: null | "<CTCAE term + grade>"
```

`outcome_tag` semantics:
- `progressed_on` → drug class demoted to re-challenge tier; needs §5 data to surface.
- `progressed_after` → for platinum, re-eligibility is driven by `pfi_months`; for others, demote
  one tier and show re-challenge evidence.
- `stopped_toxicity` → the specific class is excluded unless the limiting toxicity has resolved to
  ≤ grade 1 and the label permits re-start (store label rule in §4).
- `completed_maintenance` (PARPi/bev) → maintenance-after-maintenance needs §5 evidence
  (OReO, MITO-16B); otherwise collapsed.

---

## 3. Regimen record (one per regimen × setting)

```yaml
regimen:
  id: MIRV_PR_FRa_high
  name: Mirvetuximab soravtansine
  setting: platinum_resistant_recurrence
  histology_scope: [HGSC]
  drug_classes: [ADC_FRa]
  biomarker_gate: { fra: [high] }
  pivotal_trial: MIRASOL
  pmid: <PMID>
  comparator: investigator-choice chemo

  efficacy:
    os:
      benefit: positive | negative | immature | not_reported
      hr: <verify>
      ci95: [<verify>, <verify>]
      median_months: { exp: <verify>, ctrl: <verify> }
      evidence_strength: replicated | single_phase3 | prespecified_subgroup |
                         crossover_confounded | phase2 | retrospective
    pfs:
      hr: <verify>
      ci95: [<verify>, <verify>]
      median_months: { exp: <verify>, ctrl: <verify> }
    orr: { exp: <verify>, ctrl: <verify> }

  toxicity:                                   # from tox.json extraction
    grade3plus_any_pct: <n> | not_reported
    signature_ae: ["blurred vision", "keratopathy", "neuropathy"]
    discontinuation_pct: <n> | not_reported
    dose_reduction_pct: <n> | not_reported
    source: "GO_summaries/<file>.md"

  label_rules:                                # see §4
    permanent_discontinue_triggers:
      - { ae: "ocular", grade: ">=3 or grade 2 not resolving", source: "USPI <date> §2.x" }
      - { ae: "pneumonitis", grade: ">=3", source: "USPI <date> §2.x" }
    hold_and_reduce_triggers:
      - { ae: "ocular", grade: 2, action: "hold until ≤G1, reduce 1 level" }
    baseline_contraindications: [ocular_disease]   # maps to patient.baseline_risk

  rechallenge:                                # see §5
    after_progression_on_same_class: { evidence: null }
```

Ranking tiers derived from `efficacy.os.benefit` × `evidence_strength`:
1. OS positive, replicated
2. OS positive, single phase 3
3. OS positive, subgroup / crossover-confounded
4. PFS-only (collapsed; HR + absolute gain shown)
5. No phase 3 (phase 2 / retrospective)

---

## 4. Adverse-effect layer — source is the drug label, not CTCAE

CTCAE v5 only grades severity (1–5). Hold / reduce / discontinue thresholds come from:
- FDA USPI §2 "Dosage Modifications for Adverse Reactions" (primary; DailyMed)
- EMA SmPC §4.2 (cross-check)
- Trial protocol dose-modification tables where stored in `GO_summaries/`

Extract per drug (not per regimen — reuse across regimens):

| drug | AE | grade threshold | action (hold / reduce / discontinue) | re-start allowed? | source + label date |
|---|---|---|---|---|---|

Minimum set to extract first (covers all Table 2B/3A/3B regimens):
carboplatin, cisplatin, paclitaxel, PLD, gemcitabine, topotecan, bevacizumab,
olaparib, niraparib, rucaparib, mirvetuximab, relacorilant + nab-paclitaxel,
pembrolizumab, trastuzumab deruxtecan.

Exclusion rule: if `patient.baseline_risk[x]` is true and `x` ∈
`regimen.label_rules.baseline_contraindications` → regimen hidden with reason shown.

Demotion rule: if the patient's ledger has `stopped_toxicity` for an AE that is a
`permanent_discontinue_trigger` of the candidate → hidden.

---

## 5. Re-challenge evidence (per drug class) — ALL VALUES TO VERIFY

Store only what has a trial behind it; `null` is a valid value and must be displayed as
"no re-challenge data", never inferred.

```yaml
rechallenge:
  platinum:
    driver: pfi_months
    rules:
      - { pfi: ">=12", evidence: "ICON4 / CALYPSO / GOG-0213 populations", endpoint: OS }
      - { pfi: "6-12", evidence: "partially platinum-sensitive subgroups (CALYPSO, OCEANS)", endpoint: PFS }
      - { pfi: "<6",  evidence: "excluded from re-challenge trials", endpoint: null }
  parpi_after_parpi:
    evidence: OReO (ENGOT-ov38)
    endpoint: PFS only
    hr: "~0.57 (BRCA) / ~0.43 (non-BRCA)  # verify"
    absolute_gain_months: "~1–2  # verify"
    os: not_shown
  bevacizumab_beyond_progression:
    evidence: MITO-16B / MaNGO OV2B
    endpoint: "PFS only (HR ~0.51  # verify)"
    os: not_shown
  taxane:
    evidence: retrospective only
    endpoint: null
  pld_gemcitabine_topotecan:
    evidence: null
  immunotherapy_after_io:
    evidence: null
```

(Verified values, with corrections to this section, are in `data/rechallenge.json` → `verification_report`.)

---

## 6. Build tasks (for the dispatch session)

1. Read `20_Area/Medicine/GO_MCP/GO_summaries/` and finish `tox.json` (grade ≥3 any,
   signature AE, discontinuation %, dose-reduction %) for all trials in Tables 2A/2B/3A/3B/4.
   Mark unreported fields `"not_reported"`.
2. Build `labels.json` from USPI §2 for the 14 drugs in §4 (fetch via DailyMed; store label
   date in `source`).
3. Build `rechallenge.json` from §5, every HR verified and `pmid` filled.
4. Add `patient` form to the HTML (histology → setting → markers → baseline risk →
   prior-therapy ledger rows).
5. Implement ranking: gate by histology + setting + biomarker → apply §4 exclusions →
   apply §2 ledger demotions → sort by tier → within tier, sort by `grade3plus_any_pct`
   ascending → render cards with "why excluded / why demoted" footnotes.
6. Keep the existing evidence-browser tabs as a second view; the ranker is view 1.
7. Save data files beside the HTML; write version note `OVCA_Decision_Engine_v0.1` to
   `10_Projects/Gynecologic Oncology_MCP/`.

---

## 7. Open decisions (ask Jay before building)

- Non-HGSC histologies: build a separate reduced pool, or show "HGSC-extrapolated" with a
  warning badge?
- Should the PFS-only tier be visible by default in the ranker, or behind a toggle?
- Lower-dose weekly fractionated regimens (NTUH P-HDFL-style, weekly TC 60/AUC2): include
  as a distinct class with NTUH toxicity data, or keep out of the ranker until data is in?

---

## Decisions taken (2026-10-05)

1. **Histology:** v0.1 gates to HGSC only. Other histologies show a notice pointing to their own algorithm note; no "HGSC-extrapolated" rows.
2. **PFS-only tier:** collapsed by default. It auto-expands when the patient's profile leaves tiers 1–3 empty (e.g. HR-proficient first-line maintenance), because then it is the whole decision.
3. **Weekly fractionated regimens:** MITO-7's weekly carboplatin AUC2 + paclitaxel 60 is included as its own class (randomised data). NTUH-specific schedules stay out until local toxicity data exist.
4. **Within-tier ranking (amends task 5):** rank first by the patient's own baseline-risk flags against each regimen's signature AEs and label contraindications (hits demote), then by `grade3plus_any_pct` ascending. `not_reported` rows are shown as such and are not sorted to the bottom on that basis alone.
5. **Derived G≥3 sums:** where a source reports worst-grade-per-patient G3 and G4 (and G5) separately, their sum is exact, not an estimate, and may be stored with `derived_sum: true`.

---

## Decisions taken (2026-10-05, histotype expansion → v0.2)

6. **Non-HGSC histologies** (answers open decision 1): a separate reduced pool per histotype (`data/regimens_<hist>.json`), not HGSC-extrapolated rows. Records inherit a regimen's toxicity reference and label rules from the HGSC record via `base` (toxicity is a property of the regimen, not the histology) but carry their own tier, OS reading and `evidence_basis`.
7. **Histotype tiers**: tiers 1–3 are empty by construction for OCCC, OEC and MOC, because no regimen has shown an OS benefit in its own histotype. Tier 5 = randomised histotype comparison (or stratified clear cell/mucinous subgroup, or the ICON1/ACTION death counts for observation vs chemotherapy) with no efficacy difference. Tier 6 = included-not-broken-out, single-arm, observational, or biomarker extrapolation. Tier 7 = negative histotype result, harm, or histotype excluded from the pivotal trial.
8. **Evidence-browser badges on histotype pages** are the histotype-level reading (`out`: os / pfs / signal / ns / harm / single / obs / no_subgroup / excluded / pending), derived from the note's "Clear cell / OEC / MOC data" column plus per-trial overrides in `tools/overrides/`. Trial-wide HRs are displayed but never relabelled as histotype results.
9. **Within-tier toxicity sort** (amends decision 4): any-cause G≥3 where printed; otherwise the treatment-related G≥3 figure, labelled as treatment-related (a lower bound for any-cause); rows with neither sort last.
10. **Histotype-specific inputs**: OEC — grade, molecular class, WT1, ER/PR (WT1-positive → notice to switch to HGSC; MMRd → pembrolizumab gate; ER/PR → endocrine gate). MOC — invasion pattern, primary-confirmed flag (warning until confirmed). Molecular class is a prognostic modifier and a biomarker gate, not a treatment selector: no OEC trial has used it.
11. **Labels** for the new agents were fetched from DailyMed SPL by `tools/fetch_labels.py` (§2 and §4 only). Sintilimab has no FDA label and is recorded as such; INOVA's record carries bevacizumab's rules only.
12. **Not yet in the ranker**: germ cell, sex cord–stromal (own notes; different setting structure), low-grade serous (no note), carcinosarcoma (uterine note only).
13. **Response to platinum is setting-dependent.** Adjuvant, first-line chemotherapy and neoadjuvant have no prior platinum: the response, PFI and prior-lines fields are hidden and set to null / 0. The field shows only where maintenance follows the platinum just completed (first-line maintenance; platinum-sensitive recurrence). Options NED (no measurable disease after complete resection) / CR / PR / SD / PD. Each maintenance record carries `gate.response_in` and a verbatim `response_source` from the vault extract: PAOLA-1 lists NED explicitly; DUO-O and KEYLYNK-001 also admitted SD; SOLO1, PRIMA, ATHENA-MONO and the recurrence PARPi trials say CR/PR and do not state how NED was classified — NED is accepted as clinical CR and the card says so. PD on the platinum just completed is platinum-refractory and excludes every maintenance record. PFI is counted from the last platinum dose, adjuvant included; adjuvant counts as one prior line. PRIMA's exclusion of stage III R0 after primary debulking is a caution (the form does not yet record primary vs interval surgery).
14. **End-of-chemotherapy status as three inputs (2026-10-06; supersedes the single response field in 13).** NED is not CR in RECIST 1.1 (only patients with measurable baseline disease are assessable for response; no NED category) or in GCIG CA-125 criteria (response needs a pretreatment CA-125 ≥2× ULN). The trials disagree: PAOLA-1 and ATHENA-MONO made NED its own category; SOLO1 folded it into CR (normal CA-125) or PR (CA-125 > ULN); PRIMA, PRIME, NOVA give no definition in the main text. So the form records **surgery timing** (primary / interval / none), **residual after that surgery**, **imaging** and **CA-125** at the end of the platinum just completed, and the ranker translates them into each trial's own category with the matching subgroup HR (`data/response_schemes.json`, definitions verbatim from the full texts). Exclusions follow each trial's wording (stable disease: excluded by SOLO1, PRIMA, NOVA/NORA; caution for PAOLA-1, ATHENA-MONO, SOLO2/Study 19, ARIEL3 where a GCIG CA-125 response or the PR wording could admit it; CA-125 > ULN: excluded by ARIEL3, caution for Study 19). PAOLA-1 PR (ITT HR 0.86, 0.63–1.19) carries a caution. Surgery timing makes PRIMA's high-risk definition exact (stage III R0 after primary debulking is outside PRIMA; PRIME admitted it). Secondary cytoreduction is not recorded.
15. **Protocol-verified CA-125 entry rule (2026-10-05).** The PRIMA and NOVA protocols (ClinicalTrials.gov uploads) and the PRIME protocol/eMethods (Europe PMC) were read in full; all are filed in GO_PDFs. None defines NED; all use physician/investigator-assessed CR/PR, and each requires "CA-125 in the normal range or CA-125 decrease by more than 90% … stable for at least 7 days". The CA-125 input therefore has four values: ≤ ULN / > ULN but fell >90% and stable ≥7 days / > ULN with a smaller fall / unknown. A smaller fall excludes PRIMA, PRIME and NOVA. No disease on imaging with CA-125 still above ULN is PR in PRIMA and NOVA (their RECIST appendix: raised markers "must normalize for a patient to be considered in complete clinical response"). PRIMA ("residual disease following chemotherapy must be 2 cm or less") and NOVA ("no measurable lesion > 2 cm") carry a caution when residual disease is present; size is not recorded.
