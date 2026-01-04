# 实现计划: AgentCore 飞书通知工具

## 概述

本实现计划将设计文档转化为可执行的编码任务。任务按照依赖关系排序，确保每个任务都建立在前一个任务的基础上。

## 任务

- [x] 1. 项目初始化和基础结构
  - 创建项目目录结构
  - 初始化 pyproject.toml 和依赖配置
  - 创建 SAM 模板骨架
  - _需求: 5.1_

- [x] 2. 实现 Feishu Client 模块
  - [x] 2.1 实现核心数据类型和异常类
    - 创建 MessageType 枚举
    - 创建 FeishuResponse 数据类
    - 创建 FeishuClientError、ValidationError、NetworkError 异常类
    - _需求: 1.2, 1.3, 1.4, 1.5_

  - [x] 2.2 实现参数验证逻辑
    - 实现 _validate_params 方法
    - 验证 webhook_url 格式（必须以 https:// 开头）
    - 验证 message 非空
    - 验证 msg_type 有效性
    - 验证 post 类型必须有 title
    - _需求: 1.3, 1.5_

  - [ ]* 2.3 编写输入验证属性测试
    - **Property 1: 输入验证正确性**
    - **验证: 需求 1.3, 1.5**

  - [x] 2.4 实现消息构建逻辑
    - 实现 _build_payload 方法
    - 支持 text 消息格式
    - 支持 post 消息格式
    - _需求: 1.6, 1.7_

  - [ ]* 2.5 编写消息格式构建属性测试
    - **Property 2: 消息格式构建正确性**
    - **验证: 需求 1.6, 1.7**

  - [x] 2.6 实现 HTTP 请求发送
    - 实现 _send_request 方法
    - 设置超时配置（连接: 5s，读取: 10s）
    - 处理 HTTP 响应和错误
    - _需求: 1.1, 1.2, 6.3_

  - [x] 2.7 实现重试机制
    - 实现 _send_with_retry 方法
    - 实现指数退避策略
    - 处理 429 限流响应
    - _需求: 6.1, 6.2, 6.4_

  - [ ]* 2.8 编写重试机制属性测试
    - **Property 6: 重试机制正确性**
    - **验证: 需求 6.1**

  - [x] 2.9 实现 send_notification 主方法
    - 组合验证、构建、发送逻辑
    - _需求: 1.1, 1.2_

- [x] 3. 检查点 - 确保 Feishu Client 测试通过
  - 确保所有测试通过，如有问题请询问用户

- [x] 4. 实现 Lambda Handler 模块
  - [x] 4.1 实现工具名称解析
    - 实现 _get_tool_name 函数
    - 处理带 target 前缀的工具名称
    - _需求: 2.2_

  - [ ]* 4.2 编写工具名称解析属性测试
    - **Property 3: 工具名称解析正确性**
    - **验证: 需求 2.2**

  - [x] 4.3 实现参数提取和验证
    - 从 event 中提取 webhook_url、message、msg_type、title
    - 验证必需参数存在
    - _需求: 2.1, 2.4_

  - [ ]* 4.4 编写必需参数验证属性测试
    - **Property 4: 必需参数验证**
    - **验证: 需求 2.4**

  - [x] 4.5 实现响应构建
    - 实现 _success_response 函数
    - 实现 _error_response 函数
    - _需求: 2.5, 2.6_

  - [ ]* 4.6 编写成功响应格式属性测试
    - **Property 5: 成功响应格式**
    - **验证: 需求 2.5**

  - [x] 4.7 实现 lambda_handler 主函数
    - 组合工具名称解析、参数提取、业务逻辑调用
    - 实现错误处理和日志记录
    - _需求: 2.3, 2.6, 2.7_

  - [ ]* 4.8 编写错误类型区分属性测试
    - **Property 7: 错误类型区分**
    - **验证: 需求 6.5**

- [x] 5. 检查点 - 确保 Lambda Handler 测试通过
  - 确保所有测试通过，如有问题请询问用户

- [x] 6. 创建 Tool Schema 定义
  - [x] 6.1 创建 tool_schema.json 文件
    - 定义 send_feishu_notification 工具
    - 定义 inputSchema 和 outputSchema
    - _需求: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [ ]* 6.2 编写 Tool Schema 验证测试
    - 验证 schema 结构符合 AgentCore Gateway 格式
    - _需求: 3.6_

- [x] 7. 创建 SAM 部署模板
  - [x] 7.1 定义 Cognito 资源
    - 创建 User Pool
    - 创建 Resource Server 和 scope
    - 创建 User Pool Client（client_credentials 流程）
    - 创建 User Pool Domain
    - _需求: 4.1, 4.2, 4.3, 4.4_

  - [x] 7.2 定义 Lambda 函数资源
    - 配置 Python 3.11 运行时
    - 配置内存和超时
    - 创建 IAM 执行角色
    - _需求: 5.1, 5.2, 5.5_

  - [x] 7.3 定义 AgentCore Gateway 资源
    - 创建 Gateway 并配置 Cognito authorizer（仅使用 AllowedClients，不使用 AllowedAudience）
    - 创建 Gateway Target 关联 Lambda 和 Tool Schema
    - 创建 Gateway 服务角色
    - _需求: 4.5, 5.3, 5.4_

  - [x] 7.4 定义 Outputs
    - 输出 Gateway URL 和 Gateway ID
    - 输出 Cognito Client ID 和 Token Endpoint
    - _需求: 4.6, 5.6_

- [x] 8. 最终检查点 - 确保所有测试通过
  - 运行完整测试套件
  - 确保所有测试通过，如有问题请询问用户

## 备注

- 标记 `*` 的任务为可选任务，可跳过以加快 MVP 开发
- 每个任务都引用了具体的需求以便追溯
- 检查点确保增量验证
- 属性测试验证通用正确性属性
- 单元测试验证特定示例和边界情况

