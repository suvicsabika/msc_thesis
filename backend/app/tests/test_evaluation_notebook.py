"""Offline checks for notebook token reporting."""

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

NOTEBOOK_PATH = (
    Path(__file__).resolve().parents[1]
    / "validation"
    / "ticket_classification_evaluation.ipynb"
)


def code_cells():
    notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
    return [
        "".join(cell["source"])
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    ]


class NotebookSyntaxTests(unittest.TestCase):
    def test_direct_notebook_is_separate_and_uses_direct_transport(self):
        notebook = json.loads(
            NOTEBOOK_PATH.with_name(
                "ticket_classification_evaluation_direct.ipynb"
            ).read_text(encoding="utf-8")
        )
        sources = [
            "".join(c["source"])
            for c in notebook["cells"]
            if c["cell_type"] == "code"
        ]
        for source in sources:
            compile(source, "direct notebook", "exec")
        self.assertIn('"transport": "direct"', sources[1])
        self.assertIn('"evaluation_results_direct"', sources[0])
        self.assertIn("RUN_ANALYSIS = False", sources[0])
        self.assertIn("N_RUNS = 3", sources[0])

    def test_cells_compile_and_paid_analysis_is_disabled_by_default(self):
        cells = code_cells()
        for path in NOTEBOOK_PATH.parent.glob("*.ipynb"):
            notebook = json.loads(path.read_text(encoding="utf-8"))
            for index, cell in enumerate(notebook["cells"]):
                if cell["cell_type"] == "code":
                    compile("".join(cell["source"]), f"{path}:{index}", "exec")
        self.assertIn("RUN_ANALYSIS = False", cells[0])
        self.assertIn("EXPERIMENT_NOTE", cells[0])


@unittest.skipUnless(
    importlib.util.find_spec("pandas") and importlib.util.find_spec("sklearn"),
    "Install the notebook's pandas and scikit-learn extras for report tests.",
)
class NotebookUsageTests(unittest.TestCase):
    def setUp(self):
        import pandas as pd

        from app.validation import evaluation_reporting

        self.reporting = evaluation_reporting

        self.pd = pd
        self.expected = {
            "category": "API",
            "sentiment": "Neutral",
            "priority": "Low",
        }
        self.tickets = [
            {
                "id": f"REF-{index}",
                "subject": f"Test ticket {index}",
                "expected": self.expected,
            }
            for index in range(4)
        ]
        self.labels = {
            "category": ["API", "General"],
            "sentiment": ["Negative", "Neutral", "Positive"],
            "priority": ["Low", "Medium", "High", "Very High"],
        }
        self.saved = {
            "ticket_ids": {f"REF-{i}": f"MCP-{i}" for i in range(4)},
            "results": {
                "REF-0": {
                    "status": "success",
                    "analysis_seconds": 1.25,
                    "response": {
                        "decision": self.expected,
                        "usage": {
                            "input_tokens": 20,
                            "output_tokens": 10,
                            "total_tokens": 30,
                        },
                    },
                },
                "REF-1": {
                    "status": "success",
                    "analysis_seconds": 1.5,
                    "response": {"decision": self.expected},
                },
                "REF-2": {
                    "status": "failed",
                    "analysis_seconds": 0.5,
                    "error": "Synthetic failure",
                },
            },
            "sessions": [{"wall_seconds": 4}],
        }

    def test_usage_and_missing_attempts_are_kept_separate(self):
        predictions = self.reporting.prediction_table(
            self.saved, "run_01", self.tickets, self.labels
        )
        self.assertEqual(predictions.total_tokens.iloc[0], 30)
        self.assertTrue(predictions.total_tokens.iloc[1:].isna().all())
        self.assertEqual(predictions.status.iloc[-1], "not_run")
        self.assertEqual(predictions.total_tokens.sum(min_count=1), 30)

    def test_zero_tokens_are_known_and_invalid_usage_stays_missing(self):
        cases = [
            ({"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}, 0),
            (None, None),
            ({"total_tokens": 30}, None),
            (
                {"input_tokens": True, "output_tokens": 2, "total_tokens": 3},
                None,
            ),
            (
                {"input_tokens": -1, "output_tokens": 2, "total_tokens": 1},
                None,
            ),
            ("invalid", None),
        ]
        for usage, expected in cases:
            with self.subTest(usage=usage):
                saved = copy.deepcopy(self.saved)
                saved["results"]["REF-0"]["response"]["usage"] = usage
                value = self.reporting.prediction_table(
                    saved, "run_01", self.tickets, self.labels
                ).total_tokens.iloc[0]
                if expected is None:
                    self.assertTrue(self.pd.isna(value))
                else:
                    self.assertEqual(value, expected)

    def test_csv_reports_include_tokens_without_rewriting_checkpoints(self):
        with tempfile.TemporaryDirectory(prefix="ticket-report-test-") as tmp:
            run_dir = Path(tmp)
            checkpoint = run_dir / "results.json"
            checkpoint.write_text(json.dumps(self.saved), encoding="utf-8")
            original = checkpoint.read_bytes()
            with (
                patch.object(self.reporting, "plot_matrix"),
                patch.object(self.reporting, "display"),
            ):
                _, metrics, stats = self.reporting.report_run(
                    self.saved,
                    run_dir,
                    self.tickets,
                    self.labels,
                    self.pd.DataFrame(),
                )
            exported = self.pd.read_csv(run_dir / "runtime_tokens.csv")
            predictions = self.pd.read_csv(run_dir / "predictions.csv")
            self.assertEqual(exported.observed_total_tokens.iloc[0], 30)
            self.assertEqual(
                exported.mean_total_tokens_where_available.iloc[0], 30
            )
            self.assertEqual(stats["usage_available_tickets"], 1)
            self.assertEqual(stats["usage_missing_tickets"], 3)
            self.assertTrue(predictions.total_tokens.iloc[1:].isna().all())
            self.assertTrue((metrics.coverage == 0.5).all())
            self.assertEqual(checkpoint.read_bytes(), original)

    def test_costs_preserve_missing_and_zero_usage(self):
        runtime = self.pd.DataFrame(
            {
                "method": ["MCP"] * 3,
                "run": ["known", "zero", "missing"],
                "usage_available_tickets": [1, 1, 0],
                "usage_missing_tickets": [0, 0, 1],
                "observed_input_tokens": [1_000_000, 0, float("nan")],
                "observed_output_tokens": [1_000_000, 0, float("nan")],
            }
        )
        costs, summary = self.reporting.estimate_costs(runtime, "gpt-6-luna")
        self.assertAlmostEqual(costs.estimated_total_cost_usd.iloc[0], 0.6)
        self.assertEqual(costs.estimated_total_cost_usd.iloc[1], 0)
        self.assertTrue(self.pd.isna(costs.estimated_total_cost_usd.iloc[2]))
        self.assertAlmostEqual(summary.mean_ticket_cost_usd.iloc[0], 0.3)
        _, missing = self.reporting.estimate_costs(
            runtime.iloc[2:], "gpt-6-luna"
        )
        self.assertTrue(self.pd.isna(missing.estimated_total_cost_usd.iloc[0]))
        with self.assertRaises(ValueError):
            self.reporting.estimate_costs(runtime, "unpriced-model")


if __name__ == "__main__":
    unittest.main()
