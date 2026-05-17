# MCP Ticket Analyzer Prototype

Full-stack prototype for an MCP-based customer support ticket analyzer.

## Tech Stack

- Frontend: React, Tailwind CSS, Vite
- Backend: FastAPI, SQLAlchemy, SQLite, Pydantic
- AI/MCP: Model Context Protocol Python SDK, FastMCP, OpenAI Responses API

## Setup

### Backend

```bash
cd backend
py -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
```

Create backend/.env:

```bash
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4.1-nano
OPENAI_DRAFT_MODEL=gpt-4.1-mini
```

Run backend manually:

```bash
venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
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
.\run.all.ps1
```

If PowerShell *blocks* the script:

```bash
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\run.all.ps1
```

### MCP Inspector

From the backend folder:

```bash
npx @modelcontextprotocol/inspector .\venv\Scripts\python.exe -m app.mcp.ticket_server
```

### Main Workflow

1. User creates a support ticket.
2. FastAPI saves it into SQLite.
3. The MCP workflow starts automatically.
4. The MCP client reads ticket resources from the MCP server.
5. OpenAI returns a structured triage decision.
6. MCP tools persist category, sentiment, priority, SLA, and draft response.
7. The dashboard and ticket detail page show the updated result.

### Main Endpoints

```bash
GET  /api/health
GET  /api/tickets
POST /api/tickets
GET  /api/tickets/{ticket_id}
POST /api/tickets/{ticket_id}/analyze
GET  /api/tickets/{ticket_id}/draft
GET  /api/dashboard/summary
```