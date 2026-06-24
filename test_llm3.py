import os
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv

# Load environment variables from .env
load_dotenv(find_dotenv())

api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
base_url = os.environ.get("LLM_BASE_URL") or os.environ.get("OPENAI_BASE_URL", "https://integrate.api.nvidia.com/v1")
model = os.environ.get("LLM_MODEL") or os.environ.get("OPENAI_MODEL", "meta/llama-3.1-8b-instruct")

if not api_key:
    raise ValueError("Neither LLM_API_KEY nor OPENAI_API_KEY environment variable is set. Please create a .env file.")

client = OpenAI(api_key=api_key, base_url=base_url)

prompts = [
    'You are a clinic receptionist. The patient said: "hey". Patient name is unknown. You still need their full name. Write your reply as the receptionist (1-2 sentences, friendly):',
    'You are a clinic receptionist. The patient said: "my name is dave". Patient name is dave. You still need their phone. Write your reply as the receptionist (1-2 sentences, friendly):',
    'Extract JSON from: "my name is John Smith and I need to see a doctor for a headache". Fields: intent, full_name, reason_for_visit. Use null for missing.',
]

for i, prompt in enumerate(prompts):
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200 if i < 2 else 512,
            temperature=0.3,
            timeout=10
        )
        print(f"{i+1}: {resp.choices[0].message.content}")
        print("---")
    except Exception as e:
        print(f"{i+1}: {type(e).__name__}: {e}")
        print("---")