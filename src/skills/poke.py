from skill_base import Skill, register_skill

@register_skill
class POKE(Skill):
    name = "POKE"
    description = "One-shot: fire poke skill toward enemy. Falls back to basic attack or advancing if out of range."
    when = "Poke skill off cooldown, enemy in poke range."
    until = "Skill cast or fallback action (one frame)."
    sub_func_returns = {"fire": "dict: action/status/skill/detail. status: success|walk."}

    def func_fire(self, ctx):
        return {"action": "poke", "status": "success", "detail": "poke skill fired"}
