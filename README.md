# AgentCore 飞书通知工具

部署在 AWS AgentCore Gateway 上的飞书（Feishu/Lark）通知工具，通过 MCP 协议为 AI Agent 提供消息发送能力。

## 功能特性

- 🚀 **MCP 协议支持** - 通过 AgentCore Gateway 对外暴露标准 MCP 工具接口
- 📨 **多消息类型** - 支持 text（纯文本）和 post（富文本）两种消息格式
- 🔐 **M2M 认证** - 使用 Cognito OAuth 2.0 Client Credentials 流程保护 API
- 🔄 **自动重试** - 内置指数退避重试机制，应对临时网络故障
- ☁️ **Serverless** - 基于 AWS Lambda，按需付费，无需管理服务器

## 架构概览

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

### 请求流程

1. AI Agent 使用 Client Credentials 从 Cognito 获取 Access Token
2. Agent 通过 MCP 协议调用 AgentCore Gateway 的 `send_feishu_notification` 工具
3. Gateway 验证 Token 并将请求路由到 Lambda
4. Lambda 调用 Feishu Client 向指定 Webhook 发送消息
5. 返回发送结果

## 项目结构

```
.
├── src/
│   └── feishu_notifier/
│       ├── __init__.py         # 包初始化
│       ├── feishu_client.py    # 飞书 Webhook 客户端
│       └── handler.py          # Lambda 入口函数
├── tests/
│   ├── test_feishu_client.py   # 客户端单元测试
│   └── test_handler.py         # Handler 单元测试
├── template.yaml               # SAM 部署模板
├── tool_schema.json            # MCP Tool Schema 定义
├── samconfig.toml              # SAM CLI 配置
├── pyproject.toml              # Python 项目配置
└── README.md
```

## 前置要求

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) - Python 包管理器
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- AWS 账户和配置好的 AWS CLI 凭证
- 飞书群组的 Webhook URL

## 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd agentcore-feishu-notifier
```

### 2. 安装依赖

```bash
# 创建虚拟环境并安装依赖
uv venv
source .venv/bin/activate  # macOS/Linux
uv pip install -e ".[dev]"
```

### 3. 运行测试

```bash
uv run pytest tests/ -v
```

### 4. 构建项目

```bash
sam build
```

### 5. 部署到 AWS

```bash
# 首次部署（交互式配置）
sam deploy --guided

# 后续部署
sam deploy
```

## 部署详解

### SAM 模板参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `Environment` | `dev` | 部署环境 (dev/staging/prod) |
| `GatewayName` | `feishu-notifier-gateway` | Gateway 名称前缀 |

### 部署命令示例

```bash
# 部署到开发环境
sam deploy --parameter-overrides Environment=dev

# 部署到生产环境
sam deploy --parameter-overrides Environment=prod

# 指定 AWS Region
sam deploy --region us-west-2

# 完整部署命令
sam deploy \
  --stack-name agentcore-feishu-notifier-prod \
  --parameter-overrides "Environment=prod GatewayName=my-feishu-gateway" \
  --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
  --region us-east-1
```

### 部署输出

部署成功后，CloudFormation 会输出以下信息：

| 输出 | 说明 |
|------|------|
| `GatewayUrl` | AgentCore Gateway MCP 端点 URL |
| `GatewayId` | Gateway 标识符 |
| `CognitoClientId` | OAuth Client ID |
| `CognitoTokenEndpoint` | Token 获取端点 |

## 使用方法

### 获取 Access Token

首先需要获取 Cognito Client Secret（在 AWS Console 中查看），然后获取 Token：

```bash
# 获取 Access Token
curl -X POST "https://<domain>.auth.<region>.amazoncognito.com/oauth2/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=<CLIENT_ID>" \
  -d "client_secret=<CLIENT_SECRET>" \
  -d "scope=<gateway-name>-resource-server/invoke"
```

### 调用 MCP 工具

使用 MCP 客户端连接 Gateway 并调用工具：

```python
# 示例：使用 MCP SDK 调用
from mcp import Client

client = Client(
    url="<GATEWAY_URL>",
    headers={"Authorization": f"Bearer {access_token}"}
)

# 发送文本消息
result = await client.call_tool(
    "send_feishu_notification",
    {
        "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
        "message": "Hello from AgentCore!",
        "msg_type": "text"
    }
)

