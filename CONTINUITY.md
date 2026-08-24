# CONTINUITY.md

## Snapshot
- Goal: 2026-08-06 [USER]: Build an agentic medicine project that can be deployed on the personal website.
- Now: 2026-08-07 [TOOL]: Route is installed into `../personal_website` (uncommitted) as a six-lesson walkthrough plus sandbox, promoted to the homepage feature slot, and added to `/projects` as the first archive entry. Parity passes 112/112; browser QA passed against the real site directory.
- Next: 2026-08-07 [USER]: Review and decide whether to commit and push. The site working tree also carries an unrelated uncommitted CSS refactor that predates this work.
- Open questions: 2026-08-07 [ASSUMPTION]: Route name `/clinical-agent` is assistant-chosen and still UNCONFIRMED. The page h1 was renamed to the question form "When should a clinical AI agent refuse to act?" on the assistant's recommendation, which the user did not explicitly confirm.

## Invariants / Constraints
- 2026-08-06 [USER]: The artifact must be deployable on the personal website.
- 2026-08-06 [CODE]: Site domain is static, zero-tracking, and has no server-side model access (site decisions D002, D004, D013), so the demo is deterministic and offline; base agents are stand-ins, not LLMs.
- 2026-08-06 [CODE]: The browser engine must stay bit-faithful to the VMAG Python harness; `tools/parity_check.py` must pass at 112/112 before any deploy.
- 2026-08-06 [CODE]: No PHI. No patient names, MRNs, DOBs, or record UUIDs in `web/`. Only synthetic Synthea-derived clinical vocabulary.
- 2026-08-06 [CODE]: Page metrics are computed live by the shipped engine; never hard-code a figure.
- 2026-08-06 [CODE]: Keep code files under 300 lines (site invariant). Zero inline scripts and styles so the strict CSP needs no `unsafe-inline`.
- 2026-08-06 [CODE]: Keep tracking files ASCII; dates are `YYYY-MM-DD`.
- 2026-08-06 [CODE]: Safety enforcement lives outside the model; make no claim that depends on an agent choosing to comply.

