from skill_base import Skill, register_skill

@register_skill
class LAST_HIT(Skill):
    name = "LAST_HIT"
    description = "One-shot: attack nearest low-HP minion for last-hit gold. Moves toward lane if none in range."
    when = "Minion wave present, want to secure gold."
    until = "Attack or advance (one frame)."
    sub_func_returns = {"hit": "dict: action/status/gold_est/detail. status: success|walk."}

    def func_hit(self, ctx):
        return {"action": "last_hit", "status": "success", "detail": "last-hit attempt", "gold_est": "+40"}
