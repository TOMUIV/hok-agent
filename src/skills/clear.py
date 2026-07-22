from skill_base import Skill, register_skill

@register_skill
class CLEAR(Skill):
    name = "CLEAR"
    description = "One-shot: basic attack nearest enemy minion. Use to push wave or clear under tower."
    when = "Minions in range, want to push wave or defend."
    until = "Attack or advance (one frame)."
    sub_func_returns = {"clear": "dict: action/status/detail. status: attacking|walk."}

    def func_clear(self, ctx):
        return {"action": "clear", "status": "attacking", "detail": "clearing minions"}
