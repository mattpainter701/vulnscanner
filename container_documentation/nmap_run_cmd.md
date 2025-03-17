# Set variables
$TARGET_IP = "172.16.16.1"
$TIMESTAMP = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$REPORT_FILE = "nmap_report_$TIMESTAMP.txt"
$REPORT_PATH = "C:\Users\Home\deepseek\Vuln_Scanner\reports"

# Ensure the reports directory exists
mkdir $REPORT_PATH -ErrorAction SilentlyContinue

# Define the path for the temporary script (in the host's TEMP folder)
$scriptPath = "$env:TEMP\run_nmap.sh"

# Build the Nmap command string (no extra quotes needed)
$nmapCmd = "nmap -sS -sV -O -p- --script vulners,ssl-enum-ciphers,ssh-auth-methods,smb-os-discovery,smb-vuln-ms17-010,smb-vuln-ms08-067 -T4 $TARGET_IP -oN /nmap_reports/$REPORT_FILE"

# Create the temporary script file with the command
$scriptContent = "#!/bin/sh`n$nmapCmd"
Set-Content -Path $scriptPath -Value $scriptContent

# (Optional) Display the script content for verification:
Write-Output "Script content:"
Get-Content $scriptPath

# Run the Docker container, overriding the entrypoint to /bin/sh,
# and pass the command to execute our temporary script.
docker run --rm --name nmap-vulnscan --privileged --network bridge `
  -v "${REPORT_PATH}:/nmap_reports" `
  -v "${scriptPath}:/run_nmap.sh" `
  --entrypoint /bin/sh instrumentisto/nmap:latest -c "/run_nmap.sh"


Explanation:
Variables & Directory Setup:

We set the target IP, generate a timestamp, and build the report file name.
We ensure the local reports directory exists.
Temporary Script:

We create a temporary shell script (run_nmap.sh) that contains the full Nmap command.
The script uses a standard shebang (#!/bin/sh) so that it can be executed by /bin/sh in the container.
Docker Run:

The -v "${REPORT_PATH}:/nmap_reports" flag mounts your local reports folder into /nmap_reports inside the container.
The -v "${scriptPath}:/run_nmap.sh" flag mounts your temporary script into the container.
The --entrypoint /bin/sh option overrides the container's default entrypoint.
We pass -c "/run_nmap.sh" so that /bin/sh executes our script.
What to Expect:
Once the scan completes, the Nmap report will be saved in:
makefile
Copy
C:\Users\Home\deepseek\Vuln_Scanner\reports\nmap_report_YYYY-MM-DD_HH-mm-ss.txt
The command should now run without errors such as “unrecognized option: c” or “Failed to resolve 'bash'.”
