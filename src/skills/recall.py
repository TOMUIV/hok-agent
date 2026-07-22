from skill_base import Skill, register_skill

@register_skill
class RECALL(Skill):
    name = "RECALL"
    description = "Start recall channel. If interrupted (hit), move toward base instead."
    when = "Low HP, safe position (under tower), no enemy nearby."
    until = "Channel complete or interrupted (one frame)."
    sub_func_returns = {"channel": "dict: action/status/detail. status: recalling|moving."}

    def func_channel(self, ctx):
        return {"action": "recall", "status": "recalling", "detail": "recall channel"}
