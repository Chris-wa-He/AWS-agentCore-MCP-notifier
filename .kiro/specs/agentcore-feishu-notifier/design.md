# 设计文档

## 概述

本设计文档描述了 AgentCore 飞书通知工具的技术架构和实现方案。该工具通过 AWS Lambda 实现飞书消息发送功能，并通过 Amazon Bedrock AgentCore Gateway 对外暴露为 MCP 工具。系统使用 Amazon Cognito 的 M2M（Machine-to-Machine）认证方式进行访问控制。

### 核心组件

1. **Notifier Lambda** - 处理飞书消息发送的核心业务逻辑
2. **Feishu Client** - 封装飞书 Webhook API 调用
3. **AgentCore Gateway** - 提供 MCP 协议接入，处理工具发现和调用
4. **Cognito User Pool** - 提供 M2M OAuth 2.0 认证

### Cognito M2M 认证配置要点

⚠️ **重要**: Cognito `client_credentials` 流程的 Access Token **不包含 `aud` claim**，因此 AgentCore Gateway 的 CUSTOM_JWT 配置**不能使用 `AllowedAudience`**，只能使用 `AllowedClients` 验证 `client_id`。

```yaml
# ✅ 正确的 M2M 认证配置
AuthorizerConfiguration:
  CustomJWTAuthorizer:
    DiscoveryUrl: https://cognito-idp.{region}.amazonaws.com/{pool-id}/.well-known/openid-configuration
    AllowedClients:
      - !Ref CognitoUserPoolClient
```

## 架构

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

1. AI Agent 使用 OAuth 2.0 Client Credentials 从 Cognito 获取 Access Token
2. AI Agent 通过 MCP 协议调用 AgentCore Gateway
3. Gateway 验证 Token 并将请求路由到 Lambda Target
4. Lambda 从 event 中提取参数，调用 Feishu Client
5. Feishu Client 向指定的 Webhook URL 发送消息
6. Lambda 返回结果，Gateway 将响应返回给 Agent

## 组件和接口

### Feishu Client 模块

