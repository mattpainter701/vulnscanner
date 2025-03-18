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

# Start ZAP container
Write-Host "Starting ZAP container..."
docker run -d --name zap -p 8080:8080 `
    -v "${PWD}:/zap" `
    --network=bridge `
    --entrypoint "/zap/zap.sh" `
    zaproxy/zap-weekly -daemon -host 0.0.0.0 `
    -config api.key=mysecretapikey `
    -config api.addrs.addr.name=.* `
    -config api.addrs.addr.regex=true

# Wait for ZAP to start
Write-Host "Waiting for ZAP to start..."
Start-Sleep -Seconds 10

# Update the target in the script
Write-Host "Updating target in the scan script..."
$scriptContent = Get-Content -Path "container_documentation/zaproxy_test.py" -Raw
$scriptContent = $scriptContent -replace '(target = "https?://)[^"]*"', ('$1' + $targetUrl + '"')
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