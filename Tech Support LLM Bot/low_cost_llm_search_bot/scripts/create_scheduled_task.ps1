# Creates a startup scheduled task for the backend. Run as administrator.
# Replace DOMAIN\rag-svc with the approved service account before use.
$TaskName = "Cybersecurity AI Assistant Backend"
$ScriptPath = "C:\RAGAssistant\scripts\run_backend.ps1"
$ServiceAccount = "DOMAIN\rag-svc"

$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`""
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -User $ServiceAccount -RunLevel LeastPrivilege
Write-Host "Created scheduled task: $TaskName"
