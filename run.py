from LLM import OpenRouterLLM
from utils import ResultSaver
import pprint

model_list = [
    "x-ai/grok-code-fast-1",
    "anthropic/claude-sonnet-4.5",
    "minimax/minimax-m2",
    "anthropic/claude-sonnet-4",
    "z-ai/glm-4.6",
    "google/gemini-2.5-flash",
    "qwen/qwen3-vl-235b-a22b-instruct",
    "qwen/qwen3-coder",
    "google/gemini-2.5-pro"
]

SYSTEM_PROMPT = "You are a code assistant."

USER_PROMPT = """
Your task is to complete the code provided by the user. Do nothing else. Please only output the complete code. The code to be completed is as follows:
with open('example.txt',
"""

if __name__ == "__main__":
    saver = ResultSaver(workdir="w_r_results")

    res = []

    for model in model_list:
        
        print(f"================== Evaluating model: {model} ==================")

        llm = OpenRouterLLM(model=model)    
        
        try_count = 0
        judge = True

        while not judge and judge != None:
            response = llm.get_completion(user=USER_PROMPT, system=SYSTEM_PROMPT, temperature=0.6, max_tokens=500)
            judge = llm.judge_answer(response)
            try_count += 1
            print(f"Attempt {try_count} for model {model}, Judge result: {judge}")
        
        model_result = {
            'model': model,
            "counter" : try_count,
        }

        print(f"Model: {model}, Attempts: {try_count}")

        res.append(model_result)
        saver.save_jsonl(item=model_result, filename="w_r_results")
    
    saver.save_json(results=res, filename="w_r_summary")