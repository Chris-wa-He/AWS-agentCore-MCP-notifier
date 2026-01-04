"""Lambda Handler - AgentCore Gateway 请求处理"""

import json
import logging
from typing import Any, Optional

from .feishu_client import (
    FeishuClient,
    ValidationError,
    NetworkError,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 工具名称分隔符 (AgentCore Gateway 使用 ___ 作为 target 和 tool 名称的分隔符)
TOOL_NAME_DELIMITER = "___"


def _get_tool_name(context: Any) -> str:
    """
    从 context 中提取工具名称
    
    AgentCore Gateway 传递的工具名称格式为: {target_name}___{tool_name}
    需要去除 target 前缀获取实际工具名称
    
    Args:
        context: Lambda context 对象
        
    Returns:
        str: 实际工具名称
    """
    try:
        full_name = context.client_context.custom.get(
            "bedrockAgentCoreToolName", ""
        )
        # 去除 target 前缀
        if TOOL_NAME_DELIMITER in full_name:
            return full_name.split(TOOL_NAME_DELIMITER, 1)[1]
        return full_name
    except (AttributeError, KeyError, TypeError):
        # 如果无法从 context 获取，返回默认工具名称
        return "send_feishu_notification"


def _success_response(data: dict) -> dict:
    """
    构建成功响应
    
    Args:
        data: 响应数据
        
    Returns:
        dict: 成功响应对象
    """
    return {
        "success": True,
        "data": data
    }


def _error_response(message: str, error_code: str) -> dict:
    """
    构建错误响应
    
    Args:
        message: 错误消息
        error_code: 错误码
        
    Returns:
        dict: 错误响应对象
    """
    return {
        "success": False,
        "error": {
            "code": error_code,
            "message": message
        }
    }


def _handle_send_notification(event: dict) -> dict:
    """
    处理发送通知请求
    
    Args:
        event: 包含工具参数的事件对象
        
    Returns:
        dict: 操作结果
    """
    # 提取参数
    webhook_url = event.get("webhook_url")
    message = event.get("message")
    msg_type = event.get("msg_type", "text")
    title = event.get("title")
    
    # 验证必需参数
    if not webhook_url:
        return _error_response(
            "Missing required parameter: webhook_url",
            "VALIDATION_ERROR"
        )
    if not message:
        return _error_response(
            "Missing required parameter: message",
            "VALIDATION_ERROR"
        )
    
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


def lambda_handler(event: dict, context: Any) -> dict:
    """
    Lambda 入口函数
    
    处理来自 AgentCore Gateway 的工具调用请求
    
    Args:
        event: Gateway 传递的事件对象，包含工具参数
        context: Lambda 上下文对象，包含请求元数据
        
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
            result = _error_response(
                f"Unknown tool: {tool_name}",
                "UNKNOWN_TOOL"
            )
        
        logger.info(f"Response: {json.dumps(result)}")
        return result
        
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return _error_response(str(e), "INTERNAL_ERROR")
