"""Tests for Feishu Client"""

import pytest
from unittest.mock import patch, MagicMock
import urllib.error

from feishu_notifier.feishu_client import (
    FeishuClient,
    FeishuResponse,
    MessageType,
    ValidationError,
    NetworkError,
)


class TestFeishuClientValidation:
    """测试参数验证"""
    
    def test_empty_webhook_url_raises_error(self):
        """空 webhook_url 应该抛出验证错误"""
        client = FeishuClient()
        with pytest.raises(ValidationError, match="webhook_url is required"):
            client.send_notification("", "test message")
    
    def test_invalid_webhook_url_raises_error(self):
        """非 https:// 开头的 URL 应该抛出验证错误"""
        client = FeishuClient()
        with pytest.raises(ValidationError, match="must start with https://"):
            client.send_notification("http://example.com", "test message")
    
    def test_empty_message_raises_error(self):
        """空消息应该抛出验证错误"""
        client = FeishuClient()
        with pytest.raises(ValidationError, match="message cannot be empty"):
            client.send_notification("https://example.com", "")
    
    def test_whitespace_message_raises_error(self):
        """纯空白消息应该抛出验证错误"""
        client = FeishuClient()
        with pytest.raises(ValidationError, match="message cannot be empty"):
            client.send_notification("https://example.com", "   ")
    
    def test_invalid_msg_type_raises_error(self):
        """无效的消息类型应该抛出验证错误"""
        client = FeishuClient()
        with pytest.raises(ValidationError, match="msg_type must be one of"):
            client.send_notification("https://example.com", "test", msg_type="invalid")
    
    def test_post_without_title_raises_error(self):
        """post 类型没有 title 应该抛出验证错误"""
        client = FeishuClient()
        with pytest.raises(ValidationError, match="title is required"):
            client.send_notification("https://example.com", "test", msg_type="post")


class TestFeishuClientPayloadBuilding:
    """测试消息构建"""
    
    def test_build_text_payload(self):
        """测试 text 消息格式"""
        client = FeishuClient()
        payload = client._build_payload("Hello", "text", None)
        
        assert payload == {
            "msg_type": "text",
            "content": {"text": "Hello"}
        }
    
    def test_build_post_payload(self):
        """测试 post 消息格式"""
        client = FeishuClient()
        payload = client._build_payload("Hello", "post", "Title")
        
        assert payload == {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": "Title",
                        "content": [[{"tag": "text", "text": "Hello"}]]
                    }
                }
            }
        }


class TestFeishuClientSendRequest:
    """测试请求发送"""
    
    @patch("feishu_notifier.feishu_client.urllib.request.urlopen")
    def test_successful_send(self, mock_urlopen):
        """测试成功发送"""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"code": 0, "msg": "ok"}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = FeishuClient()
        response = client.send_notification(
            "https://open.feishu.cn/webhook/xxx",
            "test message"
        )
        
        assert response.success is True
        assert response.code == 0
    
    @patch("feishu_notifier.feishu_client.urllib.request.urlopen")
    def test_api_error_response(self, mock_urlopen):
        """测试 API 返回错误"""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"code": 19001, "msg": "invalid webhook"}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        client = FeishuClient()
        response = client.send_notification(
            "https://open.feishu.cn/webhook/xxx",
            "test message"
        )
        
        assert response.success is False
        assert response.code == 19001
    
    @patch("feishu_notifier.feishu_client.urllib.request.urlopen")
    def test_network_error_raises_exception(self, mock_urlopen):
        """测试网络错误"""
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        
        client = FeishuClient()
        with pytest.raises(NetworkError, match="Network error"):
            client.send_notification(
                "https://open.feishu.cn/webhook/xxx",
                "test message"
            )
    
    @patch("feishu_notifier.feishu_client.urllib.request.urlopen")
    def test_http_429_raises_network_error(self, mock_urlopen):
        """测试 429 限流"""
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "https://example.com", 429, "Too Many Requests", {}, None
        )
        
        client = FeishuClient()
        # 设置较短的退避时间以加快测试
        client.INITIAL_BACKOFF = 0.01
        
        with pytest.raises(NetworkError, match="Rate limited"):
            client.send_notification(
                "https://open.feishu.cn/webhook/xxx",
                "test message"
            )
    
    @patch("feishu_notifier.feishu_client.urllib.request.urlopen")
    def test_http_400_raises_validation_error(self, mock_urlopen):
        """测试 400 客户端错误"""
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "https://example.com", 400, "Bad Request", {}, None
        )
        
        client = FeishuClient()
        with pytest.raises(ValidationError, match="Client error"):
            client.send_notification(
                "https://open.feishu.cn/webhook/xxx",
                "test message"
            )


class TestFeishuClientRetry:
    """测试重试机制"""
    
    @patch("feishu_notifier.feishu_client.time.sleep")
    @patch("feishu_notifier.feishu_client.urllib.request.urlopen")
    def test_retry_on_network_error(self, mock_urlopen, mock_sleep):
        """测试网络错误时重试"""
        # 前两次失败，第三次成功
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"code": 0, "msg": "ok"}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        
        mock_urlopen.side_effect = [
            urllib.error.URLError("Connection refused"),
            urllib.error.URLError("Connection refused"),
            mock_response,
        ]
        
        client = FeishuClient()
        response = client.send_notification(
            "https://open.feishu.cn/webhook/xxx",
            "test message"
        )
        
        assert response.success is True
        assert mock_urlopen.call_count == 3
        assert mock_sleep.call_count == 2
    
    @patch("feishu_notifier.feishu_client.time.sleep")
    @patch("feishu_notifier.feishu_client.urllib.request.urlopen")
    def test_max_retries_exceeded(self, mock_urlopen, mock_sleep):
        """测试超过最大重试次数"""
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        
        client = FeishuClient()
        with pytest.raises(NetworkError, match="All 3 retry attempts failed"):
            client.send_notification(
                "https://open.feishu.cn/webhook/xxx",
                "test message"
            )
        
        assert mock_urlopen.call_count == 3