## Decisions
- D001 ACTIVE 2026-08-06 [CODE]: Build the project as a public demo of the existing VMAG artifact rather than a new research track. Rationale: VMAG already positions itself as instantiation plus honest measurement; a second diverging artifact would add claims without adding evidence.
- D002 ACTIVE 2026-08-06 [CODE]: Port the guard to client-side ES modules instead of calling a model or a backend. Rationale: the site has no server-side model access, and a deterministic port is what makes the enforcement A/B honest and reproducible in a browser.
- D003 ACTIVE 2026-08-06 [CODE]: Ship pre-resolved record facts (observation lookups, thresholds, identity comparison) instead of the Synthea cohort. Rationale: the policy only branches on a handful of derived values, and a public page has no business serving anything chart-shaped.
- D004 ACTIVE 2026-08-06 [CODE]: Replace record identity with synthetic labels while preserving the match/mismatch outcome, and sanitize the one upstream task string that quotes a cohort patient's name. The export asserts the base agents' red-flag keyword set is unchanged, so the rewrite provably cannot alter a decision.
- D005 ACTIVE 2026-08-06 [CODE]: Verify the port with a full-grid parity harness (112 episodes) comparing action, ordered tool-call log, per-case scores, aggregate metrics, policy-only decisions, and policy error. Exclude rationale strings, which are display text and format differently across the two languages.
- D006 ACTIVE 2026-08-06 [CODE]: Reproduce Python's rounding in JS (`round3`, round-half-to-even) and round derived components before subtracting, matching `run_eval.py`. Rationale: raw fractions gave a 0.286 unsafe-rate spread where the published summary says 0.285, which would read as the two artifacts disagreeing.
- D007 ACTIVE 2026-08-06 [CODE]: Compute all page metrics live from the shipped engine rather than transcribing them. Rationale: removes any possibility of the page citing numbers the engine does not produce.
- D008 ACTIVE 2026-08-06 [CODE]: Split styles across `agent.css` / `agent-panel.css` / `agent-trace.css` and emit generated case data one case per line, to respect the site's 300-line cap.
- D009 ACTIVE 2026-08-06 [CODE]: Give the route its own CSP block with `script-src 'self'`, following the `/ultimate-tic-tac-toe` precedent, rather than relaxing the site-wide policy.
- D010 ACTIVE 2026-08-06 [CODE]: `install_to_site.py` patches only `_headers` and `sitemap.xml`, idempotently. It does not edit portfolio copy and does not commit or push; linking and publishing stay with the user.
- D012 ACTIVE 2026-08-07 [USER]: Promote the clinical agent to the homepage `project-feature` slot and demote Three-Body into the mini-projects strip. Rationale: the site asks for AI-healthcare internships but showed no healthcare project; VMAG's own README states its intended use is exactly this portfolio centerpiece.
- D013 ACTIVE 2026-08-07 [USER]: Keep the walkthrough and the sandbox on one route rather than splitting them. Rationale: the site's stated principle is a deliberately small page count, and the lesson only lands if the reader can try it in place.
- D014 ACTIVE 2026-08-07 [CODE]: Structure the page as six numbered lessons, each a contrast of two live runs differing in exactly one variable (the record or the guard, never both), with a required `shows` and `limits` note per lesson. Rationale: adapted from the reference teaching repo the user cited; chapter numbering is already this site's convention (`D007` upstream).
- D015 ACTIVE 2026-08-07 [CODE]: Define lessons as data in `ca-lessons.js` and render them, rather than hand-writing six HTML blocks. Rationale: keeps the page inside the 300-line cap and makes it impossible for a lesson's prose to describe an outcome the engine did not produce.
- D016 ACTIVE 2026-08-07 [CODE]: Generate the portfolio evidence image from the node harness output (`tools/make_feature_image.py`) instead of drawing or screenshotting it. Rationale: the homepage card and the Open Graph preview then cannot drift from the result they depict.
- D017 ACTIVE 2026-08-07 [CODE]: Surface attribution ("the research project is mine") and move the scope notice into the first screen. Rationale: without attribution a visitor reads the page as a demo of someone else's work; a page about clinical decisions should state its limits before its results, not after.
- D011 ACTIVE 2026-08-06 [CODE]: Distinguish the two unsafe modes in the UI (wrong resolution vs. record leak). Rationale: conflating them produced the contradictory verdict "resolved as Act where the safe resolution was Act" on the injection cases, where the action is right and the leak is the failure.

## State
### Done (recent)
- 2026-08-06 [CODE]: Wrote `tools/export_cases.py`; generated `web/assets/ca-cases.js` from the 14 VMAG cases with resolved policy facts and synthetic identity.
- 2026-08-06 [TOOL]: Confirmed the export leaks no Synthea-style names or UUIDs after adding task-text sanitization.
- 2026-08-06 [CODE]: Ported the action space, policy, four base agents, environment, guard, runtime, and scoring to eight ES modules.
- 2026-08-06 [CODE]: Built `tools/node_harness.mjs` and `tools/parity_check.py`.
- 2026-08-06 [TOOL]: Parity passes 112/112 episodes on action, ordered tool-call log, per-case scores, aggregate metrics, policy-only decisions, policy error, enforcement-delta rows, invariance, and generalization gap.
- 2026-08-06 [CODE]: Built `clinical-agent.html` plus three stylesheets and the render/app modules, with a live enforcement-delta table, three stat cards, and a caveat panel.
- 2026-08-06 [CODE]: Wrote `tools/install_to_site.py`; verified idempotency on a scratchpad copy of the site.
- 2026-08-06 [TOOL]: Browser QA swept all 112 case/agent/guard combinations: zero console messages, zero copy defects, 33 unsafe episodes with the guard off and 0 with it on (matching the Python per-agent counts 7+6+10+10).
- 2026-08-06 [CODE]: Fixed two copy defects found by that sweep: the contradictory injection verdict, and the ungrammatical "held back and escalate to clinician".
- 2026-08-06 [TOOL]: No horizontal overflow at 1265px, 820px, or 390px; exactly one `<script src>`, zero inline scripts, zero inline styles.

