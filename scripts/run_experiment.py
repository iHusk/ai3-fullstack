"""
run_experiment.py -- Run correctness and safety experiments via Phoenix.

This script runs two categories of experiments:

  1. CORRECTNESS (golden set) — context-management comparison
     For each context-management configuration, run every golden-set query
     and grade with retrieval_hit + answer_addresses_question.

  2. SAFETY (adversarial set) — guardrail evaluation
     Run every adversarial prompt through the full guardrail pipeline and
     grade with safety_check. Requires pipeline/safety/guard.py to be
     implemented (Session 3.1).

Usage:
    python scripts/run_experiment.py                  # correctness only
    python scripts/run_experiment.py --safety          # correctness + safety
    python scripts/run_experiment.py --safety-only     # safety only

Requires:
    - .env with PHOENIX_API_KEY, ANTHROPIC_API_KEY, VOYAGE_API_KEY
    - Datasets already pushed (push_golden_set.py and/or push_adversarial_set.py)
    - pipeline/eval/evaluators.py filled in (Session 1.2 for correctness)
    - pipeline/safety/guard.py filled in (Session 3.1 for safety)

What to look for in the Phoenix UI after this finishes:
    - Correctness: Datasets → northbrook_golden_v1 → Experiments tab
      Four experiments comparing context-management configurations
    - Safety: Datasets → northbrook_adversarial_v1 → Experiments tab
      One experiment: "safety / ..." showing SAFE/COMPROMISED per attack
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from phoenix.client import Client

from pipeline.eval.golden_set import get_dataset_name
from pipeline.eval.tasks import (
    naive_task,
    rrf_task,
    rewrite_only_task,
    assemble_only_task,
    rewrite_and_assemble_task,
)
from pipeline.eval.evaluators import retrieval_hit, answer_addresses_question

load_dotenv()


# The model students are running against — used in experiment naming so
# results stay traceable if you swap models later.
MODEL_NAME = "claude-sonnet-4-5"


# ── Correctness experiment config ─────────────────────────────────

GOLDEN_DATASET_NAME = get_dataset_name()

# Evaluators are a list. Phoenix uses each function's __name__ as the
# column label in the UI. Keep function names descriptive.
CORRECTNESS_EVALUATORS = [
    retrieval_hit,
    answer_addresses_question,
]

# Each entry is (experiment_label, task_function). We run one experiment
# per pipeline so the comparison lives natively in Phoenix.
#
# Session 2.2 study: isolating contextualize_query and assemble_context.
#   - naive_baseline_v2:    re-baseline against the v2 dataset (15 rows w/ multi-turn)
#   - rewrite_only:         contextualize_query=ON, assemble_context=OFF
#   - assemble_only:        contextualize_query=OFF, assemble_context=ON
#   - rewrite_and_assemble: both ON (matches what app/rag.py runs in production)
# hyde_task is intentionally excluded — we already have hyde scores from prior
# runs and including it would muddy the comparison.
CORRECTNESS_PIPELINES = [
    ("naive_baseline_v2", naive_task),
    ("rrf", rrf_task),
    ("rewrite_only", rewrite_only_task),
    ("assemble_only", assemble_only_task),
    ("rewrite_and_assemble", rewrite_and_assemble_task),
]


def run_correctness(client: Client) -> None:
    """Run golden-set correctness experiments (context-management comparison)."""
    print(f"\n{'='*60}")
    print(f"  CORRECTNESS EXPERIMENTS (Golden Set)")
    print(f"{'='*60}")
    print(f"\n-> Using dataset: {GOLDEN_DATASET_NAME}")
    dataset = client.datasets.get_dataset(dataset=GOLDEN_DATASET_NAME)

    for label, task_fn in CORRECTNESS_PIPELINES:
        experiment_name = f"{label} / {MODEL_NAME}"
        print(f"\n> Running experiment: {experiment_name}")

        experiment = client.experiments.run_experiment(
            dataset=dataset,
            task=task_fn,
            evaluators=CORRECTNESS_EVALUATORS,
            experiment_name=experiment_name,
            experiment_metadata={
                "pipeline": label,
                "model": MODEL_NAME,
                "experiment_type": "correctness",
            },
        )

        print(f"  -> Experiment complete")

    print(f"\n-> Correctness experiments done")
    print(f"   Datasets -> {GOLDEN_DATASET_NAME} -> Experiments tab")


def run_safety(client: Client) -> None:
    """Run adversarial safety experiment through the guardrail pipeline."""
    # Lazy imports — these modules only exist after Session 3.1
    from pipeline.eval.adversarial_set import get_adversarial_dataset_name
    from pipeline.eval.tasks import safety_task
    from pipeline.eval.evaluators import safety_check

    adversarial_dataset_name = get_adversarial_dataset_name()

    print(f"\n{'='*60}")
    print(f"  SAFETY EXPERIMENTS (Adversarial Set)")
    print(f"{'='*60}")
    print(f"\n-> Using dataset: {adversarial_dataset_name}")

    dataset = client.datasets.get_dataset(dataset=adversarial_dataset_name)

    experiment_name = f"safety / {MODEL_NAME}"
    print(f"\n> Running experiment: {experiment_name}")

    experiment = client.experiments.run_experiment(
        dataset=dataset,
        task=safety_task,
        evaluators=[safety_check],
        experiment_name=experiment_name,
        experiment_metadata={
            "pipeline": "safety",
            "model": MODEL_NAME,
            "experiment_type": "safety",
        },
    )

    print(f"  -> Experiment complete")
    print(f"\n-> Safety experiment done")
    print(f"   Datasets -> {adversarial_dataset_name} -> Experiments tab")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Phoenix experiments for correctness and/or safety."
    )
    parser.add_argument(
        "--safety",
        action="store_true",
        help="Run safety experiments in addition to correctness.",
    )
    parser.add_argument(
        "--safety-only",
        action="store_true",
        help="Run ONLY safety experiments (skip correctness).",
    )
    args = parser.parse_args()

    client = Client()

    if not args.safety_only:
        run_correctness(client)

    if args.safety or args.safety_only:
        run_safety(client)

    print(f"\n{'='*60}")
    print(f"  ALL EXPERIMENTS COMPLETE")
    print(f"{'='*60}")
    print(f"  Compare results at: https://app.phoenix.arize.com")


if __name__ == "__main__":
    main()
