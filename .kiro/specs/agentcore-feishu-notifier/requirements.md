# 需求文档

## 简介

本项目是一个部署在 AWS AgentCore Gateway 上的飞书（Feishu/Lark）通知工具。项目使用 AWS Lambda 实现飞书消息发送的业务逻辑，通过 SAM CLI 进行管理和部署。AgentCore Gateway 负责 MCP 协议处理，Lambda 函数只需专注于通知功能的实现。Gateway 使用 Amazon Cognito 的 M2M（Machine-to-Machine）认证方式进行访问控制。

## 术语表

- **Notifier_Lambda**: Lambda 函数，实现飞书消息发送的核心业务逻辑
- **Feishu_Client**: 飞书 API 客户端模块，封装飞书 Webhook 调用逻辑
- **AgentCore_Gateway**: AWS Bedrock AgentCore 网关服务，提供 MCP 协议接入能力，自动处理工具发现和调用
- **Tool_Schema**: Lambda 工具定义，描述工具名称、输入输出参数结构，供 Gateway 解析
- **SAM_Template**: AWS SAM 部署模板，定义 Lambda 函数和 AgentCore Gateway 资源
- **Webhook_URL**: 飞书机器人 Webhook 地址，作为工具调用参数传入
- **Event_Object**: Gateway 传递给 Lambda 的事件对象，包含工具输入参数
- **Context_Object**: Gateway 传递给 Lambda 的上下文对象，包含请求元数据
- **Cognito_User_Pool**: Amazon Cognito 用户池，用于 M2M 认证
- **Resource_Server**: Cognito 资源服务器，定义 OAuth 2.0 scope
- **Client_Credentials**: OAuth 2.0 客户端凭证，用于 M2M 认证流程

## 需求

### 需求 1: 飞书消息发送

**用户故事:** 作为开发者，我希望能够向飞书群组发送通知，以便及时告知团队成员重要事件。

#### 验收标准

1. 当收到有效的消息内容和 Webhook_URL 时，Feishu_Client 应当将消息发送到指定的 Webhook_URL
2. 当消息成功投递时，Feishu_Client 应当返回包含投递状态的成功响应
3. 如果 Webhook_URL 格式无效，则 Feishu_Client 应当返回 URL 格式验证错误
4. 如果 Webhook_URL 不可达，则 Feishu_Client 应当返回包含描述性错误信息的网络错误响应
5. 如果消息内容为空或无效，则 Feishu_Client 应当返回消息验证错误
6. Feishu_Client 应当支持 text 消息类型用于基础通知
7. Feishu_Client 应当支持 post（富文本）消息类型用于带标题的格式化通知

### 需求 2: Lambda 函数处理

**用户故事:** 作为系统运维人员，我希望 Lambda 函数能够可靠地处理 Gateway 请求，以确保通知被正确处理。

#### 验收标准

1. 当从 Gateway 收到 event 对象时，Notifier_Lambda 应当从 event 中提取工具参数
2. 当 context 对象包含工具名称时，Notifier_Lambda 应当去除 target 前缀并识别实际工具
3. 当收到 send_feishu_notification 工具调用时，Notifier_Lambda 应当使用提供的参数调用 Feishu_Client
4. 如果 event 中缺少必需参数（webhook_url 或 message），则 Notifier_Lambda 应当返回错误响应
5. 当处理成功完成时，Notifier_Lambda 应当返回包含操作结果的 JSON 响应
6. 如果发生意外错误，则 Notifier_Lambda 应当捕获异常并返回优雅的错误响应
7. Notifier_Lambda 应当记录传入的 event 和响应以便调试

### 需求 3: 工具定义 (Tool Schema)

**用户故事:** 作为 AI Agent 开发者，我希望有定义良好的工具 schema，以便 AgentCore Gateway 能够正确暴露通知工具。

#### 验收标准

1. Tool_Schema 应当定义一个名为 "send_feishu_notification" 的工具，包含名称和描述
2. Tool_Schema 应当在 inputSchema 中定义 "webhook_url" 作为必需的 string 类型参数，用于指定目标飞书群组
3. Tool_Schema 应当在 inputSchema 中定义 "message" 作为必需的 string 类型参数
4. Tool_Schema 应当在 inputSchema 中定义可选的 "msg_type" 参数（默认值: "text"，可选值: "text" 或 "post"）
5. Tool_Schema 应当在 inputSchema 中定义可选的 "title" 参数用于富文本消息
6. Tool_Schema 应当遵循 AgentCore Gateway ToolDefinition 格式，包含 type、description 和 properties
7. Tool_Schema 应当可以内联嵌入 SAM 模板或上传到 S3

### 需求 4: Cognito M2M 认证

**用户故事:** 作为安全工程师，我希望 Gateway 使用 Cognito M2M 认证，以确保只有授权的客户端能够调用通知工具。

#### 验收标准

1. SAM_Template 应当定义 Cognito User Pool 用于 M2M 认证
2. SAM_Template 应当定义 Resource Server 并配置适当的 OAuth 2.0 scope
3. SAM_Template 应当定义 User Pool Client 并启用 client_credentials 授权流程
4. SAM_Template 应当为 User Pool 创建域名以支持 OAuth 2.0 端点
5. AgentCore_Gateway 应当配置 Cognito 作为 Inbound Auth 的 identity provider
6. SAM_Template 应当输出 Client ID、Client Secret 和 Token Endpoint 供客户端使用

### 需求 5: SAM 部署模板

**用户故事:** 作为 DevOps 工程师，我希望有完整的 SAM 模板，以便通过单个命令部署 Lambda、Gateway 和认证资源。

#### 验收标准

1. SAM_Template 应当定义使用 Python 3.11+ 运行时的 Lambda 函数
2. SAM_Template 应当配置 Lambda 的适当内存（128MB）和超时（30s）设置
3. SAM_Template 应当定义 AgentCore Gateway 资源并关联 Cognito authorizer
4. SAM_Template 应当定义 Gateway Target，将 Lambda 函数与 Tool_Schema 关联
5. SAM_Template 应当包含具有最小权限的 Lambda IAM 执行角色
6. SAM_Template 应当输出 Gateway endpoint URL、Gateway ID 和认证相关信息
7. 当执行 `sam deploy` 时，SAM_Template 应当创建所有必需的 AWS 资源

### 需求 6: 错误处理与重试

**用户故事:** 作为系统运维人员，我希望有健壮的错误处理机制，以确保临时故障不会导致通知丢失。

#### 验收标准

1. 当飞书 API 调用发生网络超时时，Feishu_Client 应当使用指数退避策略重试请求最多 3 次
2. 如果所有重试尝试都失败，则 Feishu_Client 应当返回包含失败原因的详细错误响应
3. Feishu_Client 应当为 HTTP 请求设置适当的超时值（连接: 5s，读取: 10s）
4. 当检测到限流（HTTP 429）时，Feishu_Client 应当在重试前遵守 retry-after 头
5. Notifier_Lambda 应当在响应中区分客户端错误（4xx）和服务器错误（5xx）

