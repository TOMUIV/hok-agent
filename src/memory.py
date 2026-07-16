import json, os, re, time, math
from openai import OpenAI

MEMORY_JSON = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                           "trajectories", "memory.json")
RETRY_MAX = 3


def _read_trajectory(path):
    entries = []
    if not os.path.isfile(path):
        return entries
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries


def _extract_key_events(traj_entries):
    events = []
    last_hp_self = last_hp_enemy = None
    last_gold_self = 0
    tower_had_zero = set()
    fired_minion_wave = False
    for idx, entry in enumerate(traj_entries):
        user_msg = entry.get("user_msg", "")
        m = re.search(r"=== FRAME (\d+)", user_msg) or re.search(r"Frame (\d+)", user_msg)
        frame = int(m.group(1)) if m else idx

        m_self_hp = re.search(r"\[SELF\].*?HP:([\d.]+)/([\d.]+)", user_msg)
        m_enemy_hp = re.search(r"\[ENEMY\].*?HP:([\d.]+)/([\d.]+)", user_msg)
        m_self_gold = re.search(r"\[SELF\].*?Gold:([\d.]+)", user_msg)

        hs = float(m_self_hp.group(1)) if m_self_hp else None
        he = float(m_enemy_hp.group(1)) if m_enemy_hp else None
        gs = int(float(m_self_gold.group(1))) if m_self_gold else last_gold_self

        if he is not None and last_hp_enemy is not None and he == 0 and last_hp_enemy > 0:
            events.append({"frame": frame, "type": "kill"})
        if hs is not None and last_hp_self is not None and hs == 0 and last_hp_self > 0:
            events.append({"frame": frame, "type": "death"})
        if last_gold_self > 0 and gs - last_gold_self >= 200:
            events.append({"frame": frame, "type": "gold_spike", "delta": gs - last_gold_self})
        if last_gold_self > 0 and gs - last_gold_self >= 1000:
            events.append({"frame": frame, "type": "power_spike", "delta": gs - last_gold_self})

        # Tower fall detection (debounced: fires once per tower)
        for ttype in ["outer", "inner", "crystal"]:
            pat = f"{ttype}=HP:0/"
            if pat in user_msg and ttype not in tower_had_zero:
                side = "?"
                if "--- TOWERS ---" in user_msg:
                    tow_sec = user_msg.split("--- TOWERS ---")[1].split("---")[0]
                    if "RED:" in tow_sec and pat in tow_sec.split("RED:")[1].split("|")[0] if "RED:" in tow_sec else "":
                        side = "RED"
                events.append({"frame": frame, "type": "tower_fall", "detail": f"{side} {ttype} destroyed"})
                tower_had_zero.add(ttype)

        # Minion wave detection (count visible > 6, fires once per game)
        minion_m = re.search(r"(\d+) visible", user_msg)
        if minion_m and not fired_minion_wave:
            cnt = int(minion_m.group(1))
            if cnt > 6:
                events.append({"frame": frame, "type": "minion_wave", "detail": f"{cnt} minions pushing"})
                fired_minion_wave = True

        if hs is not None:
            last_hp_self = hs
        if he is not None:
            last_hp_enemy = he
        last_gold_self = gs
    return events


def _f(pat, text, g=1, d=0):
    m = re.search(pat, text)
    return float(m.group(g)) if m else d


