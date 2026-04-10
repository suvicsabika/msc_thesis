$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\mcp-backend'; npx -y @modelcontextprotocol/inspector .venv\Scripts\python.exe -m mcp_server.server"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\mcp-frontend'; npm run dev"