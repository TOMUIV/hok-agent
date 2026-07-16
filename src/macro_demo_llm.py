import sys, os
sys.path.insert(0, os.path.dirname(__file__))
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

from mock_env import MockEnv
from macro_agent import MacroAgent
from strategy_executor import BUTTONS

HERO_AI = 199
HERO_BOT = 169

api_key = os.getenv("DASHSCOPE_API_KEY", "")
base_url = os.getenv("DASHSCOPE_BASE_URL", "")
model = os.getenv("MODEL_NAME", "deepseek-v4-flash")

env = MockEnv(hero_ids=[HERO_AI, HERO_BOT])
agent = MacroAgent("Agent", HERO_AI, HERO_BOT,
    api_key=api_key, base_url=base_url, model=model)
camp_list = [[{"hero_id": HERO_AI}], [{"hero_id": HERO_BOT}]]
state = env.reset(camp_hero_list=camp_list, use_common_ai=[False, True])

has_llm = bool(api_key)
print(f"LLM: {'ON' if has_llm else 'OFF (fallback random)'}  model={model}")
print(f"{'Agent(LLM)' if has_llm else 'Agent(random)'} vs Bot")
print()

step = 0
gameover = False
while not gameover and step < 100:
    action, reply = agent.decide(state)
    btn, mx, mz, skx, skz, tgt = action
    pb = state.get("req_pb")
    hp = ""
    if pb and hasattr(pb, "hero_list"):
        hl = pb.hero_list
        hp = f"YOU:{getattr(hl[0],'hp',0):.0f}/{getattr(hl[0],'max_hp',0)} ENEMY:{getattr(hl[1],'hp',0):.0f}/{getattr(hl[1],'max_hp',0)}"
    print(f"S{step:3d} ({mx:2d},{mz:2d}) b={btn}({BUTTONS[btn]}) {reply[:50]:50s} {hp}")
    state = env.step([action, (0,0,0,0,0,0)])
    if state.get("req_pb"):
        gameover = state["req_pb"].gameover
    step += 1

print(f"\nGame over at step {step}")
