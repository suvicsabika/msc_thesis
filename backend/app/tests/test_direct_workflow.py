"""Verify direct analysis with MCP imports forbidden."""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def direct_scenario(backend, scenario):
    import asyncio
    import builtins
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    sys.path.insert(0, backend)
    original_import = builtins.__import__

    def no_mcp(name, *args, **kwargs):
        if name == "mcp" or name.startswith(("mcp.", "app.mcp")):
            raise AssertionError(f"Direct analysis imported {name}")
        return original_import(name, *args, **kwargs)

    builtins.__import__ = no_mcp
    from app.ai.schemas import TicketTriageDecision
    from app.db.database import SessionLocal, engine
    from app.db.init_db import create_db_and_tables
    from app.models.response_draft import ResponseDraftModel
    from app.models.ticket import TicketModel
    from app.services import ticket_analysis_workflow as workflow
    from app.services.direct_ticket_client import (
        DirectTicketClient,
        analyze_ticket_with_direct_workflow,
    )

    create_db_and_tables()
    with SessionLocal() as db:
        db.add(
            TicketModel(
                id="DIRECT-TEST",
                subject="API outage",
                body="Orders blocked",
                customer="Test",
                customerEmail="test@example.com",
            )
        )
        db.commit()
    decision = TicketTriageDecision(
        category="API",
        classificationConfidence=0.9,
        classificationReason="API outage",
        sentiment="Neutral",
        sentimentScore=0.5,
        sentimentReason="Factual report",
        priority="Very High",
        sla="1h",
        priorityConfidence=0.9,
        priorityReason="Orders blocked",
        responseDraft="We will review this.",
        requiresApproval=True,
        responseDraftReason="Human review",
        reasoningSummary="API outage",
    )
    arguments = {
        "set_ticket_classification": {
            "ticket_id": "DIRECT-TEST",
            "category": decision.category,
            "confidence": decision.classificationConfidence,
            "reason": decision.classificationReason,
        },
        "set_ticket_sentiment": {
            "ticket_id": "DIRECT-TEST",
            "sentiment": decision.sentiment,
            "score": decision.sentimentScore,
            "reason": decision.sentimentReason,
        },
        "set_ticket_priority": {
            "ticket_id": "DIRECT-TEST",
            "priority": decision.priority,
            "sla": decision.sla,
            "confidence": decision.priorityConfidence,
            "reason": decision.priorityReason,
        },
        "save_response_draft": {
            "ticket_id": "DIRECT-TEST",
            "draft": decision.responseDraft,
            "requires_approval": True,
            "reason": decision.responseDraftReason,
        },
    }

    def call(name, values):
        return SimpleNamespace(
            type="function_call",
            name=name,
            arguments=json.dumps(values),
            call_id=name,
        )

    calls = [call("read_mcp_resource", {"uri": "ticket://DIRECT-TEST/raw"})]
    calls.extend(call(name, values) for name, values in arguments.items())
    if scenario == "scope":
        calls[0] = call("read_mcp_resource", {"uri": "ticket://OTHER/raw"})
    if scenario == "read_first":
        calls.pop(0)
    responses = [
        SimpleNamespace(status="completed", output=calls, usage=None),
        SimpleNamespace(
            status="completed",
            output=[],
            usage=None,
            output_text=decision.model_dump_json(),
        ),
    ]

    async def run():
        with (
            patch.object(
                workflow, "get_openai_client", return_value=AsyncMock()
            ),
            patch.object(
                workflow, "request_ticket_step", side_effect=responses
            ),
            patch(
                "asyncio.create_subprocess_exec", side_effect=AssertionError
            ),
        ):
            if scenario in {"scope", "read_first"}:
                try:
                    await analyze_ticket_with_direct_workflow("DIRECT-TEST")
                except Exception:
                    pass
                else:
                    raise AssertionError("Expected a rejected operation")
                with SessionLocal() as db:
                    assert (
                        db.get(TicketModel, "DIRECT-TEST").category
                        == "General"
                    )
                    assert db.query(ResponseDraftModel).count() == 0
                return
            result = await analyze_ticket_with_direct_workflow("DIRECT-TEST")
            assert result.transport == "direct"
            assert result.decision == decision
            assert len(result.mcpToolResults) == 4
            assert result.mcpResourceReads == ["ticket://DIRECT-TEST/raw"]
            assert result.usage is None
            client = DirectTicketClient()
            for suffix in [
                "raw",
                "classification",
                "priority",
                "history",
                "draft_response",
            ]:
                json.loads(
                    await client.read_resource_text(
                        f"ticket://DIRECT-TEST/{suffix}"
                    )
                )
            with SessionLocal() as db:
                assert (
                    db.get(TicketModel, "DIRECT-TEST").priority == "Very High"
                )
                assert db.query(ResponseDraftModel).one().requiresApproval
            # The HTTP selector must dispatch to the direct workflow.
            from app.api.routes.tickets import analyze_ticket

            with patch(
                "app.api.routes.tickets.run_ticket_analysis",
                side_effect=AssertionError,
            ):
                with SessionLocal() as db:
                    # Mock responses again for a fresh full analysis.
                    with patch.object(
                        workflow, "request_ticket_step", side_effect=responses
                    ):
                        assert (
                            await analyze_ticket("DIRECT-TEST", db, "direct")
                        ).transport == "direct"

    try:
        asyncio.run(run())
        assert not any(
            name == "mcp" or name.startswith("mcp.") for name in sys.modules
        )
    finally:
        engine.dispose()


class DirectWorkflowTests(unittest.TestCase):
    def test_direct_workflow_and_http_selector_without_mcp(self):
        self.run_scenario("success")

    def test_direct_workflow_rejects_other_ticket_resources(self):
        self.run_scenario("scope")

    def test_direct_workflow_requires_read_before_save(self):
        self.run_scenario("read_first")

    def run_scenario(self, scenario):
        with tempfile.TemporaryDirectory(prefix="ticket-direct-test-") as tmp:
            backend = Path(tmp) / "backend"
            source = Path(__file__).resolve().parents[1]
            for path in source.rglob("*"):
                if path.is_file() and path.suffix == ".py":
                    target = backend / "app" / path.relative_to(source)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, target)
            catalog = source / "services/direct_ticket_catalog.json"
            shutil.copyfile(catalog, backend / "app/services" / catalog.name)
            result = subprocess.run(
                [
                    sys.executable,
                    __file__,
                    "--scenario",
                    str(backend),
                    scenario,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(
                result.returncode, 0, result.stdout + result.stderr
            )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--scenario":
        direct_scenario(sys.argv[2], sys.argv[3])
    else:
        unittest.main()