def _call_llm(sys_msg, user_msg, llm_client, model, max_tokens=800):
    try:
        resp = llm_client.chat.completions.create(
            model=model, messages=[{"role": "system", "content": sys_msg},
                                    {"role": "user", "content": user_msg}],
            temperature=0.5, max_tokens=max_tokens,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception:
        return ""


def _format_sys_prompt(hero_ai, hero_bot, extra_proto, experience):
    from hero_db import hero_name
    from prompts import PROMPT_BASE, EXPERIENCE_WARNING
    ai_name = hero_name(hero_ai)
    bot_name = hero_name(hero_bot)
    exp_text = experience if experience else "(no prior experience)"
    exp_text += "\n\n" + EXPERIENCE_WARNING
    return PROMPT_BASE.format(
        self_name=ai_name, enemy_name=bot_name,
        self_type="?", enemy_type="?",
        self_hero_id=hero_ai, enemy_hero_id=hero_bot,
        skilldoc="", hero_info="", experience=exp_text,
    ) + extra_proto


class MemorySystem:
    def __init__(self, path=None):
        self.path = path or MEMORY_JSON
        self.episodic = []
        self.semantic = []
        self._load()

    def _load(self):
        if not os.path.isfile(self.path):
            return
        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.episodic = data.get("episodic", [])
        self.semantic = data.get("semantic", [])

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"episodic": self.episodic, "semantic": self.semantic},
                      f, ensure_ascii=False, indent=2)

    def _get_humantic(self, hero_ai, hero_bot):
        from skill_db import get_matchup
        mu = get_matchup(hero_ai, hero_bot)
        if not mu:
            return ""
        return "\n".join(f"  {k}: {mu[k]}" for k in
                         ["summary", "advantage", "danger", "tip_offense",
                          "tip_defense", "power_spike", "key_skill"] if k in mu)

    def retrieve(self, hero_ai, hero_bot):
        sections = []
        hum = self._get_humantic(hero_ai, hero_bot)
        if hum:
            sections.append("--- HUMANTIC (human guide, reference only, do not score) ---\n" + hum)

        epi = [e for e in self.episodic if e.get("hero_ai") == hero_ai and e.get("hero_bot") == hero_bot]
        epi.sort(key=lambda e: e.get("timestamp", 0), reverse=True)
        if epi:
            sec = ["--- EPISODIC ---"]
            for e in epi[:5]:
                sup = e.get("supported", 0); ctr = e.get("contradicted", 0)
                sec.append(f"  {e.get('case_id','')} ({sup}/{sup+ctr} supported)")
                if e.get("lesson"): sec.append(f"    lesson: {e['lesson'][:200]}")
            sections.append("\n".join(sec))

        sem = [s for s in self.semantic if s.get("hero_ai") == hero_ai and s.get("hero_bot") == hero_bot]
        sem.sort(key=lambda s: s.get("supported", 0) / max(s.get("contradicted", 0) + s.get("supported", 0), 1), reverse=True)
        if sem:
            sec = ["--- SEMANTIC ---"]
            for s in sem[:5]:
                sup = s.get("supported", 0); ctr = s.get("contradicted", 0)
                sec.append(f"  {s.get('rule','')} ({sup}/{sup+ctr} supported)")
            sections.append("\n".join(sec))

        if not sections:
            return ""
        return "\n\n" + "\n\n".join(sections)

    def reflect(self, hero_ai, hero_bot, outcome, duration_frames,
                trajectory_path, llm_client=None):
        from hero_db import hero_name
        from prompts import PROMPT_SYS2_EVENT, PROMPT_SYS3_GLOBAL, PROMPT_AUDIT

        ai_name = hero_name(hero_ai)
        bot_name = hero_name(hero_bot)
        model = os.environ.get("MODEL_NAME", "deepseek-v4-flash")
        traj = _read_trajectory(trajectory_path)
        game_id = f"game_{int(time.time())}"
        experience = self.retrieve(hero_ai, hero_bot) or ""
        buffer = []  # list of dicts: {type, kind, content, game_id, source}

        # ── SYS2: Event Analysis ──
        sys2_sys = _format_sys_prompt(hero_ai, hero_bot, PROMPT_SYS2_EVENT, experience)
        for ev in _extract_key_events(traj):
            ev_type = ev["type"]
            ev_frame = ev["frame"]
            bef = self._slice_trajectory(traj, ev_frame - 100, ev_frame)
            aft = self._slice_trajectory(traj, ev_frame, ev_frame + 100)
            user = f"---\n=== EVENT: {ev_type.upper()} @{ev_frame} ===\n\n"
            user += f"--- BEFORE (F{ev_frame-100}~F{ev_frame}) ---\n" + bef + "\n\n"
            user += f"--- AFTER (F{ev_frame}~F{ev_frame+100}) ---\n" + aft
            reply = self._retry(sys2_sys, user, llm_client, model)
            items = _parse_episodic_semantic(reply, game_id, ev_type, ev_frame)
            buffer.extend(items)

        # ── SYS3: Global Review ──
        sys3_sys = _format_sys_prompt(hero_ai, hero_bot, PROMPT_SYS3_GLOBAL, experience)
        full_detail = self._slice_trajectory(traj, 0, len(traj) * 1000)
        user3 = f"Match: {ai_name} vs {bot_name}, {outcome}, {duration_frames} frames\n\n"
        user3 += "=== DETAIL (full game) ===\n" + full_detail
        reply3 = self._retry(sys3_sys, user3, llm_client, model)
        buffer.extend(_parse_episodic_semantic(reply3, game_id, "GLOBAL", 0))

        # ── AUDIT (always run, re-score both DB and BUFFER) ──
        kept = []
        audit_sys = _format_sys_prompt(hero_ai, hero_bot, PROMPT_AUDIT, experience)
        audit_user = f"Match: {ai_name} vs {bot_name}, {outcome}, {duration_frames} frames\n\n"
        audit_user += "=== BUFFER EXPERIENCE (candidates) ===\n"
        if buffer:
            for item in buffer:
                if item["kind"] == "episodic":
                    audit_user += f"--- Case: {item['case_id']} ---\n  Context: {item.get('context','')}\n  Lesson: {item.get('lesson','')}\n"
                else:
                    audit_user += f"- {item.get('rule','')}\n"
        else:
            audit_user += "(none)\n"
        reply4 = self._retry(audit_sys, audit_user, llm_client, model)
        if reply4:
            kept = _parse_audit_scores(reply4, buffer, self.episodic, self.semantic)

        # ── Merge kept BUFFER items to DB ──
        for item in kept:
            if item["kind"] == "episodic":
                item["hero_ai"] = hero_ai
                item["hero_bot"] = hero_bot
                item["hero_ai_name"] = ai_name
                item["hero_bot_name"] = bot_name
                item["timestamp"] = time.time()
                self.episodic.append(item)
            else:
                self._merge_semantic(hero_ai, hero_bot, item.get("rule", ""),
                                     hero_ai, hero_bot, outcome, game_id)
        self.save()

    def _retry(self, sys_msg, user_msg, llm_client, model):
        for attempt in range(RETRY_MAX):
            reply = _call_llm(sys_msg, user_msg, llm_client, model)
            if reply and len(reply) > 20:
                return reply
        return ""

    def _slice_trajectory(self, traj, f_start, f_end):
        lines = []
        for entry in traj:
            msg = entry.get("user_msg", "")
            m = re.search(r"Frame (\d+)", msg)
            f = int(m.group(1)) if m else 0
            if f_start <= f <= f_end:
                pr = entry.get("parsed_results", "")
                snippet = msg[:500] + ("\n  Action result: " + pr[:100] if pr else "")
                lines.append(f"[Frame {f}] {snippet[:300]}")
                if len(lines) > 300:
                    lines.append("... (truncated)")
                    break
        return "\n".join(lines)

    def _merge_semantic(self, hero_ai, hero_bot, rule_text, ai_id, bot_id, outcome, game_id):
        rule = rule_text.strip()
        if not rule or len(rule) < 10:
            return
        for sem in self.semantic:
            if sem.get("hero_ai") == hero_ai and sem.get("hero_bot") == hero_bot:
                if self._similar(sem.get("rule", ""), rule):
                    if outcome == "win":
                        sem["supported"] = sem.get("supported", 0) + 1
                    else:
                        sem["contradicted"] = sem.get("contradicted", 0) + 1
                    if game_id not in sem.get("source_games", []):
                        sem.setdefault("source_games", []).append(game_id)
                    sem["updated_at"] = time.time()
                    return
        self.semantic.append({
            "rule": rule, "hero_ai": hero_ai, "hero_bot": hero_bot,
            "supported": 1 if outcome == "win" else 0,
            "contradicted": 0 if outcome == "win" else 1,
            "source_games": [game_id],
            "created_at": time.time(), "updated_at": time.time(), "active": True,
        })

    def _similar(self, a, b):
        if not a or not b:
            return False
        if a == b:
            return True
        wa, wb = set(a.lower().split()), set(b.lower().split())
        return len(wa & wb) / max(len(wa), len(wb)) > 0.6

    def debug_summary(self):
        return {
            "episodic_count": len(self.episodic),
            "semantic_count": len(self.semantic),
            "recent_episodic": [
                {"id": e.get("case_id", "?"), "lesson": e.get("lesson", "")[:60],
                 "scored": f"{e.get('supported',0)}/{e.get('supported',0)+e.get('contradicted',0)}"}
                for e in sorted(self.episodic, key=lambda x: x.get("timestamp", 0), reverse=True)[:5]
            ],
            "top_semantic": [
                {"rule": s.get("rule", "")[:80], "supported": s.get("supported", 0),
                 "contradicted": s.get("contradicted", 0)}
                for s in sorted(self.semantic, key=lambda x: x.get("supported", 0) - x.get("contradicted", 0), reverse=True)[:5]
            ],
        }