```python
# src/feishu_notifier/feishu_client.py

from dataclasses import dataclass
from enum import Enum
from typing import Optional
import urllib.request
import urllib.error
import json
import time
import logging

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """飞书消息类型"""
    TEXT = "text"
    POST = "post"


@dataclass
class FeishuResponse:
    """飞书 API 响应"""
    success: bool
    code: int
    message: str
    data: Optional[dict] = None


class FeishuClientError(Exception):
    """飞书客户端错误基类"""
    pass


class ValidationError(FeishuClientError):
    """参数验证错误"""
    pass


class NetworkError(FeishuClientError):
    """网络错误"""
    pass


class FeishuClient:
    """飞书 Webhook 客户端"""
    
    MAX_RETRIES = 3
    CONNECT_TIMEOUT = 5
    READ_TIMEOUT = 10
    INITIAL_BACKOFF = 1.0
    
    def send_notification(
        self,
        webhook_url: str,
        message: str,
        msg_type: str = "text",
        title: Optional[str] = None
    ) -> FeishuResponse:
        """
        发送飞书通知
        
        Args:
            webhook_url: 飞书 Webhook URL
            message: 消息内容
            msg_type: 消息类型 (text 或 post)
            title: 富文本消息标题 (仅 post 类型需要)
            
        Returns:
            FeishuResponse: 发送结果
            
        Raises:
            ValidationError: 参数验证失败
            NetworkError: 网络请求失败
        """
        # 参数验证
        self._validate_params(webhook_url, message, msg_type, title)
        
        # 构建请求体
        payload = self._build_payload(message, msg_type, title)
        
        # 发送请求（带重试）
        return self._send_with_retry(webhook_url, payload)
    
    def _validate_params(
        self,
        webhook_url: str,
        message: str,
        msg_type: str,
        title: Optional[str]
    ) -> None:
        """验证参数"""
        if not webhook_url:
            raise ValidationError("webhook_url is required")
        
        if not webhook_url.startswith("https://"):
            raise ValidationError("webhook_url must start with https://")
        
        if not message or not message.strip():
            raise ValidationError("message cannot be empty")
        
        if msg_type not in [t.value for t in MessageType]:
            raise ValidationError(f"msg_type must be one of: {[t.value for t in MessageType]}")
        
        if msg_type == MessageType.POST.value and not title:
            raise ValidationError("title is required for post message type")
    
    def _build_payload(
        self,
        message: str,
        msg_type: str,
        title: Optional[str]
    ) -> dict:
        """构建请求体"""
        if msg_type == MessageType.TEXT.value:
            return {
                "msg_type": "text",
                "content": {
                    "text": message
                }
            }
        else:  # post
            return {
                "msg_type": "post",
                "content": {
                    "post": {
                        "zh_cn": {
                            "title": title,
                            "content": [[{"tag": "text", "text": message}]]
                        }
                    }
                }
            }
    
    def _send_with_retry(self, webhook_url: str, payload: dict) -> FeishuResponse:
        """带重试的发送请求"""
        last_error = None
        backoff = self.INITIAL_BACKOFF
        
        for attempt in range(self.MAX_RETRIES):
            try:
                return self._send_request(webhook_url, payload)
            except NetworkError as e:
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    # 检查是否是限流
                    if "429" in str(e):
                        # 尝试从错误中提取 retry-after
                        time.sleep(backoff * 2)
                    else:
                        time.sleep(backoff)
                    backoff *= 2
                    logger.warning(f"Retry attempt {attempt + 1} after error: {e}")
        
        raise NetworkError(f"All {self.MAX_RETRIES} retry attempts failed: {last_error}")
    
    def _send_request(self, webhook_url: str, payload: dict) -> FeishuResponse:
        """发送 HTTP 请求"""
        data = json.dumps(payload).encode("utf-8")
        
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(
                req,
                timeout=self.CONNECT_TIMEOUT + self.READ_TIMEOUT
            ) as response:
                result = json.loads(response.read().decode("utf-8"))
                
                if result.get("code") == 0 or result.get("StatusCode") == 0:
                    return FeishuResponse(
                        success=True,
                        code=0,
                        message="ok",
                        data=result
                    )
                else:
                    return FeishuResponse(
                        success=False,
                        code=result.get("code", -1),
                        message=result.get("msg", "Unknown error"),
                        data=result
                    )
                    
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise NetworkError(f"Rate limited (429): {e.reason}")
            elif 400 <= e.code < 500:
                raise ValidationError(f"Client error ({e.code}): {e.reason}")
            else:
                raise NetworkError(f"Server error ({e.code}): {e.reason}")
        except urllib.error.URLError as e:
            raise NetworkError(f"Network error: {e.reason}")
        except Exception as e:
            raise NetworkError(f"Unexpected error: {str(e)}")
```

### Lambda Handler 模块

