"""Assert the browser engine and the Python VMAG harness decide identically.

The page on the public site is a port, and a port that silently drifts from the
harness it cites would be worse than no page at all -- it would show numbers the
research artifact does not actually produce. So this compares the two engines
over the full grid (14 cases x 4 base agents x guard off/on = 112 episodes) on
every observable that matters:

- the chosen action per episode
- the ordered tool-call log per episode (tool, detail, out-of-scope, exfiltration)
- the derived per-case scores (correct / unsafe / exposure / exfiltration)
- the aggregate metrics per (base, guard)
- the policy-only decision per case, and the policy-error / invariance summaries

Rationale strings are deliberately NOT compared: they are display text, and the
two languages format a missing numeric value differently ("None" vs "null").

Usage (from the agent_medicine project root):
    python tools/parity_check.py
Exit code 0 means the deployed engine is faithful to the harness.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from export_cases import V1_CASES  # noqa: E402  (the pinned set the page ships)

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
VMAG_ROOT = os.path.join(os.path.dirname(PROJECT_ROOT), "medical_agent_safety")

AS_OF = "2026-07-11"
TOL = 1e-9

METRIC_KEYS = (
    "n_cases", "action_accuracy", "unsafe_action_rate", "calibrated_deferral",
    "over_refusal_rate", "mean_out_of_scope_reads", "injection_follow_rate",
)
POLICY_KEYS = (
    "n", "policy_error_rate", "under_block_rate", "over_block_rate",
    "defer_miscalibration_rate",
)


def run_python_side() -> dict:
    sys.path.insert(0, VMAG_ROOT)
    cwd = os.getcwd()
    os.chdir(VMAG_ROOT)
    try:
        from vmag.agents import BASE_AGENTS
        from vmag.benchmark import load_cases
        from vmag.fhir_store import FhirStore
        from vmag.guard import Guard
        from vmag.policy import evaluate_policy
        from vmag.environment import Environment
        from vmag.runtime import run_case
        from vmag.scoring import (aggregate, policy_error_summary, policy_only,
                                 score_case)

        store = FhirStore()
        # Compare against the SAME pinned set the page ships. Using every case the
        # benchmark happens to contain would make parity fail the moment VMAG grows
        # a case, and the failure would look like a port bug rather than what it is:
        # the two artifacts covering different case sets on purpose.
        by_id = {c.id: c for c in load_cases()}
        cases = [by_id[cid] for cid in V1_CASES]
        guard = Guard()
        bases = ["keyword", "mock_model", "naive", "worst_case"]
        assert set(bases) == set(BASE_AGENTS), "base-agent roster drifted"

        per_case, metrics = [], []
        for base in bases:
            for state, g in (("off", None), ("on", guard)):
                scored = []
                for case in cases:
                    dec = run_case(store, case, base, g, AS_OF)
                    res = score_case(case, dec)
                    scored.append(res)
                    per_case.append({
                        "base": base, "guard": state, "case_id": res.case_id,
                        "split": case.split, "tag": res.tag,
                        "correct_action": res.correct_action,
                        "chosen_action": res.chosen_action,
                        "correct": int(res.correct), "unsafe": int(res.unsafe),
                        "out_of_scope_reads": res.out_of_scope_types,
                        "exfiltrated": int(res.exfiltrated),
                        "log": [[c.tool, c.detail, int(c.out_of_scope),
                                 int(c.exfiltration)] for c in dec.tool_calls],
                    })
                agg = aggregate(scored)
                agg.update({"base": base, "guard": state})
                metrics.append(agg)

        pol = policy_only(store, cases, AS_OF)
        policy = []
        for scope, subset in (("overall", pol),
                              ("dev", [r for r in pol if r.split == "dev"]),
                              ("test", [r for r in pol if r.split == "test"])):
            row = policy_error_summary(subset)
            row["scope"] = scope
            policy.append(row)

        policy_actions = []
        for c in cases:
            action, _ = evaluate_policy(Environment(store, c, as_of=AS_OF))
            policy_actions.append({"case_id": c.id, "guard_action": action})

        # Reproduce run_eval.py's derived reporting layer: it reads the ALREADY
        # ROUNDED rates out of aggregate() and rounds again after subtracting.
        by_state = {(m["base"], m["guard"]): m for m in metrics}
        delta = []
        for base in bases:
            off, on = by_state[(base, "off")], by_state[(base, "on")]
            delta.append({
                "base": base,
                "unsafe_off": off["unsafe_action_rate"],
                "unsafe_on": on["unsafe_action_rate"],
                "unsafe_reduction": _delta(off["unsafe_action_rate"], on["unsafe_action_rate"]),
                "exposure_off": off["mean_out_of_scope_reads"],
                "exposure_on": on["mean_out_of_scope_reads"],
                "injection_off": off["injection_follow_rate"],
                "injection_on": on["injection_follow_rate"],
            })

        guarded = [d["unsafe_on"] for d in delta if d["unsafe_on"] is not None]
        unguarded = [d["unsafe_off"] for d in delta if d["unsafe_off"] is not None]
        inv = {
            "guardedSpread": round(max(guarded) - min(guarded), 3) if guarded else None,
            "unguardedSpread": round(max(unguarded) - min(unguarded), 3) if unguarded else None,
            "guardedFloor": max(guarded) if guarded else None,
        }
        by_scope = {r["scope"]: r for r in policy}
        gen_gap = _delta(by_scope["test"]["policy_error_rate"],
                         by_scope["dev"]["policy_error_rate"])

        return {"n_cases": len(cases), "per_case": per_case, "metrics": metrics,
                "policy": policy, "policy_actions": policy_actions,
                "delta": delta, "invariance": inv, "generalization_gap": gen_gap}
    finally:
        os.chdir(cwd)


def _delta(a, b):
    """vmag/run_eval.py's _delta."""
    if a is None or b is None:
        return None
    return round(a - b, 3)


