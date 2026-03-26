$portablePython = Join-Path $PSScriptRoot "tools\python312\python.exe"

if (Test-Path $portablePython) {
    & $portablePython (Join-Path $PSScriptRoot "main.py")
    exit $LASTEXITCODE
}

$systemPython = Get-Command python -ErrorAction SilentlyContinue
if ($systemPython) {
    & $systemPython.Source (Join-Path $PSScriptRoot "main.py")
    exit $LASTEXITCODE
}

throw "Python not found. Install Python or place portable Python at tools\\python312\\python.exe"
