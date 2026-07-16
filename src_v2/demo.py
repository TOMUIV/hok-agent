import sys, os, json, time

sys.path.insert(0, os.path.dirname(__file__))
from mock_env import MockEnv
from agent import LLMAgent

HERO_NAMES = {132: "马可波罗", 169: "后羿", 141: "貂蝉", 107: "赵云", 199: "公孙离"}

def run_demo(hero_ids=None, use_real_llm=False, api_key=None, max_steps=100):
    if hero_ids is None:
        hero_ids = [132, 169]
    env = MockEnv(hero_ids=hero_ids)
    agents = []
    for i, hid in enumerate(hero_ids):
        hname = HERO_NAMES.get(hid, f"Hero_{hid}")
        agent = LLMAgent(f"Agent_{hname}", hid, api_key=api_key, use_api=use_real_llm)
        agents.append(agent)
    camp_list = [[{"hero_id": hid}] for hid in hero_ids]
    state = env.reset(camp_hero_list=camp_list, use_common_ai=[False, True])
    print(f"Match: {HERO_NAMES.get(hero_ids[0], '?')} vs {HERO_NAMES.get(hero_ids[1], '?')}")
    print("=" * 50)
    step_count = 0
    gameover = False
    start_time = time.time()
    while not gameover and step_count < max_steps:
        step_count += 1
        actions = [(0, 0, 0, 0, 0, 0), (0, 0, 0, 0, 0, 0)]
        action = agents[0].decide(state)
        actions[0] = action
        state = env.step(actions)
        req_pb = state.get("req_pb", None)
        if req_pb:
            gameover = getattr(req_pb, "gameover", False)
            frame = getattr(req_pb, "frame_no", 0)
            heroes_list = getattr(req_pb, "hero_list", [])
            if step_count % 10 == 0:
                status = []
                for h in heroes_list:
                    hid = getattr(h, "config_id", "?")
                    hname = HERO_NAMES.get(hid, f"H{hid}")
                    hp = getattr(h, "hp", 0)
                    status.append(f"{hname}:{hp:.0f}")
                print(f"  Step {step_count} (Frame {frame}): {', '.join(status)}")
        if req_pb and getattr(req_pb, "gameover", False):
            break
    elapsed = time.time() - start_time
    print("=" * 50)
    print(f"Demo finished. {step_count} steps in {elapsed:.1f}s")
    return step_count

if __name__ == "__main__":
    api_key = os.environ.get("DASHSCOPE_API_KEY", "")
    use_llm = bool(api_key)
    if use_llm:
        print(f"[LLM mode: {os.environ.get('DASHSCOPE_API_KEY', '')[:8]}...]")
    else:
        print("[Fallback mode: random decisions]")
    run_demo(hero_ids=[132, 169], use_real_llm=use_llm, api_key=api_key, max_steps=100)
