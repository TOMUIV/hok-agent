from skill_base import Skill, register_skill

@register_skill
class USE_SKILL(Skill):
    name = "USE_SKILL"
    description = "Use skill slot n (1/2/3/4) toward enemy. One-shot per call."
    when = "Skill off cooldown, enemy in range."
    until = "Skill cast (one frame)."
    sub_func_returns = {"cast": "dict: action/status/slot/detail. status: success|blocked."}

    def func_cast(self, ctx):
        return {"action": "use_skill", "status": "success", "detail": f"skill slot fired"}
