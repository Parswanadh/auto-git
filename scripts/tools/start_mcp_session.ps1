Param(
    [string]$Workspace = "D:\Projects\auto-git",
    [switch]$CheckOnly
)

$PythonExe = Join-Path $Workspace ".venv\Scripts\python.exe"
$ScriptPath = Join-Path $Workspace "scripts\tools\start_mcp_session.py"

if (-not (Test-Path $PythonExe)) {
    Write-Error "Python not found at $PythonExe"
    exit 1
}

if (-not (Test-Path $ScriptPath)) {
    Write-Error "Script not found at $ScriptPath"
    exit 1
}

$Args = @($ScriptPath, "--workspace", $Workspace)
if ($CheckOnly) {
    $Args += "--check-only"
}

& $PythonExe @Args
exit $LASTEXITCODE
