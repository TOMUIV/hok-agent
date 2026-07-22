import math, re
from skill_base import SKILL_REGISTRY
import skills
from constants import CENTER, BUTTON_NAMES, LEGAL_OFFSET
from skill_context import SkillContext, clamp, direction_to, get_target_for, get_hero_pos

class ProtocolExecutor:
    def __init__(self, self_hero_id):
        self.self_hero_id = self_hero_id
        self.ctx = SkillContext(self_hero_id)
        self.last_actions = []
        self._concrete_skill = None

    def step(self, info):
        if not self.ctx.refresh(info):
            return (2, 8, 8, 8, 8, 0), ""

        if self._concrete_skill is not None:
            try:
                from skills_concrete import SKILL_REGISTRY as CONCRETE_REGISTRY
                if hasattr(self._concrete_skill, 'ctx'):
                    self._concrete_skill.ctx.refresh(info)
                action, done = self._concrete_skill.update()
                if done:
                    self._concrete_skill = None
                return action, ""
            except Exception:
                self._concrete_skill = None

        if self.last_actions:
            action = self.last_actions.pop(0)
            return action, ""

        # 持续执行同一个skill直到LLM换新的
        if self._concrete_skill is not None:
            try:
                if not self._concrete_skill.ctx.refresh(info):
                    self._concrete_skill = None
                else:
                    px = self._concrete_skill.ctx.px
                    action, done = self._concrete_skill.update()
                    btn = action[0]
                    if btn == 2:
                        mx, mz = action[1], action[2]
                        if abs(mx-8) < 1 and abs(mz-8) < 1:
                            pass  # stopped
                    if done:
                        self._concrete_skill = None
                    return action, ""
            except:
                self._concrete_skill = None

        # 还没有skill（LLM还没决策）→ 默认向前走
        mx, my = direction_to(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
        return self.ctx.make_move(mx, my), ""

    def execute_macro(self, macro_name, info):
        if not self.ctx.refresh(info):
            return (2, 8, 8, 8, 8, 0)
        from skills_concrete import SKILL_REGISTRY as CONCRETE_REGISTRY
        from skill_context import SkillContext as ConcreteCtx
        sk_cls = CONCRETE_REGISTRY.get(macro_name)
        if not sk_cls:
            return self.ctx.make_move(8, 8)
        sk = sk_cls()
        sk.ctx = ConcreteCtx(self.self_hero_id)
        sk.ctx.refresh(info)
        sk.params = {}
        if hasattr(sk, '_start'):
            sk._start()
        action, _ = sk.update()
        return action

    def process_batch(self, info, llm_output):
        if not self.ctx.refresh(info):
            return [{"type": "error", "msg": "state refresh failed"}]

        from skills_concrete import SKILL_REGISTRY as CONCRETE_REGISTRY
        from skill_context import SkillContext as ConcreteCtx

        results = []
        lines = llm_output.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line or line.startswith("Thought") or line.startswith("WhatIf"):
                continue

            m = re.match(r"@TOOL\s+(\w+)\(([^)]*)\)", line)
            if m:
                name, params_str = m.group(1), m.group(2)
                params = {}
                for p in params_str.split(","):
                    if "=" in p:
                        k, v = p.split("=", 1)
                        params[k.strip()] = v.strip()
                info["_self_id"] = self.ctx.sh
                result = execute_tool(name, info, **params)
                results.append({"type": "tool", "name": name, "result": result})
                continue

            m = re.match(r"@SKILL_OPEN\s+(\w+)", line)
            if m:
                sk_name = m.group(1)
                sk = SKILL_REGISTRY.get(sk_name)
                if sk:
                    results.append({"type": "skill_open", "name": sk_name, "doc": sk.get_doc()})
                else:
                    results.append({"type": "error", "msg": f"unknown skill: {sk_name}"})
                continue

            m = re.match(r"@SKILL_CALL\s+(\w+)\(([^)]*)\)", line)
            if m:
                sk_name = m.group(1)
                sk_cls = CONCRETE_REGISTRY.get(sk_name.upper())
                if sk_cls:
                    sk = sk_cls()
                    sk.ctx = ConcreteCtx(self.self_hero_id)
                    sk.ctx.refresh(info)
                    sk.params = {}
                    raw = m.group(2).strip()
                    if raw:
                        for p in raw.split(","):
                            if "=" in p:
                                k, v = p.split("=", 1)
                                sk.params[k.strip()] = v.strip()
                    if hasattr(sk, '_start'):
                        sk._start()
                    self._concrete_skill = sk
                    self.last_actions.clear()
                    action, done = sk.update()
                    self.last_actions.append(action)
                    results.append({"type": "skill_call", "skill": sk_name, "func": "execute"})
                else:
                    results.append({"type": "error", "msg": f"unknown concrete skill: {sk_name}"})
                continue

        return results

