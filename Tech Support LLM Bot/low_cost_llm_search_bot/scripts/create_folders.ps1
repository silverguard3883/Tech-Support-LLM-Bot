# Creates the default Windows folder structure for the assistant.
$Base = "C:\RAGAssistant"
$Folders = @(
    $Base,
    "$Base\data\documents",
    "$Base\data\sqlite",
    "$Base\data\logs",
    "$Base\data\quarantine",
    "$Base\scripts"
)

foreach ($Folder in $Folders) {
    New-Item -ItemType Directory -Force -Path $Folder | Out-Null
}

Write-Host "Created assistant folders under $Base"
