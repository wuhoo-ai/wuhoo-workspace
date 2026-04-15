#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base Agent - Agent 基类

所有辩论 Agent (Bull/Bear/Trader/Risk) 的基类。
"""

import json
import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime


class BaseAgent(ABC):
    """
    Agent 基类
    
    提供通用的 LLM 调用、Prompt 加载、输出解析等功能。
    """
    
    def __init__(
        self,
        name: str,
        prompt_path: str,
        model: str = "qwen3.5-plus",
        api_base: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        初始化 Agent

        Args:
            name: Agent 名称
            prompt_path: Prompt 模板文件路径
            model: LLM 模型名称
            api_base: API 基础 URL (默认使用百炼 Anthropic 兼容接口)
            api_key: API Key (优先 CODING_PLAN_KEY，其次 BAILIAN_API_KEY)
        """
        self.name = name
        self.model = model

        # API 配置：优先使用环境变量，默认百炼 Anthropic 兼容接口
        self.api_base = api_base or os.environ.get(
            "LLM_API_BASE",
            "https://coding.dashscope.aliyuncs.com/apps/anthropic"
        )
        # API Key 优先级：显式传入 > CODING_PLAN_KEY > BAILIAN_API_KEY
        self.api_key = api_key or os.environ.get("CODING_PLAN_KEY") or os.environ.get("BAILIAN_API_KEY")

        if not self.api_key:
            raise ValueError("API key not provided and CODING_PLAN_KEY/BAILIAN_API_KEY not set in environment")
        
        # 加载 Prompt 模板
        self.prompt_template = self._load_prompt(prompt_path)
        
        # 对话历史
        self.conversation_history: List[Dict] = []
    
    def _load_prompt(self, prompt_path: str) -> str:
        """加载 Prompt 模板"""
        path = Path(prompt_path)
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    
    def _call_llm(
        self,
        user_input: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """
        调用 LLM

        Args:
            user_input: 用户输入
            system_prompt: 系统提示 (可选)
            temperature: 温度参数
            max_tokens: 最大 token 数

        Returns:
            LLM 响应文本
        """
        import requests

        # 注意：百炼 Anthropic 兼容接口不支持 {"role": "system"} in messages
        # 系统提示需要作为第一个 user 消息的前缀传入
        system_content = system_prompt or self._extract_system_prompt()

        # 将系统提示拼接到用户输入前面
        if system_content:
            full_user_input = f"<system>{system_content}</system>\n\n{user_input}"
        else:
            full_user_input = user_input

        messages = [{"role": "user", "content": full_user_input}]
        
        # 调用 API
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # 增加超时时间和重试机制
        max_retries = 2
        last_error = None
        
        response = None
        for attempt in range(max_retries + 1):
            try:
                response = requests.post(
                    f"{self.api_base}/v1/messages",
                    headers=headers,
                    json=payload,
                    timeout=120  # 增加到 120 秒
                )
                if response.status_code == 200:
                    break
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    import time
                    time.sleep(2)  # 重试前等待 2 秒
        
        if response is None:
            raise Exception(f"LLM API request failed: {last_error}")

        if response.status_code != 200:
            raise Exception(f"LLM API error: {response.status_code} - {response.text}")
        
        result = response.json()
        # Anthropic 格式：content 是数组，提取 text 字段
        content_list = result.get("content", [])
        content = ""
        for item in content_list:
            if isinstance(item, dict) and item.get("type") == "text":
                content = item.get("text", "")
                break
        if not content:
            # 兼容 OpenAI 格式
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # 添加到对话历史（只记录实际的用户输入和助手响应）
        self.conversation_history.append({"role": "user", "content": user_input})
        self.conversation_history.append({"role": "assistant", "content": content})
        
        return content
    
    def _extract_system_prompt(self) -> Optional[str]:
        """从 Prompt 模板提取系统提示"""
        # 简单实现：返回整个模板
        # 可以改进为提取特定部分
        return self.prompt_template
    
    def _parse_json_output(self, text: str) -> Dict:
        """
        解析 JSON 输出
        
        Args:
            text: LLM 响应文本
        
        Returns:
            解析后的 JSON 对象
        """
        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # 尝试提取 JSON 代码块
        import re
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # 尝试提取第一个 { 到最后一个 }
        start = text.find('{')
        end = text.rfind('}') + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        
        # 所有尝试都失败
        raise ValueError(f"Failed to parse JSON from: {text[:200]}...")
    
    def analyze(self, input_data: Dict) -> Dict:
        """
        分析输入，生成输出
        
        Args:
            input_data: 输入数据
        
        Returns:
            分析结果
        """
        # 默认实现，子类可以覆盖
        raise NotImplementedError("Subclasses should implement this method")
    
    def reset(self) -> None:
        """重置对话历史"""
        self.conversation_history = []
    
    def get_history(self) -> List[Dict]:
        """获取对话历史"""
        return self.conversation_history.copy()
