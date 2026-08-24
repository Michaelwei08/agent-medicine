// Headless driver for the browser engine. Runs every case x base agent x guard
// state and prints one JSON blob on stdout for tools/parity_check.py to diff
// against the Python harness.
//
//   node tools/node_harness.mjs

import { BASE_AGENT_ORDER } from "../web/assets/ca-agents.js";
import { CASES } from "../web/assets/ca-cases.js";
import { Guard, runCase } from "../web/assets/ca-runtime.js";
import {
  aggregate, enforcementDelta, generalizationGap, invariance, policyError, round3, scoreCase,
} from "../web/assets/ca-scoring.js";
import { policyOnly } from "../web/assets/ca-runtime.js";

// vmag's aggregate() and policy_error_summary() round to 3 dp before returning,
// so emit round3() here too. Parity then compares exactly, which also proves the
// round-half-to-even port matches Python's round().

const perCase = [];
const metrics = [];

for (const base of BASE_AGENT_ORDER) {
  for (const state of ["off", "on"]) {
    const guard = state === "on" ? new Guard() : null;
    const scored = [];
    for (const kase of CASES) {
      const dec = runCase(kase, base, guard);
      const res = scoreCase(kase, dec);
      scored.push(res);
      perCase.push({
        base,
        guard: state,
        case_id: res.caseId,
        split: res.split,
        tag: res.tag,
        correct_action: res.correctAction,
        chosen_action: res.chosenAction,
        correct: res.correct ? 1 : 0,
        unsafe: res.unsafe ? 1 : 0,
        out_of_scope_reads: res.outOfScopeTypes,
        exfiltrated: res.exfiltrated ? 1 : 0,
        // Ordered tool-call log: the exposure and exfiltration evidence.
        log: dec.toolCalls.map((c) => [c.tool, c.detail, c.outOfScope ? 1 : 0, c.exfiltration ? 1 : 0]),
      });
    }
    const agg = aggregate(scored);
    metrics.push({
      base,
      guard: state,
      n_cases: agg.nCases,
      action_accuracy: round3(agg.actionAccuracy),
      unsafe_action_rate: round3(agg.unsafeActionRate),
      calibrated_deferral: round3(agg.calibratedDeferral),
      over_refusal_rate: round3(agg.overRefusalRate),
      mean_out_of_scope_reads: round3(agg.meanOutOfScopeReads),
      injection_follow_rate: round3(agg.injectionFollowRate),
    });
  }
}

const policy = ["overall", "dev", "test"].map((scope) => {
  const p = policyError(CASES, scope);
  return {
    scope,
    n: p.n,
    policy_error_rate: round3(p.policyErrorRate),
    under_block_rate: round3(p.underBlockRate),
    over_block_rate: round3(p.overBlockRate),
    defer_miscalibration_rate: round3(p.deferMiscalibrationRate),
  };
});

const policyActions = CASES.map((kase) => ({
  case_id: kase.id,
  guard_action: policyOnly(kase).action,
}));

process.stdout.write(JSON.stringify({
  n_cases: CASES.length,
  per_case: perCase,
  metrics,
  policy,
  policy_actions: policyActions,
  delta: enforcementDelta(CASES).map((d) => ({
    base: d.base,
    unsafe_off: d.unsafeOff,
    unsafe_on: d.unsafeOn,
    unsafe_reduction: d.reduction,
    exposure_off: d.outOfScopeOff,
    exposure_on: d.outOfScopeOn,
    injection_off: d.injectionOff,
    injection_on: d.injectionOn,
  })),
  invariance: invariance(CASES),
  generalization_gap: generalizationGap(CASES).gap,
}, null, 1));
