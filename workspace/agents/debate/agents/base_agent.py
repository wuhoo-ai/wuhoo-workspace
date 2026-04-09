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
        api_base: str = os.environ.get("LLM_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        api_key: Optional[str] = None
    ):
        """
        初始化 Agent
        
        Args:
            name: Agent 名称
            prompt_path: Prompt 模板文件路径
            model: LLM 模型名称
            api_base: API 基础 URL
            api_key: API Key (可选，默认从环境变量读取)
        """
        self.name = name
        self.model = model
        self.api_base = api_base
        self.api_key = api_key or os.environ.get("BAILIAN_API_KEY")
        
        if not self.api_key:
            raise ValueError("API key not provided and BAILIAN_API_KEY not set in environment")
        
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
        
        messages = []
        
        # 添加系统提示
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        else:
            # 从 Prompt 模板提取系统提示
            system_content = self._extract_system_prompt()
            if system_content:
                messages.append({"role": "system", "content": system_content})
        
        # 添加用户输入
        messages.append({"role": "user", "content": user_input})
        
        # 调用 API
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
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
        
        for attempt in range(max_retries + 1):
            try:
                response = requests.post(
                    f"{self.api_base}/chat/completions",
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
        
        if response.status_code != 200:
            raise Exception(f"LLM API error: {response.status_code} - {response.text}")
        
        if response.status_code != 200:
            raise Exception(f"LLM API error: {response.status_code} - {response.text}")
        
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        
        # 添加到对话历史
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
