# AGENTS.md

Operating guidance for AI coding sessions in this project.

## Goal

Ship and maintain a public, browser-only demonstration of the VMAG clinical-agent
guard on the personal website (`cpwei.qzz.io`). The demo must be faithful to the
research artifact it cites, and honest about what it does not show.

## Nature

A presentation layer over someone else's measurements -- specifically over
`../medical_agent_safety` (VMAG). This project contributes a verified port, a
web-safe data export, and a deployment path. It contributes no new claims. Do not
let it grow into a second, diverging research artifact.

## Read first

1. `CONTINUITY.md` in this project -- append-only source of truth.
2. `../medical_agent_safety/README.md` and `CLAUDE.md` -- the upstream positioning,
   especially "What is and isn't novel".
3. `../personal_website/CONTINUITY.md` -- the site's invariants and decisions
   (`D004`, `D013` govern scripts and CSP on that domain).

## Invariants

- **Parity is not optional.** Any change to `web/assets/ca-*.js` (except
  `ca-app.js` and `ca-render.js`, which are presentation only) must be followed by
  `python tools/parity_check.py` passing at 112/112. If the Python harness changes
  upstream, re-run the export and the parity check before touching the page.
- **`ca-cases.js` is generated.** Never hand-edit it. Change
  `tools/export_cases.py` and regenerate.
- **No PHI, no chart dumps, no record identifiers.** Patient names, MRNs, DOBs,
  and UUIDs must not appear in `web/`. The export's sanitizer and its red-flag
  assertion exist to enforce this; do not weaken them.
- **Enforcement lives outside the model.** Never introduce a safety claim that
  depends on an agent choosing to comply.
- **No hard-coded metrics in the page.** Numbers are computed live by the shipped
  engine. Hard-coding a figure reintroduces the drift the parity check prevents.
- **Honest caveats stay visible.** The caveat panel on the page is load-bearing,
  not decoration. Zero policy error means self-consistency, not generalization.
- **Site constraints.** Code files under 300 lines. Zero inline scripts and zero
  inline styles, so the strict CSP needs no `unsafe-inline`. No network calls, so
  `connect-src 'none'` holds. Keep tracking files ASCII; dates are `YYYY-MM-DD`.
- **Deployment is the user's call.** `install_to_site.py` writes into the site
  working tree but never commits or pushes, and never edits portfolio copy.

## Verification

```bash
python tools/export_cases.py      # only when upstream cases/data change
python tools/parity_check.py      # must print PARITY OK -- 112 episodes
python tools/install_to_site.py --dry-run
```

Browser QA, against a copy of the site rather than the real one:

- sweep all 14 x 4 x 2 combinations; expect zero console errors, and unsafe
  episodes to fall to zero with the guard on
- check no horizontal overflow at 1265px, 820px, 390px
- confirm exactly one `<script src>` and no inline scripts or styles

`.claude/launch.json` serves a scratchpad copy of the site for this purpose. Point
`install_to_site.py --target` at that copy, not at `../personal_website`, while
iterating.

## Deliverables

- `web/` -- the deployable route (page, three stylesheets, eight modules)
- `tools/` -- export, parity harness, node driver, site installer
- `README.md` -- what it is, how to verify, how to deploy
- `CONTINUITY.md` -- decisions and state

## Out of scope

- New metrics, new cases, or new policy rules. Those belong upstream in VMAG.
- Any server-side or model-backed runtime on this domain (site decision `D002`).
- Editing the portfolio's editorial copy or publishing to production.
