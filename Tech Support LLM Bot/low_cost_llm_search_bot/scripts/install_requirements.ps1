# Creates a Python virtual environment and installs dependencies.
Set-Location "C:\RAGAssistant"
python -m venv .venv
& "C:\RAGAssistant\.venv\Scripts\python.exe" -m pip install --upgrade pip
& "C:\RAGAssistant\.venv\Scripts\pip.exe" install -r requirements.txt
