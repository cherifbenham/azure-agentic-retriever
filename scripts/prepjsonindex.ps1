./scripts/load_python_env.ps1

$venvPythonPath = "./.venv/scripts/python.exe"
if (Test-Path -Path "/usr") {
  # fallback to Linux venv path
  $venvPythonPath = "./.venv/bin/python"
}

Write-Host 'Running "prepjsonindex.py"'

$cwd = (Get-Location)
$dataArg = "`"$cwd/new-data/index.json`""
$schemaArg = "`"$cwd/new-data/index-schema.json`""
$additionalArgs = ""
if ($args) {
  $additionalArgs = "$args"
}

$argumentList = "./app/backend/prepjsonindex.py --data $dataArg --schema $schemaArg $additionalArgs"

$argumentList

Start-Process -FilePath $venvPythonPath -ArgumentList $argumentList -Wait -NoNewWindow