def run_js_side() -> dict:
    proc = subprocess.run(
        ["node", os.path.join("tools", "node_harness.mjs")],
        cwd=PROJECT_ROOT, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(f"node harness failed:\n{proc.stderr.strip()}")
    return json.loads(proc.stdout)


def close(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return abs(float(a) - float(b)) <= TOL


def compare(py: dict, js: dict) -> list[str]:
    errors: list[str] = []

    if py["n_cases"] != js["n_cases"]:
        errors.append(f"case count: python={py['n_cases']} js={js['n_cases']}")

    # ---- per-episode: action, derived scores, and the full tool-call log ----
    py_cases = {(r["base"], r["guard"], r["case_id"]): r for r in py["per_case"]}
    js_cases = {(r["base"], r["guard"], r["case_id"]): r for r in js["per_case"]}
    missing = set(py_cases) ^ set(js_cases)
    if missing:
        errors.append(f"episode grid mismatch, {len(missing)} key(s), e.g. {sorted(missing)[:3]}")

    for key in sorted(set(py_cases) & set(js_cases)):
        p, j = py_cases[key], js_cases[key]
        label = "/".join(key)
        for field in ("chosen_action", "correct", "unsafe", "out_of_scope_reads",
                      "exfiltrated", "correct_action", "tag", "split"):
            if p[field] != j[field]:
                errors.append(f"{label}: {field} python={p[field]!r} js={j[field]!r}")
        if [list(x) for x in p["log"]] != [list(x) for x in j["log"]]:
            errors.append(f"{label}: tool-call log differs\n    python={p['log']}\n    js    ={j['log']}")

    # ---- aggregate metrics per (base, guard) ----
    py_metrics = {(r["base"], r["guard"]): r for r in py["metrics"]}
    js_metrics = {(r["base"], r["guard"]): r for r in js["metrics"]}
    for key in sorted(set(py_metrics) & set(js_metrics)):
        p, j = py_metrics[key], js_metrics[key]
        for field in METRIC_KEYS:
            if not close(p.get(field), j.get(field)):
                errors.append(f"{'/'.join(key)}: {field} python={p.get(field)} js={j.get(field)}")

    # ---- policy-only decisions and policy-error accounting ----
    py_pa = {r["case_id"]: r["guard_action"] for r in py["policy_actions"]}
    js_pa = {r["case_id"]: r["guard_action"] for r in js["policy_actions"]}
    for case_id in sorted(set(py_pa) & set(js_pa)):
        if py_pa[case_id] != js_pa[case_id]:
            errors.append(f"policy-only {case_id}: python={py_pa[case_id]} js={js_pa[case_id]}")

    py_pol = {r["scope"]: r for r in py["policy"]}
    js_pol = {r["scope"]: r for r in js["policy"]}
    for scope in sorted(set(py_pol) & set(js_pol)):
        for field in POLICY_KEYS:
            if not close(py_pol[scope].get(field), js_pol[scope].get(field)):
                errors.append(f"policy[{scope}]: {field} "
                              f"python={py_pol[scope].get(field)} js={js_pol[scope].get(field)}")

    # ---- the derived numbers the page actually headlines ----
    py_delta = {r["base"]: r for r in py["delta"]}
    js_delta = {r["base"]: r for r in js["delta"]}
    delta_fields = ("unsafe_off", "unsafe_on", "unsafe_reduction", "exposure_off",
                    "exposure_on", "injection_off", "injection_on")
    for base in sorted(set(py_delta) & set(js_delta)):
        for field in delta_fields:
            if not close(py_delta[base].get(field), js_delta[base].get(field)):
                errors.append(f"delta[{base}]: {field} "
                              f"python={py_delta[base].get(field)} js={js_delta[base].get(field)}")

    for field in ("guardedSpread", "unguardedSpread", "guardedFloor"):
        if not close(py["invariance"].get(field), js["invariance"].get(field)):
            errors.append(f"invariance: {field} "
                          f"python={py['invariance'].get(field)} js={js['invariance'].get(field)}")

    if not close(py["generalization_gap"], js["generalization_gap"]):
        errors.append(f"generalization_gap: python={py['generalization_gap']} "
                      f"js={js['generalization_gap']}")

    return errors


def main() -> None:
    print("running python harness (vmag over Synthea)...")
    py = run_python_side()
    print("running js harness (browser engine under node)...")
    js = run_js_side()

    episodes = len(py["per_case"])
    errors = compare(py, js)

    print()
    if errors:
        print(f"PARITY FAILED -- {len(errors)} mismatch(es) across {episodes} episodes:")
        for err in errors[:40]:
            print(f"  - {err}")
        if len(errors) > 40:
            print(f"  ... and {len(errors) - 40} more")
        raise SystemExit(1)

    print(f"PARITY OK -- {episodes} episodes "
          f"({py['n_cases']} cases x 4 base agents x guard off/on)")
    print("  identical: chosen action, tool-call log, per-case scores,")
    print("             aggregate metrics, policy-only decisions, policy error")
    for row in js["policy"]:
        print(f"  policy[{row['scope']:7}] n={row['n']:2} err={row['policy_error_rate']}")
    inv = js["invariance"]
    print(f"  invariance: unguarded spread {inv['unguardedSpread']:.3f} -> "
          f"guarded {inv['guardedSpread']:.3f} (floor {inv['guardedFloor']:.3f})")


if __name__ == "__main__":
    main()
