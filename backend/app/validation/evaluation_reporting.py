"""Reports and cost estimates for saved ticket evaluations."""

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
from IPython.display import display
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
)


TOKEN_COLUMNS = ["input_tokens", "output_tokens", "total_tokens"]
PRICING_MODEL = "gpt-6-luna"
PRICING_DATE = "2026-11-11"
INPUT_USD_PER_MILLION = 0.10
OUTPUT_USD_PER_MILLION = 0.50


def prediction_table(
    saved: dict[str, Any],
    run_name: str,
    tickets: list[dict[str, Any]],
    labels_by_task: dict[str, list[str]],
) -> pd.DataFrame:
    rows = []
    for ticket in tickets:
        key = ticket["id"]
        result = saved["results"].get(key, {"status": "not_run"})
        response = result.get("response", {})
        decision = response.get("decision", {})
        usage = response.get("usage")
        valid_usage = isinstance(usage, dict) and all(
            type(usage.get(name)) is int and usage[name] >= 0
            for name in TOKEN_COLUMNS
        )
        if not valid_usage:
            usage = {}

        row = {
            "run": run_name,
            "id": key,
            "backend_ticket_id": saved["ticket_ids"].get(key),
            "subject": ticket["subject"],
            "status": result["status"],
            "error": result.get("error"),
            "started_at": result.get("started_at"),
            "finished_at": result.get("finished_at"),
            "analysis_seconds": result.get("analysis_seconds"),
        }
        for name in TOKEN_COLUMNS:
            row[name] = usage.get(name)
        for field in labels_by_task:
            row[f"expected_{field}"] = ticket["expected"][field]
        for field in labels_by_task:
            prediction = (
                decision.get(field) if result["status"] == "success" else None
            )
            row[f"predicted_{field}"] = prediction
        rows.append(row)
    return pd.DataFrame(rows)


def classification_metrics(
    predictions: pd.DataFrame,
    run_name: str,
    labels_by_task: dict[str, list[str]],
) -> pd.DataFrame:
    successful = predictions[predictions.status == "success"]
    scores = []
    for field, labels in labels_by_task.items():
        actual = successful[f"expected_{field}"]
        predicted = successful[f"predicted_{field}"]
        accuracy = precision = recall = f1 = float("nan")
        if len(successful):
            accuracy = accuracy_score(actual, predicted)
            precision, recall, f1, _ = precision_recall_fscore_support(
                actual,
                predicted,
                labels=labels,
                average="macro",
                zero_division=0,
            )
        scores.append(
            {
                "run": run_name,
                "task": field,
                "total": len(predictions),
                "successful": len(successful),
                "coverage": len(successful) / len(predictions),
                "accuracy": accuracy,
                "macro_precision": precision,
                "macro_recall": recall,
                "macro_f1": f1,
                "correct_over_total": int((actual == predicted).sum())
                / len(predictions),
            }
        )
    return pd.DataFrame(scores)


def plot_matrix(
    matrix: Any, labels: list[str], title: str, path: Path
) -> None:
    fig, ax = plt.subplots(figsize=(9, 7))
    ConfusionMatrixDisplay(matrix, display_labels=labels).plot(
        ax=ax,
        cmap="Blues",
        colorbar=False,
        xticks_rotation=45,
        values_format="d",
    )
    ax.set(title=title, xlabel="Predicted label", ylabel="Reference label")
    fig.tight_layout()
    fig.savefig(path.with_suffix(".png"), dpi=200)
    fig.savefig(path.with_suffix(".pdf"))
    plt.show()
    plt.close(fig)


def save_confusion_tables(
    predictions: pd.DataFrame,
    run_dir: Path,
    labels_by_task: dict[str, list[str]],
) -> None:
    successful = predictions[predictions.status == "success"]
    for field, labels in labels_by_task.items():
        if len(successful):
            matrix = confusion_matrix(
                successful[f"expected_{field}"],
                successful[f"predicted_{field}"],
                labels=labels,
            )
        else:
            matrix = pd.DataFrame(0, index=labels, columns=labels).to_numpy()
        pd.DataFrame(matrix, index=labels, columns=labels).to_csv(
            run_dir / f"confusion_{field}.csv"
        )
        outcomes = pd.crosstab(
            predictions[f"expected_{field}"],
            predictions[f"predicted_{field}"].fillna("NO_RESULT"),
        )
        outcomes.reindex(
            index=labels, columns=labels + ["NO_RESULT"], fill_value=0
        ).to_csv(run_dir / f"outcomes_{field}.csv")
        title = (
            f"{run_dir.name}: {field} "
            f"({len(successful)}/{len(predictions)} successful)"
        )
        plot_matrix(matrix, labels, title, run_dir / f"confusion_{field}")


