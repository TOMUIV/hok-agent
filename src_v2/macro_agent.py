import re, os, json, time
from openai import OpenAI
from hero_db import hero_name
from state_parser import parse_state, hero_detail
from hero_skills import get_config, HERO_ROLES
from skill_db import get_matchup, get_skill
import skills  # triggers auto-discovery to populate SKILL_REGISTRY
from tools import TOOL_REGISTRY, execute_tool
from skill_base import SKILL_REGISTRY
from memory import MemoryManager
from pathfinding import astar

from trajectory import TRAJECTORY_DIR
traj_file = None
traj_path = os.path.join(TRAJECTORY_DIR, f"trajectory_{int(time.time())}.jsonl")

SYSTEM_PROMPT = """You play {self_name}({self_type}) in Honor of Kings 1v1 vs {enemy_name}({enemy_type}).
Lane is along X axis. You are at -X, enemy at +X. Destroy Crystal to win.
Enemy HP = 1 when out of vision (FOW), not real HP.

=== YOUR SKILLS ===
{self_name}:
  Skill1({s1_range}u): {s1_desc}
  Skill2({s2_range}u): {s2_desc}
  Skill3({s3_range}u): {s3_desc}
  Combo: {combo_desc}

=== MATCHUP ===
{matchup_info}

=== TOOLS ===
query_hp() → HP stats
query_position() → coordinates
query_hero_state(hero=SELF/ENEMY_0) → level, gold, cooldowns, items
query_map() → minions, towers on map
query_cooldown() → skill cooldown seconds
query_legal_actions() → available buttons right now

=== KEY RULE ===
- Enemy HP=1 and position (100000,100000) means enemy is NOT VISIBLE (FOW).
- When enemy is not visible: ALWAYS move to lane center and FARM.
- Call @SKILL_CALL FARM.move_to_lane() to advance toward enemy base.
- Do NOT wait for enemy to appear. Keep moving forward.

=== SKILLS (open doc then call subfunctions) ===
{skill_list}

=== OUTPUT FORMAT ===
You can output multiple lines per frame. Each line starts with one of:
  @TOOL <name>(<params>)      — query game state
  @SKILL_OPEN <NAME>           — read skill documentation
  @SKILL_CALL <NAME>.<func>() — execute a skill's sub-function

IMPORTANT: After querying tools and reading skill docs, you MUST call @SKILL_CALL to actually act in the game.
Without @SKILL_CALL, your hero does nothing!

=== FULL EXAMPLE ===
@TOOL query_hp()
@TOOL query_position()
@SKILL_OPEN ALL_IN
@SKILL_CALL ALL_IN.combo_start()
@SKILL_CALL ALL_IN.basic_attack()
@SKILL_CALL ALL_IN.chase()
"""

