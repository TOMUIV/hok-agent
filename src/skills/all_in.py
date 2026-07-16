from skill_base import Skill, register_skill

@register_skill
class ALL_IN(Skill):
    name = "ALL_IN"
    description = "All-in kill. Execute full combo rotation, chase to the death."
    when = "Enemy HP < 50%, core skills off cooldown, you have HP advantage."
    until = "Enemy dies (kill confirmed) or all skills on cooldown."
    sub_func_returns = {
        "combo_start": "dict: action/status/skill_cast/detail. status: success|all_done|error.",
        "basic_attack": "dict: action/status/detail. status: success|out_of_range.",
        "chase": "dict: action/status/detail. status: moving.",
    }

    def func_combo_start(self, ctx):
        """Execute the next available skill from combo_priority order."""
        cfg = ctx.hero_config
        if not cfg:
            return {"action": "combo_start", "status": "error", "detail": "no hero config"}
        prio = cfg.get("combo_priority", [3, 2, 1])
        for sn in prio:
            btn = {1: 4, 2: 5, 3: 6}[sn]
            sr = cfg.get("skill_ranges", {}).get(sn, 700)
            if ctx.dist_to_enemy() < sr and ctx.valid_btn(btn):
                ctx.make_skill(sn, ctx.ex, ctx.ey)
                return {"action": "combo_start", "status": "success", "skill_cast": sn, "detail": f"Skill{sn} released toward enemy"}
        return {"action": "combo_start", "status": "all_done", "detail": "all skills done or out of range"}

    def func_basic_attack(self, ctx):
        """Basic attack toward the enemy."""
        if ctx.valid_btn(3) and ctx.dist_to_enemy() < ctx.atk_range():
            ctx.make_attack()
            return {"action": "basic_attack", "status": "success", "detail": "attacked enemy"}
        return {"action": "basic_attack", "status": "out_of_range", "detail": "enemy not in attack range"}

    def func_chase(self, ctx):
        """Move toward enemy position to chase."""
        ctx.make_move_to(ctx.ex, ctx.ey)
        return {"action": "chase", "status": "moving", "detail": f"chasing enemy toward ({ctx.ex:.0f},{ctx.ey:.0f})"}
