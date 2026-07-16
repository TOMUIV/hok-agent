from skill_base import Skill, register_skill

@register_skill
class KITE(Skill):
    name = "KITE"
    description = "Kite backward. Auto attack while retreating. Use Skill2(落日余晖) to slow pursuing enemies. Use Skill3(灼日之矢) to stun if enemy gets too close."
    when = "Enemy advancing, you are retreating, need to create distance while dealing damage."
    until = "Enemy stops chasing or you reach tower safety."
    sub_func_returns = {
        "retreating_shot": "dict: action/status/detail. status: success|out_of_range.",
        "slow_enemy": "dict: action/status/detail. status: success|cooldown.",
        "stun_peel": "dict: action/status/detail. status: success|cooldown.",
    }

    def func_retreating_shot(self, ctx):
        """Fire a basic attack while moving backward. This is the core kiting action."""
        d = ctx.dist_to_enemy()
        if d < ctx.atk_range() and ctx.valid_btn(3):
            mx, my = direction_to(ctx.px, ctx.py, ctx.ex, ctx.ey)
            camp = ctx.camp()
            mx = clamp(mx - camp)  # bias movement toward own base
            ctx.make_move(mx, my)
            return {"action": "retreating_shot", "status": "success", "detail": "attack while retreating"}
        camp = ctx.camp()
        ctx.make_move(8 + camp, 8)
        return {"action": "retreating_shot", "status": "out_of_range", "detail": "backing up"}

    def func_slow_enemy(self, ctx):
        """Use Skill2 to slow chasing enemy."""
        if ctx.valid_btn(5) and ctx.dist_to_enemy() < 750:
            ctx.make_skill(2, ctx.ex, ctx.ey)
            return {"action": "slow_enemy", "status": "success", "detail": "Skill2 slow applied"}
        return {"action": "slow_enemy", "status": "cooldown", "detail": "skill on cooldown or out of range"}

    def func_stun_peel(self, ctx):
        """Use Skill3 to stun enemy diving you."""
        if ctx.valid_btn(6) and ctx.dist_to_enemy() < 1000:
            ctx.make_skill(3, ctx.ex, ctx.ey)
            return {"action": "stun_peel", "status": "success", "detail": "Skill3 stun for peel"}
        return {"action": "stun_peel", "status": "cooldown", "detail": "ult on cooldown or out of range"}

def clamp(v):
    return max(1, min(15, int(round(v))))

def direction_to(px, py, tx, ty):
    import math
    dx, dy = tx - px, ty - py
    d = math.sqrt(dx*dx + dy*dy)
    if d < 0.01: return (8, 8)
    return (clamp(dx/d*7 + 8), clamp(dy/d*7 + 8))
