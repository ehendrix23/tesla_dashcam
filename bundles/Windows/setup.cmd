Write-Host "========================================"
Write-Host "Tesla Dashcam - Windows Setup"
Write-Host "========================================"
Write-Host ""

Write-Host "Step 1: Ensuring winget is installed..."
$wingetCmd = Get-Command winget -ErrorAction SilentlyContinue
if (-not $wingetCmd) {
    Write-Host "ERROR: winget is not available on this system." -ForegroundColor Red
    Write-Host "Install 'App Installer' from the Microsoft Store (or update it) and try again." -ForegroundColor Yellow
    exit 1
}
Write-Host "winget is available; continuing." -ForegroundColor Green
Write-Host ""

# Ensure Git is installed (required for cloning the repo)
Write-Host "Step 2: Ensuring Git is installed..."
$gitCmd = Get-Command git -ErrorAction SilentlyContinue
if (-not $gitCmd) {
    Write-Host "Git not found; installing via winget..." -ForegroundColor Yellow
    winget install --id Git.Git -e --source winget --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to install Git via winget!" -ForegroundColor Red
        exit 1
    }

    # Refresh PATH for this session
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    $gitCmd = Get-Command git -ErrorAction SilentlyContinue
    if (-not $gitCmd) {
        Write-Host "ERROR: Git installed but not available in PATH. Try opening a new PowerShell window." -ForegroundColor Red
        exit 1
    }
    Write-Host "Git installed successfully!" -ForegroundColor Green
} else {
    Write-Host "Git already installed; skipping." -ForegroundColor Yellow
}
Write-Host ""

# Clone or update repo idempotently
Write-Host "Step 3: Preparing tesla_dashcam repository..."
$repoUrl = "https://github.com/ehendrix23/tesla_dashcam.git"
$repoDir = "tesla_dashcam"
if (Test-Path $repoDir) {
    Write-Host "Repository already exists; updating..." -ForegroundColor Yellow
    Set-Location $repoDir
    git remote get-url origin > $null 2>&1
    if ($LASTEXITCODE -ne 0) {
        git init
        git remote add origin $repoUrl
    }
    git fetch --all
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to fetch updates from origin!" -ForegroundColor Red
        exit 1
    }
} else {
    git clone $repoUrl
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to clone repository!" -ForegroundColor Red
        exit 1
    }
    Set-Location $repoDir
    Write-Host "Repository cloned successfully!" -ForegroundColor Green
}
Write-Host ""

# Ask user for branch
Write-Host "Step 4: Selecting branch..."
$branch = Read-Host "Enter branch name to checkout (default: dev)"
if ([string]::IsNullOrWhiteSpace($branch)) {
    $branch = "dev"
}

Write-Host "Checking out branch: $branch..."
git rev-parse --verify $branch > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Branch not found locally; attempting to track origin/$branch..." -ForegroundColor Yellow
    git checkout -B $branch origin/$branch
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to checkout branch '$branch' from origin!" -ForegroundColor Red
        Write-Host "Available branches (local and remote):"
        git branch -a
        exit 1
    }
} else {
    git checkout $branch
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to checkout branch '$branch'!" -ForegroundColor Red
        Write-Host "Available branches:"
        git branch -a
        exit 1
    }
}
Write-Host "Branch checked out successfully!" -ForegroundColor Green
Write-Host ""

# Determine required Python version from pyproject.toml
$pythonVersion = $null
try {
    if (Test-Path "pyproject.toml") {
        $requiresPythonLine = Select-String -Path "pyproject.toml" -Pattern '^\s*requires-python\s*=\s*"' -CaseSensitive:$false | Select-Object -First 1
        if ($requiresPythonLine) {
            $requiresPython = [regex]::Match($requiresPythonLine.Line, 'requires-python\s*=\s*"([^"]+)"').Groups[1].Value
            $m = [regex]::Match($requiresPython, '(\d+)\.(\d+)')
            if ($m.Success) {
                $pythonVersion = "$($m.Groups[1].Value).$($m.Groups[2].Value)"
            }
        }
    }
} catch {
    $pythonVersion = $null
}

if (-not $pythonVersion) {
    $pythonVersion = "3.13"
    Write-Host "NOTE: Could not determine required Python version from pyproject.toml; defaulting to $pythonVersion" -ForegroundColor Yellow
} else {
    Write-Host "Detected required Python version from pyproject.toml: $pythonVersion" -ForegroundColor Green
}
Write-Host ""

# Ensure uv is installed
Write-Host "Step 5: Ensuring uv is installed..."
$uvCmd = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uvCmd) {
    Write-Host "uv not found; installing..." -ForegroundColor Yellow
    try {
        Invoke-RestMethod -Uri "https://astral.sh/uv/install.ps1" | Invoke-Expression
    } catch {
        Write-Host "ERROR: Failed to install uv: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }

    # Ensure default install location is available in PATH for this session
    $uvBin = Join-Path $env:USERPROFILE ".local\\bin"
    if (Test-Path $uvBin) {
        $env:Path = "$uvBin;$env:Path"
    }

    $uvCmd = Get-Command uv -ErrorAction SilentlyContinue
    if (-not $uvCmd) {
        Write-Host "ERROR: uv install completed but uv is still not on PATH." -ForegroundColor Red
        Write-Host "Try opening a new PowerShell window, or add $uvBin to PATH." -ForegroundColor Yellow
        exit 1
    }
    Write-Host "uv installed successfully!" -ForegroundColor Green
} else {
    Write-Host "uv already installed; skipping." -ForegroundColor Yellow
}
Write-Host ""

# Ensure uv-managed Python is installed
Write-Host "Step 6: Ensuring uv-managed Python $pythonVersion is installed..."
& uv python install $pythonVersion
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install Python $pythonVersion via uv." -ForegroundColor Red
    exit 1
}
Write-Host "uv-managed Python installed successfully!" -ForegroundColor Green
Write-Host ""

Write-Host "========================================"
Write-Host "Setup Complete!"
Write-Host "Next steps:"
Write-Host "  1. Build executable (run from repo root): .\bundles\Windows\create_executable.cmd"
Write-Host "========================================"

