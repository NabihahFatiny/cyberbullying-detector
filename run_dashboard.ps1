$ErrorActionPreference = "Stop"
$env:PYTHONDONTWRITEBYTECODE = "1"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$appPath = Join-Path $scriptDir "app.py"
$python = Get-Command python -ErrorAction SilentlyContinue

function Test-PythonCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Executable,
        [string[]]$PrefixArgs = @()
    )

    try {
        & $Executable @PrefixArgs --version *> $null
        return $true
    } catch {
        return $false
    }
}

if ($python -and (Test-PythonCommand -Executable $python.Source)) {
    & $python.Source $appPath @args
    exit $LASTEXITCODE
}

$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($pyLauncher -and (Test-PythonCommand -Executable $pyLauncher.Source -PrefixArgs @("-3"))) {
    & $pyLauncher.Source -3 $appPath @args
    exit $LASTEXITCODE
}

$fallbackCandidates = @(
    "C:\Users\Fatiny\AppData\Local\Android\Sdk\ndk\27.0.12077973\toolchains\llvm\prebuilt\windows-x86_64\python3\python.exe",
    "C:\Python312\python.exe",
    (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"),
    (Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe"),
    (Join-Path $env:LOCALAPPDATA "Programs\Python\Python310\python.exe")
)

foreach ($candidate in $fallbackCandidates) {
    if ((Test-Path $candidate) -and (Test-PythonCommand -Executable $candidate)) {
        & $candidate $appPath @args
        exit $LASTEXITCODE
    }
}

throw "Python was not found in PATH and no working fallback interpreter was found. Install Python 3 or add it to PATH before running the dashboard."
