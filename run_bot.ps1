$projectRoot = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$portablePython = Join-Path $projectRoot "tools\python312\python.exe"
$mainFile = Join-Path $projectRoot "main.py"

Set-Location -LiteralPath $projectRoot

if (Test-Path -LiteralPath $portablePython) {
    & $portablePython $mainFile
    exit $LASTEXITCODE
}

$systemPython = Get-Command python -ErrorAction SilentlyContinue
if ($systemPython) {
    & $systemPython.Source $mainFile
    exit $LASTEXITCODE
}

throw "Python not found. Install Python or place portable Python at tools\\python312\\python.exe"