class MacroAgent:
    def __init__(self, name, self_hero_id, enemy_hero_id, api_key=None, base_url=None, model=None):
        self.name = name
        self.self_hero_id = self_hero_id
        self.enemy_hero_id = enemy_hero_id
        self.executor = V2Executor(self_hero_id)
        api_key = api_key or os.environ.get("DASHSCOPE_API_KEY", "")
        base_url = base_url or os.environ.get("DASHSCOPE_BASE_URL", "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1")
        model = model or os.environ.get("MODEL_NAME", "deepseek-v4-flash")
        self.client = OpenAI(api_key=api_key, base_url=base_url) if api_key else None
        self.model = model
        self.memory = MemoryManager()
        self.last_action_result = ""
        self.last_reply = ""
        self.frames_since_llm = 99
        self.llm_interval = 3
        self.last_llm_results = [{"type": "tool", "name": "init", "result": "started"}]
        self.skill_name = ""
        self.skill_func = ""

        global traj_file, traj_path
        if not traj_file:
            os.makedirs(TRAJECTORY_DIR, exist_ok=True)
            traj_file = open(traj_path, "w", encoding="utf-8")

        self_name = hero_name(self.self_hero_id)
        enemy_name = hero_name(self.enemy_hero_id)
        self_type = HERO_ROLES.get(self.self_hero_id, "英雄")
        enemy_type = HERO_ROLES.get(self.enemy_hero_id, "英雄")
        cfg = get_config(self.self_hero_id)

        sk = cfg.get("skill_descs", {}) if cfg else {}
        sr = cfg.get("skill_ranges", {}) if cfg else {}
        combo = cfg.get("combo_priority", [1]) if cfg else [1]
        combo_str = " → ".join([f"Skill{c}" for c in combo])

        mu = get_matchup(self.self_hero_id, self.enemy_hero_id)
        mu_lines = []
        if mu:
            for k in ["summary", "advantage", "danger", "tip_offense", "tip_defense"]:
                if k in mu: mu_lines.append(f"  {k}: {mu[k]}")

        skill_lines = []
        for sn, sobj in SKILL_REGISTRY.items():
            subs = sobj.get_sub_functions()
            sub_str = ", ".join([f"{k}({v[:30]})" for k, v in subs.items()])
            skill_lines.append(f"  {sn}: {sobj.description[:60]}")
            skill_lines.append(f"    subfunctions: {sub_str}")

        self.system_prompt = SYSTEM_PROMPT.format(
            self_name=self_name, enemy_name=enemy_name,
            self_type=self_type, enemy_type=enemy_type,
            s1_desc=sk.get(1, "?"), s2_desc=sk.get(2, "?"), s3_desc=sk.get(3, "?"),
            s1_range=sr.get(1, "?"), s2_range=sr.get(2, "?"), s3_range=sr.get(3, "?"),
            combo_desc=combo_str, matchup_info="\n".join(mu_lines),
            skill_list="\n".join(skill_lines),
        )

    def decide(self, info):
        s = info[0] if isinstance(info, list) else info
        state_text, _ = parse_state(s, self.self_hero_id)

        if not self.client:
            return (2, 8, 8, 8, 8, 0), "[no LLM]"

        self.frames_since_llm += 1
        llm_interval = 3

        if self.frames_since_llm < llm_interval and self.last_llm_results:
            has_skill_call = any(r["type"] == "skill_call" for r in self.last_llm_results)
            action, _ = self.executor.step(s, default_skill=None if has_skill_call else "FARM")
            return action, f"repeat: {self.last_llm_results[0].get('name', self.last_llm_results[0].get('skill', '?'))}"

        self.frames_since_llm = 0

        mem_ctx = self.memory.get_context()
        user_msg = f"=== MEMORY ===\n{mem_ctx}\n\n=== CURRENT STATE ===\n{state_text}"
        if self.last_action_result:
            user_msg += f"\n\n=== LAST RESULTS ===\n{self.last_action_result}"

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_msg},
        ]

        try:
            resp = self.client.chat.completions.create(
                model=self.model, messages=messages,
                temperature=0.7, max_tokens=400,
            )
            msg = resp.choices[0].message
            reply = (msg.content or "").strip()
            reply = re.sub(r"<think>.*?</think>\s*", "", reply, flags=re.DOTALL)
            if not reply:
                reply = (getattr(msg, "reasoning_content", None) or "").strip()
        except Exception:
            return (2, 8, 8, 8, 8, 0), "[LLM err]"

        results = self.executor.process_batch(s, reply)
        self.last_llm_results = results
        result_lines = []
        for r in results:
            if r["type"] == "tool":
                result_lines.append(f"@TOOL {r['name']} → {str(r['result'])[:80]}")
            elif r["type"] == "skill_open":
                result_lines.append(f"@SKILL_OPEN {r['name']} → doc opened")
            elif r["type"] == "skill_call":
                result_lines.append(f"@SKILL_CALL {r['skill']}.{r['func']} → done={r['done']}")
            elif r["type"] == "error":
                result_lines.append(f"ERROR: {r['msg']}")

        self.last_action_result = "\n".join(result_lines[:5])

        has_skill_call = any(r["type"] == "skill_call" for r in results)

        global traj_file
        if traj_file:
            traj_file.write(json.dumps({
                "step": str(time.time()),
                "user_msg": user_msg[:500],
                "llm_reply": reply,
                "parsed_results": self.last_action_result,
            }, ensure_ascii=False) + "\n")
            traj_file.flush()

        action, _ = self.executor.step(s, default_skill=None if has_skill_call else "FARM")
        return action, f"{'skill' if has_skill_call else 'farm'}: {reply[:80]}"


