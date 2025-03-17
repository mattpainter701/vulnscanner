# Cloud Security Scanner - AI Context Guide
**Instructions for AI Assistants Contributing to the Project**  
*Last Updated: [DATE]*

---

## Project Overview
We're building a SaaS security scanner that:
1. Accepts a target (URL/IP) and email via web UI.
2. Scans target with **OpenVAS**, **OWASP ZAP**, and **Nmap**.
3. Generates unified PDF/HTML reports stored in encrypted S3.
4. Supports scheduled scans via subscription plans.

**Key Stack**: AWS (Lambda, Fargate, S3), Python, React, Docker.

---

## Code Structure & Patterns

### 1. Directory Structure
```bash
/
├── frontend/           # React app
│   ├── src/pages/      # Scan submission & report pages
│   └── src/api/        # API Gateway client calls
├── backend/
│   ├── lambdas/        # Python Lambda handlers
│   │   ├── scan_submit/
│   │   ├── report_gen/
│   │   └── payment/
│   └── scanners/       # Dockerized tools
│       ├── openvas/
│       ├── zap/
│       └── nmap/
├── terraform/          # Infrastructure-as-code
└── scripts/            # Deployment/build helpers

# .env.example (Lambda/Fargate)
SCAN_QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/.../ScanQueue"
REPORTS_BUCKET = "security-scanner-reports"
MAX_FREE_SCANS = 1  # Free tier limit

#Scan Submission Handler (python)
def lambda_handler(event, context):
    # Expected JSON payload:
    # { "target": "example.com", "email": "user@mail.com" }
    
    # Validate target format first!
    if not is_public_target(event['target']):
        return {"error": "Private IPs/domains blocked"}
    
    # Free tier check (pseudo-code)
    if is_free_user(event['email']) and get_scan_count(event['email']) >= MAX_FREE_SCANS:
        return {"error": "Free tier limit reached"}
    
    # Proceed to SQS
    sqs_client.send_message(QueueUrl=SCAN_QUEUE_URL, MessageBody=json.dumps(event))


#Security Scanner Integration
#Nmap Docker Command:
# In scanner Dockerfile
RUN apt-get install -y nmap && \
    mkdir -p /reports

CMD ["sh", "-c", "nmap -sV -oX /reports/nmap.xml $TARGET"]

#OWASP ZAP PYTHON API EXAMPLE
from zapv2 import ZAPv2

def run_zap_scan(target):
    zap = ZAPv2(apikey=os.getenv('ZAP_APIKEY'))
    scan_id = zap.ascan.scan(target)
    while int(zap.ascan.status(scan_id)) < 100:
        time.sleep(5)
    return zap.core.xmlreport(scan_id)

#Critical Security Rules
# Input Validation
#Public Target Regex:

python
# Allowed: domains, public IPv4
PUBLIC_TARGET_REGEX = r'^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$|^(?!10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|192\.168\.)\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
#Blocked CIDR Ranges:
PRIVATE_NETWORKS = [
    '10.0.0.0/8',
    '172.16.0.0/12',
    '192.168.0.0/16',
    '169.254.0.0/16'  # Link-local
]


#AWS PERMISSIONS MIN FARGATE TASK ROLE
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "s3:PutObject",
        "sqs:DeleteMessage"
      ],
      "Effect": "Allow",
      "Resource": "*"
    }
  ]
}

#Infrastructure-as-Code Patterns
Terraform lambda example

# backend/lambdas/scan_submit.tf
resource "aws_lambda_function" "scan_submit" {
  filename      = "scan_submit.zip"
  function_name = "ScanSubmitHandler"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.12"
  environment {
    variables = {
      SCAN_QUEUE_URL = aws_sqs_queue.scan_queue.url
    }
  }
}

#Fargate Task Definition
resource "aws_ecs_task_definition" "scanner" {
  family                   = "security-scanner"
  cpu                      = 2048  # 2 vCPU
  memory                   = 4096  # 4GB RAM
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn       = aws_iam_role.ecs_exec.arn
  
  container_definitions = jsonencode([{
    name  = "openvas-scanner",
    image = "123456789.dkr.ecr.us-east-1.amazonaws.com/openvas:latest",
    environment = [
      { name = "TARGET", value = "$(sqs_target)" }
    ]
  }])
}
Common Pitfalls to Avoid
Never hardcode AWS credentials - Always use IAM roles.

Validate ALL user inputs - Assume malicious payloads.

Limit scanner resource usage - Prevent accidental DDoS.

Handle partial scan failures - e.g., If OpenVAS fails, still report Nmap/ZAP results.

Frequently Asked Questions (AI Context)
Q: How are rate limits enforced?
Free tier: 1 concurrent scan, 1/day via API Gateway usage plans.

Paid tiers: Track via DynamoDB user_scan_count with TTL attributes.

Q: Where is encryption handled?
S3: Server-side encryption (SSE-S3) by default.

DynamoDB: Encryption-at-rest enabled.

TLS: Enforced via API Gateway & CloudFront.

Q: Typical scan duration?
Simple scans: 2-5 minutes (Nmap + ZAP quick scan).

Full scans: 15-30 minutes (OpenVAS deep audit).

#CLI COMMAND BANK
# Test scanners locally
docker run -e TARGET=example.com security-scanner-nmap

# Deploy Lambda from CLI
aws lambda update-function-code \
  --function-name ScanSubmitHandler \
  --zip-file fileb://scan_submit.zip

# Query recent scans
aws dynamodb scan \
  --table-name UserScans \
  --filter-expression "user_id = :uid" \
  --expression-attribute-values '{":uid": {"S": "user_123"}}'

  