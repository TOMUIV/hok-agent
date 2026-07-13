import re, json
from openai import OpenAI
from state_parser import parse_state, hero_detail
from tool_set import ToolSet, TOOL_REGISTRY
from hero_db import hero_name

ACT_MAP = {"NONE":0,"MOVE":2,"NORMAL_ATTACK":3,"SKILL_1":4,"SKILL_2":5,"SKILL_3":6,"RECALL":9}
DIR_MAP = {"N":1,"NE":3,"E":5,"SE":7,"S":9,"SW":11,"W":13,"NW":15,"STOP":0}
TGT_MAP = {"ENEMY_0":1,"ENEMY_1":2,"SELF":7}

SYSTEM_PROMPT = """You are playing Honor of Kings 1v1. You control [HERO_NAME].

Each frame you receive the game state. Think step by step, use tools to gather info, then decide.

Format:
Thought: <analysis>
Action: <tool>(<params>)
Observation: <result>
...repeat up to 3 rounds...
FinalAction: <TYPE>(<params>)

Tools:
  query_hp() - check HP
  query_position() - check positions
  query_hero_state(hero=SELF/ENEMY_0) - detailed state
  query_legal_actions() - check legal actions

FinalAction types:
  MOVE(direction=N/NE/E/SE/S/SW/W/NW/STOP, distance=short/medium/long)
  ATTACK(target=ENEMY_0/ENEMY_1)
  SKILL_1(target=ENEMY_0, ox=0, oz=0)
  SKILL_2(target=ENEMY_0, ox=0, oz=0)
  SKILL_3(target=ENEMY_0, ox=0, oz=0)
  RECALL()
  WAIT()

Explore and learn. You can use up to 3 tool calls per frame before deciding."""

class ReActAgent:
    def __init__(self, name, hero_id, api_key, base_url, model="deepseek-v4-flash"):
        self.name = name
        self.hero_id = hero_id
        self.client = OpenAI(api_key=api_key, base_url=base_url) if api_key else None
        self.model = model
        self.history = []

    def decide(self, info):
        state_text, self_hero = parse_state(info, self.hero_id)
        state_text = state_text.replace("[HERO_NAME]", hero_name(self.hero_id))

        tool_set = ToolSet(info, self.hero_id)
        tools_desc = "\n".join([f"  {k}({', '.join(f'{p}={v}' for p,v in v['params'].items())}) - {v['desc']}" for k,v in TOOL_REGISTRY.items()])

        prompt = f"{state_text}\n\nTools:\n{tools_desc}\n\nYou control {hero_name(self.hero_id)}. What do you do?"
        if not self.client:
            return self._fallback(info), ""

        messages = [{"role":"system","content":SYSTEM_PROMPT.replace("[HERO_NAME]", hero_name(self.hero_id))}]
        messages.append({"role":"user","content":prompt})

        for react_step in range(4):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model, messages=messages,
                    temperature=0.8, max_tokens=400,
                )
                reply = resp.choices[0].message.content.strip()
            except Exception as e:
                return self._fallback(info), f"LLM Error: {e}"

            final = self._extract_final(reply)
            if final:
                action = self._final_to_action(final, info)
                return action, reply

            action_call = self._extract_action(reply)
            if action_call:
                tool_name, tool_params = action_call
                try:
                    result = tool_set.execute(tool_name, **tool_params)
                except Exception as e:
                    result = f"Error: {e}"
                messages.append({"role":"assistant","content":reply})
                messages.append({"role":"user","content":f"Observation: {result}\nContinue reasoning and output FinalAction."})
                continue

            messages.append({"role":"assistant","content":reply})
            messages.append({"role":"user","content":"Output FinalAction now."})

        return self._fallback(info), reply

    def _extract_final(self, text):
        m = re.search(r'FinalAction:\s*(\w+)\(([^)]*)\)', text)
        if m:
            return (m.group(1), m.group(2))
        m2 = re.search(r'FinalAction:\s*(\w+)', text)
        if m2:
            return (m2.group(1), "")
        return None

    def _extract_action(self, text):
        m = re.search(r'Action:\s*(\w+)\(([^)]*)\)', text)
        if m:
            name = m.group(1)
            params_str = m.group(2)
            params = {}
            for p in params_str.split(","):
                p = p.strip()
                if "=" in p:
                    k, v = p.split("=", 1)
                    params[k.strip()] = v.strip()
            return (name, params)
        return None

    def _final_to_action(self, final, info):
        if not final:
            return self._fallback(info)
        atype, pstr = final
        params = {}
        parts = [x.strip() for x in pstr.split(",") if x.strip()]
        for p in parts:
            if "=" in p:
                k, v = p.split("=", 1)
                params[k.strip()] = v.strip()
        if not params and len(parts) >= 1:
            params["target"] = parts[0]
        if not params and len(parts) >= 3:
            params["ox"], params["oz"] = parts[1], parts[2]

        btn = ACT_MAP.get(atype.upper(), 2)
        mvx, mvz, skx, skz, tgt = 1, 1, 1, 1, 0
        if atype.upper() == "MOVE":
            d = params.get("direction", "N").upper()
            di = DIR_MAP.get(d, 1)
            mvx, mvz = di * 2 // 5, di % 5
        elif atype.upper() == "ATTACK":
            tgt = TGT_MAP.get(params.get("target","ENEMY_0").upper(), 1)
        elif atype.upper().startswith("SKILL"):
            tgt = TGT_MAP.get(params.get("target","ENEMY_0").upper(), 1)
            skx = int(params.get("ox", 0)) + 8
            skz = int(params.get("oz", 0)) + 8
        return (btn, mvx, mvz, skx, skz, tgt)

    def _fallback(self, info):
        s = info if isinstance(info, dict) else info[0]
        la = s.get("legal_action", [])
        btns = [i for i in range(12) if i < len(la) and la[i] == 1]
        btn = btns[0] if btns else 2
        return (btn, 1, 1, 1, 1, 0)

    def reset(self):
        self.history = []
