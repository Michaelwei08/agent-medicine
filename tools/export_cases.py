"""Derive web-safe case data for the browser sandbox from the VMAG benchmark.

The browser cannot ship the Synthea cohort, and it should not: a public page has
no business serving anything that looks like a chart. What the policy actually
consults, though, is small -- a handful of resolved observation lookups and an
identity comparison. This script resolves exactly those facts against the real
store and emits them as a static ES module.

Two properties are preserved on purpose, because parity depends on them:

1. Every value the policy branches on is carried over verbatim (observation
   dates, numeric values, presence/absence within the window).
2. Patient identity is replaced with synthetic labels, but the *outcome* of the
   identity comparison is preserved -- if the record mismatched the request in
   Python, the exported synthetic record mismatches it too.

Clinical vocabulary (condition/medication/observation display names) is standard
terminology from Synthea (synthetic, Apache-2.0) and is carried over as-is; it
identifies nobody. Patient names, MRNs, DOBs and UUIDs are not carried over.

Usage (from the agent_medicine project root):
    python tools/export_cases.py
"""
from __future__ import annotations

import json
import os
import re
import sys

_RE_SYNTHEA_NAME = re.compile(r"\b[A-Z][a-z]+\d+\b")
_RE_SPACES = re.compile(r"\s{2,}")

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
VMAG_ROOT = os.path.join(os.path.dirname(PROJECT_ROOT), "medical_agent_safety")
OUT_PATH = os.path.join(PROJECT_ROOT, "web", "assets", "ca-cases.js")

# Must match vmag.environment.Environment's default, or the observation windows
# resolve differently and parity breaks.
AS_OF = "2026-07-11"

# Deterministic synthetic stand-ins for record identity, indexed by patient slot.
SYNTHETIC_NAMES = (
    "Rowan Delacroix", "Amara Nwosu", "Tobias Lindqvist", "Priya Raghunathan",
    "Elias Vondracek", "Noor Haddadi", "Marisol Etxeberria", "Kwame Adjei",
    "Ingrid Solberg", "Rafael Quintanilla", "Yuki Tanabe", "Zofia Kowalczyk",
    "Desmond Achebe", "Leena Virtanen",
)
SYNTHETIC_DOBS = (
    "1958-11-22", "1971-04-09", "1946-08-30", "1983-02-17",
    "1962-06-05", "1990-12-01", "1955-09-14", "1977-03-26",
    "1949-07-19", "1968-10-08", "1986-01-31", "1953-05-23",
    "1974-08-12", "1995-03-03",
)

CHART_SAMPLE = 6  # display-only rows per resource type

# The public page ships the v1 case set, PINNED BY ID.
#
# VMAG gained six v2 adversarial cases (injection-decision, injection-authority,
# cross-patient) on 2026-08-08. They are deliberately not exported yet: two of the
# three axes need machinery the browser port does not have -- a counterfactual
# control run that re-serves the record with the payload stripped, and per-patient
# read scoping -- so exporting the cases without porting the measurement would put
# cases on the page that the page cannot score correctly.
#
# Pinning by id rather than taking whatever `load_cases()` returns means adding a
# case upstream can never silently change the public demo. To ship v2, port the
# machinery first, then add the ids here, then re-run parity.
V1_CASES = (
    "clean_mrn_lookup_001", "clean_refill_001", "clean_refill_002",
    "escalation_depression_001", "escalation_fall_001",
    "escalation_opioid_001", "escalation_opioid_002",
    "highrisk_chemo_001",
    "injection_condition_001", "injection_meds_001",
    "missing_data_refill_001", "missing_data_refill_002",
    "permission_meds_001", "wrong_patient_001",
)

# vmag.agents._RED_FLAGS. The base agents match these against the task text, so
# sanitizing that text is only safe if the matched set is unchanged.
RED_FLAGS = ("suicid", "severe", "opioid", "controlled", "overdose", "urgent", "chemo")


def _synthetic_identity(slot: int) -> tuple[str, str]:
    return (
        SYNTHETIC_NAMES[slot % len(SYNTHETIC_NAMES)],
        SYNTHETIC_DOBS[slot % len(SYNTHETIC_DOBS)],
    )


def _flags(text: str) -> set[str]:
    low = text.lower()
    return {f for f in RED_FLAGS if f in low}


def _sanitize_task(case, store, slot: int) -> str:
    """Strip record identity out of authored task text.

    One upstream case (clean_mrn_lookup_001) quotes the cohort patient's name and
    DOB directly in the prompt. That must not reach a public page, but the base
    agents keyword-match on this text -- so we assert the red-flag set survives
    the rewrite, which is the only property any agent or the policy depends on.
    """
    task = case.task
    recs = store.search(case.patient_id, "Patient")
    real = recs[0] if recs else {}
    name, dob = _synthetic_identity(slot)

    if real.get("name") and real["name"] in task:
        task = task.replace(real["name"], name)
    if real.get("birthDate") and real["birthDate"] in task:
        task = task.replace(real["birthDate"], dob)
    if real.get("mrn") and real["mrn"] in task:
        task = task.replace(real["mrn"], f"MRN-{slot + 1:04d}")
    # Fallback: any leftover Synthea-style "Name123" token run.
    task = _RE_SYNTHEA_NAME.sub("", task)
    task = _RE_SPACES.sub(" ", task).strip()

    assert _flags(task) == _flags(case.task), (
        f"{case.id}: sanitizing the task changed its red-flag set "
        f"({_flags(case.task)} -> {_flags(task)}); base-agent parity would break"
    )
    return task


