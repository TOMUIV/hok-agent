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
