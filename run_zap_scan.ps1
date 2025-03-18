# PowerShell script to run ZAP scan
# Usage: .\run_zap_scan.ps1 <target_url>
param(
    [Parameter(Mandatory=$true)]
    [string]$targetUrl
)

# Check if URL has http/https prefix
if (-not ($targetUrl -match "^https?://")) {
    Write-Host "Adding http:// prefix to URL..."
    $targetUrl = "http://$targetUrl"
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

# Update the target in the script
Write-Host "Updating target in the scan script..."
$scriptContent = Get-Content -Path "container_documentation/zaproxy_test.py" -Raw
$scriptContent = $scriptContent -replace '(target = "https?://)[^"]*"', ('$1' + $targetUrl.Replace("http://", "").Replace("https://", "") + '"')
Set-Content -Path "container_documentation/zaproxy_test.py" -Value $scriptContent

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

# Run the scan
Write-Host "Starting vulnerability scan against $targetUrl..."
py container_documentation/zaproxy_test.py

# Output results location
Write-Host "`nScan completed! Check the generated reports."
Write-Host "Reports are saved in the current directory with names starting with 'zap_report_'"

# Offer to stop the ZAP container
$stopContainer = Read-Host "Do you want to stop the ZAP container? (y/n)"
if ($stopContainer -eq "y") {
    Write-Host "Stopping ZAP container..."
    docker stop zap
    Write-Host "ZAP container stopped."
} 