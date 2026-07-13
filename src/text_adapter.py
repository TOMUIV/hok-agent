import json
from protocol import llm_decision_to_game_action, ACTION_MAP, DecisionType

HERO_NAMES = {
    106: "小乔", 107: "赵云", 108: "墨子", 111: "孙尚香", 112: "鲁班",
    117: "钟无艳", 119: "扁鹊", 120: "白起", 121: "芈月", 123: "吕布",
    128: "曹操", 130: "宫本武藏", 131: "李白", 132: "马可波罗", 133: "狄仁杰",
    135: "项羽", 140: "关羽", 141: "貂蝉", 146: "露娜", 150: "韩信",
    152: "王昭君", 154: "花木兰", 155: "艾琳", 157: "不知火舞", 163: "橘右京",
    167: "孙悟空", 169: "后羿", 173: "李元芳", 174: "虞姬", 175: "钟馗",
    176: "杨玉环", 182: "干将莫邪", 189: "鬼谷子", 190: "诸葛亮", 192: "黄忠",
    193: "凯", 194: "苏烈", 196: "百里守约", 199: "公孙离", 502: "裴擒虎",
    510: "孙策", 513: "上官婉儿", 522: "瑶",
}

BUTTON_NAMES = [
    "None1", "None2", "Move", "Attack", "Skill1", "Skill2",
    "Skill3", "HealSkill", "ChosenSkill", "Recall", "Skill4", "EquipSkill"
]

def observation_to_text(state: dict, hero_idx: int = 0, agent_name: str = "Hero") -> str:
    obs = state.get("observation", [])
    legal_action = state.get("legal_action", [])
    req_pb = state.get("req_pb", None)
    frame_no = state.get("frame_no", 0)
    text = f"=== Frame {frame_no} ===\n"
    if req_pb is not None:
        if hasattr(req_pb, 'hero_list'):
            heroes = req_pb.hero_list
            for h in heroes:
                hid = h.config_id if hasattr(h, 'config_id') else '?'
                camp = h.camp if hasattr(h, 'camp') else '?'
                hp = getattr(h, 'hp', '?')
                hname = HERO_NAMES.get(hid, f"Hero#{hid}")
                text += f"  [{camp}] {hname}  HP: {hp}\n"
        if hasattr(req_pb, 'frame_no'):
            text = f"=== Frame {req_pb.frame_no} ===\n"
        if hasattr(req_pb, 'gameover') and req_pb.gameover:
            text += "  [GAME OVER]\n"
    else:
        text += f"  [Observation dim: {len(obs) if hasattr(obs, '__len__') else 'N/A'}]\n"
    if len(legal_action) > 0:
        la = legal_action
        button_bits = la[:12]
        available = []
        for i, bit in enumerate(button_bits):
            if bit == 1 and i < len(BUTTON_NAMES):
                available.append(BUTTON_NAMES[i])
        if available:
            text += f"  Available: {', '.join(available)}\n"
    return text

def parse_llm_response(response_text: str, hero_idx: int = 0) -> tuple:
    try:
        decision = json.loads(response_text)
    except json.JSONDecodeError:
        lines = response_text.strip().split("\n")
        decision = {"decision_type": "NONE", "params": {}}
        for line in lines:
            line = line.strip()
            if line.startswith("DECISION:"):
                decision["decision_type"] = line.replace("DECISION:", "").strip()
            elif line.startswith("TARGET:"):
                decision.setdefault("params", {})["target"] = line.replace("TARGET:", "").strip()
            elif line.startswith("DIR:"):
                decision.setdefault("params", {})["direction"] = line.replace("DIR:", "").strip()
    return llm_decision_to_game_action(decision)

OBSERVATION_SYSTEM_PROMPT = """You are an AI controlling a hero in Honor of Kings (王者荣耀).
You receive game state as structured text and must output decisions in a hierarchical format.

DECISION TYPES: MOVE, NORMAL_ATTACK, SKILL_1, SKILL_2, SKILL_3, RECALL, NONE

Parameters per decision type:
  MOVE → direction (N/NE/E/SE/S/SW/W/NW/STOP), distance (short/medium/long)
  NORMAL_ATTACK → target (ENEMY_HERO_0/ENEMY_HERO_1/NEAREST_MINION/NEAREST_TURRET)
  SKILL_1/SKILL_2/SKILL_3 → target (ENEMY_HERO_0/...), offset_x (-8~8), offset_z (-8~8)
  RECALL → no params
  NONE → no params

Output format (JSON):
{"decision_type": "MOVE", "params": {"direction": "NE", "distance": "medium"}}
"""

def get_available_decisions(state: dict) -> str:
    legal_action = state.get("legal_action", [])
    if len(legal_action) < 12:
        return "MOVE, NORMAL_ATTACK, NONE"
    button_bits = legal_action[:12]
    available = []
    for i, bit in enumerate(button_bits):
        if bit == 1 and i < len(BUTTON_NAMES):
            name = BUTTON_NAMES[i]
            if name in ACTION_MAP:
                available.append(name.upper())
    return ", ".join(available) if available else "MOVE, NONE"
