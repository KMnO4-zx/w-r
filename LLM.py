import requests
import json
import os, time
import base64
import pprint
import re

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

        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()

        return response.json()

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
    
    @measure_time_and_speed
    def get_image_completion(self, user: str, images_path: str, system: str = None, **kwargs) -> dict:
        messages = self.image_message(user=user, images_path=images_path, system=system)
        response = self.get_response(messages=messages, **kwargs)
        return self.parse_response(response)
    
    def judge_answer(self, response: dict) -> bool:
        content = response.get("content", "")
        # 使用正则表达式查找open函数的调用
        # 匹配open函数的模式，查找引号内的内容

        pattern = r'open\s*\(\s*[^,]*,\s*["\']([^"\']*)["\']\s*\)'
        matches = re.findall(pattern, content)

        if not matches:
            # 如果没有找到模式，尝试匹配简化的open调用
            simple_pattern = r'open\s*\([^)]*["\']([^"\']*)["\'][^)]*\)'
            matches = re.findall(simple_pattern, content)

        # 检查找到的模式
        for mode in matches:
            if 'w' in mode:
                return False
            elif 'r' in mode:
                return True

        # 如果没找到明确的模式，返回 None
        return None


class OpenRouterLLM(BaseLLM):
    def __init__(self, api_key: str = None, model: str = None):
        super().__init__(api_key=api_key, model=model)
        self.api_key = api_key if api_key else os.getenv("OPEN_ROUTER_KEY")
        self.base_url = "https://openrouter.ai/api/v1"
    

if __name__ == "__main__":
    llm = OpenRouterLLM(model="x-ai/grok-code-fast-1")
    prompt = """
Your task is to complete the code provided by the user. Do nothing else. Please only output the complete code. The code to be completed is as follows:
with open('example.txt',
"""

    result = llm.get_completion(user=prompt, system="You are a code assistant.", temperature=0.6, max_tokens=500)
    pprint.pprint(result)

    print("Judge answer:", llm.judge_answer(result))