def runtime_summary(
    saved: dict[str, Any],
    predictions: pd.DataFrame,
    run_name: str,
    *,
    include_previous_attempts: bool = False,
) -> dict[str, Any]:
    times = predictions.analysis_seconds.dropna()
    sessions = saved.get("sessions", [])
    known_sessions = [
        s["wall_seconds"]
        for s in sessions
        if s.get("wall_seconds") is not None
    ]
    stats = {
        "run": run_name,
        "successful": int((predictions.status == "success").sum()),
        "failed": int((predictions.status == "failed").sum()),
        "missing_or_interrupted": int(
            predictions.status.isin(["not_run", "interrupted"]).sum()
        ),
        "run_wall_seconds": sum(known_sessions)
        if known_sessions
        else float("nan"),
        "wall_time_complete": bool(sessions)
        and len(known_sessions) == len(sessions),
        "timed_tickets": len(times),
        "latency_mean_seconds": times.mean(),
        "latency_std_seconds": times.std(ddof=1),
        "latency_median_seconds": times.median(),
        "latency_p95_seconds": times.quantile(0.95),
        "usage_available_tickets": int(predictions.total_tokens.notna().sum()),
        "usage_missing_tickets": int(predictions.total_tokens.isna().sum()),
    }
    if include_previous_attempts:
        previous = [
            attempt
            for result in saved["results"].values()
            for attempt in result.get("previous_attempts", [])
        ]
        stats = {
            "run": run_name,
            "attempts_recorded": len(saved["results"]) + len(previous),
            "retried_tickets": sum(
                bool(r.get("previous_attempts"))
                for r in saved["results"].values()
            ),
            "previous_failed_attempts": sum(
                a.get("status") == "failed" for a in previous
            ),
            "previous_attempt_seconds": sum(
                a.get("analysis_seconds", 0) or 0 for a in previous
            ),
            **stats,
        }
    for k in TOKEN_COLUMNS:
        stats[f"observed_{k}"] = predictions[k].sum(min_count=1)
        stats[f"mean_{k}_where_available"] = predictions[k].mean()
    return stats


def report_run(
    saved: dict[str, Any],
    run_dir: Path,
    tickets: list[dict[str, Any]],
    labels_by_task: dict[str, list[str]],
    class_counts: pd.DataFrame,
    *,
    include_previous_attempts: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    run_dir.mkdir(parents=True, exist_ok=True)
    predictions = prediction_table(
        saved, run_dir.name, tickets, labels_by_task
    )
    metrics = classification_metrics(predictions, run_dir.name, labels_by_task)
    stats = runtime_summary(
        saved,
        predictions,
        run_dir.name,
        include_previous_attempts=include_previous_attempts,
    )
    runtime = pd.DataFrame([stats])
    save_confusion_tables(predictions, run_dir, labels_by_task)

    wrong = predictions.status != "success"
    for field in labels_by_task:
        wrong |= (
            predictions[f"expected_{field}"]
            != predictions[f"predicted_{field}"]
        )
    predictions[wrong].to_csv(run_dir / "errors.csv", index=False)
    predictions.to_csv(run_dir / "predictions.csv", index=False)
    metrics.to_csv(run_dir / "metrics.csv", index=False)
    runtime.to_csv(run_dir / "runtime_tokens.csv", index=False)
    class_counts.to_csv(run_dir / "class_counts.csv", index=False)
    predictions.status.value_counts().to_csv(run_dir / "status_counts.csv")

    display(metrics.round(4), runtime.round(3))
    columns = [
        "id",
        "backend_ticket_id",
        "status",
        "analysis_seconds",
    ] + TOKEN_COLUMNS
    with pd.option_context("display.max_rows", 110, "display.max_columns", 30):
        display(predictions[columns])
    if stats["usage_missing_tickets"]:
        print(
            f"Missing token usage for {stats['usage_missing_tickets']} "
            "tickets; totals are partial."
        )
    return predictions, metrics, stats


def estimate_costs(
    runtime: pd.DataFrame, model: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Estimate standard uncached costs from recorded token usage."""
    if model != PRICING_MODEL:
        raise ValueError(
            "Update the pricing model and rates for this experiment."
        )
    cost_by_run = runtime[
        [
            "method",
            "run",
            "usage_available_tickets",
            "usage_missing_tickets",
            "observed_input_tokens",
            "observed_output_tokens",
        ]
    ].copy()
    cost_by_run["pricing_model"] = PRICING_MODEL
    cost_by_run["pricing_date"] = PRICING_DATE
    cost_by_run["input_usd_per_million"] = INPUT_USD_PER_MILLION
    cost_by_run["output_usd_per_million"] = OUTPUT_USD_PER_MILLION
    cost_by_run["estimated_input_cost_usd"] = (
        cost_by_run["observed_input_tokens"]
        * INPUT_USD_PER_MILLION
        / 1_000_000
    )
    cost_by_run["estimated_output_cost_usd"] = (
        cost_by_run["observed_output_tokens"]
        * OUTPUT_USD_PER_MILLION
        / 1_000_000
    )
    cost_by_run["estimated_total_cost_usd"] = (
        cost_by_run["estimated_input_cost_usd"]
        + cost_by_run["estimated_output_cost_usd"]
    )
    cost_by_run["mean_ticket_cost_usd"] = cost_by_run[
        "estimated_total_cost_usd"
    ] / cost_by_run["usage_available_tickets"].replace(0, float("nan"))
    summary = cost_by_run.groupby("method").agg(
        runs=("run", "count"),
        tickets_with_usage=("usage_available_tickets", "sum"),
        tickets_without_usage=("usage_missing_tickets", "sum"),
        estimated_total_cost_usd=(
            "estimated_total_cost_usd",
            lambda x: x.sum(min_count=1),
        ),
        mean_run_cost_usd=("estimated_total_cost_usd", "mean"),
        std_run_cost_usd=("estimated_total_cost_usd", "std"),
    )
    summary["mean_ticket_cost_usd"] = summary[
        "estimated_total_cost_usd"
    ] / summary["tickets_with_usage"].replace(0, float("nan"))
    return cost_by_run, summary
