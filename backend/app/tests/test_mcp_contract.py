"""SDK v2 contract checks over real stdio with a temporary database."""

import asyncio
import importlib
import json
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch


TOOL_NAMES = [
    "set_ticket_classification",
    "set_ticket_sentiment",
    "set_ticket_intent",
    "set_ticket_priority",
    "save_response_draft",
]
RESOURCE_SUFFIXES = {
    "raw",
    "classification",
    "priority",
    "draft_response",
    "history",
}
PROMPT_NAMES = {"ticket_triage_prompt"}


class McpContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Copy Python sources only: both host and stdio server resolve
        # the same
        # temporary database through their normal database.py path
        # calculation.
        cls.temporary = tempfile.TemporaryDirectory(prefix="ticket-mcp-test-")
        cls.backend = Path(cls.temporary.name) / "backend"
        source = Path(__file__).resolve().parents[1]
        for path in source.rglob("*.py"):
            target = cls.backend / "app" / path.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
        if "app.db.database" in sys.modules:
            raise RuntimeError(
                "Run this suite in a fresh process to isolate the database."
            )
        sys.path.insert(0, str(cls.backend))
        cls.database = importlib.import_module("app.db.database")
        cls.init_db = importlib.import_module("app.db.init_db")
        cls.ticket_model = importlib.import_module(
            "app.models.ticket"
        ).TicketModel
        cls.draft_model = importlib.import_module(
            "app.models.response_draft"
        ).ResponseDraftModel
        cls.client_type = importlib.import_module(
            "app.mcp.client"
        ).TicketMcpClient
        cls.workflow = importlib.import_module(
            "app.services.ticket_analysis_workflow"
        )
        cls.decision_type = importlib.import_module(
            "app.ai.schemas"
        ).TicketTriageDecision
        assert cls.database.DATABASE_PATH.is_relative_to(cls.backend)

    @classmethod
    def tearDownClass(cls):
        cls.database.engine.dispose()
        sys.path.remove(str(cls.backend))
        cls.temporary.cleanup()

    def setUp(self):
        self.database.Base.metadata.drop_all(self.database.engine)
        self.init_db.create_db_and_tables()
        with self.database.SessionLocal() as db:
            db.add(
                self.ticket_model(
                    id="MCP-TEST01",
                    subject="Production API unavailable",
                    body=(
                        "Our production API is down and "
                        "customers cannot place orders."
                    ),
                    customer="Test Customer",
                    customerEmail="test@example.com",
                )
            )
            db.commit()
        self.decision = self.decision_type(
            category="API",
            classificationConfidence=0.95,
            classificationReason="The customer reports an API outage.",
            sentiment="Negative",
            sentimentScore=0.9,
            sentimentReason="Work is blocked.",
            customerIntent="Issue report",
            intentConfidence=0.95,
            priority="Very High",
            slaState="critical",
            sla="1h",
            priorityConfidence=0.98,
            priorityReason="Production orders are blocked.",
            responseDraft="We will review the reported API outage.",
            requiresApproval=True,
            responseDraftReason="Requires human review.",
            reasoningSummary="Production outage.",
        )

    def assert_cacheable(self, result):
        self.assertEqual(result["resultType"], "complete")
        self.assertGreaterEqual(result["ttlMs"], 0)
        self.assertIn(result["cacheScope"], {"private", "public"})

    def test_updated_at_default_and_automatic_updates(self):
        from sqlalchemy import DateTime, inspect

        columns = inspect(self.database.engine).get_columns("tickets")
        column = next(c for c in columns if c["name"] == "updatedAt")
        self.assertIsInstance(column["type"], DateTime)
        self.assertFalse(column["nullable"])
        with self.database.SessionLocal() as db:
            ticket = db.get(self.ticket_model, "MCP-TEST01")
            self.assertIsInstance(ticket.updatedAt, datetime)
            self.assertIsNone(ticket.updatedAt.tzinfo)
            old_time = datetime(2020, 1, 1, 12)
            ticket.updatedAt = old_time
            db.commit()
            db.refresh(ticket)
            self.assertEqual(ticket.updatedAt, old_time)
            ticket.owner = "New owner"
            db.commit()
            db.refresh(ticket)
            self.assertGreater(ticket.updatedAt, old_time)
            unchanged = ticket.updatedAt
            db.commit()
            db.refresh(ticket)
            self.assertEqual(ticket.updatedAt, unchanged)

    def test_ticket_and_dashboard_timestamp_responses(self):
        from fastapi.testclient import TestClient

        from app.api.routes import tickets
        from app.app import app

        payload = {
            "subject": "Test ticket",
            "body": "This is a timestamp test ticket.",
            "customer": "Test Customer",
            "customerEmail": "test@example.com",
        }
        with (
            TestClient(app) as http,
            patch.object(tickets, "run_ticket_analysis_background"),
            patch.dict(os.environ, {"DEBUG": "True"}),
        ):
            single = http.post("/api/tickets", json=payload)
            self.assertEqual(single.status_code, 201, single.text)
            bulk = http.post("/api/tickets/bulk", json={
                "tickets": [payload], "analyze": False,
            })
            self.assertEqual(bulk.status_code, 201, bulk.text)
            for ticket in [single.json(), *bulk.json()["tickets"]]:
                value = datetime.fromisoformat(ticket["updatedAt"])
                self.assertIsNone(value.tzinfo)
                detail = http.get(f'/api/tickets/{ticket["id"]}')
                self.assertEqual(detail.status_code, 200)
                self.assertEqual(
                    detail.json()["updatedAt"], ticket["updatedAt"]
                )
            self.assertEqual(http.get("/api/tickets").status_code, 200)
            dashboard = http.get("/api/dashboard/summary")
            self.assertEqual(dashboard.status_code, 200, dashboard.text)
            for item in dashboard.json()["workflowActivity"]:
                self.assertIsNone(
                    datetime.fromisoformat(item["time"]).tzinfo
                )

    def test_modern_wire_discovery_and_version_errors(self):
        """Discover the server and validate JSON-RPC responses."""
        env = {**os.environ, "PYTHONPATH": str(self.backend)}
        process = subprocess.Popen(
            [sys.executable, "-m", "app.mcp.ticket_server"],
            cwd=self.backend,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
        )
        stdin = process.stdin
        stdout = process.stdout
        assert stdin is not None, "The server must have a piped stdin."
        assert stdout is not None, "The server must have a piped stdout."
        messages: queue.Queue[str] = queue.Queue()

        def read_messages():
            for line in stdout:
                messages.put(line)

        reader = threading.Thread(
            target=read_messages,
            daemon=True,
        )
        reader.start()
        request_id = 0

        def request(method, params=None, version="2026-07-28"):
            nonlocal request_id
            request_id += 1
            meta = {
                "io.modelcontextprotocol/protocolVersion": version,
                "io.modelcontextprotocol/clientCapabilities": {},
                "io.modelcontextprotocol/clientInfo": {
                    "name": "contract-test",
                    "version": "1",
                },
            }
            message = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": {**(params or {}), "_meta": meta},
            }
            stdin.write(json.dumps(message) + "\n")
            stdin.flush()
            response = json.loads(messages.get(timeout=20))
            self.assertEqual(response["id"], request_id)
            return response

        try:
            discovery = request("server/discover")["result"]
            self.assert_cacheable(discovery)
            self.assertIn("2026-07-28", discovery["supportedVersions"])
            self.assertEqual(
                discovery["_meta"]["io.modelcontextprotocol/serverInfo"][
                    "name"
                ],
                "mcp-ticket-analyzer",
            )
            tools = request("tools/list")["result"]
            self.assert_cacheable(tools)
            self.assertEqual(
                {tool["name"] for tool in tools["tools"]}, set(TOOL_NAMES)
            )
            draft_tool = next(
                t for t in tools["tools"] if t["name"] == "save_response_draft"
            )
            self.assertIs(
                draft_tool["inputSchema"]["properties"]["requires_approval"][
                    "const"
                ],
                True,
            )
            resources = request("resources/list")["result"]
            self.assert_cacheable(resources)
            self.assertEqual(
                [r["uri"] for r in resources["resources"]], ["tickets://index"]
            )
            templates = request("resources/templates/list")["result"]
            self.assert_cacheable(templates)
            self.assertEqual(
                {r["uriTemplate"] for r in templates["resourceTemplates"]},
                {
                    f"ticket://{{ticket_id}}/{suffix}"
                    for suffix in RESOURCE_SUFFIXES
                },
            )
            prompts = request("prompts/list")["result"]
            self.assert_cacheable(prompts)
            self.assertEqual(
                {p["name"] for p in prompts["prompts"]}, PROMPT_NAMES
            )
            raw = request(
                "resources/read", {"uri": "ticket://MCP-TEST01/raw"}
            )["result"]
            self.assert_cacheable(raw)
            self.assertEqual(raw["cacheScope"], "private")
            self.assertEqual(
                json.loads(raw["contents"][0]["text"])["id"], "MCP-TEST01"
            )
            error = request("tools/list", version="2099-01-01")["error"]
            self.assertEqual(error["code"], -32022)
        finally:
            stdin.close()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            reader.join(timeout=2)
            stdout.close()
        self.assertEqual(process.returncode, 0)

    def test_resources_and_prompts_over_sdk_client(self):
        from mcp.types import TextContent

        async def scenario():
            wrapper = self.client_type()
            async with wrapper:
                client = wrapper.require_client()
                self.assertEqual(client.protocol_version, "2026-07-28")
                for suffix in RESOURCE_SUFFIXES:
                    payload = json.loads(
                        await wrapper.read_resource_text(
                            f"ticket://MCP-TEST01/{suffix}"
                        )
                    )
                    self.assertEqual(
                        payload.get("ticketId", payload.get("id")),
                        "MCP-TEST01",
                    )
                index = json.loads(
                    await wrapper.read_resource_text("tickets://index")
                )
                self.assertEqual(index["tickets"][0]["id"], "MCP-TEST01")
                for name in PROMPT_NAMES:
                    messages = await wrapper.get_prompt_messages(
                        name, {"ticket_id": "MCP-TEST01"}
                    )
                    self.assertEqual(messages[0].role, "user")
                    content = messages[0].content
                    assert isinstance(content, TextContent), (
                        "The prompt must contain text."
                    )
                    self.assertIn("MCP-TEST01", content.text)
                    self.assertIn("Priority rules:", content.text)
                    self.assertIn("- Very High: 1h", content.text)
            with self.assertRaisesRegex(RuntimeError, "not connected"):
                wrapper.require_client()

        asyncio.run(scenario())

    def test_full_workflow_persists_via_stdio_and_preserves_json_aliases(self):
        with patch.object(
            self.workflow,
            "analyze_ticket_with_openai",
            return_value=self.decision,
        ) as llm:
            result = asyncio.run(
                self.workflow.analyze_ticket_with_mcp_workflow("MCP-TEST01")
            )
        llm.assert_called_once()
        message = llm.call_args.args[1][0]
        self.assertEqual(message.role, "user")
        ticket_json = message.content.text.split("Ticket JSON:\n", 1)[1]
        self.assertEqual(json.loads(ticket_json)["id"], "MCP-TEST01")
        self.assertEqual(
            [item["tool"] for item in result.mcpToolResults], TOOL_NAMES
        )
        encoded = json.loads(result.model_dump_json())
        for item in encoded["mcpToolResults"]:
            self.assertIs(item["result"]["isError"], False)
            self.assertEqual(item["result"]["resultType"], "complete")
            self.assertNotIn("structured_content", item["result"])
        with self.database.SessionLocal() as db:
            ticket = db.get(self.ticket_model, "MCP-TEST01")
            assert ticket is not None, "The test ticket must exist."
            self.assertEqual(
                (
                    ticket.category,
                    ticket.sentiment,
                    ticket.priority,
                    ticket.sla,
                ),
                ("API", "Negative", "Very High", "1h"),
            )
            draft = db.query(self.draft_model).one()
            self.assertEqual(draft.draft, self.decision.responseDraft)
            self.assertIs(draft.requiresApproval, True)

    def test_openai_request_preserves_mcp_prompt_content_and_roles(self):
        from unittest.mock import Mock

        from app.ai import openai_client
        from app.ai.prompts import TRIAGE_SYSTEM_PROMPT

        async def get_messages():
            async with self.client_type() as wrapper:
                return await wrapper.get_prompt_messages(
                    "ticket_triage_prompt", {"ticket_id": "MCP-TEST01"}
                )

        messages = asyncio.run(get_messages())
        client = Mock()
        client.responses.parse.return_value = Mock(
            output_parsed=self.decision, usage=None, id="test-response"
        )
        with patch.object(
            openai_client, "get_openai_client", return_value=client
        ):
            result = openai_client.analyze_ticket_with_openai(
                "MCP-TEST01", messages
            )
        self.assertEqual(result, self.decision)
        request = client.responses.parse.call_args.kwargs
        self.assertIs(request["text_format"], self.decision_type)
        self.assertEqual(request["input"], [
            {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
            {"role": "user", "content": messages[0].content.text},
        ])

    def test_tool_errors_stop_calls_and_enforce_human_approval(self):
        async def scenario():
            async with self.client_type() as wrapper:
                with self.assertRaisesRegex(
                    RuntimeError, "does_not_exist.*failed"
                ):
                    await wrapper.call_tool("does_not_exist", {})
                with self.assertRaisesRegex(
                    RuntimeError, "set_ticket_classification.*failed"
                ):
                    await wrapper.call_tool(
                        "set_ticket_classification",
                        {
                            "ticket_id": "MISSING",
                            "category": "API",
                            "confidence": 0.9,
                            "reason": "Test",
                        },
                    )
                with self.assertRaisesRegex(
                    RuntimeError, "save_response_draft.*failed"
                ):
                    await wrapper.call_tool(
                        "save_response_draft",
                        {
                            "ticket_id": "MCP-TEST01",
                            "draft": "Test",
                            "requires_approval": False,
                            "reason": "Test",
                        },
                    )

        asyncio.run(scenario())
        with self.database.SessionLocal() as db:
            self.assertEqual(db.query(self.draft_model).count(), 0)

    def test_failed_first_tool_prevents_later_workflow_writes(self):
        # An invalid model output exercises the real server's input
        # validation,
        # rather than replacing the MCP transport or call_tool with a
        # mock.
        invalid_decision = self.decision.model_copy(
            update={"category": "Invalid category"}
        )
        with patch.object(
            self.workflow,
            "analyze_ticket_with_openai",
            return_value=invalid_decision,
        ):
            with self.assertRaisesRegex(
                RuntimeError, "set_ticket_classification.*failed"
            ):
                asyncio.run(
                    self.workflow.analyze_ticket_with_mcp_workflow(
                        "MCP-TEST01"
                    )
                )
        with self.database.SessionLocal() as db:
            ticket = db.get(self.ticket_model, "MCP-TEST01")
            assert ticket is not None, "The test ticket must exist."
            self.assertEqual(
                (ticket.category, ticket.sentiment, ticket.priority),
                ("General", "Neutral", "Low"),
            )
            self.assertEqual(db.query(self.draft_model).count(), 0)

    def test_rest_api_analysis_and_bulk_creation(self):
        from fastapi.testclient import TestClient

        from app.app import app

        with (
            TestClient(app) as http,
            patch.object(
                self.workflow,
                "analyze_ticket_with_openai",
                return_value=self.decision,
            ),
            patch.dict(os.environ, {"DEBUG": "True"}),
        ):
            response = http.post("/api/tickets/MCP-TEST01/analyze")
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(len(response.json()["mcpToolResults"]), 5)
            self.assertIs(
                http.get("/api/tickets/MCP-TEST01/draft").json()[
                    "requiresApproval"
                ],
                True,
            )
            self.assertEqual(
                http.get("/api/tickets/MCP-TEST01").json()["category"], "API"
            )
            bulk = http.post(
                "/api/tickets/bulk",
                json={
                    "analyze": False,
                    "tickets": [
                        {
                            "subject": "Test ticket",
                            "body": "This is an integration test ticket.",
                            "customer": "Test Customer",
                            "customerEmail": "test@example.com",
                        }
                    ],
                },
            )
            self.assertEqual(bulk.status_code, 201, bulk.text)
            self.assertEqual(bulk.json()["createdCount"], 1)
            self.assertFalse(bulk.json()["analysisScheduled"])

    def test_workflow_timeout_remains_a_rest_504_after_cleanup(self):
        from fastapi.testclient import TestClient

        from app.app import app

        with (
            TestClient(app) as http,
            patch.object(
                self.workflow,
                "analyze_ticket_with_openai",
                side_effect=asyncio.TimeoutError,
            ),
        ):
            response = http.post("/api/tickets/MCP-TEST01/analyze")
            self.assertEqual(response.status_code, 504, response.text)
        with self.database.SessionLocal() as db:
            self.assertEqual(db.query(self.draft_model).count(), 0)


if __name__ == "__main__":
    unittest.main()