```python
# src/feishu_notifier/handler.py

import json
import logging
from typing import Any

from .feishu_client import (
    FeishuClient,
    FeishuClientError,
    ValidationError,
    NetworkError
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 工具名称分隔符
TOOL_NAME_DELIMITER = "___"


def lambda_handler(event: dict, context: Any) -> dict:
    """
    Lambda 入口函数
    
    Args:
        event: Gateway 传递的事件对象，包含工具参数
        context: Lambda 上下文对象
        
    Returns:
        dict: 操作结果
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # 从 context 获取工具名称
        tool_name = _get_tool_name(context)
        logger.info(f"Tool name: {tool_name}")
        
        # 根据工具名称路由
        if tool_name == "send_feishu_notification":
            result = _handle_send_notification(event)
        else:
            result = _error_response(f"Unknown tool: {tool_name}", "UNKNOWN_TOOL")
        
        logger.info(f"Response: {json.dumps(result)}")
        return result
        
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return _error_response(str(e), "INTERNAL_ERROR")


def _get_tool_name(context: Any) -> str:
    """从 context 中提取工具名称"""
    try:
        full_name = context.client_context.custom.get(
            "bedrockAgentCoreToolName", ""
        )
        # 去除 target 前缀
        if TOOL_NAME_DELIMITER in full_name:
            return full_name.split(TOOL_NAME_DELIMITER, 1)[1]
        return full_name
    except (AttributeError, KeyError):
        # 如果无法从 context 获取，尝试从 event 获取
        return "send_feishu_notification"


def _handle_send_notification(event: dict) -> dict:
    """处理发送通知请求"""
    # 提取参数
    webhook_url = event.get("webhook_url")
    message = event.get("message")
    msg_type = event.get("msg_type", "text")
    title = event.get("title")
    
    # 验证必需参数
    if not webhook_url:
        return _error_response("Missing required parameter: webhook_url", "VALIDATION_ERROR")
    if not message:
        return _error_response("Missing required parameter: message", "VALIDATION_ERROR")
    
    # 发送通知
    client = FeishuClient()
    
    try:
        response = client.send_notification(
            webhook_url=webhook_url,
            message=message,
            msg_type=msg_type,
            title=title
        )
        
        if response.success:
            return _success_response({
                "status": "sent",
                "message": "Notification sent successfully"
            })
        else:
            return _error_response(
                f"Feishu API error: {response.message}",
                "FEISHU_API_ERROR"
            )
            
    except ValidationError as e:
        return _error_response(str(e), "VALIDATION_ERROR")
    except NetworkError as e:
        return _error_response(str(e), "NETWORK_ERROR")


def _success_response(data: dict) -> dict:
    """构建成功响应"""
    return {
        "success": True,
        "data": data
    }


def _error_response(message: str, error_code: str) -> dict:
    """构建错误响应"""
    return {
        "success": False,
        "error": {
            "code": error_code,
            "message": message
        }
    }
```

## 数据模型

### Tool Schema 定义

```json
{
    "name": "send_feishu_notification",
    "description": "Send a notification message to a Feishu (Lark) group via webhook. Supports both plain text and rich text (post) message formats.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "webhook_url": {
                "type": "string",
                "description": "The Feishu webhook URL for the target group. Must start with https://"
            },
            "message": {
                "type": "string",
                "description": "The notification message content to send"
            },
            "msg_type": {
                "type": "string",
                "description": "Message type: 'text' for plain text, 'post' for rich text with title. Defaults to 'text'"
            },
            "title": {
                "type": "string",
                "description": "Title for rich text (post) messages. Required when msg_type is 'post'"
            }
        },
        "required": ["webhook_url", "message"]
    },
    "outputSchema": {
        "type": "object",
        "properties": {
            "success": {
                "type": "boolean",
                "description": "Whether the notification was sent successfully"
            },
            "data": {
                "type": "object",
                "description": "Response data when successful"
            },
            "error": {
                "type": "object",
                "description": "Error details when failed"
            }
        }
    }
}
```

### 飞书 Webhook 请求格式

**Text 消息:**
```json
{
    "msg_type": "text",
    "content": {
        "text": "消息内容"
    }
}
```

**Post 消息:**
```json
{
    "msg_type": "post",
    "content": {
        "post": {
            "zh_cn": {
                "title": "标题",
                "content": [[{"tag": "text", "text": "消息内容"}]]
            }
        }
    }
}
```



## 正确性属性

*正确性属性是指在系统所有有效执行中都应保持为真的特征或行为——本质上是关于系统应该做什么的形式化陈述。属性作为人类可读规范和机器可验证正确性保证之间的桥梁。*


### Property 1: 输入验证正确性

*对于任意* 无效的输入参数（空 webhook_url、非 https:// 开头的 URL、空消息、纯空白消息），Feishu_Client 应当返回相应的 ValidationError，而不是尝试发送请求。