import math, re as _re
from tools import TOOL_REGISTRY as _TR, execute_tool as _et

BTN_MOVE = 2
BTN_ATTACK = 3
BTN_SKILL1 = 4
BTN_SKILL2 = 5
BTN_SKILL3 = 6
BTN_RECALL = 9
CENTER = 8

def _clamp(v):
    return max(1, min(15, int(round(v))))

def _direction(px, py, tx, ty):
    dx, dy = tx - px, ty - py
    d = math.sqrt(dx*dx + dy*dy)
    if d < 0.01: return (CENTER, CENTER)
    mx = _clamp(dy/d*1 + CENTER)
    mz = _clamp(dx/d*1 + CENTER)
    return (mx, mz)

def _target_for(la, btn):
    off = 12 + 16 * 4
    row = off + btn * 8
    if row + 8 > len(la): return 0
    for t in range(8):
        if la[row + t] == 1.0: return t
    return 0

def _valid_btn(la, btn):
    return btn < len(la) and la[btn] == 1.0

class SkillCtx:
    def __init__(self, sid):
        self.sid = sid
        self.la = []
        self.sh = None
        self.eh = None
        self.px = self.py = 0
        self.ex = self.ey = 0
        self.cfg = None

    def refresh(self, info):
        self.la = info.get("legal_action", [])
        pb = info.get("req_pb")
        if not pb: return False
        for h in getattr(pb, "hero_list", []):
            if h.config_id == self.sid: self.sh = h
            else: self.eh = h
        if not self.sh or not self.eh: return False
        loc_s = getattr(self.sh, "location", None)
        loc_e = getattr(self.eh, "location", None)
        if not loc_s or not loc_e: return False
        self.px, self.py = loc_s.x, loc_s.y
        self.ex, self.ey = loc_e.x, loc_e.y
        self.cfg = get_config(self.sid)
        return True

    def dist(self): return math.sqrt((self.ex-self.px)**2 + (self.ey-self.py)**2)
    def atk_range(self): return getattr(self.sh, "atk_range", 700)
    def camp(self): return -1 if getattr(self.sh, "camp", 0) == 1 else 1
    def valid_btn(self, btn): return _valid_btn(self.la, btn)
    @property
    def hero_config(self): return self.cfg
    def dist_to_enemy(self): return self.dist()
    def make_move(self, mx, my): return (BTN_MOVE, mx, my, CENTER, CENTER, _target_for(self.la, BTN_MOVE))
    def make_attack(self):
        mx, my = _direction(self.px, self.py, self.ex, self.ey)
        return (BTN_ATTACK, mx, my, CENTER, CENTER, _target_for(self.la, BTN_ATTACK))
    def make_skill(self, skill_num, tx, ty):
        btn = {1:BTN_SKILL1,2:BTN_SKILL2,3:BTN_SKILL3}[skill_num]
        sx, sy = _direction(self.px, self.py, tx, ty)
        return (btn, CENTER, CENTER, sx, sy, _target_for(self.la, btn))
    def make_move_to(self, tx, ty):
        mx, my = _direction(self.px, self.py, tx, ty)
        return (BTN_MOVE, mx, my, CENTER, CENTER, _target_for(self.la, BTN_MOVE))

