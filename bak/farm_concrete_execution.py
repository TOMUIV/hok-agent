import math
from skill_base import Skill

CENTER = 8
BTN_MOVE, BTN_ATTACK = 2, 3
BTN_SKILL1, BTN_SKILL2, BTN_SKILL3 = 4, 5, 6

def clamp(v):
    return max(1, min(15, int(round(v))))

def steer_toward(px, py, tx, ty):
    dx, dy = tx - px, ty - py
    d = math.sqrt(dx*dx + dy*dy)
    if d < 0.01:
        return (CENTER, CENTER)
    return (clamp(dx/d*7 + CENTER), clamp(dy/d*7 + CENTER))

def dist(px, py, tx, ty):
    return math.sqrt((tx-px)**2 + (ty-py)**2)

def valid_btn(la, btn):
    return btn < len(la) and la[btn] == 1.0

def get_target_for(la, btn):
    off = 12 + 16 * 4
    row = off + btn * 8
    if row + 8 > len(la):
        return 0
    for t in range(8):
        if la[row + t] == 1.0:
            return t
    return 0


class Farm(Skill):
    name = "FARM"
    def update(self):
        """推进补兵，打架前开技能。已到中线附近+无战斗+无小兵=预期目的达成。"""
        ar = self.ctx.atk_range()
        mx, my = steer_toward(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
        d = dist(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
        soldiers_near = sum(1 for s in self.ctx.soldiers if dist(self.ctx.px, self.ctx.py, s['x'], s['z']) < ar)
        m_low = self.ctx.nearest_low_hp_minion(hp_threshold=300)

        # 预期目的达成：已到中线路段 + 无敌人可打 + 无残血兵可补
        near_lane = abs(self.ctx.px) < 12000
        no_fight = d > ar * 2 and soldiers_near == 0
        no_last_hit = not m_low
        if near_lane and no_fight and no_last_hit:
            return self.ctx.make_move(mx, my), True

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
