# PowerShell script to run ZAP scan
# Usage: .\run_zap_scan.ps1 <target_url>
param(
    [Parameter(Mandatory=$true)]
    [string]$targetUrl,
    
    [Parameter(Mandatory=$false)]
    [switch]$keepContainerRunning = $false
)

# Check if URL has http/https prefix
if (-not ($targetUrl -match "^https?://")) {
    Write-Host "Adding https:// prefix to URL..."
    $targetUrl = "https://$targetUrl"
}

# Create reports directory if it doesn't exist
if (-not (Test-Path -Path "reports")) {
    Write-Host "Creating reports directory..."
    New-Item -Path "reports" -ItemType Directory | Out-Null
}

# Check if Docker is running
try {
    docker info | Out-Null
} catch {
    Write-Error "Docker is not running. Please start Docker and try again."
    exit 1
}

# Remove existing ZAP container if it exists
Write-Host "Removing any existing ZAP containers..."
docker rm -f zap 2>$null

# Start ZAP container with zaproxy/zap-weekly image and correct paths
Write-Host "Starting ZAP container with zaproxy/zap-weekly image..."
docker run -d --name zap -p 8080:8080 `
    -v "${PWD}:/home/zap/wrk" `
    zaproxy/zap-weekly zap.sh -daemon -host 0.0.0.0 `
    -config api.key=mysecretapikey `
    -config api.addrs.addr.name=.* `
    -config api.addrs.addr.regex=true

# Wait for ZAP to start
Write-Host "Waiting for ZAP to start..."
Start-Sleep -Seconds 20  # Increased wait time for weekly build

# Check if ZAP is running
Write-Host "Checking if ZAP is running..."
$zapRunning = $false
$retry = 0
while (-not $zapRunning -and $retry -lt 5) {  # Increased retry attempts
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8080/JSON/core/view/version/?apikey=mysecretapikey" -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            $zapRunning = $true
            Write-Host "ZAP is running!"
        }
    } catch {
        Write-Host "ZAP not responding yet. Waiting 5 more seconds..."
        Start-Sleep -Seconds 5
        $retry++
    }
}

if (-not $zapRunning) {
    Write-Host "Failed to start ZAP. Checking container logs..."
    docker logs zap
    Write-Host "Container status:"
    docker ps -a | findstr zap
    exit 1
}

# Install required Python packages if not already installed
Write-Host "Checking Python dependencies..."
try {
    python -c "import zapv2" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Installing Python OWASP ZAP package..."
        py -m pip install python-owasp-zap-v2.4 requests
    }
} catch {
    Write-Host "Installing Python OWASP ZAP package..."
    py -m pip install python-owasp-zap-v2.4 requests
}

# Run the scan - pass the target URL as a command line argument
Write-Host "Starting vulnerability scan against $targetUrl..."
py container_documentation/zaproxy_test.py "$targetUrl"

# Output results location
Write-Host "`nScan completed! Check the generated reports."
Write-Host "Reports are saved in the 'reports' directory with names starting with 'zap_report_'"

# Stop the container by default unless -keepContainerRunning is specified
if (-not $keepContainerRunning) {
    Write-Host "Stopping ZAP container..."
    docker stop zap
    Write-Host "ZAP container stopped."
} else {
    Write-Host "ZAP container is still running. Stop it manually when done with 'docker stop zap'"
} 