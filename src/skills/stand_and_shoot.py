from skill_base import Skill, register_skill

@register_skill
class STAND_AND_SHOOT(Skill):
    name = "STAND_AND_SHOOT"
    description = "Max DPS mode. Stack passive to 3 stacks → activate Skill1(multi-shot) → auto attack. Weave Skill2 between attacks for extra poke. Use Skill3 to stun if enemy tries to escape."
    when = "Safe position, enemy in attack range, want maximum sustained damage."
    until = "Enemy retreats, danger approaches, or all skills exhausted."
    sub_func_returns = {
        "ramp_up": "dict: action/status/stacks. status: stacking|ready.",
        "barrage": "dict: action/status/detail. status: success|cooldown.",
        "suppress": "dict: action/status/detail. status: success|out_of_range.",
        "finish": "dict: action/status/detail. status: stun|executed.",
    }

    def func_ramp_up(self, ctx):
        """Stack passive by basic attacking to reach max attack speed stacks."""
        if ctx.valid_btn(3) and ctx.dist_to_enemy() < ctx.atk_range():
            ctx.make_attack()
            return {"action": "ramp_up", "status": "stacking", "detail": "stacking passive"}
        return {"action": "ramp_up", "status": "ready", "detail": "passive stacked or enemy in range"}

    def func_barrage(self, ctx):
        """Activate skill 1 (multi-shot) for max DPS. Must have passive stacked first."""
        if ctx.valid_btn(4) and ctx.dist_to_enemy() < 800:
            ctx.make_skill(1, ctx.ex, ctx.ey)
            return {"action": "barrage", "status": "success", "detail": "Skill1 multi-shot active"}
        return {"action": "barrage", "status": "cooldown", "detail": "skill on cooldown or enemy out of range"}

    def func_suppress(self, ctx):
        """Sustained auto-attack fire."""
        if ctx.valid_btn(3) and ctx.dist_to_enemy() < ctx.atk_range():
            ctx.make_attack()
            return {"action": "suppress", "status": "success", "detail": "auto attacking"}
        return {"action": "suppress", "status": "out_of_range", "detail": "enemy not in attack range"}

    def func_finish(self, ctx):
        """Use skill 3 (ult) to stun fleeing enemy, or skill 2 to slow."""
        if ctx.valid_btn(6) and ctx.dist_to_enemy() < 1000:
            ctx.make_skill(3, ctx.ex, ctx.ey)
            return {"action": "finish", "status": "stun", "detail": "Skill3 stun fired"}
        if ctx.valid_btn(5) and ctx.dist_to_enemy() < 750:
            ctx.make_skill(2, ctx.ex, ctx.ey)
            return {"action": "finish", "status": "executed", "detail": "Skill2 slow fired"}
        return {"action": "finish", "status": "executed", "detail": "no skills available"}
