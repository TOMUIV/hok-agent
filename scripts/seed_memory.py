"""初始经验种子：原子技能规则"""
import json, os, time

SEED_SEMANTIC = [
    # === 发育推线 ===
    "just respawned, no enemies visible -> MOVE_TO toward lane center to farm",
    "minion wave present and safe -> LAST_HIT nearest low-HP minion for gold",
    "enemy minions pushing into tower range -> CLEAR to defend tower",
    "multiple minions in range -> CLEAR to push wave and gain level advantage",

    # === 消耗与击杀 ===
    "enemy in attack range and poke skill ready -> POKE to chip HP",
    "enemy HP below 40% and self HP above 60% -> COMBO_STEP to go for the kill",
    "enemy at low HP and fleeing -> CHASE to secure kill",
    "enemy in range and self has HP/item advantage -> ATTACK then COMBO_STEP",
    "self behind enemy tower -> RETREAT (tower aggro = death)",

    # === 防御与撤退 ===
    "self HP below 30% and enemy visible -> RETREAT toward own tower",
    "under tower fire -> RETREAT immediately (tower hits hard)",
    "self HP below 15% or outnumbered -> RETREAT all the way to spawn",
    "self past center of map (x > 0) and enemy missing -> RETREAT (possible gank)",

    # === 走位与节奏 ===
    "enemy just died (HP <= 0) -> LAST_HIT minions to push wave, then ATTACK tower",
    "self at base with full HP -> MOVE_TO toward lane to rejoin fight",
    "no enemy visible and no minions in range -> MOVE_TO forward to apply pressure",
    "self has item completed and enemy in range -> POKE to test fight",
    "enemy under their tower pushing wave -> POKE to harass, don't dive",
    "after winning trade, enemy recalling -> CLEAR wave fast to deny gold",
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
