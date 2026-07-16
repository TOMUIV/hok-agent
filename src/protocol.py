REACT_PROTOCOL = """
每帧决策采用 ReAct 格式，可以多步推理：

Thought: <对当前局面的分析>
Action: <工具名>(<参数>)
Observation: <工具返回结果>

... (可重复多轮) ...

FinalAction: <决策类型>(<参数>)

决策类型:
  MOVE(direction, distance)     - 移动
    direction: N/NE/E/SE/S/SW/W/NW/STOP
    distance: short/medium/long
  ATTACK(target)                - 普通攻击
    target: ENEMY_0/ENEMY_1/NEAREST_MINION/NEAREST_TURRET
  SKILL_1(target, ox, oz)       - 技能1
  SKILL_2(target, ox, oz)       - 技能2
  SKILL_3(target, ox, oz)       - 技能3（大招）
  RECALL()                      - 回城
  WAIT()                        - 等待/不做操作
"""

TOOL_DEFINITIONS = {
    "query_hp": {
        "description": "查询所有英雄当前血量百分比",
        "params": {}
    },
    "query_position": {
        "description": "查询自己和敌方英雄的位置坐标",
        "params": {}
    },
    "query_hero_state": {
        "description": "查询指定英雄的详细状态（等级、经济、装备等）",
        "params": {"hero": "ENEMY_0 / ENEMY_1 / SELF"}
    },
    "query_cooldown": {
        "description": "查询技能冷却状态",
        "params": {}
    },
    "query_map": {
        "description": "查询地图状态（塔、小兵、野怪）",
        "params": {}
    },
    "query_buff": {
        "description": "查询英雄身上的 buff/debuff",
        "params": {}
    },
    "query_legal_actions": {
        "description": "查询当前可执行的合法操作",
        "params": {}
    },
}

FINAL_ACTION_PATTERNS = {
    "MOVE": r"MOVE\((\w+),\s*(\w+)\)",
    "ATTACK": r"ATTACK\((\w+)\)",
    "SKILL_1": r"SKILL_1\((\w+),\s*(-?\d+),\s*(-?\d+)\)",
    "SKILL_2": r"SKILL_2\((\w+),\s*(-?\d+),\s*(-?\d+)\)",
    "SKILL_3": r"SKILL_3\((\w+),\s*(-?\d+),\s*(-?\d+)\)",
    "RECALL": r"RECALL\(\)",
    "WAIT": r"WAIT\(\)",
}

ACTION_MAP = {
    "MOVE": 2, "NORMAL_ATTACK": 3, "ATTACK": 3,
    "SKILL_1": 4, "SKILL_2": 5, "SKILL_3": 6,
    "RECALL": 9, "NONE": 0,
}

DIR_MAP = {
    "N": (0, 1), "NE": (1, 1), "E": (1, 0), "SE": (1, -1),
    "S": (0, -1), "SW": (-1, -1), "W": (-1, 0), "NW": (-1, 1),
    "STOP": (0, 0),
}

TGT_MAP = {
    "ENEMY_HERO_0": 1, "ENEMY_HERO_1": 2, "ENEMY_0": 1, "ENEMY_1": 2,
    "NEAREST_MINION": 3, "NEAREST_TURRET": 4, "SELF": 7,
}

class DecisionType:
    MOVE = "MOVE"
    NORMAL_ATTACK = "NORMAL_ATTACK"
    ATTACK = "ATTACK"
    SKILL_1 = "SKILL_1"
    SKILL_2 = "SKILL_2"
    SKILL_3 = "SKILL_3"
    RECALL = "RECALL"
    NONE = "NONE"

def llm_decision_to_game_action(decision: dict) -> tuple:
    dtype = decision.get("decision_type", "NONE").upper()
    params = decision.get("params", {})

    btn = ACTION_MAP.get(dtype, 0)
    mvx, mvz = 1, 1
    skx, skz = 1, 1
    tgt = 0

    if dtype == "MOVE":
        d = params.get("direction", "N").upper()
        dx, dz = DIR_MAP.get(d, (0, 1))
        dist = params.get("distance", "medium")
        factor = {"short": 1, "medium": 2, "long": 3}.get(dist, 2)
        mvx = dx * factor + 8
        mvz = dz * factor + 8
    elif dtype in ("ATTACK", "NORMAL_ATTACK"):
        tgt = TGT_MAP.get(params.get("target", "ENEMY_0").upper(), 1)
    elif dtype.startswith("SKILL"):
        tgt = TGT_MAP.get(params.get("target", "ENEMY_0").upper(), 1)
        ox = int(params.get("offset_x", params.get("ox", 0)))
        oz = int(params.get("offset_z", params.get("oz", 0)))
        skx = ox + 8
        skz = oz + 8

    mvx = max(1, min(15, mvx))
    mvz = max(1, min(15, mvz))
    skx = max(1, min(15, skx))
    skz = max(1, min(15, skz))

    return (btn, mvx, mvz, skx, skz, tgt)

