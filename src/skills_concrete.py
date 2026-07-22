import math
from skill_base import Skill
from skill_context import (
    clamp, direction_to, dist, get_target_for, valid_btn,
    get_hero_pos, self_enemy, SkillContext,
    CENTER, BTN_MOVE, BTN_ATTACK, BTN_RECALL,
    LEGAL_OFFSET,
)


# ===== ATOMIC SKILLS =====
# Each does ONE unit function per call. LLM decides composition in === ACTION ===.

class MoveTo(Skill):
    """Multi-step: move toward (x,y) or in a direction. Detects stuck and returns control."""
    name = "MOVE_TO"
    DIR_MAP = {
        "N": (8, 1), "NE": (15, 1), "E": (15, 8), "SE": (15, 15),
        "S": (8, 15), "SW": (1, 15), "W": (1, 8), "NW": (1, 1),
    }
    def _start(self):
        self._stuck_count = 0
        self._last_pos = None
        d = self.params.get("direction", "").strip().upper()
        if d in self.DIR_MAP:
            self.aim = ("dir", self.DIR_MAP[d])
        else:
            tx = float(self.params.get("x", self.ctx.ex))
            ty = float(self.params.get("y", self.ctx.ey))
            self.aim = ("pos", (tx, ty))
    def update(self):
        cp = (self.ctx.px, self.ctx.py)
        if cp == self._last_pos:
            self._stuck_count += 1
            if self._stuck_count >= 30:
                return self.ctx.make_move(), True
        else:
            self._stuck_count = 0
            self._last_pos = cp
        if self.aim[0] == "dir":
            mx, my = self.aim[1]
            return self.ctx.make_move(mx, my), False
        tx, ty = self.aim[1]
        # 分别检查 x 和 z: 各自距离 < 800 就算到达
        if abs(self.ctx.px - tx) < 800 and abs(self.ctx.py - ty) < 800:
            return self.ctx.make_move(), True
        mx, my = direction_to(self.ctx.px, self.ctx.py, tx, ty)
        return self.ctx.make_move(mx, my), False

