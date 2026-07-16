import re, os, json, time, collections
from openai import OpenAI
from state_parser import parse_state
from strategy_executor import ProtocolExecutor
from skill_db import get_matchup
from skill_base import SKILL_REGISTRY

from memory import MemorySystem
from prompts import PROMPT_BASE, PROMPT_SYS1_PROTOCOL, EXPERIENCE_WARNING
import gamecore_data as gc
from trajectory import TRAJECTORY_DIR
traj_file = None
traj_path = os.path.join(TRAJECTORY_DIR, f"trajectory_{int(time.time())}.jsonl")

class MacroAgent:
    def __init__(self, name, self_hero_id, enemy_hero_id, api_key=None, base_url=None, model=None, memory_system=None):
        self.name = name
        self.self_hero_id = self_hero_id
        self.enemy_hero_id = enemy_hero_id
        self.executor = ProtocolExecutor(self_hero_id)
        api_key = api_key or os.environ.get("DASHSCOPE_API_KEY", "")
        base_url = base_url or os.environ.get("DASHSCOPE_BASE_URL", "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1")
        model = model or os.environ.get("MODEL_NAME", "deepseek-v4-flash")
        self.client = OpenAI(api_key=api_key, base_url=base_url) if api_key else None
        self.model = model
        self.history = collections.deque(maxlen=100)
        self.last_action_result = ""
        self.last_results_full = []
        self.last_thought = ""
        self._prev_frame = None
        self._prev_pb = None
        self._prev_pb_10 = None
        self._prev_data = None
        self.state_changes_str = ""
        self._call_count = 0
        self.memory = memory_system
        global traj_file, traj_path
        if not traj_file:
            traj_file = open(traj_path, "w", encoding="utf-8")

        import gamecore_data as gc

        self_name = gc.get_hero_en_name(self_hero_id)
        enemy_name = gc.get_hero_en_name(enemy_hero_id)
        self_type = gc.get_hero_role(self_hero_id)
        enemy_type = gc.get_hero_role(enemy_hero_id)

        def format_hero_skills(hid, name, role):
            lines = [f"  {name} ({role})"]
            skills = gc.get_hero_skill_info(hid)
            if not skills:
                lines.append("    (no detailed skill data from gamecore)")
            for slot in [1, 2, 3]:
                s = skills.get(slot)
                if s:
                    lines.append(f"    S{slot}: range={s['range']} shape={s['shape']} aim={s['release']} ep={s['ep_cost']}")
            return "\n".join(lines)

        hero_info_lines = [format_hero_skills(self_hero_id, self_name, self_type)]
        hero_info_lines.append("")
        hero_info_lines.append(format_hero_skills(enemy_hero_id, enemy_name, enemy_type))

        mu = get_matchup(self_hero_id, self.enemy_hero_id)
        if mu:
            hero_info_lines.append("")
            hero_info_lines.append("  Matchup:")
            for k in ["summary", "advantage", "danger", "tip_offense", "tip_defense", "power_spike", "key_skill"]:
                if k in mu:
                    hero_info_lines.append(f"    {k}: {mu[k]}")

        hero_info = "\n".join(hero_info_lines)

        skilldoc_lines = []
        for sk_name in sorted(SKILL_REGISTRY.keys()):
            sk = SKILL_REGISTRY[sk_name]
            doc = sk.get_doc()
            skilldoc_lines.append(doc)
        skilldoc = "\n\n".join(skilldoc_lines)

        if self.memory:
            exp = self.memory.retrieve(self_hero_id, enemy_hero_id)
            exp = exp if exp else "(no prior experience for this matchup)"
            exp += "\n\n" + EXPERIENCE_WARNING
        else:
            exp = "(memory system disabled)\n\n" + EXPERIENCE_WARNING

        self.system_prompt = PROMPT_BASE.format(
            self_name=self_name, enemy_name=enemy_name,
            self_type=self_type, enemy_type=enemy_type,
            self_hero_id=self_hero_id, enemy_hero_id=enemy_hero_id,
            skilldoc=skilldoc,
            hero_info=hero_info,
            experience=exp,
        ) + PROMPT_SYS1_PROTOCOL

    def on_game_end(self, outcome):
        global traj_file, traj_path
        if traj_file:
            traj_file.close()
            traj_file = None
        if self.memory:
            frame_count = 0
            if self.history:
                last = self.history[-1]
                frame_count = last.get("frame", 0)
            self.memory.reflect(
                self.self_hero_id, self.enemy_hero_id,
                outcome, frame_count,
                traj_path, self.client,
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
        if not self.history:
            return "(game start, no prior calls)"

        if self._prev_pb and pb_curr:
            for cid in [self.self_hero_id, self.enemy_hero_id]:
                cur = self._get_hero_data(pb_curr, cid)
                prev = self._get_hero_data(self._prev_pb, cid)
                if cur and prev:
                    hp_change = cur["hp"] - prev["hp"]
                    gold_change = cur["gold"] - prev["gold"]
                    if self.history:
                        last = self.history[-1]
                        if hp_change != 0 or gold_change != 0:
                            parts = []
                            if hp_change < 0:
                                parts.append(f"dmg_taken:{-hp_change}")
                            elif hp_change > 0:
                                parts.append(f"healed:{hp_change}")
                            if gold_change > 0:
                                parts.append(f"gold:+{gold_change}")
                            last["actual"] = ", ".join(parts) if parts else "no_change"

        sections = []
        entries = list(self.history)
        pos_self, pos_enemy = [], []
        gold_self_start = gold_self_end = gold_enemy_start = gold_enemy_end = 0
        tower_hp_start = tower_hp_end = {}
        kills = deaths = 0
        skill_count = {}
        prev_hp = {}

        for idx, e in enumerate(entries):
            d = e.get("data", {})
            if d.get("self_pos"): pos_self.append(d["self_pos"])
            if d.get("enemy_pos"): pos_enemy.append(d["enemy_pos"])
            gs = d.get("self_gold", 0); ge = d.get("enemy_gold", 0)
            if idx == 0: gold_self_start = gs; gold_enemy_start = ge
            gold_self_end = gs; gold_enemy_end = ge

            hp_s = d.get("self_hp", 0); hp_e = d.get("enemy_hp", 0)
            if prev_hp:
                if prev_hp.get("self", 0) > 0 and hp_s == 0: deaths += 1
                if prev_hp.get("enemy", 0) > 0 and hp_e == 0: kills += 1
            prev_hp = {"self": hp_s, "enemy": hp_e}

            act = e.get("action_name", "")
            if act:
                sk = act.split(".")[0] if "." in act else act
                skill_count[sk] = skill_count.get(sk, 0) + 1

            thp = e.get("tower_hp", {})
            if idx == 0: tower_hp_start = dict(thp)
            tower_hp_end = dict(thp)

        # TRENDS
        last_self_item = entries[-1].get("data", {}).get("self_item", "(none)") if entries else "(none)"
        last_enemy_item = entries[-1].get("data", {}).get("enemy_item", "(none)") if entries else "(none)"

        def _side_block(tag, pos_list, g_start, g_end, k, d, sk_count, item_str):
            lines = [f"--- {tag} ---"]
            if pos_list:
                lines.append("  PATH: " + " -> ".join([f"({x:.0f},{y:.0f})" for x, y in pos_list]))
            lines.append(f"  GOLD: {g_start} -> {g_end} (+{g_end-g_start})")
            lines.append(f"  ITEMS: {item_str}")
            lines.append(f"  KDA: {k}/{d}")
            if sk_count:
                lines.append("  SKILL: " + " | ".join([f"{sk}:{c}" for sk, c in sorted(sk_count.items())]))
            return "\n".join(lines)

        tower_parts = []
        for label in ["RED outer", "RED crystal", "BLUE outer", "BLUE crystal"]:
            s = tower_hp_start.get(label); e = tower_hp_end.get(label)
            if s is not None and e is not None and s != e:
                tower_parts.append(f"{label} {s:.0f}->{e:.0f}({e-s:+.0f})")

        trend_self = _side_block("SELF", pos_self, gold_self_start, gold_self_end, kills, deaths, skill_count, last_self_item)
        enemy_skill = {}
        trend_enemy = _side_block("ENEMY", pos_enemy, gold_enemy_start, gold_enemy_end, deaths, kills, enemy_skill, last_enemy_item)
        trend_text = trend_self + "\n\n" + trend_enemy
        if tower_parts:
            trend_text += "\n\nTOWER: " + " | ".join(tower_parts)
        sections.append("=== TRENDS (last {} frames) ===".format(len(entries)) + "\n" + trend_text)

        # DETAIL (all frames)
        detail_lines = []
        for e in entries:
            d = e.get("data", {})
            act_name = e.get("action_name", "none")
            raw = e.get("raw", "")
            actual = e.get("actual", "")
            segs = self._extract_think_segments(raw)
            sp = d.get("self_pos"); ep = d.get("enemy_pos")
            sh = d.get("self_hp", 0); smh = d.get("self_max_hp", 1)
            sg = d.get("self_gold", 0); eh = d.get("enemy_hp", 0)
            emh = d.get("enemy_max_hp", 1); eg = d.get("enemy_gold", 0)
            si = d.get("self_item", "(none)")
            ei = d.get("enemy_item", "(none)")

            detail_lines.append(f"[Frame {e['frame']}] {act_name}")
            if segs["review"]: detail_lines.append(f"  Review: {segs['review']}")
            if segs["check"]: detail_lines.append(f"  WhatIf check: {segs['check']}")
            if segs["situation"]: detail_lines.append(f"  Situation: {segs['situation']}")
            if segs["whatif_1"]: detail_lines.append(f"  WhatIf 1: {segs['whatif_1']}")
            if segs["whatif_2"]: detail_lines.append(f"  WhatIf 2: {segs['whatif_2']}")
            if segs["decision"]: detail_lines.append(f"  Decision: {segs['decision']}")
            detail_lines.append(f"  Action: {act_name}")

            # DELTA block
            hp_sd = d.get("delta_self_hp", ""); hp_ed = d.get("delta_enemy_hp", "")
            gd_s = d.get("delta_self_gold", ""); gd_e = d.get("delta_enemy_gold", "")
            td = d.get("delta_tower", ""); md = d.get("delta_minions", "")
            if hp_sd or hp_ed or gd_s or td:
                delta = ["  === DELTA ==="]
                s_d = []; e_d = []
                if hp_sd: s_d.append(f"HP: {hp_sd}")
                if gd_s: s_d.append(f"GOLD: {gd_s}")
                if md: s_d.append(f"MINIONS: {md}")
                s_d.append(f"ITEMS: {si}")
                if hp_ed: e_d.append(f"HP: {hp_ed}")
                if gd_e: e_d.append(f"GOLD: {gd_e}")
                e_d.append(f"ITEMS: {ei}")
                if td: s_d.append(f"TOWER: {td}")
                if s_d: delta.append("  --- SELF ---\n    " + "\n    ".join(s_d))
                if e_d: delta.append("  --- ENEMY ---\n    " + "\n    ".join(e_d))
                detail_lines.extend(delta)

            sp_str = f"({sp[0]:.0f},{sp[1]:.0f})" if sp else "(?,?)"
            ep_str = f"({ep[0]:.0f},{ep[1]:.0f})" if ep else "(?,?)"
            detail_lines.append(f"  SELF: @{sp_str}  HP {sh}/{smh}  G{sg}  ITEM: {si}")
            detail_lines.append(f"  ENEMY: @{ep_str}  HP {eh}/{emh}  G{eg}  ITEM: {ei}")
            detail_lines.append("")
        sections.append(f"=== DETAIL (all {len(entries)} frames) ===" + "\n" + "\n".join(detail_lines).rstrip())

        return "\n\n".join(sections)

    def decide(self, info):
        s = info[0] if isinstance(info, list) else info
        state_text, _ = parse_state(s, self.self_hero_id)

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

        try:
            resp = self.client.chat.completions.create(
                model=self.model, messages=messages,
                temperature=0.7, max_tokens=400, top_p=1,
            )
            msg = resp.choices[0].message
            content = (msg.content or "").strip()
            # extract think block for memory, strip from action
            think_match = re.search(r"<think>(.*?)</think>", content, re.DOTALL)
            self.last_thought = think_match.group(1).strip() if think_match else ""
            reply = re.sub(r"<think>.*?</think>\s*", "", content, flags=re.DOTALL)
            reply = reply.strip()
            if not reply:
                reply = (getattr(msg, "reasoning_content", None) or "").strip()
                self.last_thought = reply
        except Exception:
            return (2, 8, 8, 8, 8, 0), "[LLM err]"

        global traj_file

        results = self.executor.process_batch(s, reply)
        self.last_results_full = []
        for r in results:
            if r["type"] == "skill_call":
                result = r.get("result", {})
                if isinstance(result, dict):
                    lines = [f"@SKILL_CALL {r['skill']}.{r['func']}()"]
                    for k, v in result.items():
                        lines.append(f"  {k}: {v}")
                    self.last_results_full.append("\n".join(lines))
                else:
                    self.last_results_full.append(f"@SKILL_CALL {r['skill']}.{r['func']}() → {result}")
            elif r["type"] == "error":
                self.last_results_full.append(f"ERROR: {r['msg']}")

        raw_output = ""
        if self.last_thought:
            raw_output += f"<think>\n{self.last_thought}\n</think>"
        if reply:
            raw_output += f"\n<action>\n{reply}\n</action>"

        pb_curr = s.get("req_pb")
        frame_no = getattr(pb_curr, 'frame_no', 0) if pb_curr else 0

        # Build rich data for memory
        data = {}
        if pb_curr:
            for cid, tag in [(self.self_hero_id, "self"), (self.enemy_hero_id, "enemy")]:
                hd = self._get_hero_data(pb_curr, cid)
                if hd:
                    data[f"{tag}_pos"] = hd["pos"]
                    data[f"{tag}_hp"] = hd["hp"]
                    data[f"{tag}_max_hp"] = hd["max_hp"]
                    data[f"{tag}_gold"] = hd["gold"]
                    data[f"{tag}_level"] = hd["level"]
                    data[f"{tag}_item"] = hd["item"]

        tower_hp = {}
        for o in getattr(pb_curr, 'organ_list', []):
            cid = getattr(o, 'ConfigID', 0)
            label = {1: "BLUE outer", 2: "RED outer", 106: "BLUE crystal", 107: "RED crystal",
                     42: "BLUE inner", 43: "RED inner"}.get(cid)
            if label:
                tower_hp[label] = getattr(o, 'Hp', 0)
        data["tower_hp"] = tower_hp

        # Compute DELTA vs previous frame
        if self._prev_data is not None:
            def _diff(cur, prev_key, fmt="{}"):
                pv = self._prev_data.get(prev_key)
                if pv is not None and cur != pv:
                    return fmt.format(cur - pv)
                return ""
            data["delta_self_hp"] = _diff(data.get("self_hp"), "self_hp", "{:+.0f}")
            data["delta_enemy_hp"] = _diff(data.get("enemy_hp"), "enemy_hp", "{:+.0f}")
            data["delta_self_gold"] = _diff(data.get("self_gold"), "self_gold", "{:+.0f}")
            data["delta_enemy_gold"] = _diff(data.get("enemy_gold"), "enemy_gold", "{:+.0f}")
            tower_changes = []
            for label in ["RED outer", "RED crystal", "BLUE outer", "BLUE crystal"]:
                c = tower_hp.get(label)
                p = self._prev_data.get("tower_hp", {}).get(label)
                if c is not None and p is not None and c != p:
                    tower_changes.append(f"{label} {c:.0f}({c-p:+.0f})")
            data["delta_tower"] = ", ".join(tower_changes) if tower_changes else ""
            data["delta_minions"] = ""  # soldier count not tracked
        else:
            data["delta_self_hp"] = data["delta_enemy_hp"] = ""
            data["delta_self_gold"] = data["delta_enemy_gold"] = ""
            data["delta_tower"] = data["delta_minions"] = ""

        self._prev_data = dict(data)

        pred = self._parse_prediction(self.last_thought)
        act_name = self.last_results_full[0][:60] if self.last_results_full else "none"

        self.history.append({
            "frame": frame_no,
            "data": data,
            "prediction": pred,
            "actual": "",
            "action_name": act_name,
            "raw": raw_output.strip(),
        })

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

        if traj_file:
            traj_file.write(json.dumps({
                "step": str(time.time()),
                "system_prompt": self.system_prompt,
                "user_msg": user_msg,
                "llm_reply": reply,
                "parsed_results": "\n".join(self.last_results_full),
            }, ensure_ascii=False) + "\n")
            traj_file.flush()
        action, _ = self.executor.step(s)
        return action, f"batch: {reply[:80]}"
