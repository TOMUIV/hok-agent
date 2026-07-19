from skill_base import Skill, register_skill

@register_skill
class POKE(Skill):
    name = "POKE"
    description = "Ranged poke. Use Skill1 or basic attack to chip HP from safe distance."
    when = "HP advantage, poke skill off cooldown, enemy positioned forward."
    until = "Poke skill goes on cooldown or enemy retreats out of range."
    sub_func_returns = {
        "aim_skill": "dict: action/status/skill/detail. status: success|out_of_range|error.",
        "basic_attack": "dict: action/status/detail. status: success|out_of_range.",
        "reposition_back": "dict: action/status/detail. status: moving.",
    }

    def func_aim_skill(self, ctx):
        """Cast the poke skill (configurable, usually Skill1) toward the enemy."""
        cfg = ctx.hero_config
        if not cfg:
            return {"action": "aim_skill", "status": "error", "detail": "no hero config"}
        pk = cfg.get("poke_skill", 1)
        btn = {1: 4, 2: 5, 3: 6}[pk]
        sr = cfg.get("skill_ranges", {}).get(pk, 700)
        if ctx.dist_to_enemy() < sr and ctx.valid_btn(btn):
            ctx.make_skill(pk, ctx.ex, ctx.ey)
            return {"action": "aim_skill", "status": "success", "skill": pk, "detail": f"Skill{pk} aimed at enemy"}
        return {"action": "aim_skill", "status": "out_of_range", "detail": "enemy out of poke range"}

    def func_basic_attack(self, ctx):
        """Basic attack enemy once."""
        if ctx.valid_btn(3) and ctx.dist_to_enemy() < ctx.atk_range():
            ctx.make_attack()
            return {"action": "basic_attack", "status": "success", "detail": "attacked enemy"}
        return {"action": "basic_attack", "status": "out_of_range", "detail": "enemy not in attack range"}

    def func_reposition_back(self, ctx):
        """Take a step back toward own base to maintain safe distance."""
        camp = ctx.camp()
        ctx.make_move(8 + camp, 8)
        return {"action": "reposition_back", "status": "moving", "detail": "stepping back toward tower"}
