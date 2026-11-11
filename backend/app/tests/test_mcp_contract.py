"""SDK v2 contract checks over real stdio with a temporary database."""

import asyncio
import copy
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
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


TOOL_NAMES = [
    "set_ticket_classification",
    "set_ticket_sentiment",
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
        if "app.db.database" in sys.modules:
            raise RuntimeError(
                "Run this suite in a fresh process to isolate the database."
            )
        # Other suites may have imported shared configuration already.
        cls.previous_app_modules = {
            name: module
            for name, module in list(sys.modules.items())
            if name == "app" or name.startswith("app.")
        }
        for name in cls.previous_app_modules:
            del sys.modules[name]
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
        sys.path.insert(0, str(cls.backend))
        cls.timeouts = importlib.import_module("app.core.timeouts")
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
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                del sys.modules[name]
        sys.modules.update(cls.previous_app_modules)

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
            priority="Very High",
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

        from app.schemas.ticket import TicketRead

        columns = inspect(self.database.engine).get_columns("tickets")
        self.assertEqual(
            {column["name"] for column in columns},
            set(TicketRead.model_fields),
        )
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

    def test_dashboard_priority_counts_and_trends_agree(self):
        from app.services.dashboard_service import build_dashboard_summary

        now = datetime(2026, 11, 4, 12, tzinfo=timezone.utc)
        priorities_and_ages = [
            ("Very High", 1),
            ("Very High", 2),
            ("High", 1),
            ("Very High", 8),
            ("High", 8),
            ("High", 9),
            ("High", 10),
        ]
        tickets = [
            SimpleNamespace(
                id=str(index),
                category="General",
                priority=priority,
                sentiment="Neutral",
                status="Open",
                createdAt=now - timedelta(days=age),
                updatedAt=now - timedelta(days=age),
            )
            for index, (priority, age) in enumerate(priorities_and_ages)
        ]
        summary = build_dashboard_summary(tickets, now)
        self.assertEqual(summary.kpis.highPriorityTickets, 7)
        self.assertEqual(summary.kpis.veryHighPriorityTickets, 3)
        self.assertEqual(summary.trends.highPriorityTickets.changePercent, -25)
        self.assertEqual(
            summary.trends.veryHighPriorityTickets.changePercent, 100
        )

    def test_resolved_today_uses_utc_and_excludes_old_or_future_updates(self):
        from app.services.dashboard_service import build_dashboard_summary

        now = datetime(2026, 11, 4, 12, tzinfo=timezone.utc)
        updates = [
            ("Resolved", "2026-11-04T00:00:00"),
            ("Resolved", "2026-11-04T03:00:00+02:00"),
            ("Resolved", "2026-11-04T00:30:00+02:00"),
            ("Resolved", "2026-11-03T23:59:59Z"),
            ("Resolved", "2026-11-04T13:00:00Z"),
            ("Resolved", "2026-11-05T00:00:00Z"),
            ("Open", "2026-11-04T01:00:00Z"),
        ]
        tickets = [
            SimpleNamespace(
                id=str(index),
                category="General",
                priority="Low",
                sentiment="Neutral",
                status=status,
                createdAt=now - timedelta(days=30),
                updatedAt=datetime.fromisoformat(
                    updated.replace("Z", "+00:00")
                ),
            )
            for index, (status, updated) in enumerate(updates)
        ]
        self.assertEqual(
            build_dashboard_summary(tickets, now).kpis.resolvedToday, 2
        )

    def test_final_decision_enforces_the_sla_for_every_priority(self):
        from pydantic import ValidationError

        from app.core.ticket_policy import SLA_BY_PRIORITY
        from app.mcp.prompts import build_ticket_triage_prompt

        for priority, sla in SLA_BY_PRIORITY.items():
            values = {**self.decision.model_dump(), "priority": priority}
            with self.subTest(priority=priority):
                result = self.decision_type.model_validate(
                    {**values, "sla": sla}
                )
                self.assertEqual(result.sla, sla)
                self.assertIn(
                    f"- {priority}: {sla}",
                    build_ticket_triage_prompt("MCP-TEST01"),
                )
                for invalid in ["whenever", "1d", *SLA_BY_PRIORITY.values()]:
                    if invalid != sla:
                        with self.assertRaises(ValidationError):
                            self.decision_type.model_validate(
                                {**values, "sla": invalid}
                            )

    def test_mcp_rejects_invalid_slas_before_updating_the_ticket(self):
        async def scenario():
            async with self.client_type() as wrapper:
                for sla in ["whenever", "1 day", "12h", "4h"]:
                    with self.subTest(sla=sla):
                        with self.assertRaisesRegex(RuntimeError, "failed"):
                            await wrapper.call_tool(
                                "set_ticket_priority",
                                {
                                    "ticket_id": "MCP-TEST01",
                                    "priority": "Very High",
                                    "sla": sla,
                                    "confidence": 0.9,
                                    "reason": "Test priority policy",
                                },
                            )

        asyncio.run(scenario())
        with self.database.SessionLocal() as db:
            ticket = db.get(self.ticket_model, "MCP-TEST01")
            self.assertEqual((ticket.priority, ticket.sla), ("Low", "1 day"))

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
            bulk = http.post(
                "/api/tickets/bulk",
                json={
                    "tickets": [payload],
                    "analyze": False,
                },
            )
            self.assertEqual(bulk.status_code, 201, bulk.text)
            for ticket in [single.json(), *bulk.json()["tickets"]]:
                value = datetime.fromisoformat(ticket["updatedAt"])
                self.assertIsNone(value.tzinfo)
                detail = http.get(f"/api/tickets/{ticket['id']}")
                self.assertEqual(detail.status_code, 200)
                self.assertEqual(
                    detail.json()["updatedAt"], ticket["updatedAt"]
                )
            self.assertEqual(http.get("/api/tickets").status_code, 200)
            dashboard = http.get("/api/dashboard/summary")
            self.assertEqual(dashboard.status_code, 200, dashboard.text)
            for item in dashboard.json()["workflowActivity"]:
                self.assertIsNone(datetime.fromisoformat(item["time"]).tzinfo)

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
            response = json.loads(
                messages.get(timeout=self.timeouts.OPERATION_TIMEOUT_SECONDS)
            )
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
            priority_tool = next(
                t for t in tools["tools"] if t["name"] == "set_ticket_priority"
            )
            self.assertEqual(
                set(priority_tool["inputSchema"]["properties"]),
                {"ticket_id", "priority", "sla", "confidence", "reason"},
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
                process.wait(timeout=self.timeouts.OPERATION_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=self.timeouts.OPERATION_TIMEOUT_SECONDS)
            reader.join(timeout=self.timeouts.OPERATION_TIMEOUT_SECONDS)
            stdout.close()
        self.assertEqual(process.returncode, 0)

    def test_direct_catalog_matches_current_mcp_definitions(self):
        path = (
            Path(__file__).resolve().parents[1]
            / "services/direct_ticket_catalog.json"
        )
        expected = json.loads(path.read_text(encoding="utf-8"))

        async def scenario():
            async with self.client_type() as client:
                self.assertEqual(await client.discover_catalog(), expected)

        asyncio.run(scenario())

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

    def model_call(self, name, arguments):
        call = SimpleNamespace(
            type="function_call",
            name=name,
            arguments=json.dumps(arguments),
            call_id=f"call_{name}_{arguments.get('uri', '')}",
        )
        return SimpleNamespace(
            status="completed",
            output=[call],
            output_text="",
            usage=None,
        )

    def final_response(self, decision=None):
        return SimpleNamespace(
            status="completed",
            output=[],
            output_text=(decision or self.decision).model_dump_json(),
            usage=None,
        )

    def saving_calls(self):
        return {
            "set_ticket_classification": {
                "ticket_id": "MCP-TEST01",
                "category": "API",
                "confidence": 0.95,
                "reason": "The customer reports an API outage.",
            },
            "set_ticket_sentiment": {
                "ticket_id": "MCP-TEST01",
                "sentiment": "Negative",
                "score": 0.9,
                "reason": "Work is blocked.",
            },
            "set_ticket_priority": {
                "ticket_id": "MCP-TEST01",
                "priority": "Very High",
                "sla": "1h",
                "confidence": 0.98,
                "reason": "Production orders are blocked.",
            },
            "save_response_draft": {
                "ticket_id": "MCP-TEST01",
                "draft": "We will review the reported API outage.",
                "requires_approval": True,
                "reason": "Requires human review.",
            },
        }

    def workflow_responses(self, order=None):
        calls = self.saving_calls()
        return [
            self.model_call(
                "read_mcp_resource",
                {
                    "uri": "ticket://MCP-TEST01/raw",
                },
            ),
            *[
                self.model_call(name, calls[name])
                for name in (order or TOOL_NAMES)
            ],
            self.final_response(),
        ]

    @contextmanager
    def model_responses(self, responses):
        """Mock OpenAI while using real discovery and stdio."""
        remaining = iter(responses)
        requests = []

        async def request(client, ticket_id, messages, tools):
            requests.append(copy.deepcopy((messages, tools)))
            response = next(remaining)
            if isinstance(response, BaseException):
                raise response
            return response

        with (
            patch.object(
                self.workflow, "get_openai_client", return_value=AsyncMock()
            ),
            patch.object(
                self.workflow, "request_ticket_step", side_effect=request
            ),
        ):
            yield requests

    def run_workflow(self):
        return asyncio.run(
            self.workflow.analyze_ticket_with_mcp_workflow("MCP-TEST01")
        )

    def test_model_selects_resources_and_tool_order_over_real_stdio(self):
        order = [
            "set_ticket_priority",
            "save_response_draft",
            "set_ticket_classification",
            "set_ticket_sentiment",
        ]
        responses = self.workflow_responses(order)
        responses.insert(
            2,
            self.model_call(
                "read_mcp_resource",
                {
                    "uri": "ticket://MCP-TEST01/history",
                },
            ),
        )
        with self.model_responses(responses) as requests:
            result = self.run_workflow()
        self.assertEqual([r["tool"] for r in result.mcpToolResults], order)
        self.assertEqual(
            result.mcpResourceReads,
            [
                "ticket://MCP-TEST01/raw",
                "ticket://MCP-TEST01/history",
            ],
        )
        first_messages, first_tools = requests[0]
        self.assertEqual(first_messages[0]["role"], "system")
        self.assertEqual(first_messages[1]["role"], "user")
        self.assertIn("Priority rules:", first_messages[1]["content"])
        self.assertNotIn("customers cannot place orders", str(first_messages))
        catalog = json.loads(first_messages[2]["content"])["catalog"]
        self.assertEqual(
            {t["name"] for t in catalog["tools"]}, set(TOOL_NAMES)
        )
        self.assertEqual(catalog["resources"][0]["uri"], "tickets://index")
        self.assertEqual(len(catalog["resourceTemplates"]), 5)
        for tool in catalog["tools"]:
            advertised = next(
                t for t in first_tools if t["name"] == tool["name"]
            )
            self.assertEqual(advertised["parameters"], tool["inputSchema"])
        outputs = [
            m
            for m in requests[1][0]
            if isinstance(m, dict) and m.get("type") == "function_call_output"
        ]
        self.assertEqual(outputs[0]["call_id"], responses[0].output[0].call_id)
        self.assertEqual(json.loads(outputs[0]["output"])["id"], "MCP-TEST01")
        # The later model request sees actual results from the server.
        final_outputs = [
            m
            for m in requests[-1][0]
            if isinstance(m, dict) and m.get("type") == "function_call_output"
        ]
        self.assertEqual(len(final_outputs), 6)
        self.assertEqual(
            json.loads(final_outputs[1]["output"])["isError"], False
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

    def test_openai_request_has_tools_and_strict_final_decision(self):
        from app.ai import openai_client

        client = AsyncMock()
        client.responses.create.return_value = SimpleNamespace(
            id="test", usage=None
        )
        messages = [{"role": "user", "content": "Test task"}]
        tools = [{"type": "function", "name": "test_tool"}]
        asyncio.run(
            openai_client.request_ticket_step(
                client,
                "MCP-TEST01",
                messages,
                tools,
            )
        )
        request = client.responses.create.call_args.kwargs
        self.assertEqual(request["input"], messages)
        self.assertEqual(request["tools"], tools)
        self.assertEqual(request["tool_choice"], "auto")
        self.assertIs(request["parallel_tool_calls"], True)
        schema = request["text"]["format"]["schema"]
        self.assertIs(schema["additionalProperties"], False)
        self.assertNotIn("customerIntent", schema["properties"])

    def test_real_openai_sdk_round_trip_with_offline_http_transport(self):
        import httpx2
        from openai import AsyncOpenAI

        responses = iter(self.workflow_responses())
        requests = []

        def respond(request):
            payload = json.loads(request.content)
            requests.append(payload)
            step = next(responses)
            if step.output:
                call = step.output[0]
                output = [
                    {
                        "type": "function_call",
                        "id": f"fc_{len(requests)}",
                        "call_id": call.call_id,
                        "name": call.name,
                        "arguments": call.arguments,
                        "status": "completed",
                    }
                ]
            else:
                output = [
                    {
                        "type": "message",
                        "id": "msg_final",
                        "role": "assistant",
                        "status": "completed",
                        "content": [
                            {
                                "type": "output_text",
                                "text": step.output_text,
                                "annotations": [],
                            }
                        ],
                    }
                ]
            return httpx2.Response(
                200,
                json={
                    "id": f"resp_{len(requests)}",
                    "object": "response",
                    "created_at": 0,
                    "model": payload["model"],
                    "status": "completed",
                    "output": output,
                    "usage": {
                        "input_tokens": 100 * len(requests),
                        "output_tokens": 10 * len(requests),
                        "total_tokens": 110 * len(requests),
                    },
                },
            )

        client = AsyncOpenAI(
            api_key="offline-test-key",
            http_client=httpx2.AsyncClient(
                transport=httpx2.MockTransport(respond)
            ),
        )
        with patch.object(
            self.workflow, "get_openai_client", return_value=client
        ):
            result = self.run_workflow()
        self.assertEqual(result.decision, self.decision)
        self.assertEqual(len(requests), 6)
        self.assertEqual(requests[0]["tool_choice"], "auto")
        self.assertIs(requests[0]["parallel_tool_calls"], True)
        self.assertEqual(
            requests[1]["input"][-1]["type"], "function_call_output"
        )
        self.assertIn("API is down", requests[1]["input"][-1]["output"])
        self.assertEqual(
            result.usage.model_dump(),
            {
                "input_tokens": 2100,
                "output_tokens": 210,
                "total_tokens": 2310,
            },
        )

    def test_usage_counts_requests_including_batched_tools_and_final(self):
        from fastapi.testclient import TestClient

        from app.app import app

        calls = self.saving_calls()
        batch = self.model_call("unused", {})
        batch.output = [
            self.model_call(name, arguments).output[0]
            for name, arguments in calls.items()
        ]
        responses = [
            self.workflow_responses()[0],
            batch,
            self.final_response(),
        ]
        for response, input_tokens, output_tokens in zip(
            responses, [10, 20, 30], [3, 5, 7]
        ):
            response.usage = SimpleNamespace(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
            )
        with (
            TestClient(app) as http,
            self.model_responses(responses) as requests,
        ):
            result = http.post("/api/tickets/MCP-TEST01/analyze")
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(len(requests), 3)
        self.assertEqual(len(result.json()["mcpToolResults"]), 4)
        self.assertEqual(
            result.json()["usage"],
            {"input_tokens": 60, "output_tokens": 15, "total_tokens": 75},
        )

    def test_usage_is_unavailable_when_a_round_has_no_usage(self):
        responses = self.workflow_responses()
        for response in responses[:-1]:
            response.usage = SimpleNamespace(
                input_tokens=10, output_tokens=2, total_tokens=12
            )
        with self.model_responses(responses):
            result = self.run_workflow()
        self.assertIsNone(result.usage)

    def test_catalog_discovery_handles_pagination(self):
        wrapper = self.client_type()
        wrapper.client = AsyncMock()

        def page(key, items, cursor=None):
            return SimpleNamespace(
                next_cursor=cursor,
                model_dump=lambda **kwargs: {key: items},
            )

        wrapper.client.list_tools.side_effect = [
            page("tools", [{"name": "first"}], "page2"),
            page("tools", [{"name": "second"}]),
        ]
        wrapper.client.list_resources.return_value = page("resources", [])
        wrapper.client.list_resource_templates.return_value = page(
            "resourceTemplates", []
        )
        catalog = asyncio.run(wrapper.discover_catalog())
        self.assertEqual(
            [t["name"] for t in catalog["tools"]], ["first", "second"]
        )
        self.assertEqual(
            wrapper.client.list_tools.call_args.kwargs, {"cursor": "page2"}
        )

    def test_prompt_does_not_fetch_ticket_data(self):
        async def scenario():
            async with self.client_type() as wrapper:
                # A nonexistent ticket still has a valid task template.
                messages = await wrapper.get_prompt_messages(
                    "ticket_triage_prompt", {"ticket_id": "MISSING"}
                )
                self.assertIn("MISSING", messages[0].content.text)
                self.assertNotIn("Ticket JSON:", messages[0].content.text)

        asyncio.run(scenario())

    def test_model_cannot_read_other_tickets_or_global_index(self):
        from jsonschema import ValidationError

        for uri in ["ticket://OTHER/raw", "tickets://index"]:
            with (
                self.subTest(uri=uri),
                self.model_responses(
                    [self.model_call("read_mcp_resource", {"uri": uri})]
                ),
            ):
                with self.assertRaises(ValidationError):
                    self.run_workflow()

    def test_model_must_read_raw_before_writes_or_completion(self):
        for response in [
            self.model_call(
                "save_response_draft",
                self.saving_calls()["save_response_draft"],
            ),
            self.final_response(),
        ]:
            with (
                self.subTest(response=response),
                self.model_responses([response]),
            ):
                with self.assertRaisesRegex(RuntimeError, "raw ticket"):
                    self.run_workflow()
        with self.database.SessionLocal() as db:
            self.assertEqual(db.query(self.draft_model).count(), 0)

    def test_invalid_tool_arguments_stop_before_writes(self):
        from jsonschema import ValidationError

        cases = [
            (
                "set_ticket_classification",
                {"category": "Invalid"},
                ValidationError,
            ),
            ("set_ticket_priority", {"ticket_id": "OTHER"}, ValueError),
            (
                "save_response_draft",
                {"requires_approval": False},
                ValidationError,
            ),
        ]
        raw = self.workflow_responses()[0]
        for name, changes, error_type in cases:
            arguments = {**self.saving_calls()[name], **changes}
            with (
                self.subTest(name=name),
                self.model_responses(
                    [
                        raw,
                        self.model_call(name, arguments),
                    ]
                ),
            ):
                with self.assertRaises(error_type):
                    self.run_workflow()
        with self.database.SessionLocal() as db:
            self.assertEqual(db.query(self.draft_model).count(), 0)
            ticket = db.get(self.ticket_model, "MCP-TEST01")
            self.assertEqual(
                (ticket.category, ticket.priority), ("General", "Low")
            )

    def test_duplicate_draft_is_rejected(self):
        draft = self.model_call(
            "save_response_draft", self.saving_calls()["save_response_draft"]
        )
        with self.model_responses(
            [self.workflow_responses()[0], draft, draft]
        ):
            with self.assertRaisesRegex(RuntimeError, "Duplicate MCP save"):
                self.run_workflow()
        with self.database.SessionLocal() as db:
            self.assertEqual(db.query(self.draft_model).count(), 1)

    def test_early_completion_is_rejected(self):
        with self.model_responses(
            [
                self.workflow_responses()[0],
                self.final_response(),
            ]
        ):
            with self.assertRaisesRegex(RuntimeError, "Missing successful"):
                self.run_workflow()

    def test_final_decision_must_match_successful_saves(self):
        responses = self.workflow_responses()
        responses[-1] = self.final_response(
            self.decision.model_copy(update={"category": "Billing"})
        )
        with self.model_responses(responses):
            with self.assertRaisesRegex(RuntimeError, "differs from saved"):
                self.run_workflow()

    def test_round_limit_and_incomplete_responses(self):
        for responses, message in [
            ([self.workflow_responses()[0]] * 2, "round limit"),
            ([SimpleNamespace(status="incomplete")], "incomplete"),
        ]:
            with (
                self.subTest(message=message),
                patch.object(self.workflow, "MAX_MODEL_ROUNDS", 2),
                self.model_responses(responses),
            ):
                with self.assertRaisesRegex(RuntimeError, message):
                    self.run_workflow()

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

    def test_rest_api_analysis_and_bulk_creation(self):
        from fastapi.testclient import TestClient

        from app.app import app

        with (
            TestClient(app) as http,
            self.model_responses(self.workflow_responses()),
            patch.dict(os.environ, {"DEBUG": "True"}),
        ):
            response = http.post("/api/tickets/MCP-TEST01/analyze")
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(len(response.json()["mcpToolResults"]), 4)
            self.assertIsNone(response.json()["usage"])
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
            self.model_responses([asyncio.TimeoutError()]),
        ):
            response = http.post("/api/tickets/MCP-TEST01/analyze")
            self.assertEqual(response.status_code, 504, response.text)
        with self.database.SessionLocal() as db:
            self.assertEqual(db.query(self.draft_model).count(), 0)

    def test_operation_timeout_is_shared_by_mcp_model_and_database(self):
        from sqlalchemy import text

        from app.ai.openai_client import get_openai_client

        async def scenario():
            async with self.client_type() as wrapper:
                self.assertEqual(
                    wrapper.require_client().read_timeout_seconds, 60
                )
            with patch.dict(os.environ, {"OPENAI_API_KEY": "offline-test"}):
                async with get_openai_client() as client:
                    self.assertEqual(client.timeout, 60)
                    self.assertEqual(client.max_retries, 0)

        asyncio.run(scenario())
        self.assertEqual(self.workflow.run_step.__defaults__, (60,))
        with self.database.engine.connect() as connection:
            self.assertEqual(
                connection.scalar(text("PRAGMA busy_timeout")), 60_000
            )

    def test_overall_timeout_cancels_analysis_and_returns_504(self):
        from fastapi.testclient import TestClient

        from app.api.routes import tickets
        from app.app import app

        cancelled = []

        async def stalled_analysis(ticket_id):
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.append(ticket_id)

        self.assertEqual(tickets.ANALYSIS_TIMEOUT_SECONDS, 300)
        with (
            TestClient(app) as http,
            patch.object(tickets, "ANALYSIS_TIMEOUT_SECONDS", 0.01),
            patch.object(
                tickets,
                "analyze_ticket_with_mcp_workflow",
                side_effect=stalled_analysis,
            ),
        ):
            response = http.post("/api/tickets/MCP-TEST01/analyze")
        self.assertEqual(response.status_code, 504)
        self.assertEqual(cancelled, ["MCP-TEST01"])


if __name__ == "__main__":
    unittest.main()