class AttackTarget(Skill):
    """One-shot: basic attack toward enemy (target=enemy) or minion (target=minion)."""
    name = "ATTACK"
    def update(self):
        t = self.params.get("target", "enemy")
        target_id = 2 if t == "minion" else 0
        mx, my = direction_to(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
        atk = self.ctx.make_attack(mx, my, target=target_id)
        if atk: return atk, True
        return self.ctx.make_move(mx, my), True

class UseSkill(Skill):
    """One-shot: use skill slot n (1/2/3/4) toward enemy."""
    name = "USE_SKILL"
    def update(self):
        slot = int(self.params.get("slot", 1))
        btn = {1: 4, 2: 5, 3: 6, 4: 10}.get(slot, 4)
        sk = self.ctx.aim_skill(btn, self.ctx.ex, self.ctx.ey)
        if sk: return sk, True
        return self.ctx.make_move(), True

class RecallSkill(Skill):
    """One-shot: start recall. If blocked, move toward base one step."""
    name = "RECALL"
    def update(self):
        if valid_btn(self.ctx.la, BTN_RECALL):
            return (BTN_RECALL, CENTER, CENTER, CENTER, CENTER, get_target_for(self.ctx.la, BTN_RECALL)), True
        camp = self.ctx.camp()
        return self.ctx.make_move(CENTER + camp, CENTER), True

class PokeSkill(Skill):
    """One-shot: use hero's configured poke skill toward enemy. Falls back to basic attack or advance."""
    name = "POKE"
    def update(self):
        cfg = self.ctx.hero_config
        ar = self.ctx.atk_range()
        if cfg:
            pk = cfg.get("poke_skill", 1)
            btn = {1: 4, 2: 5, 3: 6}[pk]
            sr = cfg.get("skill_ranges", {}).get(pk, 700)
            d = dist(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
            if d < sr and valid_btn(self.ctx.la, btn):
                sx, sy = direction_to(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
                return (btn, CENTER, CENTER, sx, sy, get_target_for(self.ctx.la, btn)), True
        mx, my = direction_to(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
        return self.ctx.make_move(mx, my), True

class ComboStep(Skill):
    """One-shot: try each skill in combo priority order, fire the first available."""
    name = "COMBO_STEP"
    def update(self):
        cfg = self.ctx.hero_config
        d = dist(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
        if cfg:
            prio = cfg.get("combo_priority", [3, 2, 1])
            for sn in prio:
                btn = {1: 4, 2: 5, 3: 6}[sn]
                sr = cfg.get("skill_ranges", {}).get(sn, 700)
                if d < sr and valid_btn(self.ctx.la, btn):
                    sx, sy = direction_to(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
                    return (btn, CENTER, CENTER, sx, sy, get_target_for(self.ctx.la, btn)), True
        ar = self.ctx.atk_range()
        mx, my = direction_to(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
        if d < ar and valid_btn(self.ctx.la, BTN_ATTACK):
            return (BTN_ATTACK, mx, my, CENTER, CENTER, get_target_for(self.ctx.la, BTN_ATTACK)), True
        return self.ctx.make_move(mx, my), True

class RetreatSkill(Skill):
    """Multi-step: move toward own spawn. Continues each frame until close."""
    name = "RETREAT"
    def update(self):
        camp = self.ctx.camp()
        sp_x = -32308 if camp < 0 else 32308
        sp_z = -32322 if camp < 0 else 32322
        if dist(self.ctx.px, self.ctx.py, sp_x, sp_z) < 300:
            return self.ctx.make_move(), True
        mx, my = direction_to(self.ctx.px, self.ctx.py, sp_x, sp_z)
        return self.ctx.make_move(mx, my), False

class ChaseSkill(Skill):
    """Multi-step: move toward enemy. Attacks if in range."""
    name = "CHASE"
    def update(self):
        mx, my = direction_to(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
        ar = self.ctx.atk_range()
        d = dist(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
        if d < ar and valid_btn(self.ctx.la, BTN_ATTACK):
            return (BTN_ATTACK, mx, my, CENTER, CENTER, get_target_for(self.ctx.la, BTN_ATTACK)), True
        return self.ctx.make_move(mx, my), False

class KiteSkill(Skill):
    """One-shot per frame: basic attack enemy while moving backward."""
    name = "KITE"
    def update(self):
        camp = self.ctx.camp()
        mx, my = direction_to(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
        ar = self.ctx.atk_range()
        d = dist(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
        if d < ar and valid_btn(self.ctx.la, BTN_ATTACK):
            return (BTN_ATTACK, clamp(mx + camp), my, CENTER, CENTER, get_target_for(self.ctx.la, BTN_ATTACK)), True
        return self.ctx.make_move(clamp(mx + camp), my), True

class DodgeSkill(Skill):
    """One-shot: use dash/escape skill toward own base. Falls back to moving."""
    name = "DODGE"
    def update(self):
        cfg = self.ctx.hero_config
        if not cfg: return self.ctx.make_move(), True
        slot = int(self.params.get("slot", "0"))
        esc = slot if slot > 0 else cfg.get("escape_skill", 0) or 0
        if not esc: return self.ctx.make_move(), True
        btn = {1: 4, 2: 5, 3: 6}[esc]
        if not valid_btn(self.ctx.la, btn): return self.ctx.make_move(), True
        camp = self.ctx.camp()
        ax = self.ctx.px + camp * 5000
        ay = self.ctx.py + camp * 5000
        sx, sy = direction_to(self.ctx.px, self.ctx.py, ax, ay)
        return (btn, CENTER, CENTER, sx, sy, get_target_for(self.ctx.la, btn)), True

class LastHitSkill(Skill):
    """One-shot: basic attack nearest low-HP minion. Moves toward lane if none."""
    name = "LAST_HIT"
    def update(self):
        m = self.ctx.nearest_low_hp_minion(hp_threshold=300)
        ar = self.ctx.atk_range()
        if m and dist(self.ctx.px, self.ctx.py, m['x'], m['z']) < ar:
            mx, my = direction_to(self.ctx.px, self.ctx.py, m['x'], m['z'])
            atk = self.ctx.make_attack(mx, my, target=2)
            if atk: return atk, True
        mx, my = direction_to(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
        return self.ctx.make_move(mx, my), True

class ClearSkill(Skill):
    """One-shot: basic attack nearest enemy minion. Moves toward lane if none."""
    name = "CLEAR"
    def update(self):
        ar = self.ctx.atk_range()
        soldiers_near = [s for s in self.ctx.soldiers if dist(self.ctx.px, self.ctx.py, s['x'], s['z']) < ar]
        if soldiers_near:
            mx, my = direction_to(self.ctx.px, self.ctx.py, soldiers_near[0]['x'], soldiers_near[0]['z'])
            atk = self.ctx.make_attack(mx, my, target=2)
            if atk: return atk, True
        mx, my = direction_to(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
        return self.ctx.make_move(mx, my), True

class WaitSkill(Skill):
    """One-shot: stand still for this frame."""
    name = "WAIT"
    def update(self):
        return self.ctx.make_move(CENTER, CENTER), True

SKILL_REGISTRY = {
    "MOVE_TO": MoveTo,
    "ATTACK": AttackTarget,
    "USE_SKILL": UseSkill,
    "RECALL": RecallSkill,
    "POKE": PokeSkill,
    "COMBO_STEP": ComboStep,
    "RETREAT": RetreatSkill,
    "CHASE": ChaseSkill,
    "KITE": KiteSkill,
    "DODGE": DodgeSkill,
    "LAST_HIT": LastHitSkill,
    "CLEAR": ClearSkill,
    "WAIT": WaitSkill,
}