def _parse_episodic_semantic(text, game_id, ev_type, ev_frame):
    items = []
    current_kind = None  # "ref_epi" | "new_epi" | "ref_sem" | "new_sem"
    current_case = {}
    for line in text.split("\n"):
        ls = line.strip()
        if ls == "=== REFERENCE EPISODIC ===":
            current_kind = "ref_epi"
        elif ls == "=== NEW EPISODIC ===":
            current_kind = "new_epi"
        elif ls == "=== REFERENCE SEMANTIC ===":
            current_kind = "ref_sem"
        elif ls == "=== NEW SEMANTIC ===":
            current_kind = "new_sem"
        elif ls.startswith("--- Case:") and current_kind in ("ref_epi", "new_epi"):
            if current_case.get("lesson"):
                items.append(current_case)
            current_case = {"kind": "episodic", "case_id": ls.replace("--- Case:", "").replace("---", "").strip(),
                            "game_id": game_id, "source_event": ev_type, "source_frame": ev_frame,
                            "supported": 0, "contradicted": 0, "context": "", "lesson": ""}
            if current_kind == "ref_epi":
                current_case["reference"] = True
        elif ls.startswith("Context:") and current_case.get("kind") == "episodic":
            current_case["context"] = (current_case.get("context", "") + " " + ls.split(":", 1)[1].strip()).strip()
        elif ls.startswith("Lesson:") and current_case.get("kind") == "episodic":
            current_case["lesson"] = (current_case.get("lesson", "") + " " + ls.split(":", 1)[1].strip()).strip()
        elif ls.startswith("- ") and current_kind in ("ref_sem", "new_sem"):
            item = {"kind": "semantic", "rule": ls[2:].strip(), "game_id": game_id,
                    "supported": 0, "contradicted": 0}
            if current_kind == "ref_sem":
                item["reference"] = True
            items.append(item)
    if current_case.get("lesson"):
        items.append(current_case)
    return items


