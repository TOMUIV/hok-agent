from skill_base import Skill, register_skill

@register_skill
class DODGE(Skill):
    name = "DODGE"
    description = "One-shot: use dash/escape skill toward own base. Continuous (no damage interrupt). Falls back to basic movement."
    when = "Enemy diving you, need instant repositioning."
    until = "Dash cast or fallback (one frame)."
    sub_func_returns = {"escape": "dict: action/status/slot/detail. status: dashed|moved."}

    def func_escape(self, ctx):
        return {"action": "dodge", "status": "dashed", "detail": "escape skill used"}
