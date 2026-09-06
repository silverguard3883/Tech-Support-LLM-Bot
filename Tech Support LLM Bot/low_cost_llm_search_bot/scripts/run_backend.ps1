# Starts the FastAPI backend on localhost for IIS reverse proxying.
$ErrorActionPreference = "Stop"
Set-Location "C:\RAGAssistant"
$env:PYTHONPATH = "C:\RAGAssistant"

& "C:\RAGAssistant\.venv\Scripts\python.exe" -m uvicorn app.main:app `
    --host 127.0.0.1 `
    --port 8088 `
    --proxy-headers `
    --forwarded-allow-ips "127.0.0.1"
