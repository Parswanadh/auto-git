param(
    [string]$SourcePath = "D:\Projects\auto-git",
    [string]$TargetPath = "D:\Projects\AutoGIT",
    [string]$RepoName = "AutoGIT",
    [ValidateSet("public", "private")]
    [string]$Visibility = "public"
)

$ErrorActionPreference = "Stop"

Write-Host "[1/6] Preparing target folder: $TargetPath"
if (Test-Path $TargetPath) {
    throw "Target path already exists. Use a fresh folder path: $TargetPath"
}
New-Item -ItemType Directory -Path $TargetPath | Out-Null

Write-Host "[2/6] Copying organized project files"
$excludeDirs = @(
    ".git", ".venv", "__pycache__", "logs", "output", "generated_repos", "node_modules",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox", ".nox", ".hypothesis", ".cache",
    "remotion-auto-git", "external", "auto_git.egg-info", "data\checkpoints", "data\memory",
    "data\metrics", "data\test_memory", "data\vector_db"
)
$excludeFiles = @("*.log", "*.out", "*.err", "*.pid", "*.tmp", "*.bak", "*.mp4", "*.mov", "*.avi", "*.webm", "*.wav")

$roboArgs = @($SourcePath, $TargetPath, "/E", "/R:1", "/W:1")
if ($excludeDirs.Count -gt 0) {
    $roboArgs += "/XD"
    $roboArgs += $excludeDirs
}
if ($excludeFiles.Count -gt 0) {
    $roboArgs += "/XF"
    $roboArgs += $excludeFiles
}

& robocopy @roboArgs | Out-Null
$roboCode = $LASTEXITCODE
if ($roboCode -ge 8) {
    throw "Robocopy failed with exit code $roboCode"
}

Write-Host "[3/6] Initializing git repository"
Push-Location $TargetPath
try {
    git init | Out-Null
    git checkout -B main | Out-Null

    Write-Host "[4/6] Creating initial commit"
    git add .
    git commit -m "Initial organized import" | Out-Null

    Write-Host "[5/6] Creating GitHub repo and pushing"
    $gh = Get-Command gh -ErrorAction SilentlyContinue
    if (-not $gh) {
        throw "GitHub CLI (gh) is not installed. Install gh and run this script again."
    }

    gh auth status | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "GitHub CLI is not authenticated. Run: gh auth login"
    }

    gh repo create $RepoName --$Visibility --source . --remote origin --push --confirm
    if ($LASTEXITCODE -ne 0) {
        throw "GitHub repo creation or push failed."
    }

    Write-Host "[6/6] Done. Repo created and pushed: $RepoName"
}
finally {
    Pop-Location
}
