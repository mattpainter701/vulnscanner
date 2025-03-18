docker run -d --name zap -p 8080:8080 -v "C:/Users/Home/deepseek/Vuln_Scanner:/zap" --network=bridge zaproxy/zap-weekly zap.sh -daemon -host 0.0.0.0 -config api.key=mysecretapikey -config api.addrs.addr.name=.* -config api.addrs.addr.regex=true



🔹 Breakdown of Each Flag:
-d → Runs the container in detached mode (background).
--name zap → Names the container zap for easy reference.
-p 8080:8080 → Exposes port 8080 for API/Web UI access.
-v C:/Users/Home/deepseek/Vuln_Scanner:/zap → Mounts a local directory into the container to persist reports.
--network=bridge → Ensures the container has network connectivity.
zaproxy/zap-weekly zap.sh -daemon -host 0.0.0.0 → Runs ZAP in daemon mode so it accepts API requests.
-config api.key=mysecretapikey → Sets the API key for secure API access.
-config api.addrs.addr.name=.* → Allows API requests from all addresses.
-config api.addrs.addr.regex=true → Interprets the addr.name as a regex.
