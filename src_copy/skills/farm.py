from skill_base import Skill, register_skill

@register_skill
class FARM(Skill):
    name = "FARM"
    description = "Farm minions. Prioritize last-hitting low HP minions for gold and XP."
    when = "Laning phase, minion wave nearby, safe to approach."
    until = "None (loop until LLM switches to another skill)."
    sub_func_returns = {
        "last_hit": "dict with action/status/detail/gold_est. status: success|no_target.",
        "move_to_lane": "dict with action/status/detail. status: moving.",
        "retreat_to_tower": "dict with action/status/detail. status: moving.",
    }

    def func_last_hit(self, ctx):
        """Attack the nearest low-HP minion to secure last-hit gold. Switches to move_to_lane if no minion in range."""
        if ctx.valid_btn(3) and ctx.dist_to_enemy() < ctx.atk_range():
            ctx.make_attack()
            return {"action": "last_hit", "status": "success", "detail": "attacked nearest minion", "gold_est": "+40"}
        return {"action": "move_to_lane", "status": "no_target", "detail": "no minion in attack range"}

    def func_move_to_lane(self, ctx):
        """Move toward the lane center (X=0) where minions converge."""
        mid_x = 0
        ctx.make_move_to(mid_x, 48)
        return {"action": "move_to_lane", "status": "moving", "detail": f"heading toward lane center X={mid_x}"}

    def func_retreat_to_tower(self, ctx):
        """Walk back toward own tower after pushing wave."""
        camp = ctx.camp()
        ctx.make_move(8 + camp, 8)
        return {"action": "retreat_to_tower", "status": "moving", "detail": "walking back to tower range"}
