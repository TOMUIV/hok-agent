from hero_db import hero_name
from state_parser import hero_detail

TOOL_REGISTRY = {}

def register(name, description, params=None):
    def wrapper(fn):
        TOOL_REGISTRY[name] = {"fn": fn, "description": description, "parameters": params or {}}
        return fn
    return wrapper

@register("query_hp", "查询双方当前血量百分比")
def query_hp(info):
    pb = info.get("req_pb")
    if not pb:
        return "No data"
    lines = []
    for h in getattr(pb, "hero_list", []):
        cid = getattr(h, "config_id", 0)
        hp = getattr(h, "hp", 0)
        mhp = getattr(h, "max_hp", 1)
        pct = hp / mhp * 100
        visible = getattr(h, "camp_visible", [])
        fow = " (FOW)" if not (any(visible) if visible else True) else ""
        lines.append(f"{hero_name(cid)}: {hp}/{mhp}({pct:.0f}%){fow}")
    return "\n".join(lines)

@register("query_position", "查询双方当前位置坐标")
def query_position(info):
    pb = info.get("req_pb")
    if not pb:
        return "No data"
    lines = []
    for h in getattr(pb, "hero_list", []):
        cid = getattr(h, "config_id", 0)
        loc = getattr(h, "location", None)
        pos = f"({loc.x},{loc.y})" if loc and hasattr(loc, "x") else "(?,?)"
        lines.append(f"{hero_name(cid)} @ {pos}")
    return "\n".join(lines)

@register("query_hero_state", "查询英雄详细信息", {"hero": "SELF / ENEMY_0"})
def query_hero_state(info, hero="SELF"):
    pb = info.get("req_pb")
    if not pb:
        return "No data"
    self_id = getattr(info.get("_self_id"), "config_id", 0) if info.get("_self_id") else 0
    target = None
    for h in getattr(pb, "hero_list", []):
        cid = getattr(h, "config_id", 0)
        if hero == "SELF" and cid == self_id:
            target = h
            break
        if hero.startswith("ENEMY") and cid != self_id:
            target = h
            break
    if not target and getattr(pb, "hero_list", []):
        target = getattr(pb, "hero_list", [])[0]
    if not target:
        return "No hero found"
    return hero_detail(target)

@register("query_map", "查询地图状态（小兵、防御塔、野怪）")
def query_map(info):
    pb = info.get("req_pb")
    if not pb:
        return "No data"
    lines = []
    organs = getattr(pb, "organ_list", [])
    soldiers = getattr(pb, "soldier_list", [])
    monsters = getattr(pb, "monster_list", [])
    if organs:
        lines.append(f"Turrets: {len(organs)}")
    if soldiers:
        lines.append(f"Minions: {len(soldiers)}")
    if monsters:
        lines.append(f"Monsters: {len(monsters)}")
    return "\n".join(lines) if lines else "No map objects visible"

@register("query_cooldown", "查询技能冷却状态")
def query_cooldown(info):
    return "Cooldown: use query_hero_state for per-hero info"

@register("query_legal_actions", "查询当前可使用的按钮")
def query_legal_actions(info):
    la = info.get("legal_action", [])
    names = ["None1","None2","Move","Attack","Skill1","Skill2","Skill3","Heal","Chosen","Recall","Skill4","Equip"]
    available = [names[i] for i in range(12) if i < len(la) and la[i] == 1]
    return f"Legal: {', '.join(available)}" if available else "No legal actions"

def execute_tool(name, info, **params):
    entry = TOOL_REGISTRY.get(name)
    if not entry:
        return f"Unknown tool: {name}"
    return entry["fn"](info, **params)

