"""Tests for Lambda Handler"""

import pytest
from unittest.mock import patch, MagicMock

from feishu_notifier.handler import (
    lambda_handler,
    _get_tool_name,
    _success_response,
    _error_response,
    TOOL_NAME_DELIMITER,
)


class TestToolNameParsing:
    """测试工具名称解析"""
    
    def test_parse_tool_name_with_prefix(self):
        """测试带前缀的工具名称解析"""
        context = MagicMock()
        context.client_context.custom = {
            "bedrockAgentCoreToolName": "feishu-target___send_feishu_notification"
        }
        
        result = _get_tool_name(context)
        assert result == "send_feishu_notification"
    
    def test_parse_tool_name_without_prefix(self):
        """测试不带前缀的工具名称"""
        context = MagicMock()
        context.client_context.custom = {
            "bedrockAgentCoreToolName": "send_feishu_notification"
        }
        
        result = _get_tool_name(context)
        assert result == "send_feishu_notification"
    
    def test_parse_tool_name_missing_context(self):
        """测试缺少 context 时返回默认值"""
        context = MagicMock()
        context.client_context = None
        
        result = _get_tool_name(context)
        assert result == "send_feishu_notification"
    
    def test_parse_tool_name_empty(self):
        """测试空工具名称"""
        context = MagicMock()
        context.client_context.custom = {
            "bedrockAgentCoreToolName": ""
        }
        
        result = _get_tool_name(context)
        assert result == ""


class TestResponseBuilding:
    """测试响应构建"""
    
    def test_success_response(self):
        """测试成功响应格式"""
        result = _success_response({"status": "ok"})
        
        assert result["success"] is True
        assert result["data"] == {"status": "ok"}
    
    def test_error_response(self):
        """测试错误响应格式"""
        result = _error_response("Something went wrong", "TEST_ERROR")
        
        assert result["success"] is False
        assert result["error"]["code"] == "TEST_ERROR"
        assert result["error"]["message"] == "Something went wrong"


class TestLambdaHandler:
    """测试 Lambda Handler"""
    
    @patch("feishu_notifier.handler.FeishuClient")
    def test_successful_notification(self, mock_client_class):
        """测试成功发送通知"""
        mock_client = MagicMock()
        mock_client.send_notification.return_value = MagicMock(
            success=True,
            code=0,
            message="ok"
        )
        mock_client_class.return_value = mock_client
        
        context = MagicMock()
        context.client_context.custom = {
            "bedrockAgentCoreToolName": "target___send_feishu_notification"
        }
        
        event = {
            "webhook_url": "https://open.feishu.cn/webhook/xxx",
            "message": "Test message"
        }
        
        result = lambda_handler(event, context)
        
        assert result["success"] is True
        assert result["data"]["status"] == "sent"
    
    def test_missing_webhook_url(self):
        """测试缺少 webhook_url"""
        context = MagicMock()
        context.client_context.custom = {
            "bedrockAgentCoreToolName": "send_feishu_notification"
        }
        
        event = {
            "message": "Test message"
        }
        
        result = lambda_handler(event, context)
        
        assert result["success"] is False
        assert result["error"]["code"] == "VALIDATION_ERROR"
        assert "webhook_url" in result["error"]["message"]
    
    def test_missing_message(self):
        """测试缺少 message"""
        context = MagicMock()
        context.client_context.custom = {
            "bedrockAgentCoreToolName": "send_feishu_notification"
        }
        
        event = {
            "webhook_url": "https://open.feishu.cn/webhook/xxx"
        }
        
        result = lambda_handler(event, context)
        
        assert result["success"] is False
        assert result["error"]["code"] == "VALIDATION_ERROR"
        assert "message" in result["error"]["message"]
    
    def test_unknown_tool(self):
        """测试未知工具"""
        context = MagicMock()
        context.client_context.custom = {
            "bedrockAgentCoreToolName": "unknown_tool"
        }
        
        event = {}
        
        result = lambda_handler(event, context)
        
        assert result["success"] is False
        assert result["error"]["code"] == "UNKNOWN_TOOL"
    
    @patch("feishu_notifier.handler.FeishuClient")
    def test_feishu_api_error(self, mock_client_class):
        """测试飞书 API 错误"""
        mock_client = MagicMock()
        mock_client.send_notification.return_value = MagicMock(
            success=False,
            code=19001,
            message="invalid webhook"
        )
        mock_client_class.return_value = mock_client
        
        context = MagicMock()
        context.client_context.custom = {
            "bedrockAgentCoreToolName": "send_feishu_notification"
        }
        
        event = {
            "webhook_url": "https://open.feishu.cn/webhook/xxx",
            "message": "Test message"
        }
        
        result = lambda_handler(event, context)
        
        assert result["success"] is False
        assert result["error"]["code"] == "FEISHU_API_ERROR"
    
    @patch("feishu_notifier.handler.FeishuClient")
    def test_network_error(self, mock_client_class):
        """测试网络错误"""
        from feishu_notifier.feishu_client import NetworkError
        
        mock_client = MagicMock()
        mock_client.send_notification.side_effect = NetworkError("Connection failed")
        mock_client_class.return_value = mock_client
        
        context = MagicMock()
        context.client_context.custom = {
            "bedrockAgentCoreToolName": "send_feishu_notification"
        }
        
        event = {
            "webhook_url": "https://open.feishu.cn/webhook/xxx",
            "message": "Test message"
        }
        
        result = lambda_handler(event, context)
        
        assert result["success"] is False
        assert result["error"]["code"] == "NETWORK_ERROR"
