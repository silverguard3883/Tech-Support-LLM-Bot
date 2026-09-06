# Basic health checks from the Windows server.
$BaseUrl = "http://127.0.0.1:8088"
Invoke-RestMethod -Uri "$BaseUrl/api/health"
Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags"
