"""初始经验种子：状态机决策规则"""
import json, os, time

# 完全对应 run_full_battle.py StateMachine.decide() 的19条规则
SEED_SEMANTIC = [
    # 按优先级排列，和状态机一致
    "HP below 1% (just respawned) -> call FARM to move to lane",
    "self_x within 2000 of spawn and HP below 60% -> call RETREAT to recover at fountain",
    "HP below 30% -> call RETREAT to fall back",
    "enemy HP <= 0 (enemy just died) -> call FARM to push lane and last hit minions",
    "2 or more enemy minions within 5000 range -> call DEFEND to clear wave first",
    "self_x past danger_x (enemy tower range) -> call RETREAT to avoid tower aggro",
    "self_x past center of map (x > 0) -> call POKE to harass enemy from mid range",
    "enemy_x past danger_x - 1000 and self_x > -20000 -> call POKE to pressure enemy near tower",
    "HP below 35% and enemy has HP advantage -> call RETREAT to avoid being killed",
    "distance to enemy > 8000 -> call FARM to move forward toward lane",
    "distance to enemy between 3500 and 8000 -> call POKE to approach and harass",
    "HP above 60% and enemy in range -> call ALL_IN to commit to the fight",
    "default when none of above apply -> call KITE to reposition safely",
    "after calling RETREAT, stay in RETREAT until reaching spawn area",
]

SEED_EPISODIC = []


def seed_memory(memory_path, hero_ai=None, hero_bot=None):
    now = time.time()
    semantic = []
    for rule_text in SEED_SEMANTIC:
        semantic.append({
            "rule": rule_text,
            "hero_ai": hero_ai,
            "hero_bot": hero_bot,
            "supported": 1,
            "contradicted": 0,
            "source_games": ["seed_sm"],
            "created_at": now,
            "updated_at": now,
            "active": True,
        })
    data = {"episodic": [], "semantic": semantic}
    os.makedirs(os.path.dirname(memory_path), exist_ok=True)
    with open(memory_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Seeded {len(semantic)} semantic rules from state machine")


if __name__ == "__main__":
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                        "trajectories", "memory.json")
    seed_memory(path)
    print(f"Written to {path}")
