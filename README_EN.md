# AgentCore Feishu Notifier

A Feishu (Lark) notification tool deployed on AWS AgentCore Gateway, providing message sending capabilities for AI Agents via MCP protocol.

## Features

- 🚀 **MCP Protocol Support** - Exposes standard MCP tool interface through AgentCore Gateway
- 📨 **Multiple Message Types** - Supports text (plain text) and post (rich text) message formats
- 🔐 **M2M Authentication** - API protected by Cognito OAuth 2.0 Client Credentials flow
- 🔄 **Auto Retry** - Built-in exponential backoff retry mechanism for transient network failures
- ☁️ **Serverless** - Based on AWS Lambda, pay-per-use, no server management required

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│   AI Agent      │────▶│  AgentCore Gateway   │────▶│ Notifier Lambda │
│  (MCP Client)   │     │  (MCP Server)        │     │                 │
└─────────────────┘     └──────────────────────┘     └────────┬────────┘
        │                        │                            │
        │                        │                            ▼
        │                 ┌──────┴──────┐              ┌──────────────┐
        │                 │   Cognito   │              │ Feishu Client│
        │                 │  User Pool  │              └──────┬───────┘
        │                 │   (M2M)     │                     │
        │                 └─────────────┘                     ▼
        │                                              ┌──────────────┐
        └──────────────────────────────────────────────│ Feishu API   │
                                                       │ (Webhook)    │
                                                       └──────────────┘
```

### Request Flow

1. AI Agent obtains Access Token from Cognito using Client Credentials
2. Agent calls the `send_feishu_notification` tool on AgentCore Gateway via MCP protocol
3. Gateway validates the Token and routes the request to Lambda
4. Lambda invokes Feishu Client to send message to the specified Webhook
5. Returns the result

## Project Structure

```
.
├── src/
│   └── feishu_notifier/
│       ├── __init__.py         # Package initialization
│       ├── feishu_client.py    # Feishu Webhook client
│       └── handler.py          # Lambda entry point
├── tests/
│   ├── test_feishu_client.py   # Client unit tests
│   └── test_handler.py         # Handler unit tests
├── template.yaml               # SAM deployment template
├── tool_schema.json            # MCP Tool Schema definition
├── samconfig.toml              # SAM CLI configuration
├── pyproject.toml              # Python project configuration
└── README.md
```

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) - Python package manager
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- AWS account with configured AWS CLI credentials
- Feishu group Webhook URL

## Quick Start

### 1. Clone the Project

```bash
git clone <repository-url>
cd agentcore-feishu-notifier
```

### 2. Install Dependencies

```bash
# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # macOS/Linux
uv pip install -e ".[dev]"
```

### 3. Run Tests

```bash
uv run pytest tests/ -v
```

### 4. Build the Project

```bash
sam build
```

### 5. Deploy to AWS

```bash
# First deployment (interactive configuration)
sam deploy --guided

# Subsequent deployments
sam deploy
```

## Deployment Details

### SAM Template Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `Environment` | `dev` | Deployment environment (dev/staging/prod) |
| `GatewayName` | `feishu-notifier-gateway` | Gateway name prefix |

### Deployment Command Examples

```bash
# Deploy to development environment
sam deploy --parameter-overrides Environment=dev

# Deploy to production environment
sam deploy --parameter-overrides Environment=prod

# Specify AWS Region
sam deploy --region us-west-2

# Full deployment command
sam deploy \
  --stack-name agentcore-feishu-notifier-prod \
  --parameter-overrides "Environment=prod GatewayName=my-feishu-gateway" \
  --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
  --region us-east-1
```

### Deployment Outputs

After successful deployment, CloudFormation outputs the following:

| Output | Description |
|--------|-------------|
| `GatewayUrl` | AgentCore Gateway MCP endpoint URL |
| `GatewayId` | Gateway identifier |
| `CognitoClientId` | OAuth Client ID |
| `CognitoTokenEndpoint` | Token endpoint |

## Usage

### Obtain Access Token

First, get the Cognito Client Secret (from AWS Console), then obtain the Token:

```bash
# Get Access Token
curl -X POST "https://<domain>.auth.<region>.amazoncognito.com/oauth2/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=<CLIENT_ID>" \
  -d "client_secret=<CLIENT_SECRET>" \
  -d "scope=<gateway-name>-resource-server/invoke"