class V2Executor:
    def __init__(self, sid):
        self.ctx = SkillCtx(sid)
        self.last_action = (BTN_MOVE, CENTER, CENTER, CENTER, CENTER, 0)
        self.owned = set()

    def _auto_buy(self):
        from hero_skills import get_config, ITEM_DB, get_item_cost
        cfg = get_config(self.ctx.sid)
        if not cfg: return
        gold = getattr(self.ctx.sh, 'money', 0)
        if gold < 710: return
        for item in cfg.get("items", []):
            if item not in self.owned:
                cost = ITEM_DB.get(item, {}).get("cost", 9999)
                if gold >= cost:
                    self.owned.add(item)
                    break

    def step(self, info, default_skill=None):
        if not self.ctx.refresh(info):
            return ((2, 8, 8, 8, 8, 0), False)
        self._auto_buy()
        d = self.ctx.dist()
        ar = self.ctx.atk_range()
        hp = getattr(self.ctx.sh, 'hp', 0)
        max_hp = getattr(self.ctx.sh, 'max_hp', 1)
        hp_pct = hp / max_hp

        if hp_pct < 0.2:
            if _valid_btn(self.ctx.la, BTN_RECALL):
                self.last_action = (BTN_RECALL, CENTER, CENTER, CENTER, CENTER, _target_for(self.ctx.la, BTN_RECALL))
                return (self.last_action, True)
            camp = self.ctx.camp()
            self.last_action = (BTN_MOVE, CENTER, 7 if camp < 0 else 9, CENTER, CENTER, _target_for(self.ctx.la, BTN_MOVE))
            return (self.last_action, False)

        if hp_pct < 0.45:
            if d < ar * 1.2 and _valid_btn(self.ctx.la, BTN_ATTACK):
                if getattr(self.ctx.eh, 'hp', 0) < hp * 0.8:
                    pass
                else:
                    camp = self.ctx.camp()
                    self.last_action = (BTN_MOVE, CENTER, 7 if camp < 0 else 9, CENTER, CENTER, _target_for(self.ctx.la, BTN_MOVE))
                    return (self.last_action, False)

        if d < ar * 1.2:
            for btn in [BTN_SKILL3, BTN_SKILL2, BTN_SKILL1]:
                if _valid_btn(self.ctx.la, btn):
                    self.last_action = (btn, CENTER, CENTER, CENTER, CENTER, _target_for(self.ctx.la, btn))
                    return (self.last_action, False)
            if _valid_btn(self.ctx.la, BTN_ATTACK):
                mx, mz = _direction(self.ctx.px, self.ctx.py, self.ctx.ex, self.ctx.ey)
                self.last_action = (BTN_ATTACK, mx, mz, CENTER, CENTER, _target_for(self.ctx.la, BTN_ATTACK))
                return (self.last_action, False)

        if default_skill == "FARM":
            self.last_action = (BTN_MOVE, CENTER, 9, CENTER, CENTER, _target_for(self.ctx.la, BTN_MOVE))
            return (self.last_action, False)
        camp = self.ctx.camp()
        self.last_action = (BTN_MOVE, CENTER, 9 if camp < 0 else 7, CENTER, CENTER, _target_for(self.ctx.la, BTN_MOVE))
        return (self.last_action, False)

    def process_batch(self, info, llm_output):
        if not self.ctx.refresh(info):
            return [{"type": "error", "msg": "refresh failed"}]

        results = []
        lines = llm_output.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line: continue

            m = _re.match(r"@TOOL\s+(\w+)\(([^)]*)\)", line)
            if m:
                name = m.group(1)
                ps = m.group(2)
                params = {}
                for p in ps.split(","):
                    if "=" in p: k, v = p.split("=", 1); params[k.strip()] = v.strip()
                info["_self_id"] = self.ctx.sh
                result = _et(name, info, **params)
                results.append({"type": "tool", "name": name, "result": result})
                continue

            m = _re.match(r"@SKILL_OPEN\s+(\w+)", line)
            if m:
                sk = SKILL_REGISTRY.get(m.group(1))
                if sk:
                    results.append({"type": "skill_open", "name": m.group(1), "doc": sk.get_doc()})
                else:
                    results.append({"type": "error", "msg": f"unknown skill: {m.group(1)}"})
                continue

            m = _re.match(r"@SKILL_CALL\s+(\w+)\.(\w+)\(([^)]*)\)", line)
            if m:
                sn, fn, _ = m.group(1), m.group(2), m.group(3)
                sk = SKILL_REGISTRY.get(sn)
                if sk:
                    act = sk.execute(self.ctx, fn)
                    if isinstance(act, tuple):
                        self.last_action = act
                    results.append({"type": "skill_call", "skill": sn, "func": fn, "done": False})
                else:
                    results.append({"type": "error", "msg": f"unknown skill: {sn}"})
                continue

        return results
