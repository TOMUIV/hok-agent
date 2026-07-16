import math
from pathfinding import astar
from skill_base import Skill, CompositeSkill

CENTER = 8
BTN_MOVE, BTN_ATTACK = 2, 3
BTN_SKILL1, BTN_SKILL2, BTN_SKILL3 = 4, 5, 6
BTN_RECALL = 9

def clamp(v):
    return max(1, min(15, int(round(v))))

def direction_to(px, py, tx, ty):
    dx, dy = tx - px, ty - py
    d = math.sqrt(dx*dx + dy*dy)
    if d < 0.01:
        return (CENTER, CENTER)
    return (clamp(dx/d*7 + CENTER), clamp(dy/d*7 + CENTER))

def dist(px, py, tx, ty):
    return math.sqrt((tx-px)**2 + (ty-py)**2)

def get_target_for(la, btn):
    off = 12 + 16 * 4
    row = off + btn * 8
    if row + 8 > len(la):
        return 0
    for t in range(8):
        if la[row + t] == 1.0:
            return t
    return 0

def valid_btn(la, btn):
    return btn < len(la) and la[btn] == 1.0

def get_hero_pos(h):
    loc = getattr(h, 'location', None)
    if loc and hasattr(loc, 'x'):
        return (loc.x, loc.y)
    return None

def self_enemy(req_pb, sid):
    sh = eh = None
    for h in req_pb.hero_list:
        if h.config_id == sid:
            sh = h
        else:
            eh = h
    return sh, eh

class SkillContext:
    def __init__(self, self_hero_id):
        self.self_hero_id = self_hero_id
        self.hero_config = None
        self.la = []
        self.sh = None
        self.eh = None
        self.px = self.py = 0
        self.ex = self.ey = 0

    def refresh(self, info):
        self.la = info.get("legal_action", [])
        pb = info.get("req_pb")
        if not pb:
            return False
        self.sh, self.eh = self_enemy(pb, self.self_hero_id)
        if not self.sh or not self.eh:
            return False
        sp = get_hero_pos(self.sh)
        ep = get_hero_pos(self.eh)
        if not sp or not ep:
            return False
        self.px, self.py = sp
        self.ex, self.ey = ep
        from hero_skills import get_config
        self.hero_config = get_config(self.self_hero_id)
        return True

    def make_move(self, mx=None, my=None):
        if mx is None:
            mx = my = CENTER
        return (BTN_MOVE, mx, my, CENTER, CENTER, get_target_for(self.la, BTN_MOVE))

    def make_attack(self, mx, my):
        if valid_btn(self.la, BTN_ATTACK):
            return (BTN_ATTACK, mx, my, CENTER, CENTER, get_target_for(self.la, BTN_ATTACK))
        return None

    def aim_skill(self, btn, tx, ty):
        if not valid_btn(self.la, btn):
            return None
        sx, sy = direction_to(self.px, self.py, tx, ty)
        return (btn, CENTER, CENTER, sx, sy, get_target_for(self.la, btn))

    def atk_range(self):
        return getattr(self.sh, 'atk_range', 700)

    def camp(self):
        v = getattr(self.sh, 'camp', 0)
        return -1 if v == 1 else 1

# ========== CONCRETE SKILLS ==========

class MoveTo(Skill):
    name = "MOVE_TO"
    def _start(self):
        tx = self.params.get("x", self.ctx.ex)
        ty = self.params.get("y", self.ctx.ey)
        obstacles = self.params.get("obstacles", [])
        if self.params.get("use_astar", True):
            self.path = astar(self.ctx.px, self.ctx.py, tx, ty, obstacles)
        else:
            self.path = [(tx, ty)]
        self.path_idx = 0

    def update(self):
        if self.path_idx >= len(self.path):
            return self.ctx.make_move(), True
        tx, ty = self.path[self.path_idx]
        d = dist(self.ctx.px, self.ctx.py, tx, ty)
        if d < 800:
            self.path_idx += 1
            if self.path_idx >= len(self.path):
                return self.ctx.make_move(), True
            tx, ty = self.path[self.path_idx]
        mx, my = direction_to(self.ctx.px, self.ctx.py, tx, ty)
        return self.ctx.make_move(mx, my), False

