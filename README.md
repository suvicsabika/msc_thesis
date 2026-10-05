# MCP Ticket Analyzer Prototype

Full-stack prototype for an MCP-based customer support ticket analyzer.

## Tech Stack

- Frontend: React, Tailwind CSS, Vite
- Backend: FastAPI, SQLAlchemy, SQLite, Pydantic
- AI/MCP: official MCP Python SDK 2.3.0 (`MCPServer`, `Client`), MCP protocol 2026-07-28, OpenAI Responses API

## Setup

### Backend

```bash
cd backend
py -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
```

Requires Python 3.10 or newer. Create backend/app/.env:

```bash
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4.1-nano
```

Run backend manually:

```bash
venv\Scripts\python.exe -m uvicorn app.app:app --reload --port 8000
```

### API docs:

```bash
http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend URL:

```bash
http://localhost:5173
```

Run Everything from the project root:

```bash
.\run_all.ps1
```

If PowerShell *blocks* the script:

```bash
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\run_all.ps1
```

### MCP Inspector

From the backend folder:

```bash
+.\venv\Scripts\Activate.ps1
npx @modelcontextprotocol/inspector --config .\mcp.inspector.json --server ticket
 ```
 
The configuration selects the Inspector's **modern** protocol era. When launching
the Inspector with a positional Python command instead, select **Protocol Era:
modern** in Server Settings. A legacy connection uses the old initialization
handshake and does not verify the 2026-07-28 protocol.

Expected discovery: five tools, one fixed resource (`tickets://index`), five
resource templates, and two prompts. Ticket-specific resources appear under
**Templates**, not the fixed URI list.


### Main Workflow

1. User creates a support ticket.
2. FastAPI saves it into SQLite.
3. The host workflow starts automatically and connects its SDK client over stdio.
 -  SDK v2 discovers the server with `server/discover`; the host verifies protocol 2026-07-28.
4. The MCP client reads ticket resources from the MCP server.
5. OpenAI returns a structured triage decision.
 -  Customer intent is returned by its existing tool but is not yet stored.
 -  A tool error stops the remaining workflow steps; drafts always require human approval.

6. MCP tools persist category, sentiment, priority, SLA, and draft response.
7. The dashboard and ticket detail page show the updated result.

### Main Endpoints

```bash
GET  /api/health
GET  /api/tickets
POST /api/tickets
POST /api/tickets/bulk  # DEBUG=True required
GET  /api/tickets/{ticket_id}
POST /api/tickets/{ticket_id}/analyze
GET  /api/tickets/{ticket_id}/draft
GET  /api/dashboard/summary
```