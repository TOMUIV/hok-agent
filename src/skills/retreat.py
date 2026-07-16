from skill_base import Skill, register_skill

@register_skill
class RETREAT(Skill):
    name = "RETREAT"
    description = "Retreat to safety under tower. Disengage from combat and return to tower range."
    when = "Low HP, enemy pressing hard, skills on cooldown, or outnumbered."
    until = "Under tower or enemy stops chasing."
    sub_func_returns = {
        "move_to_tower": "dict: action/status/detail. status: moving|arrived.",
        "defend_self": "dict: action/status/detail. status: success|no_skill.",
        "recall": "dict: action/status/detail. status: recalling|interrupted.",
    }

    def func_move_to_tower(self, ctx):
        """Move directly toward own tower."""
        camp = ctx.camp()
        return {"action": "move_to_tower", "status": "moving", "detail": f"retreating toward own tower"}

    def func_defend_self(self, ctx):
        """Use escape skill if enemy gets too close during retreat."""
        cfg = ctx.hero_config
        if not cfg:
            return {"action": "defend_self", "status": "no_skill", "detail": "no config"}
        esc = cfg.get("escape_skill")
        if not esc:
            return {"action": "defend_self", "status": "no_skill", "detail": "no escape skill"}
        btn = {1: 4, 2: 5, 3: 6}[esc]
        sr = cfg.get("skill_ranges", {}).get(esc, 500)
        if ctx.dist_to_enemy() < sr * 0.6 and ctx.valid_btn(btn):
            ctx.make_skill(esc, ctx.ex, ctx.ey)
            return {"action": "defend_self", "status": "success", "skill": esc, "detail": f"Skill{esc} used to peel enemy"}
        return {"action": "defend_self", "status": "no_skill", "detail": "enemy too far or skill on cd"}

    def func_recall(self, ctx):
        """Use recall channel when safe."""
        if ctx.valid_btn(9):
            return {"action": "recall", "status": "recalling", "detail": "channeling recall"}
        return {"action": "recall", "status": "interrupted", "detail": "recall not available, move to safety first"}
