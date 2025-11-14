import requests
import json
import os, time
import base64
import pprint
import re
import asyncio
import aiohttp

from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv())

from utils import measure_time_and_speed


class BaseLLM:
    def __init__(self, api_key: str = None, model: str = "gpt-4o"):
        self.api_key = api_key if api_key else os.getenv("OPENAI_API_KEY")
        self.base_url = "https://api.openai.com/v1"
        self.model = model

    def text_message(self, user: str, system: str = None, history: list = None) -> list:
        result = [{"role": "system", "content": system if system else "You are a helpful assistant."},]
        if history:
            for h in history:
                if h['role'] == 'user':
                    result.append({"role": "user", "content": h['content']})
                elif h['role'] == 'assistant':
                    result.append({"role": "assistant", "content": h['content']})
        result.append({"role": "user", "content": user})
        return result
    
    def image_message(self, user: str, images_path: str, system: str = None) -> list:
        result = [
            {"role": "system", "content": system if system else "You are a helpful assistant."}
        ]

        # 获取目录下所有图片文件
        if not os.path.isdir(images_path):
            raise ValueError(f"Path {images_path} is not a valid directory")

        # 支持的图片格式
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif', '.svg'}
        image_files = []

        # 遍历目录获取所有图片文件
        for filename in os.listdir(images_path):
            if any(filename.lower().endswith(ext) for ext in image_extensions):
                full_path = os.path.join(images_path, filename)
                if os.path.isfile(full_path):
                    image_files.append(full_path)

        # 按文件名排序
        image_files.sort()

        # 构建消息内容
        content = [{"type": "text", "text": user}]

        # 添加所有图片
        for img_path in image_files:
            with open(img_path, "rb") as img_file:
                img_base64 = base64.b64encode(img_file.read()).decode('utf-8')

                # 根据文件扩展名确定 MIME 类型
                ext = os.path.splitext(img_path)[1].lower()
                mime_types = {
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.gif': 'image/gif',
                    '.bmp': 'image/bmp',
                    '.webp': 'image/webp',
                    '.tiff': 'image/tiff',
                    '.tif': 'image/tiff',
                    '.svg': 'image/svg+xml'
                }
                mime_type = mime_types.get(ext, 'image/jpeg')

                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{img_base64}"
                    }
                })

        result.append({"role": "user", "content": content})
        return result

    def get_response(self, messages: list, **kwargs) -> dict:
        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": self.model,
            "messages": messages,
            **{k: v for k, v in kwargs.items()}
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        max_retries = 3
        retry_delay = 3  # seconds

        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    print(f"Request failed after {max_retries} attempts: {e}")
                    raise

        return response.json()

    async def get_response_async(self, messages: list, **kwargs) -> dict:
        """异步版本的get_response函数"""
        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": self.model,
            "messages": messages,
            **{k: v for k, v in kwargs.items()}
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        max_retries = 3
        retry_delay = 3  # seconds

        async with aiohttp.ClientSession() as session:
            for attempt in range(max_retries):
                try:
                    async with session.post(url, json=payload, headers=headers) as response:
                        response.raise_for_status()
                        return await response.json()
                except aiohttp.ClientError as e:
                    if attempt < max_retries - 1:
                        print(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
                        print(f"Retrying in {retry_delay} seconds...")
                        await asyncio.sleep(retry_delay)
                    else:
                        print(f"Request failed after {max_retries} attempts: {e}")
                        raise

        return await response.json()

    def parse_response(self, response) -> dict:
        message = response["choices"][0]["message"]
        reasoning_content = message.get("reasoning_content", None)
        content = message.get("content", "")

        model = response.get("model", "")
        usage = response.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)

        reasoning_tokens = None
        completion_tokens_details = usage.get("completion_tokens_details", {})
        if reasoning_content and completion_tokens_details:
            reasoning_tokens = completion_tokens_details.get("reasoning_tokens", None)

        return {
            "model": model,
            "content": content,
            "reasoning_content": reasoning_content,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "reasoning_tokens": reasoning_tokens
        }
    
    @measure_time_and_speed
    def get_completion(self, user: str, system: str = None, history: list = None, **kwargs) -> dict:
        messages = self.text_message(user=user, system=system, history=history)
        response = self.get_response(messages=messages, **kwargs)
        return self.parse_response(response)

    async def get_completion_async(self, user: str, system: str = None, history: list = None, **kwargs) -> dict:
        """异步版本的get_completion函数"""
        messages = self.text_message(user=user, system=system, history=history)
        response = await self.get_response_async(messages=messages, **kwargs)
        return self.parse_response(response)
    
    @measure_time_and_speed
    def get_image_completion(self, user: str, images_path: str, system: str = None, **kwargs) -> dict:
        messages = self.image_message(user=user, images_path=images_path, system=system)
        response = self.get_response(messages=messages, **kwargs)
        return self.parse_response(response)
    
    def judge_answer(self, response: dict) -> str:
        content = response.get("content", "")

        # 移除代码块标记，避免干扰正则表达式匹配
        content = re.sub(r'```(?:python)?\n?', '', content)
        content = re.sub(r'```', '', content)

        # 使用正则表达式查找open函数的调用
        # 匹配open函数的模式，查找引号内的内容
        patterns = [
            # 标准open调用: open(filename, "mode")
            r'open\s*\(\s*[^,]*,\s*["\']([^"\']*)["\']\s*\)',
            # with语句中的open调用: with open(filename, "mode") as f:
            r'with\s+open\s*\(\s*[^,]*,\s*["\']([^"\']*)["\']\s*\)\s*as',
            # 简化的open调用，处理更复杂的参数情况
            r'open\s*\([^)]*["\']([^"\']*)["\'][^)]*\)',
            # 处理带变量的open调用
            r'open\s*\([^)]*,\s*["\']([^"\']*)["\']',
            # 处理多行代码块中的with open
            r'with\s+open\s*\([^)]*["\']([^"\']*)["\'][^)]*\)\s*as',
            # 处理代码补全场景：直接以模式开头的字符串
            r'^[\'"]([rwa+]+)[\'"]\s*\)\s*as\s+\w+\s*:',
            # 处理更简单的模式检测
            r'^[\'"]([rwa+]+)[\'"]',
            # 处理带逗号的模式
            r'^[\'"]([rwa+]+)[\'"]\s*,',
            # 处理右括号后的模式
            r'^[\'"]([rwa+]+)[\'"]\s*\)'
        ]

        all_matches = []
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            all_matches.extend(matches)

        # 检查找到的模式
        for mode in all_matches:
            mode = mode.lower().strip()
            if 'w' in mode:
                return "w"
            elif 'r' in mode:
                return "r"

        # 特殊处理：如果内容以 'r') 或 'w') 开头，直接判断
        content_first_line = content.strip().split('\n')[0].strip()
        if content_first_line.startswith("'r')") or content_first_line.startswith('"r")'):
            return "r"
        elif content_first_line.startswith("'w')") or content_first_line.startswith('"w")'):
            return "w"

        # 处理更简单的场景：直接检测以 'r' 或 'w' 开头的字符串
        simple_match = re.match(r'^[\'"]([rwa+]+)[\'"]', content.strip())
        if simple_match:
            mode = simple_match.group(1).lower()
            if 'w' in mode:
                return "w"
            elif 'r' in mode:
                return "r"

        # 如果没找到明确的模式，返回 None
        return None


class OpenRouterLLM(BaseLLM):
    def __init__(self, api_key: str = None, model: str = None):
        super().__init__(api_key=api_key, model=model)
        self.api_key = api_key if api_key else os.getenv("OPEN_ROUTER_KEY")
        self.base_url = "https://openrouter.ai/api/v1"
    

model_list = [
    "x-ai/grok-code-fast-1",
    "moonshotai/kimi-k2-0905"
    "anthropic/claude-sonnet-4.5",
    "anthropic/claude-sonnet-4",
    "z-ai/glm-4.6",
    "google/gemini-2.5-flash",
    "qwen/qwen3-vl-235b-a22b-instruct",
    "qwen/qwen3-coder",
    "google/gemini-2.5-pro",
]

if __name__ == "__main__":
    llm = OpenRouterLLM(model="moonshotai/kimi-k2-0905")
    prompt = """
Your task is to complete the code provided by the user. Do nothing else. Please only output the complete code. The code to be completed is as follows:
with open('example.txt',
"""

    result = llm.get_completion(user=prompt, system="You are a code assistant.", temperature=0.7, max_tokens=500)
    pprint.pprint(result)

    print("Judge answer:", llm.judge_answer(result))