def _parse_audit_scores(text, buffer, db_episodic, db_semantic):
    kept = []
    used_game_ids = set()
    current_section = None
    buffer_idx = -1
    last_db_match = None
    for line in text.split("\n"):
        ls = line.strip()
        if "BUFFER EXPERIENCE SCORES" in ls:
            current_section = "buffer"
            buffer_idx = -1
        elif "DB EXPERIENCE SCORES" in ls:
            current_section = "db"
            last_db_match = None

        if current_section == "db":
            if ls.startswith("--- Case:"):
                cid = ls.replace("--- Case:", "").replace("---", "").strip()
                last_db_match = ("episodic", cid)
            elif ls.startswith("- "):
                rule_text = ls[2:].strip()
                last_db_match = ("semantic", rule_text)
            elif "Score:" in ls:
                score = 1 if "Score: 1" in ls else (-1 if "Score: -1" in ls else 0)
                if last_db_match and score != 0:
                    kind, key = last_db_match
                    if kind == "episodic":
                        for item in db_episodic:
                            if item.get("case_id", "") == key:
                                if score == 1:
                                    item["supported"] = item.get("supported", 0) + 1
                                else:
                                    item["contradicted"] = item.get("contradicted", 0) + 1
                                break
                    else:
                        for item in db_semantic:
                            if item.get("rule", "") == key:
                                if score == 1:
                                    item["supported"] = item.get("supported", 0) + 1
                                else:
                                    item["contradicted"] = item.get("contradicted", 0) + 1
                                break
                last_db_match = None

        elif current_section == "buffer":
            if ls.startswith("--- Case:") or ls.startswith("- "):
                buffer_idx += 1
            if "Score: 1" in ls:
                if 0 <= buffer_idx < len(buffer):
                    item = buffer[buffer_idx]
                    if item.get("game_id") not in used_game_ids or not item.get("reference"):
                        kept.append(item)
                        used_game_ids.add(item.get("game_id", ""))
    return kept
