from skill_base import Skill, register_skill

@register_skill
class KITE(Skill):
    name = "KITE"
    description = "One-shot per frame: basic attack enemy while moving backward. Continuous (no damage interrupt)."
    when = "Enemy advancing, you want to deal damage while retreating."
    until = "One frame of kiting."
    sub_func_returns = {"shot": "dict: action/status/detail. status: shooting|backing."}

    def func_shot(self, ctx):
        return {"action": "kite", "status": "shooting", "detail": "attack while retreating"}
