"""Optional API collection for the evaluation notebook."""

import hashlib
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from time import perf_counter

import requests

from app.core.timeouts import (
    EVALUATION_READ_TIMEOUT_SECONDS,
    OPERATION_TIMEOUT_SECONDS,
)


def now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    temporary.replace(path)


def backend_version(root):
    """Record local source files; the running server must match them."""
    source_hash = hashlib.sha256()
    for path in sorted((root / "backend/app").rglob("*.py")):
        source_hash.update(str(path.relative_to(root)).encode())
        source_hash.update(path.read_bytes())
    try:
        commit = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=OPERATION_TIMEOUT_SECONDS,
        ).strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        commit = "unavailable"
    return {
        "backend_source_hash": source_hash.hexdigest(),
        "backend_commit": commit,
    }


def post(base_url, path, payload=None):
    response = requests.post(
        base_url + path,
        json=payload,
        timeout=(OPERATION_TIMEOUT_SECONDS, EVALUATION_READ_TIMEOUT_SECONDS),
    )
    response.raise_for_status()
    return response.json()


def create_tickets(tickets, base_url):
    fields = ["subject", "body", "customer", "customerEmail"]
    payload = []
    for ticket in tickets:
        item = {field: ticket[field] for field in fields}
        item["category"] = "General"
        payload.append(item)
    uploaded = post(
        base_url, "/api/tickets/bulk", {"analyze": False, "tickets": payload}
    )
    assert uploaded["analysisScheduled"] is False
    created = uploaded["tickets"]
    assert len(created) == len(tickets)
    assert len({ticket["id"] for ticket in created}) == len(tickets)
    for reference, actual in zip(tickets, created):
        assert reference["subject"] == actual["subject"]
        assert reference["body"] == actual["body"]
    return {
        reference["id"]: actual["id"]
        for reference, actual in zip(tickets, created)
    }


def execute_run(run_dir, tickets, settings):
    """Save each attempt once, including failures and interruptions."""
    path = run_dir / "results.json"
    if path.exists():
        saved = read_json(path)
    else:
        saved = {
            "settings": settings,
            "started_at": now(),
            "creation_started": False,
            "ticket_ids": {},
            "results": {},
            "sessions": [],
        }
    assert saved["settings"] == settings, (
        "Settings changed: choose a new EXPERIMENT_DIR."
    )
    if len(saved["results"]) == len(tickets):
        print(run_dir.name, "- reusing saved attempts")
        return saved

    started = perf_counter()
    session = {
        "started_at": now(),
        "status": "interrupted",
        "wall_seconds": None,
    }
    saved["sessions"].append(session)
    lock = Lock()
    write_json(path, saved)
    try:
        if not saved["ticket_ids"]:
            assert not saved["creation_started"], (
                "Uncertain previous bulk upload: inspect the backend."
            )
            saved["creation_started"] = True
            write_json(path, saved)
            saved["ticket_ids"] = create_tickets(tickets, settings["base_url"])
            write_json(path, saved)

        def analyze(ticket):
            key = ticket["id"]
            record = {"status": "interrupted", "started_at": now()}
            with lock:
                saved["results"][key] = record.copy()
                write_json(path, saved)
            started_request = perf_counter()
            try:
                route = f"/api/tickets/{saved['ticket_ids'][key]}/analyze"
                if settings.get("transport") == "direct":
                    route += "?transport=direct"
                response = post(
                    settings["base_url"],
                    route,
                )
                record["response"] = response
                if settings.get("transport") == "direct":
                    assert response.get("transport") == "direct", (
                        "Backend did not confirm direct execution. "
                        "Restart the updated backend."
                    )
                for field, labels in settings["labels"].items():
                    assert response["decision"].get(field) in labels, (
                        "Invalid decision"
                    )
                record["status"] = "success"
            except Exception as error:
                record.update(status="failed", error=str(error))
            finally:
                record["finished_at"] = now()
                record["analysis_seconds"] = perf_counter() - started_request
            with lock:
                saved["results"][key] = record
                write_json(path, saved)
            return key, record

        pending = [t for t in tickets if t["id"] not in saved["results"]]
        with ThreadPoolExecutor(max_workers=settings["concurrency"]) as pool:
            futures = [pool.submit(analyze, ticket) for ticket in pending]
            for future in as_completed(futures):
                key, record = future.result()
                print(
                    f"{run_dir.name}: {key} - {record['status']} "
                    f"({record['analysis_seconds']:.2f}s)"
                )
        session["status"] = "finished"
        saved["finished_at"] = now()
    finally:
        session["finished_at"] = now()
        session["wall_seconds"] = perf_counter() - started
        write_json(path, saved)
    return saved


def run_experiment(run_dirs, tickets, settings):
    assert settings["model"] and settings["experiment_note"].strip(), (
        "Verify MODEL and fill in EXPERIMENT_NOTE first."
    )
    if settings.get("transport") == "direct":
        # An older backend could ignore the query and start MCP instead.
        response = requests.get(
            settings["base_url"] + "/openapi.json",
            timeout=(OPERATION_TIMEOUT_SECONDS, OPERATION_TIMEOUT_SECONDS),
        )
        response.raise_for_status()
        parameters = response.json()["paths"][
            "/api/tickets/{ticket_id}/analyze"
        ]["post"].get("parameters", [])
        assert any(
            p["name"] == "transport"
            and p["in"] == "query"
            and "direct" in p.get("schema", {}).get("enum", [])
            for p in parameters
        ), "Backend lacks direct transport support; restart it first."
    manifest = run_dirs[0].parent / "experiment.json"
    if manifest.exists():
        assert read_json(manifest)["settings"] == settings, (
            "Use a new EXPERIMENT_DIR."
        )
    else:
        write_json(manifest, {"settings": settings, "created_at": now()})
    for run_dir in run_dirs:
        execute_run(run_dir, tickets, settings)
