# Northbrook QA — Docker launcher (Windows PowerShell 5.1+ / 7+)
# Usage: .\scripts\run.ps1 [-Rebuild] [-Help]
#
# If you get "running scripts is disabled on this system",
# run .\scripts\run.cmd instead — it bypasses ExecutionPolicy.

[CmdletBinding()]
param(
    [Alias('r')][switch]$Rebuild,
    [Alias('h')][switch]$Help
)

$ErrorActionPreference = 'Stop'

$ImageName     = 'northbrook-qa'
$ContainerName = 'northbrook-qa-app'
$Port          = 8501

if ($Help) {
    Write-Host "Usage: .\scripts\run.ps1 [-Rebuild] [-Help]"
    Write-Host "App will start on http://localhost:$Port"
    exit 0
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Docker is not installed. Install Docker Desktop:" -ForegroundColor Red
    Write-Host "       https://www.docker.com/products/docker-desktop/" -ForegroundColor Red
    exit 1
}

docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker is not running. Start Docker Desktop." -ForegroundColor Red
    exit 1
}

# Clean any stale container from a prior crashed run
docker rm -f $ContainerName *> $null

docker image inspect $ImageName *> $null
$ImageMissing = ($LASTEXITCODE -ne 0)

if ($Rebuild -or $ImageMissing) {
    Write-Host "Building image '$ImageName'... (first build takes 5-10 min; AV may slow it further)" -ForegroundColor Cyan
    docker build -t $ImageName .
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: docker build failed." -ForegroundColor Red
        exit 1
    }
}

# Build a Docker-friendly mount path:
# - forward slashes (Docker rejects C:\... in -v)
# - quoted at use-site (handles paths with spaces)
$DataDir = Join-Path $PWD.Path 'data'
if (-not (Test-Path $DataDir)) {
    New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
}
$DataDirFwd = $DataDir -replace '\\','/'

Write-Host ""
Write-Host "Starting app..." -ForegroundColor Green
Write-Host "Open http://localhost:$Port in your browser." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop."
Write-Host ""

# If a local .env exists, pass it so Phoenix env vars (and anthropic/voyage)
# reach the container. Community Cloud uses its Secrets dashboard for the
# Phoenix triple — but locally we read from .env to mirror "real" tracing.
$EnvArgs = @()
if (Test-Path ".env") {
    $EnvArgs = @("--env-file", ".env")
}

try {
    docker run --rm `
        --name $ContainerName `
        -p "${Port}:${Port}" `
        @EnvArgs `
        -v "${DataDirFwd}:/app/data" `
        $ImageName
}
finally {
    if (docker ps -q -f "name=^${ContainerName}$") {
        Write-Host ""
        Write-Host "Stopping container..." -ForegroundColor Yellow
        docker stop $ContainerName *> $null
    }
}
