# Clinical Agent Sandbox

A deployable, browser-only demonstration of the VMAG thesis: a clinical AI agent
fails dangerously not only by being wrong, but by **acting** when the correct
behavior was to gather a missing lab, abstain, or escalate to a clinician -- and
the fix belongs outside the model.

The route is a **six-lesson walkthrough followed by a sandbox**. Each lesson names
two runs that differ in exactly one thing -- the record, or the guard, never both
-- so the reader can attribute the change, and each carries a required "what this
shows" and "what it does not show". Below the lessons, a visitor can run any of
the 14 cases against any of four base agents (benign to adversarial) with
enforcement on or off, and read the episode step by step: what the agent
proposed, what the guard allowed, which records were touched, whether an
instruction hidden in the chart was obeyed, and how it scored.

Everything runs client-side. No network calls, no storage, no model in the loop.

## What this is and is not

This is a **public demo of existing work**, not new research. The benchmark,
policy, guard, and metrics are ported from
[`../medical_agent_safety`](../medical_agent_safety) (VMAG), which is itself
positioned as an instantiation and honest measurement rather than a new
architecture -- see that project's `README.md` and `docs/RELATED_WORK.md`.

What this project adds is narrow and specific:

- an **exactly faithful** browser port of the guard, verified against the Python
  harness over all 112 episodes (see Parity below);
- a **web-safe case export** that ships the facts the policy branches on without
  shipping anything resembling a chart;
- a deployment path onto a static, zero-tracking site with a strict CSP.

The numbers on the page are computed live by the shipped engine rather than
hard-coded, so the page cannot silently drift from the artifact it cites.

Read the page's own caveat panel before quoting any figure. In particular: the
cases and the policy were written by the same author, so the zero policy error
and zero generalization gap show self-consistency, **not** generalization.

## Layout

```
web/
  clinical-agent.html     the route
  agent.css               page styles (hero, results, tables)
  agent-lesson.css        scope notice, headline band, the six lessons
  agent-panel.css         sandbox component (controls, stage)
  agent-trace.css         episode trace (steps, chips)
  assets/
    ca-actions.js         action space          <- vmag/actions.py
    ca-policy.js          data-driven policy    <- vmag/policy.py
    ca-agents.js          four base agents      <- vmag/agents.py
    ca-runtime.js         environment + guard   <- vmag/environment.py, guard.py, runtime.py
    ca-scoring.js         metrics               <- vmag/scoring.py, run_eval.py
    ca-lessons.js         the six lessons, as data
    ca-lesson-view.js     lesson rendering
    ca-render.js          trace and table rendering
    ca-app.js             control wiring, deep links
    ca-cases.js           GENERATED case data -- do not edit by hand
    clinical-agent-project.webp   GENERATED evidence image
tools/
  export_cases.py         derive ca-cases.js from the VMAG benchmark
  parity_check.py         assert the JS engine matches the Python harness
  node_harness.mjs        run the JS engine headlessly for the parity check
  make_feature_image.py   render the evidence image from harness output
  install_to_site.py      install the route into ../personal_website
```

Site-side tooling (CSS lint, config generation, local preview) lives in the site
repo at `../personal_website/tools/`, not here -- the site has to lint, generate
and preview itself after a clean clone.

## Where it appears on the site

- `/clinical-agent` -- the walkthrough and sandbox
- `/` -- the homepage `project-feature` slot (Three-Body moved to the mini strip)
- `/projects#clinical-agent` -- the first archive entry

The lessons are defined as data in `ca-lessons.js` and rendered, rather than
written as six HTML blocks. That keeps the page under the line cap and, more
importantly, makes it impossible for a lesson's prose to describe an outcome the
engine did not actually produce. Adding or repointing a lesson is a data edit.

## Parity

The deployed engine is a port, and a port that drifts from the harness it cites
would be worse than no page at all. `tools/parity_check.py` runs the full grid --
14 cases x 4 base agents x guard off/on = 112 episodes -- through both engines and
requires identical:

- chosen action per episode
- ordered tool-call log per episode (tool, detail, out-of-scope, exfiltration)
- per-case scores (correct / unsafe / exposure / exfiltration)
- aggregate metrics per (base, guard)
- policy-only decision per case, plus policy error, invariance, and the
  generalization gap

Rationale strings are excluded on purpose: they are display text, and Python and
JavaScript format a missing numeric value differently.

```bash
python tools/parity_check.py
```

Exit code 0 means the page is faithful to the harness. Rounding is included in
the comparison: `round3()` in `ca-scoring.js` reproduces Python's round-half-to-
even, and the derived rows round their components before subtracting, matching
`run_eval.py`. Without that the page would report a 0.286 unsafe-rate spread
where the published table says 0.285.

## Regenerating case data

`web/assets/ca-cases.js` is generated. It carries the resolved observation
lookups, thresholds, and identity comparisons the policy branches on, plus small
display samples of clinical vocabulary. It does **not** carry patient names,
MRNs, dates of birth, or record UUIDs; identity is replaced with synthetic labels
(`SYN-01`...) chosen so the match/mismatch outcome is preserved. One upstream case
quotes the cohort patient's name in its prompt text; the export rewrites it and
asserts the base agents' red-flag keyword set is unchanged, so the rewrite cannot
alter any decision.

```bash
python tools/export_cases.py
python tools/parity_check.py    # always re-verify after regenerating
```

Requires the sibling VMAG checkout at `../medical_agent_safety` with its Synthea
data present.

## Deploying

```bash
python tools/install_to_site.py --dry-run
python tools/install_to_site.py
```

This copies the route's files, registers it in the site's `site.json` with
`"scripts": true`, and then calls the site's own `tools/gen_config.py` to
regenerate `_headers` and `sitemap.xml`. It does not edit those files directly --
the site generates them, and two writers would eventually disagree. Every step is
idempotent. It deliberately does not link the route from `index.html` or
`projects.html` -- where this sits in the portfolio narrative is an editorial call
-- and it does not commit or push.

Local preview, from the site repo (`python -m http.server` will 404 on every
clean route and will not apply the CSP):

```bash
python tools/serve_site.py
```

## Constraints this project inherits

- **Static and offline.** The site is a zero-tracking static deployment; a
  server-side model call is not available on this domain, so the demo is
  deterministic rather than LLM-driven. The base agents are stand-ins, and
  `ca-agents.js` marks the seam where a real model-driven agent would return a
  plan.
- **Enforcement outside the model.** No safety claim here depends on a model
  choosing to comply -- that is what the flat guarded column demonstrates.
- **No PHI, ever.** Synthetic (Synthea, Apache-2.0) records only, with
  identifiers stripped.
- **Code files under 300 lines**, matching the site's invariant. The generated
  case file is one case per line for the same reason.

## Status

Built 2026-08-06, rebuilt as the six-lesson walkthrough and installed 2026-08-07.
Parity passes at 112/112 episodes. Served from the real site directory, the route
was exercised across all 112 case/agent/guard combinations with no console
messages and no failed requests, deep links restore state on a cold load, and
`/`, `/projects`, and `/clinical-agent` have no horizontal overflow at 1265px or
390px.

Installed into `../personal_website` but **not committed**. That working tree also
carries an unrelated uncommitted CSS refactor that predates this work, so review
the diff before committing. See `CONTINUITY.md`.
