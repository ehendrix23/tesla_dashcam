Write-Host "========================================"
Write-Host "Tesla Dashcam - Windows Setup"
Write-Host "========================================"
Write-Host ""

# Ensure Chocolatey is installed
Write-Host "Step 1: Ensuring Chocolatey is installed..."
$chocoCmd = Get-Command choco -ErrorAction SilentlyContinue
if (-not $chocoCmd) {
    Set-ExecutionPolicy Bypass -Scope Process -Force
    iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to install Chocolatey!" -ForegroundColor Red
        exit 1
    }
    Write-Host "Chocolatey installed successfully!" -ForegroundColor Green
} else {
    Write-Host "Chocolatey already installed; skipping." -ForegroundColor Yellow
}
Write-Host ""

# Refresh environment to get choco in PATH
$refreshCmd = Get-Command refreshenv -ErrorAction SilentlyContinue
if ($refreshCmd) {
    refreshenv
} else {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}

# Ensure Python 3.13+ is installed
Write-Host "Step 2: Ensuring Python 3.13+ is installed..."
$pyCmd = Get-Command py -ErrorAction SilentlyContinue
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd -and -not $pyCmd) {
    choco install python --version=3.13 -y --params "'/PrependPath:1'"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "WARNING: Exact version 3.13 not found, trying latest Python 3.x..." -ForegroundColor Yellow
        choco install python3 -y --params "'/PrependPath:1'"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "ERROR: Failed to install Python!" -ForegroundColor Red
            exit 1
        }
    }
    Write-Host "Python installed successfully!" -ForegroundColor Green
} else {
    # Prefer Python Launcher if available to avoid Windows Store alias
    if ($pyCmd) {
        $pyverOutput = (& py -3 --version 2>&1 | Select-Object -First 1)
    } else {
        $pyverOutput = (& python --version 2>&1 | Select-Object -First 1)
    }
    if ($pyverOutput -match 'was not found|Microsoft Store') {
        Write-Host "Detected Windows Store alias; installing Python via Chocolatey..." -ForegroundColor Yellow
        choco install python --version=3.13 -y --params "'/PrependPath:1'"
        if ($LASTEXITCODE -ne 0) {
            choco install python3 -y --params "'/PrependPath:1'"
            if ($LASTEXITCODE -ne 0) {
                Write-Host "ERROR: Failed to install Python!" -ForegroundColor Red
                exit 1
            }
        }
        $pyverOutput = (& python --version 2>&1 | Select-Object -First 1)
    }
    $pyver = ($pyverOutput -replace '^Python\s+', '').Trim()
    if ($pyver -and $pyver -match '^(\d+)\.(\d+)(?:\.(\d+))?$') {
        $maj = [int]$Matches[1]
        $min = [int]$Matches[2]
        if ($maj -lt 3 -or ($maj -eq 3 -and $min -lt 13)) {
            Write-Host "Python $pyver detected; upgrading to 3.13..." -ForegroundColor Yellow
            choco upgrade python -y
            if ($LASTEXITCODE -ne 0) {
                Write-Host "WARNING: Python upgrade failed; continuing with existing version." -ForegroundColor Yellow
            } else {
                Write-Host "Python upgraded successfully!" -ForegroundColor Green
            }
        } else {
            Write-Host "Python $pyver detected; meets requirement; skipping install." -ForegroundColor Yellow
        }
    } else {
        Write-Host "NOTE: Could not parse Python version ($pyverOutput); proceeding." -ForegroundColor Yellow
    }
}
Write-Host ""

# Refresh environment again to get python in PATH
if ($refreshCmd) {
    refreshenv
} else {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}

# Verify Python installation (prefer py launcher)
Write-Host "Verifying Python installation..."
if ($pyCmd) {
    $verifyOut = (& py -3 --version 2>&1 | Select-Object -First 1)
    if ($verifyOut -and $verifyOut -match '^Python') {
        Write-Host $verifyOut
        # Get actual interpreter path and prepend to PATH to bypass WindowsApps alias
        $pyExePath = (& py -3 -c "import sys; print(sys.executable)" 2>&1 | Select-Object -First 1)
        if ($pyExePath -and (Test-Path $pyExePath)) {
            $pyDir = Split-Path -Parent $pyExePath
            $env:Path = "$pyDir;$env:Path"
        }
    } else {
        Write-Host "py launcher present but version could not be determined; falling back to python.exe" -ForegroundColor Yellow
        $verifyOut = (python --version 2>&1 | Select-Object -First 1)
    }
} else {
    $verifyOut = (python --version 2>&1 | Select-Object -First 1)
}
if (-not ($verifyOut -and $verifyOut -match '^Python')) {
    Write-Host "Python not found in PATH; attempting to locate python.exe..." -ForegroundColor Yellow
    $pythonExe = Get-ChildItem -Path 'C:\Python*','C:\Program Files\Python*' -Filter 'python.exe' -File -Recurse -ErrorAction SilentlyContinue | Sort-Object -Property LastWriteTime -Descending | Select-Object -First 1
    if ($pythonExe) {
        $env:Path = "$($pythonExe.Directory.FullName);$env:Path"
        Write-Host "Found Python at $($pythonExe.FullName); updating PATH for this session." -ForegroundColor Green
        $verifyOut = (& $pythonExe.FullName --version 2>&1 | Select-Object -First 1)
        Write-Host $verifyOut
    } else {
        Write-Host "ERROR: Python is not available in PATH!" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host $verifyOut
}
Write-Host ""

# Ensure Git is installed
Write-Host "Step 3: Ensuring Git is installed..."
$gitCmd = Get-Command git -ErrorAction SilentlyContinue
if (-not $gitCmd) {
    choco install git -y
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to install Git!" -ForegroundColor Red
        exit 1
    }
    Write-Host "Git installed successfully!" -ForegroundColor Green
} else {
    Write-Host "Git already installed; skipping." -ForegroundColor Yellow
}
Write-Host ""

# Refresh environment to get git in PATH
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# Clone or update repo idempotently
Write-Host "Step 4: Preparing tesla_dashcam repository..."
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
Write-Host "Step 5: Selecting branch..."
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

Write-Host "========================================"
Write-Host "Setup Complete!"
Write-Host "Next steps:"
Write-Host "  1. Install requirements: pip install -r requirements_create_executable_windows.txt"
Write-Host "  2. Build executable: cd bundles\Windows && .\create_executable.cmd"
Write-Host "========================================"