- 2026-08-07 [USER]: Reviewed the reference teaching repo `XiaoRed5/Agentic-RL-Most-Detailed-Intro` and chose to adopt its numbered-progression pattern, keeping this site's editorial voice and refusing its superlative framing.
- 2026-08-07 [CODE]: Rebuilt the route as six lessons plus a sandbox: added `ca-lessons.js` and `ca-lesson-view.js`, a headline result band, an attribution section, a fourth stat card for the verified port, a Next-experiment block, and deep links (`#case=...&agent=...&guard=...`).
- 2026-08-07 [TOOL]: Caught and fixed a copy/evidence mismatch in lesson 06: both chosen variants were guard-off and both came out unsafe, so the cards did not show the "depends on which agent you got" claim. Repointed to `escalation_opioid_001`, where the keyword filter defers correctly and the adversarial agent drafts the order.
- 2026-08-07 [CODE]: Split `ca-lesson-view.js` out of `ca-render.js`, which had reached exactly 300 lines.
- 2026-08-07 [CODE]: Added `tools/make_feature_image.py`; generated `clinical-agent-project.webp` (1280x720) from harness output, then fixed a clipped title and a cramped legend.
- 2026-08-07 [CODE]: Promoted the route to the homepage feature slot, moved Three-Body into the mini strip (now a balanced 2x2), changed "Four builds" to "Five builds", added the first `/projects` archive entry with My work / Honest limit / Next, and a fifth item to "What these projects demonstrate".
- 2026-08-07 [TOOL]: Installed into `../personal_website` (22 actions). All internal link targets across the three touched pages resolve.

- 2026-08-07 [USER]: Raised that the site's architecture felt wrong and asked for outside reference. Reddit was unreachable (Anthropic's crawler is disallowed there); the plain-HTML and SSG cases were read from other sources and both have merit.
- 2026-08-07 [TOOL]: Retracted an incorrect claim from that review. I had said `/clinical-agent` being absent from the nav was a live bug caused by markup duplication; checking every page showed no project route is in the nav (`/three-body` and `/ultimate-tic-tac-toe` are not either), so the route follows the site's convention and nothing was broken.
- 2026-08-07 [CODE]: Site architecture work, tiered. Tier 0: removed 34 dead CSS declarations (a superseded dark theme). Tier 1: replaced the site's 300-line file cap with a dead-declaration lint. Tier 2: made `site.json` the source of truth for `_headers` and `sitemap.xml`, collapsing 10 hand-copied CSP directive lists to one.
- 2026-08-07 [CODE]: Moved site tooling out of this project into `../personal_website/tools/`, and rewired `install_to_site.py` to register the route in `site.json` and call the site's generator instead of patching its outputs.

### Now
- 2026-08-07 [TOOL]: Complete and verified against the real site directory. Uncommitted.

### Next
- 2026-08-07 [USER]: Review and decide whether to commit and push.
- 2026-08-07 [USER]: Confirm or change the route name `/clinical-agent` and the question-form h1.
- 2026-08-07 [CODE]: Optional: update the homepage meta description, which still describes the site without mentioning clinical agent safety.
- 2026-08-07 [CODE]: Optional: the Chinese walkthrough repo discussed as a separate reach play; deliberately not started here.
- 2026-08-07 [CODE]: Optional: when VMAG gains a model-driven base agent, decide whether the page represents it or stays deterministic.

