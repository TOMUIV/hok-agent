import sys, os, math, random
sys.path.insert(0, os.path.dirname(__file__))
sys.stdout.reconfigure(encoding='utf-8')

from mock_env import MockEnv, HERO_TEMPLATES
from strategy_executor import StrategyExecutor, MACRO_ACTIONS, BUTTONS

def test_executor():
    env = MockEnv(hero_ids=[199, 169])
    executor = StrategyExecutor(self_hero_id=199)
    camp_list = [[{"hero_id": 199}], [{"hero_id": 169}]]
    state = env.reset(camp_hero_list=camp_list, use_common_ai=[False, True])

    tests = 0
    failures = []
    for step in range(300):
        for macro in MACRO_ACTIONS:
            if state.get("req_pb") and state["req_pb"].gameover:
                break
            action = executor.execute(macro, state)
            btn, mx, mz, skx, skz, tgt = action
            la = state.get("legal_action", [])
            if len(la) >= 12:
                if mx < 1 or mx > 15 or mz < 1 or mz > 15 or skx < 1 or skx > 15 or skz < 1 or skz > 15:
                    failures.append(f"step{step} {macro}: coord out of bounds ({mx},{mz},{skx},{skz})")
                if tgt < 0 or tgt > 7:
                    failures.append(f"step{step} {macro}: target out of range {tgt}")
                if btn < 0 or btn > 11:
                    failures.append(f"step{step} {macro}: button out of range {btn}")
                btn_name = BUTTONS[btn] if btn < len(BUTTONS) else "?"
                if btn < 12 and la[btn] != 1:
                    failures.append(f"step{step} {macro}: illegal button {btn}({btn_name})")
                tests += 1
        state = env.step([(0,0,0,0,0,0), (0,0,0,0,0,0)])
        if state.get("req_pb") and state["req_pb"].gameover:
            break

    print(f"Tested {tests} actions")
    if failures:
        print(f"FAILURES ({len(failures)}):")
        for f in failures[:20]:
            print(f"  {f}")
    else:
        print("ALL ACTIONS LEGAL: no failures")
    return len(failures) == 0

def test_scripted_game():
    env = MockEnv(hero_ids=[199, 169])
    executor = StrategyExecutor(self_hero_id=199)
    camp_list = [[{"hero_id": 199}], [{"hero_id": 169}]]
    state = env.reset(camp_hero_list=camp_list, use_common_ai=[False, True])

    script = ["FARM"] * 10 + ["POKE"] * 5 + ["PURSUE"] * 5 + ["KITE"] * 3 + ["RETREAT"] * 5 + ["DEFEND"] * 5 + ["ALL_IN"] * 5
    gameover = False
    step = 0

    while not gameover and step < 100:
        macro = script[step % len(script)]
        action = executor.execute(macro, state)
        btn, mx, mz, skx, skz, tgt = action
        pb = state.get("req_pb")
        hp_str = ""
        if pb and hasattr(pb, "hero_list"):
            hp_str = ", ".join([
                f"ID{h.config_id}:{getattr(h,'hp',0):.0f}/{getattr(h,'max_hp',0)}"
                for h in pb.hero_list
            ])
        print(f"Step{step:3d} {macro:12s} ({mx:2d},{mz:2d}) btn={btn}({BUTTONS[btn]}) tgt={tgt} | {hp_str}")
        state = env.step([action, (0,0,0,0,0,0)])
        if state.get("req_pb"):
            gameover = state["req_pb"].gameover
        step += 1

    print(f"\nGame over at step {step}")

if __name__ == "__main__":
    print("=== Validating strategy_executor ===")
    ok = test_executor()
    print()
    print("=== Scripted game (no LLM) ===")
    test_scripted_game()
