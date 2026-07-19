import re, os, json, time, math
from openai import OpenAI
from state_parser import parse_state
from strategy_executor import ProtocolExecutor
from skill_base import SKILL_REGISTRY

from memory import MemorySystem
from prompts import PROMPT_SYS1_PROTOCOL, EXPERIENCE_WARNING, build_full_prompt
import gamecore_data as gc
from trajectory import TRAJECTORY_DIR

FRAME_BUFFER_MAX = 2000
BTN_NAMES = ["None1","None2","Move","Attack","Skill1","Skill2","Skill3","HealSkill","ChosenSkill","Recall","Skill4","EquipSkill"]
traj_file = None
traj_path = os.path.join(TRAJECTORY_DIR, f"trajectory_{int(time.time())}.jsonl")

class MacroAgent:
    def __init__(self, name, self_hero_id, enemy_hero_id, api_key=None, base_url=None, model=None, memory_system=None, max_tokens=400, thinking=True):
        self.name = name
        self.self_hero_id = self_hero_id
        self.enemy_hero_id = enemy_hero_id
        self.executor = ProtocolExecutor(self_hero_id)
        self.max_tokens = max_tokens
        self.thinking = thinking
        api_key = api_key or os.environ.get("DASHSCOPE_API_KEY", "")
        base_url = base_url or os.environ.get("DASHSCOPE_BASE_URL", "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1")
        model = model or os.environ.get("MODEL_NAME", "deepseek-v4-flash")
        self.client = OpenAI(api_key=api_key, base_url=base_url) if api_key else None
        self.model = model
        self.frame_buffer = []
        self.last_action_result = ""
        self.last_results_full = []
        self.last_thought = ""
        self._prev_pb = None
        self._prev_pb_10 = None
        self._prev_frame = None
        self.state_changes_str = ""
        self._call_count = 0
        self.memory = memory_system
        self._last_llm_entry = None
        self._last_raw_llm = ""
        self._last_skill_name = ""
        global traj_file, traj_path
        if not traj_file:
            traj_file = open(traj_path, "w", encoding="utf-8")

        exp = self.memory.retrieve(self_hero_id, enemy_hero_id) if self.memory else None
        self.system_prompt = build_full_prompt(self_hero_id, enemy_hero_id, PROMPT_SYS1_PROTOCOL, experience=exp)

    def push_frame(self, frame, action_name, action_tuple, delta, events, llm_data=None):
        """Record one frame into frame_buffer.
        delta = {self_hp, self_gold, self_pos, enemy_hp, enemy_gold, enemy_pos, tower}
        events = [{type, frame}]
        llm_data = {think_sections, reply, parsed_results} or None
        """
        entry = {"frame": frame, "action_name": action_name, "action": list(action_tuple),
                 "delta": delta, "events": events}
        if llm_data:
            entry["phase"] = "llm"
            entry["think"] = llm_data.get("think_sections", {})
            entry["llm_reply"] = llm_data.get("reply", "")
            entry["parsed_results"] = llm_data.get("parsed_results", "")
        else:
            entry["phase"] = "skill"
        self.frame_buffer.append(entry)
        if len(self.frame_buffer) > FRAME_BUFFER_MAX:
            self.frame_buffer = self.frame_buffer[-FRAME_BUFFER_MAX:]

    def on_game_end(self, outcome):
        global traj_file, traj_path
        if traj_file:
            traj_file.close()
            traj_file = None
        if self.memory:
            frame_count = self.frame_buffer[-1]["frame"] if self.frame_buffer else 0
            reflect_path = traj_path
            self.memory.reflect(
                self.self_hero_id, self.enemy_hero_id,
                outcome, frame_count,
                traj_path, self.client,
                reflect_path=reflect_path,
            )

    def _get_hero_data(self, pb, cid):
        for h in getattr(pb, 'hero_list', []):
            if getattr(h, 'config_id', 0) == cid:
                loc = getattr(h, 'location', None)
                px = loc.x if loc and hasattr(loc, 'x') else None
                py = loc.y if loc and hasattr(loc, 'y') else None
                equip_list = getattr(h, 'equipment', None) or []
                eq_names = []
                for eq in equip_list:
                    eq_id = getattr(eq, 'config_id', 0)
                    if eq_id:
                        eq_names.append(gc.get_equip_name(eq_id))
                return {
                    "hp": getattr(h, 'hp', 0), "max_hp": getattr(h, 'max_hp', 1),
                    "gold": getattr(h, 'money', 0), "level": getattr(h, 'level', 1),
                    "pos": (px, py) if px is not None else None,
                    "item": ", ".join(eq_names) if eq_names else "(none)",
                }
        return None

    def _parse_prediction(self, think_text):
        if not think_text:
            return ""
        for line in think_text.split("\n"):
            line = line.strip()
            if "WhatIf" in line and "→" in line:
                return line
        return ""

    def _extract_think_segments(self, think_text):
        segs = {"review": "", "check": "", "situation": "", "whatif_1": "", "whatif_2": "", "decision": ""}
        if not think_text:
            return segs
        for line in think_text.split("\n"):
            line = line.strip()
            if line.startswith("- Review:") or line.startswith("Review:"):
                segs["review"] = line.split(":", 1)[1].strip() if ":" in line else line
            elif line.startswith("- WhatIf check:") or line.startswith("WhatIf check:"):
                segs["check"] = line.split(":", 1)[1].strip() if ":" in line else line
            elif line.startswith("- Situation:") or line.startswith("Situation:"):
                segs["situation"] = line.split(":", 1)[1].strip() if ":" in line else line
            elif line.startswith("- WhatIf 1:") or line.startswith("WhatIf 1:"):
                segs["whatif_1"] = line.split(":", 1)[1].strip() if ":" in line else line
            elif line.startswith("- WhatIf 2:") or line.startswith("WhatIf 2:"):
                segs["whatif_2"] = line.split(":", 1)[1].strip() if ":" in line else line
            elif line.startswith("- Decision:") or line.startswith("Decision:"):
                segs["decision"] = line.split(":", 1)[1].strip() if ":" in line else line
        return segs

    def _build_memory_text(self, pb_curr):
        if not self.frame_buffer:
            return "(game start, no prior calls)"

        buf = self.frame_buffer
        llm_frames = sum(1 for f in buf if f.get("phase") == "llm")

        # TRENDS from frame_buffer
        pos_self = []; pos_enemy = []
        g_self_start = g_self_end = g_enemy_start = g_enemy_end = 0
        kills = deaths = 0
        skill_count = {}
        for idx, f in enumerate(buf):
            d = f.get("delta", {})
            if d.get("self_pos"):
                old = d["self_pos"]["old"]
                pos_self.append((d["self_pos"]["new"][0], d["self_pos"]["new"][1]))
            else:
                old = None
            gs = d.get("self_gold", {}).get("new", 0)
            ge = d.get("enemy_gold", {}).get("new", 0)
            if idx == 0:
                g_self_start = gs; g_enemy_start = ge
            g_self_end = gs; g_enemy_end = ge

            for ev in f.get("events", []):
                if ev["type"] == "kill": kills += 1
                if ev["type"] == "death": deaths += 1

            an = f.get("action_name", "")
            if an:
                sk = an.split(".")[0] if "." in an else an
                skill_count[sk] = skill_count.get(sk, 0) + 1

        def _side_block(tag, pl, gs, ge, k, d, skc):
            lines = [f"--- {tag} ---"]
            if pl:
                step = max(1, len(pl)//20)
                sample = pl[::step]
                lines.append("  PATH: " + " -> ".join([f"({x:.0f},{y:.0f})" for x, y in sample]))
            lines.append(f"  GOLD: {gs} -> {ge} (+{ge-gs})")
            lines.append(f"  KDA: {k}/{d}")
            if skc:
                lines.append("  SKILL: " + " | ".join([f"{sk}:{c}" for sk, c in sorted(skc.items())]))
            return "\n".join(lines)

        trend_self = _side_block("SELF", pos_self, g_self_start, g_self_end, kills, deaths, skill_count)
        trend_enemy = _side_block("ENEMY", pos_enemy, g_enemy_start, g_enemy_end, deaths, kills, {})
        trend_text = trend_self + "\n\n" + trend_enemy
        sections = [f"=== TRENDS (last {len(buf)} frames, {llm_frames} LLM calls) ===" + "\n" + trend_text]

        # EVENTS
        all_events = []
        for f in buf:
            all_events.extend(f.get("events", []))
        if all_events:
            ev_lines = ["=== EVENTS ==="]
            for ev in all_events:
                ev_lines.append(f"  {ev['type'].upper()} @{ev['frame']}")
            sections.append("\n".join(ev_lines))

        # DETAIL (every frame)
        detail_lines = []
        for f in buf:
            d = f.get("delta", {})
            an = f.get("action_name", "none")
            phase = f.get("phase", "skill")

            sfx = f" ({phase})" if phase == "skill" else ""
            detail_lines.append(f"[Frame {f['frame']}] {an}{sfx}")

            if phase == "llm":
                th = f.get("think", {})
                if th.get("review"): detail_lines.append(f"  Review: {th['review']}")
                if th.get("check"): detail_lines.append(f"  WhatIf check: {th['check']}")
                if th.get("situation"): detail_lines.append(f"  Situation: {th['situation']}")
                if th.get("whatif_1"): detail_lines.append(f"  WhatIf 1: {th['whatif_1']}")
                if th.get("whatif_2"): detail_lines.append(f"  WhatIf 2: {th['whatif_2']}")
                if th.get("decision"): detail_lines.append(f"  Decision: {th['decision']}")
                detail_lines.append(f"  Action: {an}")

            # DELTA (every frame)
            delta_lines = ["  === DELTA ==="]
            sd = []; ed = []
            dh = d.get("self_hp", {}); deh = d.get("enemy_hp", {})
            dg = d.get("self_gold", {}); deg = d.get("enemy_gold", {})
            dp = d.get("self_pos", {}); dep = d.get("enemy_pos", {})
            di = d.get("self_item", ""); dei = d.get("enemy_item", "")
            dt = d.get("tower", {})

            if dh: sd.append(f"HP: {dh.get('old',0):.0f}→{dh.get('new',0):.0f} ({dh.get('diff',0):+.0f})")
            if dg: sd.append(f"GOLD: {dg.get('old',0):.0f}→{dg.get('new',0):.0f} ({dg.get('diff',0):+.0f})")
            if dp: sd.append(f"POS: ({dp.get('old',[0,0])[0]:.0f},{dp.get('old',[0,0])[1]:.0f})→({dp.get('new',[0,0])[0]:.0f},{dp.get('new',[0,0])[1]:.0f})")
            sd.append(f"ITEMS: {di}")
            if deh: ed.append(f"HP: {deh.get('old',0):.0f}→{deh.get('new',0):.0f} ({deh.get('diff',0):+.0f})")
            if deg: ed.append(f"GOLD: {deg.get('old',0):.0f}→{deg.get('new',0):.0f} ({deg.get('diff',0):+.0f})")
            if dep: ed.append(f"POS: ({dep.get('old',[0,0])[0]:.0f},{dep.get('old',[0,0])[1]:.0f})→({dep.get('new',[0,0])[0]:.0f},{dep.get('new',[0,0])[1]:.0f})")
            ed.append(f"ITEMS: {dei}")
            if dt: sd.append(f"TOWER: {dt}")

            if sd: delta_lines.append("  --- SELF ---\n    " + "\n    ".join(sd))
            if ed: delta_lines.append("  --- ENEMY ---\n    " + "\n    ".join(ed))
            detail_lines.extend(delta_lines)

            # events in this frame
            for ev in f.get("events", []):
                detail_lines.append(f"  <<< {ev['type'].upper()} >>>")

            # state snapshot for LLM frames
            if phase == "llm":
                sh = d.get("self_hp", {}); eh = d.get("enemy_hp", {})
                sp_cur = d.get("self_pos", {}).get("new", (0,0))
                ep_cur = d.get("enemy_pos", {}).get("new", (0,0))
                s_hp = sh.get("new", "?") if sh else "?"
                e_hp = eh.get("new", "?") if eh else "?"
                s_g = d.get("self_gold", {}).get("new", "?")
                e_g = d.get("enemy_gold", {}).get("new", "?")
                detail_lines.append(f"  SELF: @({sp_cur[0]:.0f},{sp_cur[1]:.0f})  HP {s_hp}  G{s_g}  ITEM: {di}")
                detail_lines.append(f"  ENEMY: @({ep_cur[0]:.0f},{ep_cur[1]:.0f})  HP {e_hp}  G{e_g}  ITEM: {dei}")

            detail_lines.append("")

        sections.append("=== DETAIL (all {len(buf)} frames) ===" + "\n" + "\n".join(detail_lines).rstrip())
        return "\n\n".join(sections)

    def decide(self, info):
        s = info[0] if isinstance(info, list) else info
        state_text, _ = parse_state(s, self.self_hero_id)

        global traj_file

        # 1) concrete skill 还在执行中 → 不调 LLM，继续跑
        if self.executor._concrete_skill is not None:
            self._last_llm_entry = None
            action, _ = self.executor.step(s)
            return action, "skill_continue"

        if not self.client:
            return (2, 8, 8, 8, 8, 0), "[fallback]"

        pb_curr = s.get("req_pb")
        mem_text = self._build_memory_text(pb_curr)

        user_msg = f"{mem_text}\n\n{state_text}"
        if self.state_changes_str:
            user_msg += f"\n\n=== STATE CHANGES ===\n{self.state_changes_str}"
        if self.last_results_full:
            results_str = "\n".join(self.last_results_full)
            user_msg += f"\n\n=== LAST RESULTS ===\n{results_str}"
        else:
            user_msg += "\n\n=== LAST RESULTS ===\n(No Skill Called)"

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_msg},
        ]

        reply = ""
        error_info = ""
        try:
            kwargs = dict(model=self.model, messages=messages,
                          temperature=0.7, max_tokens=self.max_tokens, top_p=1)
            if not self.thinking:
                kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
            resp = self.client.chat.completions.create(**kwargs)
            msg = resp.choices[0].message
            content = (msg.content or "").strip()
            self._last_raw_llm = content
            # extract === THINK === and === ACTION === sections
            think_match = re.search(r"=== THINK ===\s*(.*?)(?:\s*=== ACTION ===|\s*$)", content, re.DOTALL)
            self.last_thought = think_match.group(1).strip() if think_match else ""
            action_match = re.search(r"=== ACTION ===\s*(.*)", content, re.DOTALL)
            reply = action_match.group(1).strip() if action_match else content.strip()
        except Exception as e:
            error_info = f"[LLM Error] {type(e).__name__}: {e}"
            print(error_info, flush=True)

        if error_info:
            self.executor._concrete_skill = None
            return (2, 8, 8, 8, 8, 0), error_info

        results = self.executor.process_batch(s, reply)
        if not results:
            error_info = "[Parse Error] no valid @SKILL_CALL in === ACTION === section"
            print(error_info, flush=True)
            self._last_llm_entry = {"error": error_info, "system_prompt": self.system_prompt,
                                     "user_msg": user_msg, "llm_reply": reply, "parsed_results": ""}
            self.executor._concrete_skill = None
            return (2, 8, 8, 8, 8, 0), error_info

        self.last_results_full = []
        for r in results:
            if r["type"] == "skill_call":
                self._last_skill_name = f"{r['skill']}.{r['func']}()"
                result = r.get("result", {})
                if isinstance(result, dict):
                    lines = [f"@SKILL_CALL {self._last_skill_name}"]
                    for k, v in result.items():
                        lines.append(f"  {k}: {v}")
                    self.last_results_full.append("\n".join(lines))
                else:
                    self.last_results_full.append(f"@SKILL_CALL {self._last_skill_name} → {result}")
            elif r["type"] == "error":
                self.last_results_full.append(f"ERROR: {r['msg']}")

        raw_output = ""
        if self.last_thought:
            raw_output += f"=== THINK ===\n{self.last_thought}\n"
        if reply:
            raw_output += f"=== ACTION ===\n{reply}"

        pb_curr = s.get("req_pb")
        frame_no = getattr(pb_curr, 'frame_no', 0) if pb_curr else 0

        state_changes = []
        self._call_count += 1
        ref_pb = self._prev_pb_10 if self._prev_pb_10 is not None else self._prev_pb
        if self._prev_frame is not None and ref_pb is not None and pb_curr is not None:
            def get_hp(pb, cid):
                for h in getattr(pb, 'hero_list', []):
                    if getattr(h, 'config_id', 0) == cid:
                        return getattr(h, 'hp', 0), getattr(h, 'max_hp', 1), getattr(h, 'money', 0), getattr(h, 'level', 1)
                return None, None, None, None
            for tag, cid in [("SELF", self.self_hero_id), ("ENEMY", self.enemy_hero_id)]:
                chp, cmhp, cg, clv = get_hp(pb_curr, cid)
                php, pmhp, pg, plv = get_hp(ref_pb, cid)
                if None not in (chp, php):
                    hp_diff = chp - php
                    g_diff = cg - pg
                    l_diff = clv - plv
                    parts = []
                    if hp_diff != 0:
                        parts.append(f"HP {chp}/{cmhp}({'+' if hp_diff>0 else ''}{hp_diff})")
                    if g_diff != 0:
                        parts.append(f"Gold {cg}({'+' if g_diff>0 else ''}{g_diff})")
                    if l_diff != 0:
                        parts.append(f"LV {clv}")
                    if parts:
                        state_changes.append(f"  {tag}: {' | '.join(parts)}")
            def tower_hp(pb, cid):
                for o in getattr(pb, 'organ_list', []):
                    if getattr(o, 'ConfigID', 0) == cid:
                        return getattr(o, 'Hp', 0), getattr(o, 'MaxHp', 0)
                return None, None
            for label, ocid in [("RED outer", 2), ("RED crystal", 107), ("BLUE outer", 1), ("BLUE crystal", 106)]:
                chp, cmhp = tower_hp(pb_curr, ocid)
                php, pmhp = tower_hp(ref_pb, ocid)
                if None not in (chp, php) and chp != php:
                    state_changes.append(f"  {label}: HP {chp}/{cmhp}({chp - php:+.0f})")
        self.state_changes_str = "\n".join(state_changes) if state_changes else ""

        # update snapshot for next STATE CHANGES comparison (every 10 calls)
        if self._call_count % 10 == 0:
            self._prev_pb_10 = pb_curr
        self._prev_frame = frame_no
        self._prev_pb = pb_curr

        self._last_llm_entry = {
            "system_prompt": self.system_prompt,
            "user_msg": user_msg,
            "llm_reply": reply,
            "parsed_results": "\n".join(self.last_results_full),
        }
        if error_info:
            self._last_llm_entry["error"] = error_info
        action, _ = self.executor.step(s)
        return action, f"batch: {reply[:80]}"
