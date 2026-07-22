import math
from constants import (
    CENTER, BTN_MOVE, BTN_ATTACK, BTN_RECALL,
    LEGAL_OFFSET, MOVE_ARRIVAL_DIST, STUCK_LIMIT,
    TOWER_MAP,
)
from pathfinding import astar


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
    off = LEGAL_OFFSET
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
        return (loc.x, loc.z)
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
        self.pb = None
        self.soldiers = []

    def refresh(self, info):
        self.la = info.get("legal_action", [])
        self.pb = info.get("req_pb")
        pb = self.pb
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
        self.soldiers = []
        for s in getattr(pb, 'soldier_list', []):
            if getattr(s, 'alive', True) and getattr(s, 'hp', 0) > 0:
                loc = getattr(s, 'location', None)
                if loc and hasattr(loc, 'x'):
                    camp_val = getattr(s, 'camp', None)
                    if camp_val is not None:
                        scamp = camp_val.value if hasattr(camp_val, 'value') else camp_val
                        if scamp != getattr(self.sh, 'camp', -1):
                            self.soldiers.append({
                                'hp': getattr(s, 'hp', 0),
                                'max_hp': getattr(s, 'max_hp', 1),
                                'x': getattr(loc, 'x', 0),
                                'z': getattr(loc, 'z', 0) or getattr(loc, 'y', 0),
                                'alive': True,
                            })
        return True

    def valid_btn(self, btn):
        return btn < len(self.la) and self.la[btn] == 1.0

    def dist_to_enemy(self):
        return dist(self.px, self.py, self.ex, self.ey)

    def atk_range(self):
        return getattr(self.sh, 'atk_range', 700)

    def camp(self):
        v = getattr(self.sh, 'camp', 0)
        return -1 if v == 1 else 1

    def nearest_low_hp_minion(self, hp_threshold=200):
        best = None
        best_d = float('inf')
        for s in self.soldiers:
            if s['hp'] > hp_threshold:
                continue
            d = dist(self.px, self.py, s['x'], s['z'])
            if d < best_d:
                best_d, best = d, s
        return best

    def has_minion_target(self):
        off = LEGAL_OFFSET
        row = off + BTN_ATTACK * 8
        return row + 8 <= len(self.la) and self.la[row + 2] == 1.0

    def make_move(self, mx=None, my=None):
        if mx is None:
            mx = my = CENTER
        return (BTN_MOVE, mx, my, CENTER, CENTER, get_target_for(self.la, BTN_MOVE))

    def make_move_to(self, tx, ty):
        """A* pathfind toward (tx,ty), return one-step direction."""
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

    def make_attack(self, mx, my, target=0):
        if not valid_btn(self.la, BTN_ATTACK):
            return None
        off = LEGAL_OFFSET
        row = off + BTN_ATTACK * 8
        if row + 8 <= len(self.la) and target < 8 and self.la[row + target] == 1.0:
            return (BTN_ATTACK, mx, my, CENTER, CENTER, target)
        tgt = get_target_for(self.la, BTN_ATTACK)
        return (BTN_ATTACK, mx, my, CENTER, CENTER, tgt)

    def make_skill(self, skill_num, tx, ty):
        btn = {1: 4, 2: 5, 3: 6, 4: 10}.get(skill_num, 4)
        sx, sy = direction_to(self.px, self.py, tx, ty)
        tgt = get_target_for(self.la, btn)
        return (btn, CENTER, CENTER, sx, sy, tgt)

    def aim_skill(self, btn, tx, ty):
        if not valid_btn(self.la, btn):
            return None
        tgt = get_target_for(self.la, btn)
        cfg = self.hero_config
        skill_num = {4: 1, 5: 2, 6: 3, 10: 4}.get(btn, 0)
        st = cfg.get("skill_types", {}).get(skill_num, "") if cfg else ""
        if st in ("self_buff", "projectile") or tgt == 0:
            return (btn, CENTER, CENTER, CENTER, CENTER, tgt)
        sx, sy = direction_to(self.px, self.py, tx, ty)
        return (btn, CENTER, CENTER, sx, sy, tgt)
