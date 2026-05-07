"""Export pipeline.jsonl to a flat CSV for Tableau or any spreadsheet tool.

Usage:
    uv run python scripts/export_logs_csv.py

Output:
    logs/pipeline_export.csv  — one row per query, all stage fields flattened

Tableau tip: connect via Text File connector to logs/pipeline_export.csv.
Drag 'strategy' to Columns, 'total_latency_ms' or 'top_score' to Rows for
an instant side-by-side comparison across retrieval strategies.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd
from pipeline.observability.logger import load_logs


def flatten_entry(entry: dict) -> dict:
    retrieve = entry.get("stages", {}).get("retrieve", {})
    generate = entry.get("stages", {}).get("generate", {})
    input_tokens = generate.get("input_tokens", 0)
    output_tokens = generate.get("output_tokens", 0)
    return {
        "query_id":           entry.get("query_id", ""),
        "timestamp":          entry.get("timestamp", ""),
        "strategy":           entry.get("strategy", "unknown"),
        "query":              entry.get("query", ""),
        "total_latency_ms":   entry.get("total_latency_ms", 0),
        # retrieval
        "retrieve_latency_ms": retrieve.get("latency_ms", 0),
        "n_results":           retrieve.get("n_results", 0),
        "top_score":           retrieve.get("top_score", 0.0),
        "low_score":           retrieve.get("low_score", 0.0),
        "score_spread":        retrieve.get("score_spread", 0.0),
        "unique_sources":      retrieve.get("unique_sources", 0),
        # generation
        "generate_latency_ms": generate.get("latency_ms", 0),
        "model":               generate.get("model", ""),
        "input_tokens":        input_tokens,
        "output_tokens":       output_tokens,
        "total_tokens":        input_tokens + output_tokens,
        "stop_reason":         generate.get("stop_reason", ""),
    }


def main():
    entries = load_logs(log_dir=str(_PROJECT_ROOT / "logs"))
    if not entries:
        print("No entries found in logs/pipeline.jsonl — run the app first.")
        return

    df = pd.DataFrame([flatten_entry(e) for e in entries])

    output_path = _PROJECT_ROOT / "logs" / "pipeline_export.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Exported {len(df)} rows → {output_path}")

    if df["strategy"].nunique() > 1:
        print("\nSummary by strategy:")
        cols = ["total_latency_ms", "retrieve_latency_ms", "generate_latency_ms",
                "top_score", "score_spread", "total_tokens"]
        print(df.groupby("strategy")[cols].mean().round(2).to_string())
    else:
        print(f"\nAll {len(df)} rows tagged strategy='{df['strategy'].iloc[0]}'")
        print("Run experiments with different strategies to enable comparison.")


if __name__ == "__main__":
    main()
