from hero_db import hero_name
from state_parser import hero_detail

class ToolSet:
    def __init__(self, info, self_hero_id=None):
        self.info = info
        self.pb = info.get("req_pb") if isinstance(info, dict) else info[0].get("req_pb")
        self.self_hero_id = self_hero_id

    def _hero(self, idx):
        if not self.pb:
            return None
        hl = getattr(self.pb, 'hero_list', [])
        return hl[idx] if idx < len(hl) else None

    def query_hp(self):
        if not self.pb:
            return "No data"
        lines = []
        for i, h in enumerate(getattr(self.pb, 'hero_list', [])):
            cid = getattr(h, 'config_id', 0)
            hp = getattr(h, 'hp', 0)
            mhp = getattr(h, 'max_hp', 1)
            pct = hp / mhp * 100 if mhp > 0 else 0
            side = "BLUE" if i == 1 else "RED"
            lines.append(f"{side} {hero_name(cid)}: HP {hp}/{mhp} ({pct:.0f}%)")
        return "\n".join(lines)

    def query_position(self):
        if not self.pb:
            return "No data"
        lines = []
        for i, h in enumerate(getattr(self.pb, 'hero_list', [])):
            cid = getattr(h, 'config_id', 0)
            loc = getattr(h, 'location', None)
            pos = f"({loc.x},{loc.y})" if loc and hasattr(loc, 'x') else "(?,?)"
            side = "BLUE" if i == 1 else "RED"
            lines.append(f"{side} {hero_name(cid)} @ {pos}")
        return "\n".join(lines)

    def query_hero_state(self, hero="SELF"):
        if not self.pb:
            return "No data"
        hl = getattr(self.pb, 'hero_list', [])
        target = None
        for h in hl:
            cid = getattr(h, 'config_id', 0)
            if hero == "SELF" and cid == self.self_hero_id:
                target = h
                break
            elif hero.startswith("ENEMY") and cid != self.self_hero_id:
                target = h
                break
        if not target and hl:
            target = hl[0]
        return hero_detail(target)

    def query_legal_actions(self):
        s = self.info if isinstance(self.info, dict) else self.info[0]
        la = s.get("legal_action", [])
        btns = ["None1","None2","Move","Attack","Skill1","Skill2","Skill3","Heal","Chosen","Recall","Skill4","Equip"]
        available = [btns[i] for i in range(12) if i < len(la) and la[i] == 1]
        return f"Available: {', '.join(available)}" if available else "No legal actions"

    def query_cooldown(self):
        return "Cooldown info: not yet implemented (need Skill object dump)"

    def query_map(self):
        if not self.pb:
            return "No data"
        lines = []
        organs = getattr(self.pb, 'organ_list', [])
        if organs:
            lines.append(f"Turrets/Crystals: {len(organs)}")
        soldiers = getattr(self.pb, 'soldier_list', [])
        if soldiers:
            lines.append(f"Soldiers: {len(soldiers)}")
        monsters = getattr(self.pb, 'monster_list', [])
        if monsters:
            lines.append(f"Monsters: {len(monsters)}")
        if not lines:
            lines.append("No map objects visible")
        return "\n".join(lines)

    def query_buff(self):
        if not self.pb:
            return "No data"
        lines = []
        for i, h in enumerate(getattr(self.pb, 'hero_list', [])):
            cid = getattr(h, 'config_id', 0)
            bs = getattr(h, 'buff_state', None)
            lines.append(f"{hero_name(cid)}: buff_state={bs}")
        return "\n".join(lines)

    def execute(self, tool_name, **params):
        method = getattr(self, tool_name, None)
        if not method:
            return f"Unknown tool: {tool_name}"
        return method(**params)

TOOL_REGISTRY = {
    "query_hp": {"func": "query_hp", "desc": "Check all heroes HP percentages", "params": {}},
    "query_position": {"func": "query_position", "desc": "Check all heroes positions", "params": {}},
    "query_hero_state": {"func": "query_hero_state", "desc": "Detailed state of a hero", "params": {"hero": "SELF/ENEMY_0/ENEMY_1"}},
    "query_legal_actions": {"func": "query_legal_actions", "desc": "List currently legal actions", "params": {}},
    "query_cooldown": {"func": "query_cooldown", "desc": "Check skill cooldowns", "params": {}},
    "query_map": {"func": "query_map", "desc": "Check map state (towers, minions, monsters)", "params": {}},
    "query_buff": {"func": "query_buff", "desc": "Check buffs/debuffs on heroes", "params": {}},
}
