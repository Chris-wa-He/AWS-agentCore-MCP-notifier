"""Feishu Webhook Client - 飞书 Webhook 客户端模块"""

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
    
    def _validate_params(
        self,
        webhook_url: str,
        message: str,
        msg_type: str,
        title: Optional[str]
    ) -> None:
        """
        验证参数
        
        Args:
            webhook_url: 飞书 Webhook URL
            message: 消息内容
            msg_type: 消息类型
            title: 富文本消息标题
            
        Raises:
            ValidationError: 参数验证失败
        """
        if not webhook_url:
            raise ValidationError("webhook_url is required")
        
        if not webhook_url.startswith("https://"):
            raise ValidationError("webhook_url must start with https://")
        
        if not message or not message.strip():
            raise ValidationError("message cannot be empty")
        
        valid_types = [t.value for t in MessageType]
        if msg_type not in valid_types:
            raise ValidationError(f"msg_type must be one of: {valid_types}")
        
        if msg_type == MessageType.POST.value and not title:
            raise ValidationError("title is required for post message type")

    
    def _build_payload(
        self,
        message: str,
        msg_type: str,
        title: Optional[str]
    ) -> dict:
        """
        构建请求体
        
        Args:
            message: 消息内容
            msg_type: 消息类型
            title: 富文本消息标题
            
        Returns:
            dict: 飞书 Webhook 请求体
        """
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

    
    def _send_request(self, webhook_url: str, payload: dict) -> FeishuResponse:
        """
        发送 HTTP 请求
        
        Args:
            webhook_url: 飞书 Webhook URL
            payload: 请求体
            
        Returns:
            FeishuResponse: 响应对象
            
        Raises:
            ValidationError: 客户端错误 (4xx)
            NetworkError: 网络或服务器错误
        """
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
                
                # 飞书 API 成功响应: code=0 或 StatusCode=0
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
        except json.JSONDecodeError as e:
            raise NetworkError(f"Invalid JSON response: {str(e)}")
        except Exception as e:
            raise NetworkError(f"Unexpected error: {str(e)}")

    
    def _send_with_retry(self, webhook_url: str, payload: dict) -> FeishuResponse:
        """
        带重试的发送请求
        
        Args:
            webhook_url: 飞书 Webhook URL
            payload: 请求体
            
        Returns:
            FeishuResponse: 响应对象
            
        Raises:
            NetworkError: 所有重试都失败
        """
        last_error: Optional[Exception] = None
        backoff = self.INITIAL_BACKOFF
        
        for attempt in range(self.MAX_RETRIES):
            try:
                return self._send_request(webhook_url, payload)
            except NetworkError as e:
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    # 检查是否是限流
                    if "429" in str(e):
                        # 限流时使用更长的等待时间
                        wait_time = backoff * 2
                    else:
                        wait_time = backoff
                    
                    logger.warning(
                        f"Retry attempt {attempt + 1}/{self.MAX_RETRIES} "
                        f"after {wait_time}s due to: {e}"
                    )
                    time.sleep(wait_time)
                    backoff *= 2  # 指数退避
            except ValidationError:
                # 验证错误不重试
                raise
        
        raise NetworkError(
            f"All {self.MAX_RETRIES} retry attempts failed. Last error: {last_error}"
        )

    
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
            msg_type: 消息类型 (text 或 post)，默认 text
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
