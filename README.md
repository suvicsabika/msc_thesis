# MCP Ticket Analyzer

A support ticket triage prototype built with React, FastAPI, SQLite,
OpenAI Responses API and MCP Python SDK 2.2.0 (protocol 2026-07-28).
It assigns a category, sentiment, priority and SLA target, then saves a reply draft.

## Setup

The commands below use Windows PowerShell. Install Python 3.11+ and a Node.js
version supported by Vite: `^20.19.0 || >=22.12.0`.

### Backend

From the project root:

```powershell
cd backend
py -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

This installs the app, notebook dependencies and lint tools.
Create `app/.env` inside the `backend` folder with:

```dotenv
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-6-luna
```

From the `backend` folder, start the API:

```powershell
.\venv\Scripts\python.exe -m uvicorn app.app:app --reload --port 8000
```

The API documentation is at [localhost:8000/docs](http://localhost:8000/docs).

### Frontend

Open another terminal at the project root:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Open [localhost:5173](http://localhost:5173). The frontend uses
`http://localhost:8000` by default; `VITE_API_BASE_URL` overrides it.

After setup, `run_all.ps1` starts the backend, frontend and MCP Inspector together:

```powershell
.\run_all.ps1
```

If PowerShell blocks the script, run
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal first.

### MCP Inspector

To start the Inspector separately, run from `backend`:

```powershell
.\venv\Scripts\Activate.ps1
npx.cmd @modelcontextprotocol/inspector --config .\mcp.inspector.json --server mcp-ticket-analyzer
```

The config uses the modern protocol era. The server exposes four tools,
`tickets://index`, five resource templates and `ticket_triage_prompt`.
Ticket-specific resources appear under **Templates**.

## How analysis works

1. Creating a ticket starts analysis in the background. Existing tickets can be
   analyzed again from the dashboard or detail page.
2. The host connects to the MCP server over stdio and discovers its tools,
   resources and prompt.
3. The model reads ticket data through `read_mcp_resource`, a host adapter for
   MCP resource reads.
4. The model chooses the order of the four saving tools: category, sentiment,
   priority/SLA and reply draft.
5. The host checks that the final decision matches the saved values and returns
   the result to the frontend.

The host validates arguments, limits access to the current ticket and rejects
repeated saves. The raw ticket resource must be read before any writes.
If a step fails, the run stops; earlier writes remain saved.

Timeouts are defined in [timeouts.py](backend/app/core/timeouts.py):

| Operation | Limit |
| --- | --- |
| MCP requests, model requests and workflow steps | 60 s |
| SQLite lock waits and Git metadata lookup | 60 s |
| Complete analysis | 300 s |
| Evaluation HTTP connection / response read | 60 / 360 s |

The MCP SDK has a separate 10-second discovery limit. Each analysis allows
up to 12 model rounds, and bulk analysis runs at most three tickets concurrently.

## Evaluation

Open the notebooks in VS Code and select the backend virtual environment as
the Python kernel.

| Notebook | Purpose |
| --- | --- |
| [MCP evaluation](backend/app/validation/ticket_classification_evaluation.ipynb) | Three runs of the 100-ticket reference dataset through MCP |
| [Direct evaluation](backend/app/validation/ticket_classification_evaluation_direct.ipynb) | The same workflow using Python calls without MCP transport |
| [Comparison](backend/app/validation/ticket_classification_comparison.ipynb) | Compare the saved results from both methods |

Leave `RUN_ANALYSIS=False` to rebuild reports without model requests.
The comparison notebook only reads saved experiments.
It compares accuracy, macro-F1, latency, token usage, estimated costs and
recorded resource/write counts.

[evaluation_runner.py](backend/app/validation/evaluation_runner.py) collects
responses; [evaluation_reporting.py](backend/app/validation/evaluation_reporting.py)
builds reports and estimates costs from recorded tokens.
Responses are kept in each run's `results.json`. Missing token usage stays missing,
and costs use standard uncached rates recorded in the reporting module.

The saved runs do not contain exact model/API request counts or component timings.
Latency covers a complete `/analyze` request, including model rounds and local
processing. Differences between methods cannot be attributed entirely to MCP.

### Collecting new runs

Set `EXPERIMENT_DIR` to a new folder in the relevant evaluation notebook and
check `OPENAI_MODEL` before collecting. Start the backend from the project root:

```powershell
$env:DEBUG = "True"
.\backend\venv\Scripts\python.exe -m uvicorn app.app:app --app-dir backend --host 127.0.0.1 --port 8001
```

Set `RUN_ANALYSIS=True` in that notebook and run all cells. For direct evaluation,
you can also run this command in another terminal at the project root:

```powershell
.\backend\venv\Scripts\python.exe backend/app/validation/run_direct_evaluation.py --collect
```

Each evaluation notebook collects 3 x 100 analyses and makes paid model requests.
Existing attempts are reused, and failed attempts are not retried automatically.
Switch `RUN_ANALYSIS` back to `False` afterward. Update `EXPERIMENTS` in the
comparison notebook to point to the new folders when comparing new runs.

## SLA rules and prototype limits

Priority sets the SLA target: Low = `1 day`, Medium = `12h`, High = `4h`,
Very High = `1h`. Writes and final decisions reject mismatched values.

The frontend calculates deadlines from `createdAt` and the SLA duration.
Unresolved tickets are **Due Soon** during the final 20% of their SLA window
and **At Risk** once overdue. Counts and colors refresh every minute.
High Priority counts include High and Very High tickets.

The SLA trend uses currently unresolved tickets, rather than a historical breach
log. `resolvedToday` uses the last update date as a proxy for resolution time.
The history resource returns a creation/current-status summary, not an event log.
Drafts require human review, but the **Approve draft** button has no action yet.

## Development checks

From the project root:

```powershell
.\backend\venv\Scripts\python.exe -m ruff check backend/app
.\backend\venv\Scripts\python.exe -m ruff format --check backend/app
.\backend\venv\Scripts\python.exe -m unittest discover -s backend/app/tests -v
```

From `frontend`:

```powershell
npm.cmd run lint
npm.cmd run format:check
npm.cmd test
npm.cmd run build
```

To apply formatting, remove `--check` from the Ruff formatting command above,
or run `npm.cmd run format` from `frontend`.

The sample bulk-upload payload is
[bulk_tickets_100.json](backend/app/validation/bulk_tickets_100.json).
`POST /api/tickets/bulk` requires `DEBUG=True`; the supplied payload uses
`analyze=false`, so uploading it does not start model requests:

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8000/api/tickets/bulk" `
  -Method Post `
  -ContentType "application/json" `
  -InFile ".\backend\app\data\bulk_tickets_100.json"
```