class AttackTarget(Skill):
    name = "ATTACK_TARGET"
    def update(self):
        mx, my = direction_to(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
        atk = self.ctx.make_attack(mx, my)
        if atk:
            return atk, False
        return self.ctx.make_move(mx, my), False

class UseSkill(Skill):
    name = "USE_SKILL"
    def _start(self):
        self.skill_num = self.params.get("skill_num", 1)
        self.btn = [BTN_SKILL1, BTN_SKILL2, BTN_SKILL3, BTN_SKILL1][self.skill_num-1]
    def update(self):
        sk = self.ctx.aim_skill(self.btn, self.ctx.ex, self.ctx.ey)
        if sk:
            return sk, True
        return self.ctx.make_move(), True

class Recall(Skill):
    name = "RECALL"
    def update(self):
        if valid_btn(self.ctx.la, BTN_RECALL):
            return (BTN_RECALL, CENTER, CENTER, CENTER, CENTER, get_target_for(self.ctx.la, BTN_RECALL)), True
        camp = self.ctx.camp()
        mx = CENTER + camp
        return self.ctx.make_move(mx, CENTER), False

class Farm(Skill):
    name = "FARM"
    def update(self):
        mx, my = direction_to(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
        ar = self.ctx.atk_range()
        d = dist(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
        if d < ar:
            atk = self.ctx.make_attack(mx, my)
            if atk:
                return atk, False
        return self.ctx.make_move(mx, my), False

class Poke(Skill):
    name = "POKE"
    def update(self):
        d = dist(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
        cfg = self.ctx.hero_config
        if cfg:
            pk = cfg.get("poke_skill", 1)
            btn = [BTN_SKILL1, BTN_SKILL2, BTN_SKILL3][pk-1]
            sr = cfg.get("skill_ranges", {}).get(pk, 700)
            if d < sr and valid_btn(self.ctx.la, btn):
                sx, sy = direction_to(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
                return (btn, CENTER, CENTER, sx, sy, get_target_for(self.ctx.la, btn)), False
        mx, my = direction_to(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
        ar = self.ctx.atk_range()
        if d < ar * 1.2 and valid_btn(self.ctx.la, BTN_ATTACK):
            return (BTN_ATTACK, mx, my, CENTER, CENTER, get_target_for(self.ctx.la, BTN_ATTACK)), False
        return self.ctx.make_move(clamp(mx*0.5+CENTER), clamp(my*0.5+CENTER)), False

class AllIn(Skill):
    name = "ALL_IN"
    def _start(self):
        self.combo_idx = 0
    def update(self):
        cfg = self.ctx.hero_config
        d = dist(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
        if cfg:
            prio = cfg.get("combo_priority", [3, 2, 1])
            while self.combo_idx < len(prio):
                sn = prio[self.combo_idx]
                btn = [BTN_SKILL1, BTN_SKILL2, BTN_SKILL3][sn-1]
                sr = cfg.get("skill_ranges", {}).get(sn, 700)
                if d < sr and valid_btn(self.ctx.la, btn):
                    self.combo_idx += 1
                    sx, sy = direction_to(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
                    return (btn, CENTER, CENTER, sx, sy, get_target_for(self.ctx.la, btn)), False
                self.combo_idx += 1
        mx, my = direction_to(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
        ar = self.ctx.atk_range()
        if d < ar and valid_btn(self.ctx.la, BTN_ATTACK):
            return (BTN_ATTACK, mx, my, CENTER, CENTER, get_target_for(self.ctx.la, BTN_ATTACK)), False
        return MoveTo().update(self)

class Kite(Skill):
    name = "KITE"
    def update(self):
        camp = self.ctx.camp()
        hmx, hmy = CENTER + camp, CENTER
        d = dist(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
        ar = self.ctx.atk_range()
        cfg = self.ctx.hero_config
        if cfg:
            esc = cfg.get("escape_skill")
            if esc and d < cfg.get("skill_ranges", {}).get(esc, 700):
                btn = [BTN_SKILL1, BTN_SKILL2, BTN_SKILL3][esc-1]
                st = cfg.get("skill_types", {}).get(esc, "")
                if st in ("dash", "self_buff") and valid_btn(self.ctx.la, btn):
                    ax = self.ctx.px + (hmx - CENTER) * 1000
                    ay = self.ctx.py + (hmy - CENTER) * 1000
                    sx, sy = direction_to(self.ctx.px, self.ctx.py, ax, ay)
                    return (btn, CENTER, CENTER, sx, sy, get_target_for(self.ctx.la, btn)), False
        if d < ar and valid_btn(self.ctx.la, BTN_ATTACK):
            return (BTN_ATTACK, hmx, hmy, CENTER, CENTER, get_target_for(self.ctx.la, BTN_ATTACK)), False
        return self.ctx.make_move(hmx, hmy), False

class Retreat(Skill):
    name = "RETREAT"
    def update(self):
        camp = self.ctx.camp()
        return self.ctx.make_move(CENTER + camp, CENTER), False

class Pursue(Skill):
    name = "PURSUE"
    def update(self):
        d = dist(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
        mx, my = direction_to(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
        cfg = self.ctx.hero_config
        ar = self.ctx.atk_range()
        if cfg:
            eng = cfg.get("engage_skill")
            if eng and d > ar * 0.8 and d < cfg.get("skill_ranges", {}).get(eng, 700):
                btn = [BTN_SKILL1, BTN_SKILL2, BTN_SKILL3][eng-1]
                if valid_btn(self.ctx.la, btn):
                    sx, sy = direction_to(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
                    return (btn, CENTER, CENTER, sx, sy, get_target_for(self.ctx.la, btn)), False
        if d < ar and valid_btn(self.ctx.la, BTN_ATTACK):
            return (BTN_ATTACK, mx, my, CENTER, CENTER, get_target_for(self.ctx.la, BTN_ATTACK)), False
        return self.ctx.make_move(mx, my), False

class Defend(Skill):
    name = "DEFEND"
    def update(self):
        camp = self.ctx.camp()
        hmx, hmy = CENTER + camp, CENTER
        d = dist(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
        ar = self.ctx.atk_range()
        if d < ar and valid_btn(self.ctx.la, BTN_ATTACK):
            return (BTN_ATTACK, hmx, hmy, CENTER, CENTER, get_target_for(self.ctx.la, BTN_ATTACK)), False
        return self.ctx.make_move(hmx, hmy), False

SKILL_REGISTRY = {
    "MOVE_TO": MoveTo,
    "FARM": Farm,
    "POKE": Poke,
    "ALL_IN": AllIn,
    "KITE": Kite,
    "RETREAT": Retreat,
    "PURSUE": Pursue,
    "DEFEND": Defend,
    "RECALL": Recall,
    "ATTACK_TARGET": AttackTarget,
    "USE_SKILL": UseSkill,
}
