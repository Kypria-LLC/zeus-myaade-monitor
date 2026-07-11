# TIAS 2902 Crosswalk — Monitor Governance Rule

**Status:** Active governance rule
**Effective:** 2026-07-11
**Scope:** MyAADE protocol monitoring + AADE-facing status classification
**Authority:** Verified crosswalk exhibit E-612 (private evidence package); companion erratum E-150 §12
**Primary text:** IRS-published US–Greece Income Tax Convention (TIAS 2902), signed Athens 20 Feb 1950

> Public repository. This document contains NO personal data (no AFM, no names, no addresses). It states article-numbering governance only.

---

## 1. Purpose

This rule binds the monitor's treaty-article labeling so that any AADE / MyAADE status event referencing the US–Greece tax treaty is classified against the **verified Roman-numeral crosswalk**, not deprecated shorthand.

## 2. Controlling numbering (Arts. XIV–XX)

| Article | Function | Monitor relevance |
| :--- | :--- | :--- |
| XIV | Foreign Tax Credit | Credit-claim status events |
| XV | Regulations | Procedural rule references |
| XVI | Elimination of Double Taxation | MAP / competent-authority track; DPO non-response flag |
| XVII | Taxpayer Claims | Home-state claim lodgement |
| XVIII | Exchange of Information | GDPR / exchange demand status; strict secrecy |
| XIX | Mutual Assistance | Collection-assistance events (see limitation) |
| XX | Limitation on Administrative Procedures | Public-policy refusal defense |

## 3. Art. XIX limitation (binding)

Collection assistance under Art. XIX is confined (Senate understanding 1951-09-17; Protocols 1 & 2, both integral to the Convention) to preventing treaty-unauthorized persons from enjoying exemptions/reduced rates. It does NOT authorize general collection on behalf of the other State. Monitor must not classify a general-collection event as Art. XIX assistance.

## 4. FCN separation (binding)

TIAS 2902 runs only to Art. XXI. Any "Art. XXVI" / "Art. 26" reference in a US–Greece context = Treaty of Friendship, Commerce and Navigation (FCN, TIAS 3057), NOT the tax convention. Monitor routes such references to the FCN lane.

## 5. Deprecated labels (retired)

The Arabic labels **Article 4 / 23 / 26 / 27** do not exist in TIAS 2902 and are retired. Monitor must not emit or accept these as tax-treaty article references.

## 6. Change control

This rule mirrors upstream E-612. Do not amend article mappings here without a corresponding upstream E-612 change. The machine-readable source is `data/tias2902-crosswalk.yaml` in the automation repo.
