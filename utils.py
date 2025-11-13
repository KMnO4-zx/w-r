import time
from functools import wraps
import os
import json
import numpy as np


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyEncoder, self).default(obj)


class ResultSaver:
    def __init__(self, workdir: str = "eval_results"):
        self.workdir = workdir
        if not os.path.exists(workdir):
            os.makedirs(workdir)

    def save_json(self, results: list, filename: str):
        filepath = os.path.join(self.workdir, f"{filename}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4, cls=NumpyEncoder)

    def save_jsonl(self, item: dict, filename: str):
        filepath = os.path.join(self.workdir, f"{filename}.jsonl")
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(item, ensure_ascii=False, cls=NumpyEncoder) + "\n")


def measure_time_and_speed(func):
    """装饰器：测量函数执行时间和token速度"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()

        elapsed_time = end_time - start_time

        # 如果结果是字典，添加时间信息和类名
        if isinstance(result, dict):
            result['elapsed_time'] = round(elapsed_time, 2)
            completion_tokens = result.get('completion_tokens', 0)
            if completion_tokens > 0 and elapsed_time > 0:
                result['token_speed'] = round(completion_tokens / elapsed_time, 2)
            else:
                result['token_speed'] = 0

            # 添加类名（如果是类方法）
            if args and hasattr(args[0], '__class__'):
                result['class_name'] = args[0].__class__.__name__

        return result

    return wrapper