```

### Call MCP Tool

Connect to Gateway using MCP client and invoke the tool:

```python
# Example: Using MCP SDK
from mcp import Client

client = Client(
    url="<GATEWAY_URL>",
    headers={"Authorization": f"Bearer {access_token}"}
)

# Send text message
result = await client.call_tool(
    "send_feishu_notification",
    {
        "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
        "message": "Hello from AgentCore!",
        "msg_type": "text"
    }
)

# Send rich text message
result = await client.call_tool(
    "send_feishu_notification",
    {
        "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
        "message": "This is the message body",
        "msg_type": "post",
        "title": "Notification Title"
    }
)
```

### Tool Schema

```json
{
    "name": "send_feishu_notification",
    "description": "Send a notification message to a Feishu group via webhook",
    "inputSchema": {
        "type": "object",
        "properties": {
            "webhook_url": {
                "type": "string",
                "description": "Feishu Webhook URL, must start with https://"
            },
            "message": {
                "type": "string",
                "description": "Message content"
            },
            "msg_type": {
                "type": "string",
                "description": "Message type: text (default) or post"
            },
            "title": {
                "type": "string",
                "description": "Rich text message title (required when msg_type=post)"
            }
        },
        "required": ["webhook_url", "message"]
    }
}
```

## Getting Feishu Webhook URL

1. Open Feishu and enter the target group
2. Click Group Settings → Group Bots → Add Bot
3. Select "Custom Bot"
4. Set bot name and avatar
5. Copy the generated Webhook URL

## Local Development

### Local Lambda Invocation

```bash
# Create test event file
cat > events/test_event.json << EOF
{
    "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
    "message": "Test message from local"
}
EOF

# Local invocation
sam local invoke FeishuNotifierFunction -e events/test_event.json
```

### Run Tests

```bash
# Run all tests
uv run pytest

# Run tests with coverage report
uv run pytest --cov=src --cov-report=html

# Run specific test
uv run pytest tests/test_feishu_client.py -v
```

### Code Quality

```bash
# Type checking
uv run mypy src/

# Code style checking
uv run ruff check src/
```

## Error Handling

### Error Codes

| Error Code | Description |
|------------|-------------|
| `VALIDATION_ERROR` | Parameter validation failed (e.g., invalid URL format, empty message) |
| `NETWORK_ERROR` | Network request failed (timeout, connection failure, etc.) |
| `FEISHU_API_ERROR` | Feishu API returned an error |
| `UNKNOWN_TOOL` | Unknown tool name |
| `INTERNAL_ERROR` | Internal error |

### Retry Strategy

- Maximum retries: 3
- Backoff strategy: Exponential backoff (1s → 2s → 4s)
- Timeout configuration: Connection 5s, Read 10s

## Manual Testing (10 minutes)

After deployment, follow these steps to verify the Gateway is working correctly.

### Step 1: Get Deployment Outputs

After successful deployment, retrieve the following information from CloudFormation outputs:

```bash
# View Stack outputs
aws cloudformation describe-stacks \
  --stack-name agentcore-feishu-notifier \
  --query 'Stacks[0].Outputs' \
  --output table
```

Note down the following values:
- `GatewayUrl` - Gateway MCP endpoint
- `CognitoClientId` - OAuth Client ID
- `CognitoTokenEndpoint` - Token endpoint

### Step 2: Get Cognito Client Secret

Get the Client Secret from AWS Console:
1. Go to Cognito → User Pools
2. Select `feishu-notifier-gateway-user-pool-dev`
3. App Integration → App clients
4. Click Client → Show Client Secret

### Step 3: Get Access Token

Run in terminal (replace with actual values):

```bash
# Set variables
CLIENT_ID="your-client-id"
CLIENT_SECRET="your-client-secret"
TOKEN_ENDPOINT="https://feishu-notifier-gateway-123456789012-dev.auth.us-east-1.amazoncognito.com/oauth2/token"
SCOPE="feishu-notifier-gateway-resource-server/invoke"

# Get Token
curl -X POST "$TOKEN_ENDPOINT" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=$CLIENT_ID" \
  -d "client_secret=$CLIENT_SECRET" \
  -d "scope=$SCOPE"
```

Copy the returned `access_token`.

### Step 4: Test Gateway - List Tools

```bash
GATEWAY_URL="https://gw-xxx.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"
ACCESS_TOKEN="your-access-token"