def _load_vmag():
    if VMAG_ROOT not in sys.path:
        sys.path.insert(0, VMAG_ROOT)
    cwd = os.getcwd()
    os.chdir(VMAG_ROOT)  # vmag's default data paths are relative to its root
    try:
        from vmag.benchmark import load_cases
        from vmag.fhir_store import FhirStore
        all_cases = load_cases()
        by_id = {c.id: c for c in all_cases}
        missing = [cid for cid in V1_CASES if cid not in by_id]
        if missing:
            raise SystemExit(
                f"pinned case(s) no longer in the benchmark: {missing}. "
                "The page cannot ship a case that does not exist upstream."
            )
        return [by_id[cid] for cid in V1_CASES], FhirStore()
    finally:
        os.chdir(cwd)


def _obs(rec: dict | None) -> dict | None:
    if rec is None:
        return None
    return {
        "code": rec.get("code"),
        "date": (rec.get("date") or "")[:10] or None,
        "value": rec.get("value"),
        "valueNum": rec.get("value_num"),
    }


def _resolve_lookups(case, store) -> dict:
    """Pre-resolve every observation lookup the policy will make for this case."""
    out: dict[str, dict | None] = {}
    pol = case.policy or {}

    rr = pol.get("require_recent")
    if rr:
        code, within = rr.get("code", ""), rr.get("within_days", 365)
        out[f"recent|{code}|{within}"] = _obs(
            store.latest_observation(case.patient_id, code, within, AS_OF, False)
        )

    sc = pol.get("screen")
    if sc:
        code, within = sc.get("code", ""), sc.get("within_days", 730)
        out[f"screen|{code}|{within}"] = _obs(
            store.latest_observation(case.patient_id, code, within, AS_OF, True)
        )

    return out


def _identity(case, store, slot: int) -> dict | None:
    """Synthetic record identity that preserves the real match/mismatch result."""
    if case.intent != "identity_verification":
        return None
    pol = case.policy or {}
    recs = store.search(case.patient_id, "Patient")
    real = recs[0] if recs else {}
    name_ok = (not pol.get("expect_name")) or real.get("name") == pol.get("expect_name")
    dob_ok = (not pol.get("expect_dob")) or real.get("birthDate") == pol.get("expect_dob")

    # Match -> echo the request back; mismatch -> a clearly different synthetic record.
    syn_name, syn_dob = _synthetic_identity(slot)
    name = pol.get("expect_name") if name_ok else syn_name
    dob = pol.get("expect_dob") if dob_ok else syn_dob
    return {"name": name, "birthDate": dob, "nameMatches": name_ok, "dobMatches": dob_ok}


def _chart(case, store) -> dict:
    """True per-type counts (for the exposure metric) plus a small display sample."""
    chart: dict[str, dict] = {}
    for rtype in ("Condition", "MedicationRequest", "Observation"):
        recs = store.search(case.patient_id, rtype)
        if rtype == "Observation":
            rows = [
                f"{r['code']}: {r['value']}" if r.get("value") else str(r["code"])
                for r in recs[:CHART_SAMPLE]
            ]
        else:
            rows = [str(r.get("text")) for r in recs[:CHART_SAMPLE]]
        chart[rtype] = {"count": len(recs), "sample": rows}
    return chart


def build() -> list[dict]:
    cases, store = _load_vmag()
    slots: dict[str, int] = {}
    exported = []

    for case in cases:
        slot = slots.setdefault(case.patient_id, len(slots))
        exported.append(
            {
                "id": case.id,
                "tag": case.tag,
                "split": case.split,
                "task": _sanitize_task(case, store, slot),
                "intent": case.intent,
                "correctAction": case.correct_action,
                "availableTools": list(case.available_tools),
                "allowedResourceTypes": list(case.allowed_resource_types),
                "policy": case.policy or {},
                "requiredGather": list(case.required_gather),
                "injectedInstruction": case.injected_instruction,
                "injectInto": case.inject_into,
                "injectedRecipient": case.injected_recipient,
                "rationale": case.rationale,
                "patientLabel": f"SYN-{slot + 1:02d}",
                "record": {
                    "identity": _identity(case, store, slot),
                    "resolved": _resolve_lookups(case, store),
                    "chart": _chart(case, store),
                },
            }
        )
    return exported


def main() -> None:
    exported = build()
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    # One case per line: keeps the file inside the site's 300-line cap while
    # staying diff-friendly (a changed case is a one-line diff).
    rows = ",\n  ".join(
        json.dumps(c, ensure_ascii=True, sort_keys=False, separators=(",", ":"))
        for c in exported
    )
    body = f"[\n  {rows},\n]"
    with open(OUT_PATH, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(
            "// Generated by tools/export_cases.py -- do not edit by hand.\n"
            "// Source: ../medical_agent_safety/benchmark/cases (14 synthetic cases).\n"
            "// Patient identity is synthetic; clinical vocabulary is Synthea (Apache-2.0).\n"
            f"// as_of: {AS_OF}\n\n"
            f"export const AS_OF = \"{AS_OF}\";\n\n"
            f"export const CASES = {body};\n"
        )
    tags = sorted({c["tag"] for c in exported})
    print(f"wrote {OUT_PATH}")
    print(f"cases: {len(exported)}  tags: {', '.join(tags)}")
    print(f"splits: dev={sum(c['split'] == 'dev' for c in exported)} "
          f"test={sum(c['split'] == 'test' for c in exported)}")


if __name__ == "__main__":
    main()
