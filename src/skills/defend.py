from skill_base import Skill, register_skill

@register_skill
class DEFEND(Skill):
    name = "DEFEND"
    description = "Defend under tower. Stay in tower range, clear minions, punish enemy overextension."
    when = "Enemy pushing wave to your tower, you are weaker or need to play safe."
    until = "Wave cleared or enemy retreats."
    sub_func_returns = {
        "clear_wave": "dict: action/status/detail. status: success|waiting.",
        "punish": "dict: action/status/detail. status: success|out_of_range.",
    }

    def func_clear_wave(self, ctx):
        """Use skills to clear minion wave under tower."""
        cfg = ctx.hero_config
        d = ctx.dist_to_enemy()
        ar = ctx.atk_range()
        if d < ar and ctx.valid_btn(3):
            ctx.make_attack()
            return {"action": "clear_wave", "status": "success", "detail": "attacking minions"}
        return {"action": "clear_wave", "status": "waiting", "detail": "waiting for minions in range"}

    def func_punish(self, ctx):
        """Punish enemy if they overextend into tower range."""
        cfg = ctx.hero_config
        if not cfg:
            return {"action": "punish", "status": "out_of_range", "detail": "no config"}
        pk = cfg.get("poke_skill", 1)
        btn = {1: 4, 2: 5, 3: 6}[pk]
        sr = cfg.get("skill_ranges", {}).get(pk, 600)
        d = ctx.dist_to_enemy()
        if d < sr and ctx.valid_btn(btn):
            ctx.make_skill(pk, ctx.ex, ctx.ey)
            return {"action": "punish", "status": "success", "skill": pk, "detail": f"punished enemy with Skill{pk}"}
        return {"action": "punish", "status": "out_of_range", "detail": "enemy out of punish range"}
