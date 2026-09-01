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
        api_key: Optional[str] = None,
        provider: str = "auto"
    ):
        """
        初始化 Agent

        Args:
            name: Agent 名称
            prompt_path: Prompt 模板文件路径
            model: LLM 模型名称
            api_base: API 基础 URL (默认使用百炼 Anthropic 兼容接口)
            api_key: API Key (优先 CODING_PLAN_KEY，其次 BAILIAN_API_KEY)
            provider: API 协议类型 ("anthropic" / "openai" / "auto")
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

        # 自动检测 provider
        if provider == "auto":
            if "deepseek" in (self.api_base or "").lower():
                self.provider = "openai"
            elif "dashscope" in (self.api_base or "").lower() or "anthropic" in (self.api_base or "").lower():
                self.provider = "anthropic"
            else:
                self.provider = "openai"  # 默认 OpenAI 兼容
        else:
            self.provider = provider

        if not self.api_key:
            # API key 检查延迟到 _call_llm 时（允许无 key 初始化用于测试）
            pass
        
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
        调用 LLM (支持 Anthropic / OpenAI 双协议)

        Args:
            user_input: 用户输入
            system_prompt: 系统提示 (可选)
            temperature: 温度参数
            max_tokens: 最大 token 数

        Returns:
            LLM 响应文本
        """
        import requests

        system_content = system_prompt or self._extract_system_prompt()

        if not self.api_key:
            raise ValueError("API key not set. Set CODING_PLAN_KEY or BAILIAN_API_KEY or DEEPSEEK_API_KEY environment variable.")

        if self.provider == "anthropic":
            return self._call_anthropic(user_input, system_content, temperature, max_tokens)
        else:
            return self._call_openai(user_input, system_content, temperature, max_tokens)

    def _call_anthropic(self, user_input: str, system_content: str,
                        temperature: float, max_tokens: int) -> str:
        """Anthropic 兼容协议 (bailian)"""
        import requests

        # 系统提示作为 user 消息的前缀（bailian anthropic 不支持 system role）
        full_input = f"<system>{system_content}</system>\n\n{user_input}"
        messages = [{"role": "user", "content": full_input}]

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

        response = self._http_post(
            f"{self.api_base}/v1/messages", headers, payload
        )

        result = response.json()
        content = ""
        content_list = result.get("content", [])
        for item in content_list:
            if isinstance(item, dict) and item.get("type") == "text":
                content = item.get("text", "")
                break
        if not content:
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

        self._save_history(user_input, content)
        return content

    def _call_openai(self, user_input: str, system_content: str,
                     temperature: float, max_tokens: int) -> str:
        """OpenAI 兼容协议 (deepseek / 通用)"""
        import requests

        messages = []
        if system_content:
            messages.append({"role": "system", "content": system_content})
        messages.append({"role": "user", "content": user_input})

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

        # deepseek-v4-pro: 移除 reasoning_effort 以获得更快结构化输出
        # （辩论系统需要 JSON 输出，不需要深度推理链）
        # 但 deepseek 内部仍做推理，需更多 max_tokens
        # Bear Agent 输出最大（含 bull_points_refuted 三组数组），需 10000+
        if "deepseek" in (self.api_base or "").lower():
            max_tokens = max(max_tokens, 16000)  # 至少 16000 tokens (Trader v2 reasoning很长)

        response = self._http_post(
            f"{self.api_base}/chat/completions", headers, payload
        )

        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        # deepseek reasoning 模型可能在 reasoning_content 里
        if not content:
            content = result.get("choices", [{}])[0].get("message", {}).get("reasoning_content", "")

        self._save_history(user_input, content)
        return content

    def _http_post(self, url: str, headers: dict, payload: dict) -> 'requests.Response':
        """HTTP POST with retry"""
        import requests
        import time as time_mod

        max_retries = 3
        last_error = None
        response = None

        for attempt in range(max_retries + 1):
            try:
                response = requests.post(
                    url, headers=headers, json=payload,
                    timeout=(10, 180)
                )
                if response.status_code == 200:
                    return response
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    time_mod.sleep(2)

        if response is None:
            raise Exception(f"LLM API request failed: {last_error}")
        raise Exception(f"LLM API error: {response.status_code} - {response.text[:500]}")

    def _save_history(self, user_input: str, content: str):
        """保存对话历史"""
        self.conversation_history.append({"role": "user", "content": user_input})
        self.conversation_history.append({"role": "assistant", "content": content})
    
    def _extract_system_prompt(self) -> Optional[str]:
        """从 Prompt 模板提取系统提示"""
        # 简单实现：返回整个模板
        # 可以改进为提取特定部分
        return self.prompt_template
    
    def _parse_json_output(self, text: str) -> Dict:
        """
        解析 JSON 输出（增强版 v3 — 处理推理模型输出）

        Args:
            text: LLM 响应文本（可能包含推理链 + JSON）

        Returns:
            解析后的 JSON 对象
        """
        import re

        # 1. 直接解析
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass

        # 2. 提取 ```json ... ``` 代码块（支持无闭合 ``` 的截断情况）
        m = re.search(r'```json\s*(.*?)(?:```|$)', text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1).strip())
            except json.JSONDecodeError:
                pass
            # 尝试修复截断的 ```json 块
            fixed = self._repair_truncated_json(m.group(1).strip())
            if fixed:
                try:
                    return json.loads(fixed)
                except json.JSONDecodeError:
                    pass

        # 3. 提取第一个 { 到最后 } 之间的内容
        start = text.find('{')
        end = text.rfind('}') + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass

        # 4. 从推理文本中提取 JSON（处理"我们被要求分析..."开头的情况）
        if start >= 0:
            # 尝试找到 JSON 开始的精确位置（跳过推理文字）
            json_candidates = list(re.finditer(r'\{(?=[^{]*"(?:agent|recommendation|symbol)")', text))
            for candidate in json_candidates:
                candidate_start = candidate.start()
                # 找到对应的结尾
                brace_count = 0
                end_pos = -1
                for i in range(candidate_start, len(text)):
                    if text[i] == '{':
                        brace_count += 1
                    elif text[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_pos = i + 1
                            break
                if end_pos > candidate_start:
                    try:
                        return json.loads(text[candidate_start:end_pos])
                    except json.JSONDecodeError:
                        continue

        # 5. 修复截断 JSON
        if start >= 0:
            fixed = self._repair_truncated_json(text[start:])
            if fixed:
                try:
                    return json.loads(fixed)
                except json.JSONDecodeError:
                    pass

        # 所有尝试都失败
        snippet = text[:300].replace('\n', '\\n')
        raise ValueError(f"Failed to parse JSON from: {snippet}...")

    @staticmethod
    def _repair_truncated_json(text: str) -> Optional[str]:
        """修复截断 JSON — 处理 ```json 包裹 + 数组中间字符串截断"""
        import re

        # 0. 剥离 ```json ... ``` 包裹
        text = re.sub(r'^```json\s*', '', text.strip())
        if text.endswith('```'):
            text = text[:-3].strip()

        lines = text.split('\n')
        
        # 移除末尾不完整的行（保留可能是截断字符串的行）
        while lines and not re.search(r'["\],}\]]\s*$', lines[-1].strip()):
            last_line = lines[-1].strip()
            if re.search(r':\s*".*[^"]$', last_line) or re.search(r',\s*$', last_line):
                break
            lines.pop()
        if not lines:
            return None

        text = '\n'.join(lines)

        open_braces = text.count('{') - text.count('}')
        open_brackets = text.count('[') - text.count(']')
        
        # 检查是否在字符串中被截断（处理转义引号）
        in_string = False
        i = 0
        while i < len(text):
            ch = text[i]
            if ch == '\\' and i + 1 < len(text):
                i += 2
                continue
            if ch == '"':
                in_string = not in_string
            i += 1
        
        if in_string:
            text += '"\n'
        
        if open_brackets > 0:
            text += '\n]' * open_brackets
        if open_braces > 0:
            text += '\n}' * open_braces

        # 移除尾部逗号
        text = re.sub(r',\s*([}\]])', r'\1', text)
        text = re.sub(r',\s*$', '', text, flags=re.MULTILINE)

        return text if (open_braces > 0 or open_brackets > 0 or in_string) else None
    
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
