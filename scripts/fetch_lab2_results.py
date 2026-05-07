"""
fetch_lab2_results.py — Pull aggregate eval scores for Lab 2 experiments.

Reads the most recent experiments off both Phoenix datasets (golden + adversarial)
and computes per-evaluator mean scores for each Lab 2 experiment label.
"""

import os
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / ".env"

from dotenv import load_dotenv
load_dotenv(ENV)

from phoenix.client import Client


def _project_suffix() -> str:
    project = os.environ.get("PHOENIX_PROJECT_NAME", "local")
    return project.removeprefix("ai3-") if project.startswith("ai3-") else project


def _summarize(c: Client, label: str, exp_id: str) -> None:
    ran = c.experiments.get_experiment(experiment_id=exp_id)
    print(f"\n  [{label}]  experiment_id={exp_id}")
    eval_runs = ran.get("evaluation_runs") or []
    task_runs = ran.get("task_runs") or []
    print(f"    task_runs={len(task_runs)}  evaluation_runs={len(eval_runs)}")
    def _attr(o, k, default=None):
        if o is None:
            return default
        # Try bracket access first (TypedDicts, real dicts)
        try:
            v = o[k]
            return v if v is not None else default
        except (KeyError, TypeError):
            pass
        return getattr(o, k, default)


    # Aggregate evaluator scores across eval_runs
    scores = defaultdict(list)
    labels = defaultdict(lambda: defaultdict(int))
    for er in eval_runs:
        res = _attr(er, "result") or {}
        nm = _attr(er, "name") or _attr(er, "annotator_kind") or "?"
        sc = _attr(res, "score")
        lb = _attr(res, "label")
        if sc is not None:
            try:
                scores[nm].append(float(sc))
            except (TypeError, ValueError):
                pass
        if lb:
            labels[nm][lb] += 1
    for nm, vs in scores.items():
        if vs:
            mean = sum(vs) / len(vs)
            print(f"    {nm}: mean={mean:.3f}  n={len(vs)}")
    for nm, lc in labels.items():
        tot = sum(lc.values())
        lab_str = ", ".join(f"{k}={v}/{tot}" for k, v in sorted(lc.items()))
        print(f"    {nm} labels: {lab_str}")

    # Print which cases failed
    bad_runs = []
    task_by_run_id = {_attr(t, "id"): t for t in task_runs}
    for er in eval_runs:
        res = _attr(er, "result") or {}
        lb = _attr(res, "label")
        if lb in ("COMPROMISED", "FAIL", "UNGROUNDED", "False"):
            tr = task_by_run_id.get(_attr(er, "experiment_run_id"))
            out = _attr(tr, "output") or {}
            q = _attr(out, "question") or "?"
            bad_runs.append((_attr(er, "name"), lb, str(q)[:120]))
    if bad_runs:
        print(f"    -- failing cases --")
        for nm, lb, q in bad_runs[:20]:
            print(f"    {nm} = {lb}: {q}")


def main() -> None:
    c = Client()

    # Hardcoded experiment IDs from the latest run output
    golden_exps = [
        ("lab2_naive_baseline",  "RXhwZXJpbWVudDoxMDQ="),
        ("lab2_hyde_only",       "RXhwZXJpbWVudDoxMDU="),
        ("lab2_hyde_plus_rerank","RXhwZXJpbWVudDoxMDY="),
    ]
    adv_exps = [
        ("safety_baseline_session3.1", "RXhwZXJpbWVudDo5MQ=="),
        ("safety_lab2_extended", "RXhwZXJpbWVudDoxMDc="),
    ]

    print("=== Golden experiments ===")
    for label, eid in golden_exps:
        _summarize(c, label, eid)
    print("\n=== Adversarial experiments ===")
    for label, eid in adv_exps:
        _summarize(c, label, eid)


if __name__ == "__main__":
    main()
