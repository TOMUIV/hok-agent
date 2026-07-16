import json, os
from text_adapter import observation_to_text, parse_llm_response, OBSERVATION_SYSTEM_PROMPT, get_available_decisions

LLM_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
LLM_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
LLM_MODEL = "qwen-plus"

class LLMAgent:
    def __init__(self, name: str, hero_id: int, api_key: str = None, use_api: bool = True):
        self.name = name
        self.hero_id = hero_id
        self.use_api = use_api
        self.history = []
        if use_api and (api_key or LLM_API_KEY):
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key or LLM_API_KEY, base_url=LLM_BASE_URL)
        else:
            self.client = None

    def decide(self, state: dict) -> tuple:
        obs_text = observation_to_text(state, agent_name=self.name)
        legal_str = get_available_decisions(state)
        prompt = obs_text + f"\nLegals: {legal_str}\nWhat do you do? Output JSON."
        self.history.append({"role": "user", "content": prompt})
        if self.client and self.use_api:
            try:
                resp = self.client.chat.completions.create(
                    model=LLM_MODEL,
                    messages=[{"role": "system", "content": OBSERVATION_SYSTEM_PROMPT}] + [{"role": "user", "content": prompt}],
                    temperature=0.7, max_tokens=200,
                )
                reply = resp.choices[0].message.content.strip()
            except Exception as e:
                reply = '{"decision_type": "MOVE", "params": {"direction": "N", "distance": "medium"}}'
        else:
            import random
            decisions = ["MOVE", "NORMAL_ATTACK", "SKILL_1", "NONE"]
            chosen = random.choice(decisions)
            reply = json.dumps({"decision_type": chosen, "params": {}})
        self.history.append({"role": "assistant", "content": reply})
        if len(self.history) > 20:
            self.history = self.history[-10:]
        return parse_llm_response(reply)

    def reset(self):
        self.history = []