## Working set
- `web/clinical-agent.html`
- `web/agent.css`, `web/agent-panel.css`, `web/agent-trace.css`
- `web/assets/ca-actions.js`, `ca-policy.js`, `ca-agents.js`, `ca-runtime.js`
- `web/assets/ca-scoring.js`, `ca-render.js`, `ca-app.js`, `ca-cases.js` (generated)
- `tools/export_cases.py`, `tools/parity_check.py`, `tools/node_harness.mjs`, `tools/install_to_site.py`
- `README.md`, `AGENTS.md`

## Open questions
- 2026-08-06 [ASSUMPTION]: Route name and page title are assistant-chosen and UNCONFIRMED.
- 2026-08-06 [ASSUMPTION]: Whether the route belongs in the main nav, on `/projects`, or unlinked is UNCONFIRMED.

## Incidents
- Incident: Generated case data leaked cohort patient identity
  - Symptoms: 2026-08-06 [TOOL]: The first export contained `Teodoro374 Jose871 Schulist381` and a date of birth.
  - Evidence: 2026-08-06 [TOOL]: The string came from the upstream `clean_mrn_lookup_001` task text, which quotes the patient's name and DOB in the prompt, not from the record export path.
  - Mitigation: 2026-08-06 [CODE]: Added `_sanitize_task()` to rewrite record identity in task text, with an assertion that the base agents' red-flag keyword set is unchanged so no decision can shift.
  - Status: 2026-08-06 [TOOL]: RESOLVED; re-export shows no Synthea-style name tokens and no UUIDs, and parity still passes 112/112.

## Receipts
- 2026-08-06 [TOOL]: `python tools/export_cases.py` -> 14 cases, 6 tags, dev=9 test=5.
- 2026-08-06 [TOOL]: `python tools/parity_check.py` -> `PARITY OK -- 112 episodes`; policy error 0 on overall/dev/test; invariance unguarded spread 0.285 -> guarded 0.000.
- 2026-08-06 [TOOL]: Reproduced the published 0.285 unguarded spread only after matching `run_eval.py`'s double rounding; raw fractions gave 0.286.
- 2026-08-06 [TOOL]: `install_to_site.py` run twice against a scratchpad site copy: 17 actions then 5 skips and no duplicate `_headers` or sitemap entries.
- 2026-08-06 [TOOL]: Browser sweep of 112 combinations reported 33 unsafe with guard off, 0 with guard on, and 0 detected copy or placeholder defects.
- 2026-08-06 [TOOL]: File line counts all under the 300-line site cap; largest authored file is `agent-panel.css` at 221 lines, generated `ca-cases.js` at 23.
- 2026-08-07 [TOOL]: Post-rewrite parity re-run: `PARITY OK -- 112 episodes`. Browser sweep of 112 combinations again reported 33 unsafe with the guard off and 0 with it on, matching Python.
- 2026-08-07 [TOOL]: All six lessons render two non-identical contrast cards with both a `shows` and a `limits` note; the scope notice and attribution both sit above the sandbox and the results.
- 2026-08-07 [TOOL]: Deep links verified both directions: clicking a lesson's sandbox button sets the hash and the controls, and a cold load of `#case=wrong_patient_001&agent=keyword&guard=on` restores that exact state.
- 2026-08-07 [TOOL]: Served from the real site directory: no console messages, no failed network requests, one `<script src>`, zero inline styles. No horizontal overflow on `/`, `/projects`, or `/clinical-agent` at 1265px or 390px.
- 2026-08-07 [TOOL]: Homepage feature renders the generated 1280x720 image, a 3-column facts row, a 2x2 mini grid, and a 2-line h1 at 61px; `/projects` orders `clinical-agent` first with a working `#clinical-agent` anchor.
- 2026-08-07 [TOOL]: Backed up the pre-edit working-tree `index.html` and `projects.html` to the session scratchpad before editing, because both already carried uncommitted user changes.
