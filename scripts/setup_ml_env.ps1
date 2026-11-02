# Create the Python 3.12 environment used to train and serve InfraScan models.
# Python 3.14 cannot install PyTorch. The app still runs its non-ML routes there,
# but classification, U-Net, and YOLO need this environment.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Python312 = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
if (-not (Test-Path $Python312)) {
    $Python312 = (& py -3.12 -c "import sys; print(sys.executable)").Trim()
}
if (-not (Test-Path $Python312)) {
    throw "Python 3.12 was not found. Install it with: winget install Python.Python.3.12"
}

$VenvPython = Join-Path $Root "backend\venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    & $Python312 -m venv (Join-Path $Root "backend\venv")
}

# files.pythonhosted.org stalled on this network. The Aliyun index completed the install.
$Index = @("-i", "https://mirrors.aliyun.com/pypi/simple/", "--trusted-host", "mirrors.aliyun.com")
& $VenvPython -m pip install --upgrade pip @Index
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }
& $VenvPython -m pip install --default-timeout=180 --retries 8 @Index -r (Join-Path $Root "backend\requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "backend requirements install failed" }
& $VenvPython -m pip install --default-timeout=180 --retries 8 torch torchvision --index-url https://download.pytorch.org/whl/cpu
if ($LASTEXITCODE -ne 0) { throw "PyTorch install failed" }
& $VenvPython -m pip install --default-timeout=180 --retries 8 @Index ultralytics
if ($LASTEXITCODE -ne 0) { throw "ultralytics install failed" }
& $VenvPython -m pip install --default-timeout=180 --retries 5 torch torchvision --index-url https://download.pytorch.org/whl/cpu
if ($LASTEXITCODE -ne 0) { throw "CPU PyTorch reinstall failed" }
Write-Output "Environment ready: $VenvPython"