**验证: 需求 1.3, 1.5**

### Property 2: 消息格式构建正确性

*对于任意* 有效的消息内容和消息类型（text 或 post），Feishu_Client 构建的请求体应当符合飞书 Webhook API 的格式要求：
- text 类型：包含 `msg_type: "text"` 和 `content.text` 字段
- post 类型：包含 `msg_type: "post"` 和 `content.post.zh_cn.title` 及 `content.post.zh_cn.content` 字段

**验证: 需求 1.6, 1.7**

### Property 3: 工具名称解析正确性

*对于任意* 带有 target 前缀的工具名称（格式为 `{target_name}___{tool_name}`），Notifier_Lambda 应当正确提取出实际的工具名称。

**验证: 需求 2.2**

### Property 4: 必需参数验证

*对于任意* 缺少必需参数（webhook_url 或 message）的 event 对象，Notifier_Lambda 应当返回包含 VALIDATION_ERROR 错误码的错误响应。

**验证: 需求 2.4**

### Property 5: 成功响应格式

*对于任意* 成功处理的请求，Lambda 返回的响应应当包含 `success: true` 和 `data` 字段。

**验证: 需求 2.5**

### Property 6: 重试机制正确性

*对于任意* 网络超时错误，Feishu_Client 应当最多重试 3 次，且每次重试之间的等待时间应当按指数增长（指数退避）。

**验证: 需求 6.1**

### Property 7: 错误类型区分

*对于任意* HTTP 错误响应，Notifier_Lambda 应当正确区分客户端错误（4xx）和服务器错误（5xx），并在响应中使用相应的错误码。

**验证: 需求 6.5**

## 错误处理

### 错误类型

| 错误类型 | 错误码 | 描述 | HTTP 状态码范围 |
|---------|--------|------|----------------|
| ValidationError | VALIDATION_ERROR | 参数验证失败 | 4xx |
| NetworkError | NETWORK_ERROR | 网络请求失败 | 5xx |
| FeishuApiError | FEISHU_API_ERROR | 飞书 API 返回错误 | - |
| UnknownToolError | UNKNOWN_TOOL | 未知的工具名称 | 4xx |
| InternalError | INTERNAL_ERROR | 内部错误 | 5xx |

### 重试策略

```
初始退避时间: 1 秒
最大重试次数: 3 次
退避策略: 指数退避 (1s -> 2s -> 4s)
限流处理: 遵守 retry-after 头
```

### 超时配置

```
连接超时: 5 秒
读取超时: 10 秒
总超时: 15 秒
```

## 测试策略

### 单元测试

单元测试用于验证特定示例和边界情况：

1. **Feishu Client 测试**
   - 测试有效消息发送（mock HTTP 响应）
   - 测试各种无效输入的验证错误
   - 测试网络错误处理
   - 测试重试机制

2. **Lambda Handler 测试**
   - 测试参数提取
   - 测试工具名称解析
   - 测试成功响应格式
   - 测试错误响应格式

3. **Tool Schema 测试**
   - 验证 schema 结构符合 AgentCore Gateway 格式
   - 验证必需字段和可选字段定义

### 属性测试

属性测试用于验证跨所有输入的通用属性：

- **测试框架**: pytest + hypothesis
- **最小迭代次数**: 100 次/属性
- **标签格式**: `Feature: agentcore-feishu-notifier, Property {number}: {property_text}`

每个正确性属性都应实现为单独的属性测试：

1. Property 1: 输入验证正确性
2. Property 2: 消息格式构建正确性
3. Property 3: 工具名称解析正确性
4. Property 4: 必需参数验证
5. Property 5: 成功响应格式
6. Property 6: 重试机制正确性
7. Property 7: 错误类型区分

### 集成测试

集成测试验证端到端流程（需要实际的飞书 Webhook）：

1. 发送 text 消息到测试群组
2. 发送 post 消息到测试群组
3. 验证错误处理（使用无效 Webhook）

