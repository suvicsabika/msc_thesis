"""Collection checks without a backend or model requests."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.validation import evaluation_runner as runner  # noqa: E402


class EvaluationRunnerTests(unittest.TestCase):
    def setUp(self):
        self.settings = {
            "base_url": "http://unused",
            "concurrency": 1,
            "labels": {"category": ["API"]},
        }

    def test_http_timeout_allows_the_backend_to_finish_and_close(self):
        with patch.object(runner.requests, "post") as post:
            post.return_value.json.return_value = {"status": "ok"}
            self.assertEqual(
                runner.post("http://unused", "/api/health"),
                {"status": "ok"},
            )
        post.assert_called_once_with(
            "http://unused/api/health", json=None, timeout=(60, 360)
        )
        post.return_value.raise_for_status.assert_called_once()

    def test_git_metadata_timeout_does_not_block_reporting(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "backend/app").mkdir(parents=True)
            with patch.object(
                runner.subprocess,
                "check_output",
                side_effect=subprocess.TimeoutExpired("git", 60),
            ) as git:
                self.assertEqual(
                    runner.backend_version(root)["backend_commit"],
                    "unavailable",
                )
            self.assertEqual(git.call_args.kwargs["timeout"], 60)

    def test_finished_attempts_are_reused_without_http_or_file_changes(self):
        saved = {
            "settings": self.settings,
            "results": {"REF-1": {"status": "failed"}},
        }
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            path = run_dir / "results.json"
            path.write_text(json.dumps(saved), encoding="utf-8")
            original = path.read_bytes()
            with patch.object(runner, "post") as post:
                result = runner.execute_run(
                    run_dir, [{"id": "REF-1"}], self.settings
                )
            self.assertEqual(result, saved)
            self.assertEqual(path.read_bytes(), original)
            post.assert_not_called()

    def test_resume_collects_only_pending_tickets(self):
        previous = {"status": "failed", "error": "Previous timeout"}
        saved = {
            "settings": self.settings,
            "creation_started": True,
            "ticket_ids": {"REF-1": "MCP-1", "REF-2": "MCP-2"},
            "results": {"REF-1": previous},
            "sessions": [],
        }
        response = {"decision": {"category": "API"}}
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            path = run_dir / "results.json"
            path.write_text(json.dumps(saved), encoding="utf-8")
            with patch.object(runner, "post", return_value=response) as post:
                result = runner.execute_run(
                    run_dir,
                    [{"id": "REF-1"}, {"id": "REF-2"}],
                    self.settings,
                )
            post.assert_called_once_with(
                "http://unused", "/api/tickets/MCP-2/analyze"
            )
            self.assertEqual(result["results"]["REF-1"], previous)
            self.assertEqual(result["results"]["REF-2"]["response"], response)
            self.assertEqual(result["sessions"][0]["status"], "finished")
            self.assertEqual(json.loads(path.read_text()), result)

    def test_uncertain_upload_stops_before_any_http_request(self):
        saved = {
            "settings": self.settings,
            "creation_started": True,
            "ticket_ids": {},
            "results": {},
            "sessions": [],
        }
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            (run_dir / "results.json").write_text(json.dumps(saved))
            with patch.object(runner, "post") as post:
                with self.assertRaisesRegex(AssertionError, "bulk upload"):
                    runner.execute_run(
                        run_dir, [{"id": "REF-1"}], self.settings
                    )
            post.assert_not_called()

    def test_direct_run_selects_transport_and_checks_server_confirmation(self):
        settings = {**self.settings, "transport": "direct"}
        response = {"decision": {"category": "API"}, "transport": "direct"}
        for confirmed in [True, False]:
            with self.subTest(confirmed=confirmed):
                actual = (
                    response
                    if confirmed
                    else {"decision": {"category": "API"}}
                )
                with tempfile.TemporaryDirectory() as temporary:
                    run_dir = Path(temporary)
                    with (
                        patch.object(
                            runner,
                            "create_tickets",
                            return_value={"REF-1": "MCP-1"},
                        ),
                        patch.object(
                            runner, "post", return_value=actual
                        ) as post,
                    ):
                        result = runner.execute_run(
                            run_dir, [{"id": "REF-1"}], settings
                        )
                    post.assert_called_once_with(
                        "http://unused",
                        "/api/tickets/MCP-1/analyze?transport=direct",
                    )
                    expected = "success" if confirmed else "failed"
                    self.assertEqual(
                        result["results"]["REF-1"]["status"], expected
                    )

    def test_old_backend_is_rejected_before_direct_collection(self):
        settings = {
            **self.settings,
            "transport": "direct",
            "model": "test",
            "experiment_note": "test",
        }
        with (
            patch.object(runner.requests, "get") as get,
            patch.object(runner, "execute_run") as execute,
        ):
            get.return_value.json.return_value = {
                "paths": {
                    "/api/tickets/{ticket_id}/analyze": {
                        "post": {"parameters": []}
                    }
                }
            }
            with self.assertRaisesRegex(AssertionError, "direct transport"):
                runner.run_experiment([Path("unused/run_01")], [], settings)
            execute.assert_not_called()

    def test_bulk_upload_excludes_labels_and_checks_ticket_order(self):
        ticket = {
            "id": "REF-1",
            "subject": "API unavailable",
            "body": "Requests fail.",
            "customer": "Test",
            "customerEmail": "test@example.com",
            "expected": {"category": "API"},
        }
        uploaded = {
            "analysisScheduled": False,
            "tickets": [{**ticket, "id": "MCP-1"}],
        }
        with patch.object(runner, "post", return_value=uploaded) as post:
            self.assertEqual(
                runner.create_tickets([ticket], "http://unused"),
                {"REF-1": "MCP-1"},
            )
        payload = post.call_args.args[2]
        self.assertFalse(payload["analyze"])
        self.assertNotIn("expected", payload["tickets"][0])
        self.assertEqual(payload["tickets"][0]["category"], "General")
        uploaded["tickets"][0]["body"] = "Different ticket"
        with patch.object(runner, "post", return_value=uploaded):
            with self.assertRaises(AssertionError):
                runner.create_tickets([ticket], "http://unused")


if __name__ == "__main__":
    unittest.main()
