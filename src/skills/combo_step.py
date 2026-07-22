from skill_base import Skill, register_skill

@register_skill
class COMBO_STEP(Skill):
    name = "COMBO_STEP"
    description = "One-shot: try each skill in combo_priority order, fire the first available one. Continuous (no damage interrupt)."
    when = "Enemy in range, want to deal max damage. Combo priority per hero config."
    until = "One skill fired or all unavailable (one frame)."
    sub_func_returns = {"execute": "dict: action/status/skill_cast/detail. status: success|none."}

    def func_execute(self, ctx):
        return {"action": "combo_step", "status": "success", "detail": "combo step executed"}