curl -X POST "$GATEWAY_URL" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
  }'
```

Expected response should contain the `send_feishu_notification` tool.

### Step 5: Test Gateway - Call Tool

```bash
# Replace with your Feishu Webhook URL
WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook-id"

curl -X POST "$GATEWAY_URL" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "feishu-notifier-target___send_feishu_notification",
      "arguments": {
        "webhook_url": "'"$WEBHOOK_URL"'",
        "message": "Hello from AgentCore Gateway! 🎉",
        "msg_type": "text"
      }
    }
  }'
```

Expected response:
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "success": true,
    "data": {
      "status": "sent",
      "message": "Notification sent successfully"
    }
  }
}
```

Your Feishu group should also receive the test message.

### Step 6: Test Rich Text Message (Optional)

```bash
curl -X POST "$GATEWAY_URL" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "feishu-notifier-target___send_feishu_notification",
      "arguments": {
        "webhook_url": "'"$WEBHOOK_URL"'",
        "message": "This is a rich text test message from AgentCore Gateway",
        "msg_type": "post",
        "title": "🔔 Test Notification"
      }
    }
  }'
```

### Common Testing Issues

| Issue | Possible Cause | Solution |
|-------|----------------|----------|
| `Invalid Bearer token` | Token expired or misconfigured | Re-obtain token, check AllowedClients config |
| `Access Denied` | Incorrect scope | Ensure correct scope when requesting token |
| `NETWORK_ERROR` | Lambda cannot access public internet | Check VPC config or NAT Gateway |
| `VALIDATION_ERROR` | Invalid parameter format | Check webhook_url and message parameters |

## Cleanup Resources

```bash
# Delete CloudFormation Stack
sam delete --stack-name agentcore-feishu-notifier

# Or using AWS CLI
aws cloudformation delete-stack --stack-name agentcore-feishu-notifier
```

## Cognito M2M Authentication Configuration

### Important: AllowedAudience vs AllowedClients

Access Tokens generated by Cognito's `client_credentials` flow **do not contain the `aud` (audience) claim**, unlike the `authorization_code` flow.

| OAuth Flow | Token Type | `aud` claim | `client_id` claim |
|------------|------------|-------------|-------------------|
| Authorization Code | ID Token | ✅ Yes | ✅ Yes |
| Client Credentials (M2M) | Access Token | ❌ **No** | ✅ Yes |

Therefore, for AgentCore Gateway's CUSTOM_JWT authentication configuration:

**❌ Incorrect configuration (causes "Invalid Bearer token" error):**
```yaml
AuthorizerConfiguration:
  CustomJWTAuthorizer:
    DiscoveryUrl: https://cognito-idp.{region}.amazonaws.com/{pool-id}/.well-known/openid-configuration
    AllowedAudience:  # M2M token has no aud claim!
      - resource-server-id
    AllowedClients:
      - client-id
```

**✅ Correct configuration:**
```yaml
AuthorizerConfiguration:
  CustomJWTAuthorizer:
    DiscoveryUrl: https://cognito-idp.{region}.amazonaws.com/{pool-id}/.well-known/openid-configuration
    AllowedClients:  # Only validate client_id claim
      - client-id
```

## FAQ

### Q: Deployment fails with "BedrockAgentCore resource not supported"?

A: Ensure your AWS Region supports Amazon Bedrock AgentCore service. Currently supported regions include us-east-1, us-west-2, etc.

### Q: How to get Cognito Client Secret?

A: In AWS Console → Cognito → User Pools → Select User Pool → App Integration → App clients → Click Client → Show Client Secret.

### Q: MCP endpoint returns "Invalid Bearer token" error?

A: This is usually because the Gateway's `AllowedAudience` configuration is incompatible with M2M tokens. Cognito client_credentials flow Access Tokens do not contain the `aud` claim. Remove the `AllowedAudience` configuration and keep only `AllowedClients`. See "Cognito M2M Authentication Configuration" section above.

### Q: Message sending fails with NETWORK_ERROR?

A: Check if Lambda has public internet access. If Lambda is in a VPC, you need to configure a NAT Gateway.

### Q: How to verify Access Token contents?

A: You can decode the JWT token to view its claims:
```bash
# Decode JWT payload (middle part)
echo "<ACCESS_TOKEN>" | cut -d'.' -f2 | base64 -d 2>/dev/null | jq .
```

## License

MIT License
