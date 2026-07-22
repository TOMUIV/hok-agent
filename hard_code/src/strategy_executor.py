import math, re
from skill_base import SKILL_REGISTRY
import skills
from pathfinding import astar

CENTER = 8
BTN_MOVE, BTN_ATTACK = 2, 3
BTN_SKILLS = {1:4, 2:5, 3:6, 4:10}
BTN_RECALL = 9

BUTTONS = ["None1","None2","Move","Attack","Skill1","Skill2","Skill3","HealSkill","ChosenSkill","Recall","Skill4","EquipSkill"]
MACRO_ACTIONS = ["FARM", "POKE", "ALL_IN", "KITE", "RETREAT", "DEFEND", "STAND_AND_SHOOT", "SYSTEM_HELP", "PURSUE", "MOVE_TO", "ATTACK_TARGET", "RECALL", "USE_SKILL"]

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
        self.pb = None

    def refresh(self, info):
        self.la = info.get("legal_action", [])
        self.pb = info.get("req_pb")
        pb = self.pb
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
        obstacles = None
        if self.pb:
            organs = getattr(self.pb, 'organ_list', [])
            if organs:
                def organ_pos(o):
                    loc = getattr(o, 'location', None)
                    if loc:
                        return (getattr(loc, 'x', 0), getattr(loc, 'z', 0))
                    return (getattr(o, 'x', 0), getattr(o, 'z', 0))
                obstacles = [(organ_pos(o)[0], organ_pos(o)[1], 800) for o in organs]
        path = astar(self.px, self.py, tx, ty, obstacles)
        if path and len(path) > 1:
            nx, ny = path[1]
        else:
            nx, ny = tx, ty
        mx, my = direction_to(self.px, self.py, nx, ny)
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
        self._concrete_skill = None

    def step(self, info):
        if not self.ctx.refresh(info):
            return (2, 8, 8, 8, 8, 0), ""

        if self._concrete_skill is not None:
            try:
                from skills_concrete import SKILL_REGISTRY as CONCRETE_REGISTRY
                if hasattr(self._concrete_skill, 'ctx'):
                    self._concrete_skill.ctx.refresh(info)
                action, done = self._concrete_skill.update()
                if done:
                    self._concrete_skill = None
                return action, ""
            except Exception:
                self._concrete_skill = None

        if self.last_actions:
            action = self.last_actions.pop(0)
            return action, ""

        # 持续执行同一个skill直到LLM换新的
        if self._concrete_skill is not None:
            try:
                if not self._concrete_skill.ctx.refresh(info):
                    self._concrete_skill = None
                else:
                    px = self._concrete_skill.ctx.px
                    action, done = self._concrete_skill.update()
                    btn = action[0]
                    if btn == 2:
                        mx, mz = action[1], action[2]
                        if abs(mx-8) < 1 and abs(mz-8) < 1:
                            pass  # stopped
                    if done:
                        self._concrete_skill = None
                    return action, ""
            except:
                self._concrete_skill = None

        # 还没有skill（LLM还没决策）→ 默认用FARM向前走
        try:
            from skills_concrete import SKILL_REGISTRY as CONCRETE_REGISTRY, SkillContext as ConcreteCtx
            sk_cls = CONCRETE_REGISTRY.get("FARM")
            if sk_cls:
                sk = sk_cls()
                sk.ctx = ConcreteCtx(self.self_hero_id)
                sk.ctx.refresh(info)
                sk.params = {}
                if hasattr(sk, '_start'):
                    sk._start()
                self._concrete_skill = sk
                action, done = sk.update()
                return action, ""
        except:
            pass
        return self.ctx.make_move(8, 8), ""

    def execute_macro(self, macro_name, info):
        if not self.ctx.refresh(info):
            return (2, 8, 8, 8, 8, 0)
        from skills_concrete import SKILL_REGISTRY as CONCRETE_REGISTRY, SkillContext as ConcreteCtx
        sk_cls = CONCRETE_REGISTRY.get(macro_name)
        if not sk_cls:
            return self.ctx.make_move(8, 8)
        sk = sk_cls()
        sk.ctx = ConcreteCtx(self.self_hero_id)
        sk.ctx.refresh(info)
        sk.params = {}
        if hasattr(sk, '_start'):
            sk._start()
        action, _ = sk.update()
        return action

    def process_batch(self, info, llm_output):
        if not self.ctx.refresh(info):
            return [{"type": "error", "msg": "state refresh failed"}]

        from skills_concrete import SKILL_REGISTRY as CONCRETE_REGISTRY, SkillContext as ConcreteCtx

        results = []
        lines = llm_output.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line or line.startswith("Thought") or line.startswith("WhatIf"):
                continue

            m = re.match(r"@TOOL\s+(\w+)\(([^)]*)\)", line)
            if m:
                name, params_str = m.group(1), m.group(2)
                params = {}
                for p in params_str.split(","):
                    if "=" in p:
                        k, v = p.split("=", 1)
                        params[k.strip()] = v.strip()
                info["_self_id"] = self.ctx.sh
                result = execute_tool(name, info, **params)
                results.append({"type": "tool", "name": name, "result": result})
                continue

            m = re.match(r"@SKILL_OPEN\s+(\w+)", line)
            if m:
                sk_name = m.group(1)
                sk = SKILL_REGISTRY.get(sk_name)
                if sk:
                    results.append({"type": "skill_open", "name": sk_name, "doc": sk.get_doc()})
                else:
                    results.append({"type": "error", "msg": f"unknown skill: {sk_name}"})
                continue

            m = re.match(r"@SKILL_CALL\s+(\w+)\.(\w+)\(([^)]*)\)", line)
            if m:
                sk_name = m.group(1)
                sk_cls = CONCRETE_REGISTRY.get(sk_name.upper())
                if sk_cls:
                    sk = sk_cls()
                    sk.ctx = ConcreteCtx(self.self_hero_id)
                    sk.ctx.refresh(info)
                    sk.params = {}
                    if hasattr(sk, '_start'):
                        sk._start()
                    self._concrete_skill = sk
                    self.last_actions.clear()
                    action, done = sk.update()
                    self.last_actions.append(action)
                    results.append({"type": "skill_call", "skill": sk_name, "func": m.group(2)})
                else:
                    results.append({"type": "error", "msg": f"unknown concrete skill: {sk_name}"})
                continue

        return results

