import math
from pathfinding import astar
from skill_base import Skill

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

def steer_toward(px, py, tx, ty):
    """Move toward (tx,ty). The enemy is on the lane, so this naturally follows the lane."""
    return direction_to(px, py, tx, ty)

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
        # Load soldier list for last-hit logic
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

    def nearest_low_hp_minion(self, hp_threshold=200):
        """找最近的残血小兵"""
        best = None
        best_d = float('inf')
        for s in self.soldiers:
            if s['hp'] > hp_threshold:
                continue
            d = dist(self.px, self.py, s['x'], s['z'])
            if d < best_d:
                best_d = d
                best = s
        return best

    def has_minion_target(self):
        """检查是否可以对小兵攻击(legal_action中target=2可用)"""
        off = 12 + 16 * 4
        row = off + BTN_ATTACK * 8
        if row + 8 <= len(self.la) and self.la[row + 2] == 1.0:
            return True
        return False

    def make_move(self, mx=None, my=None):
        if mx is None:
            mx = my = CENTER
        return (BTN_MOVE, mx, my, CENTER, CENTER, get_target_for(self.la, BTN_MOVE))

    def make_move_to(self, tx, ty):
        mx, my = direction_to(self.px, self.py, tx, ty)
        return self.make_move(mx, my)

    def make_attack(self, mx, my):
        if valid_btn(self.la, BTN_ATTACK):
            return (BTN_ATTACK, mx, my, CENTER, CENTER, get_target_for(self.la, BTN_ATTACK))
        return None

    def make_attack_minion(self, mx, my):
        """攻击小兵(target=2)，若不可用则攻击默认目标"""
        if valid_btn(self.la, BTN_ATTACK) and self.has_minion_target():
            return (BTN_ATTACK, mx, my, CENTER, CENTER, 2)
        if valid_btn(self.la, BTN_ATTACK):
            return (BTN_ATTACK, mx, my, CENTER, CENTER, get_target_for(self.la, BTN_ATTACK))
        return None

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
        """推进补兵，打架前开技能"""
        ar = self.ctx.atk_range()
        mx, my = steer_toward(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
        d = dist(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
        soldiers_near = sum(1 for s in self.ctx.soldiers if dist(self.ctx.px, self.ctx.py, s['x'], s['z']) < ar)

        # 0) 敌方在视野内(非FOW)且未贴身 → 大招先手晕眩(全图直线)
        if d > ar and d < 50000 and valid_btn(self.ctx.la, BTN_SKILL3):
            sx, sy = steer_toward(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
            return (BTN_SKILL3, CENTER, CENTER, sx, sy, get_target_for(self.ctx.la, BTN_SKILL3)), False

        # 1) 进战前开 Skill1 (多重箭矢, self_buff)
        if (d < ar or soldiers_near > 0) and valid_btn(self.ctx.la, BTN_SKILL1):
            return (BTN_SKILL1, CENTER, CENTER, CENTER, CENTER, get_target_for(self.ctx.la, BTN_SKILL1)), False

        # 2) 残血小兵补刀
        m = self.ctx.nearest_low_hp_minion(hp_threshold=300)
        if m:
            dm = dist(self.ctx.px, self.ctx.py, m['x'], m['z'])
            if dm < ar:
                mx_m, my_m = steer_toward(self.ctx.px, self.ctx.py, m['x'], m['z'])
                atk = self.ctx.make_attack_minion(mx_m, my_m)
                if atk:
                    return atk, False

        # 3) 敌人近身则攻击
        if d < ar and valid_btn(self.ctx.la, BTN_ATTACK):
            atk = self.ctx.make_attack(mx, my)
            if atk:
                return atk, False

        # 4) 向前推进
        return self.ctx.make_move(mx, my), False

class Poke(Skill):
    name = "POKE"
    def update(self):
        """Step forward, use poke skill, step back. Stay near lane center."""
        ar = self.ctx.atk_range()
        mx, my = steer_toward(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)

        # 残血小兵优先
        m = self.ctx.nearest_low_hp_minion(hp_threshold=300)
        if m:
            dm = dist(self.ctx.px, self.ctx.py, m['x'], m['z'])
            if dm < ar:
                mx_m, my_m = steer_toward(self.ctx.px, self.ctx.py, m['x'], m['z'])
                atk = self.ctx.make_attack_minion(mx_m, my_m)
                if atk:
                    return atk, False

        d = dist(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
        cfg = self.ctx.hero_config

        # 0) 非FOW且未贴身 → 大招先手晕眩
        if d > ar and d < 50000 and valid_btn(self.ctx.la, BTN_SKILL3):
            sx, sy = steer_toward(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
            return (BTN_SKILL3, CENTER, CENTER, sx, sy, get_target_for(self.ctx.la, BTN_SKILL3)), False

        if cfg:
            pk = cfg.get("poke_skill", 1)
            btn = [BTN_SKILL1, BTN_SKILL2, BTN_SKILL3][pk-1]
            sr = cfg.get("skill_ranges", {}).get(pk, 700)
            if d < sr and valid_btn(self.ctx.la, btn):
                sx, sy = steer_toward(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
                return (btn, CENTER, CENTER, sx, sy, get_target_for(self.ctx.la, btn)), False
        if d < ar * 1.2 and valid_btn(self.ctx.la, BTN_ATTACK):
            return (BTN_ATTACK, mx, my, CENTER, CENTER, get_target_for(self.ctx.la, BTN_ATTACK)), False
        return self.ctx.make_move(mx, my), False

class AllIn(Skill):
    name = "ALL_IN"
    def _start(self):
        self.combo_idx = 0
    def update(self):
        cfg = self.ctx.hero_config
        d = dist(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
        ar = self.ctx.atk_range()
        # 0) 非FOW且未贴身 → 大招先手晕眩
        if d > ar and d < 50000 and valid_btn(self.ctx.la, BTN_SKILL3):
            sx, sy = direction_to(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
            return (BTN_SKILL3, CENTER, CENTER, sx, sy, get_target_for(self.ctx.la, BTN_SKILL3)), False
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
        mx, my = steer_toward(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
        if d < ar and valid_btn(self.ctx.la, BTN_ATTACK):
            # 即使ALL_IN也优先补残血兵
            m = self.ctx.nearest_low_hp_minion(hp_threshold=300)
            if m and dist(self.ctx.px, self.ctx.py, m['x'], m['z']) < ar:
                mx_m, my_m = steer_toward(self.ctx.px, self.ctx.py, m['x'], m['z'])
                atk = self.ctx.make_attack_minion(mx_m, my_m)
                if atk:
                    return atk, False
            return (BTN_ATTACK, mx, my, CENTER, CENTER, get_target_for(self.ctx.la, BTN_ATTACK)), False
        mt = MoveTo()
        mt.ctx = self.ctx
        mt.params = {"x": self.ctx.ex, "y": self.ctx.ey, "use_astar": False}
        mt._start()
        return mt.update()

class Kite(Skill):
    name = "KITE"
    def update(self):
        """Move backward toward own tower, attack if enemy in range. Don't overshoot past base."""
        camp = self.ctx.camp()
        safe_x = -20000 if camp < 0 else 20000
        if (camp < 0 and self.ctx.px < safe_x) or (camp > 0 and self.ctx.px > safe_x):
            return self.ctx.make_move(8, 8), False
        d = dist(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
        ar = self.ctx.atk_range()
        mx, my = steer_toward(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
        camp = self.ctx.camp()
        mx = clamp(mx + camp)  # bias movement toward own base
        cfg = self.ctx.hero_config
        if cfg:
            esc = cfg.get("escape_skill")
            if esc and d < cfg.get("skill_ranges", {}).get(esc, 700):
                btn = [BTN_SKILL1, BTN_SKILL2, BTN_SKILL3][esc-1]
                st = cfg.get("skill_types", {}).get(esc, "")
                if st in ("dash", "self_buff") and valid_btn(self.ctx.la, btn):
                    ax = self.ctx.px + mx * 1000
                    ay = self.ctx.py + my * 1000
                    sx, sy = direction_to(self.ctx.px, self.ctx.py, ax, ay)
                    return (btn, CENTER, CENTER, sx, sy, get_target_for(self.ctx.la, btn)), False
        if d < ar and valid_btn(self.ctx.la, BTN_ATTACK):
            return (BTN_ATTACK, mx, my, CENTER, CENTER, get_target_for(self.ctx.la, BTN_ATTACK)), False
        return self.ctx.make_move(mx, my), False

class Retreat(Skill):
    name = "RETREAT"
    def update(self):
        """Walk directly to spawn center. No stopping until arrival."""
        camp = self.ctx.camp()
        sp_x = -32308 if camp < 0 else 32308
        sp_z = -32322 if camp < 0 else 32322
        dx = sp_x - self.ctx.px
        dy = sp_z - self.ctx.py
        d = math.sqrt(dx*dx + dy*dy)
        if d < 300:
            return self.ctx.make_move(8, 8), True
        mx, my = direction_to(self.ctx.px, self.ctx.py, sp_x, sp_z)
        return self.ctx.make_move(mx, my), False

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
        """DEFEND: 清兵优先，用技能清更快"""
        ar = self.ctx.atk_range()
        d_enemy = dist(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
        soldiers_near = sum(1 for s in self.ctx.soldiers if dist(self.ctx.px, self.ctx.py, s['x'], s['z']) < ar)

        # 0) 有小兵或敌人在范围 → 开 Skill1 加攻
        if (soldiers_near > 0 or d_enemy < ar) and valid_btn(self.ctx.la, BTN_SKILL1):
            return (BTN_SKILL1, CENTER, CENTER, CENTER, CENTER, get_target_for(self.ctx.la, BTN_SKILL1)), False

        # 1) 有小兵在范围 → Skill2 (AOE清兵)
        if soldiers_near >= 2 and valid_btn(self.ctx.la, BTN_SKILL2):
            sx, sy = steer_toward(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
            return (BTN_SKILL2, CENTER, CENTER, sx, sy, get_target_for(self.ctx.la, BTN_SKILL2)), False

        # 2) 残血小兵补刀
        m = self.ctx.nearest_low_hp_minion(hp_threshold=300)
        if m and dist(self.ctx.px, self.ctx.py, m['x'], m['z']) < ar:
            mx_m, my_m = steer_toward(self.ctx.px, self.ctx.py, m['x'], m['z'])
            atk = self.ctx.make_attack_minion(mx_m, my_m)
            if atk:
                return atk, False

        # 3) 有小兵在范围 → 普攻清兵
        for s in self.ctx.soldiers:
            if dist(self.ctx.px, self.ctx.py, s['x'], s['z']) < ar:
                mx_s, my_s = steer_toward(self.ctx.px, self.ctx.py, s['x'], s['z'])
                atk = self.ctx.make_attack_minion(mx_s, my_s)
                if atk:
                    return atk, False

        # 4) 有小兵在附近(5000内) → 走向最近的小兵
        best_s = None
        best_d = 5000
        for s in self.ctx.soldiers:
            sd = dist(self.ctx.px, self.ctx.py, s['x'], s['z'])
            if sd < best_d:
                best_d = sd
                best_s = s
        if best_s:
            mx_s, my_s = steer_toward(self.ctx.px, self.ctx.py, best_s['x'], best_s['z'])
            return self.ctx.make_move(mx_s, my_s), False

        # 5) 有敌人且未贴身 → 大招先手晕眩
        if d_enemy > ar and d_enemy < 50000 and valid_btn(self.ctx.la, BTN_SKILL3):
            sx, sy = steer_toward(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
            return (BTN_SKILL3, CENTER, CENTER, sx, sy, get_target_for(self.ctx.la, BTN_SKILL3)), False

        # 6) 没兵 → 打人
        if d_enemy < ar and valid_btn(self.ctx.la, BTN_ATTACK):
            return (BTN_ATTACK, CENTER, CENTER, CENTER, CENTER, get_target_for(self.ctx.la, BTN_ATTACK)), False
        # 7) 没兵没敌人 → 向前推进
        mx, my = steer_toward(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
        return self.ctx.make_move(mx, my), False

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

