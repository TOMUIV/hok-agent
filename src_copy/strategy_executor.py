import math, re
from skill_base import SKILL_REGISTRY
import skills

CENTER = 8
BTN_MOVE, BTN_ATTACK = 2, 3
BTN_SKILLS = {1:4, 2:5, 3:6, 4:10}

def clamp(v):
    return max(1, min(15, int(round(v))))

def direction_to(px, py, tx, ty):
    dx, dy = tx - px, ty - py
    d = math.sqrt(dx*dx + dy*dy)
    if d < 0.01: return (CENTER, CENTER)
    return (clamp(dx/d*7 + CENTER), clamp(dy/d*7 + CENTER))

def get_target(la, btn):
    off = 12 + 16 * 4
    row = off + btn * 8
    if row + 8 > len(la): return 0
    for t in range(8):
        if la[row + t] == 1.0: return t
    return 0

class SkillContext:
    def __init__(self, self_hero_id):
        self.self_hero_id = self_hero_id
        self.la = []
        self.sh = None
        self.eh = None
        self.px = self.py = 0
        self.ex = self.ey = 0
        self.hero_config = None

    def refresh(self, info):
        self.la = info.get("legal_action", [])
        pb = info.get("req_pb")
        if not pb: return False
        for h in getattr(pb, "hero_list", []):
            if h.config_id == self.self_hero_id: self.sh = h
            else: self.eh = h
        if not self.sh or not self.eh: return False
        loc_s = getattr(self.sh, "location", None)
        loc_e = getattr(self.eh, "location", None)
        if not loc_s or not loc_e: return False
        self.px, self.py = loc_s.x, loc_s.y
        self.ex, self.ey = loc_e.x, loc_e.y
        from hero_skills import get_config
        self.hero_config = get_config(self.self_hero_id)
        return True

    def valid_btn(self, btn):
        return btn < len(self.la) and self.la[btn] == 1.0

    def dist_to_enemy(self):
        return math.sqrt((self.ex-self.px)**2 + (self.ey-self.py)**2)

    def atk_range(self):
        return getattr(self.sh, "atk_range", 700)

    def camp(self):
        v = getattr(self.sh, "camp", 0)
        return -1 if v == 1 else 1

    def make_move(self, mx, my):
        return (BTN_MOVE, mx, my, CENTER, CENTER, get_target(self.la, BTN_MOVE))

    def make_move_to(self, tx, ty):
        mx, my = direction_to(self.px, self.py, tx, ty)
        return self.make_move(mx, my)

    def make_attack(self):
        mx, my = direction_to(self.px, self.py, self.ex, self.ey)
        tgt = get_target(self.la, BTN_ATTACK)
        return (BTN_ATTACK, mx, my, CENTER, CENTER, tgt)

    def make_skill(self, skill_num, tx, ty):
        btn = BTN_SKILLS.get(skill_num, 4)
        sx, sy = direction_to(self.px, self.py, tx, ty)
        tgt = get_target(self.la, btn)
        return (btn, CENTER, CENTER, sx, sy, tgt)

class ProtocolExecutor:
    def __init__(self, self_hero_id):
        self.self_hero_id = self_hero_id
        self.ctx = SkillContext(self_hero_id)
        self.last_actions = []
        self.current_skill_obj = None

    def step(self, info):
        if not self.ctx.refresh(info):
            return (2, 8, 8, 8, 8, 0), ""

        if self.last_actions:
            action = self.last_actions.pop(0)
            return action, ""

        return self.ctx.make_move(8, 8), ""

    def process_batch(self, info, llm_output):
        if not self.ctx.refresh(info):
            return [{"type": "error", "msg": "state refresh failed"}]

        results = []
        lines = llm_output.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line or line.startswith("Thought") or line.startswith("WhatIf"):
                continue

            m = re.match(r"@SKILL_CALL\s+(\w+)\.(\w+)\(([^)]*)\)", line)
            if m:
                sk_name, func_name, params_str = m.group(1), m.group(2), m.group(3)
                sk = SKILL_REGISTRY.get(sk_name)
                if not sk:
                    results.append({"type": "error", "msg": f"unknown skill: {sk_name}"})
                    continue
                params = {}
                for p in params_str.split(","):
                    if "=" in p:
                        k, v = p.split("=", 1)
                        params[k.strip()] = v.strip()
                result = sk.execute(func_name, self.ctx, params)
                self.current_skill_obj = sk
                results.append({"type": "skill_call", "skill": sk_name, "func": func_name, "result": result})
                continue

        return results