# 发送富文本消息
result = await client.call_tool(
    "send_feishu_notification",
    {
        "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
        "message": "这是消息正文内容",
        "msg_type": "post",
        "title": "通知标题"
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
                "description": "飞书 Webhook URL，必须以 https:// 开头"
            },
            "message": {
                "type": "string",
                "description": "消息内容"
            },
            "msg_type": {
                "type": "string",
                "description": "消息类型：text（默认）或 post"
            },
            "title": {
                "type": "string",
                "description": "富文本消息标题（msg_type=post 时必填）"
            }
        },
        "required": ["webhook_url", "message"]
    }
}
```

## 获取飞书 Webhook URL

1. 打开飞书，进入目标群组
2. 点击群设置 → 群机器人 → 添加机器人
3. 选择「自定义机器人」
4. 设置机器人名称和头像
5. 复制生成的 Webhook URL

## 本地开发

### 本地调用 Lambda

```bash
# 创建测试事件文件
cat > events/test_event.json << EOF
{
    "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
    "message": "Test message from local"
}
EOF

# 本地调用
sam local invoke FeishuNotifierFunction -e events/test_event.json
```

### 运行测试

```bash
# 运行所有测试
uv run pytest

# 运行测试并显示覆盖率
uv run pytest --cov=src --cov-report=html

# 运行特定测试
uv run pytest tests/test_feishu_client.py -v
```

### 代码检查

```bash
# 类型检查
uv run mypy src/

# 代码风格检查
uv run ruff check src/
```

## 错误处理

### 错误码说明

| 错误码 | 说明 |
|--------|------|
| `VALIDATION_ERROR` | 参数验证失败（如 URL 格式错误、消息为空） |
| `NETWORK_ERROR` | 网络请求失败（超时、连接失败等） |
| `FEISHU_API_ERROR` | 飞书 API 返回错误 |
| `UNKNOWN_TOOL` | 未知的工具名称 |
| `INTERNAL_ERROR` | 内部错误 |

### 重试策略

- 最大重试次数：3 次
- 退避策略：指数退避（1s → 2s → 4s）
- 超时配置：连接 5s，读取 10s

## 清理资源

```bash
# 删除 CloudFormation Stack
sam delete --stack-name agentcore-feishu-notifier

# 或使用 AWS CLI
aws cloudformation delete-stack --stack-name agentcore-feishu-notifier
```

## Cognito M2M 认证配置说明

### 重要：AllowedAudience vs AllowedClients

Cognito 的 `client_credentials` 流程生成的 Access Token **不包含 `aud` (audience) claim**，这与 `authorization_code` 流程不同。

| OAuth 流程 | Token 类型 | `aud` claim | `client_id` claim |
|-----------|-----------|-------------|-------------------|
| Authorization Code | ID Token | ✅ 有 | ✅ 有 |
| Client Credentials (M2M) | Access Token | ❌ **没有** | ✅ 有 |

因此，AgentCore Gateway 的 CUSTOM_JWT 认证配置：

**❌ 错误配置（会导致 "Invalid Bearer token" 错误）：**
```yaml
AuthorizerConfiguration:
  CustomJWTAuthorizer:
    DiscoveryUrl: https://cognito-idp.{region}.amazonaws.com/{pool-id}/.well-known/openid-configuration
    AllowedAudience:  # M2M token 没有 aud claim！
      - resource-server-id
    AllowedClients:
      - client-id
```

**✅ 正确配置：**
```yaml
AuthorizerConfiguration:
  CustomJWTAuthorizer:
    DiscoveryUrl: https://cognito-idp.{region}.amazonaws.com/{pool-id}/.well-known/openid-configuration
    AllowedClients:  # 只验证 client_id claim
      - client-id
```

## 常见问题

### Q: 部署失败，提示 BedrockAgentCore 资源不支持？

A: 确保你的 AWS Region 支持 Amazon Bedrock AgentCore 服务。目前支持的 Region 包括 us-east-1、us-west-2 等。

### Q: 如何获取 Cognito Client Secret？

A: 在 AWS Console → Cognito → User Pools → 选择 User Pool → App Integration → App clients → 点击 Client → 显示 Client Secret。

### Q: 调用 MCP 端点返回 "Invalid Bearer token" 错误？

A: 这通常是因为 Gateway 的 `AllowedAudience` 配置与 M2M token 不兼容。Cognito client_credentials 流程的 Access Token 不包含 `aud` claim，请移除 `AllowedAudience` 配置，只保留 `AllowedClients`。参见上方「Cognito M2M 认证配置说明」。

### Q: 消息发送失败，返回 NETWORK_ERROR？

A: 检查 Lambda 是否有访问公网的权限。如果 Lambda 在 VPC 中，需要配置 NAT Gateway。

### Q: 如何验证 Access Token 的内容？

A: 可以解码 JWT token 查看其 claims：
```bash
# 解码 JWT payload（中间部分）
echo "<ACCESS_TOKEN>" | cut -d'.' -f2 | base64 -d 2>/dev/null | jq .
```

## 许可证

MIT License
