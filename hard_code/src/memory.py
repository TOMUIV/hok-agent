import json, os, re, time, math
from openai import OpenAI

MEMORY_JSON = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                           "trajectories", "memory.json")
RETRY_MAX = 3

# ── Semantic Rule Dedup (方案二：结构化字段匹配) ──
SKILL_NAMES = {'FARM', 'POKE', 'ALL_IN', 'RETREAT', 'DEFEND', 'KITE'}

ACTION_KEYWORDS = {
    'retreat': ['retreat', 'fall back', 'back off', 'fallback', 'recover', 'fountain'],
    'push':    ['push', 'clear', 'shove', 'advance', 'pressure', 'wave'],
    'harass':  ['harass', 'poke', 'harass'],
    'farm':    ['farm', 'last hit', 'move to lane', 'cs', 'minion', 'lane'],
    'all_in':  ['all_in', 'combo', 'engage', 'commit', 'fight', 'all-in'],
    'defend':  ['defend', 'guard', 'protect', 'safe'],
    'kite':    ['kite', 'reposition', 'position'],
}

THRESHOLD_ACTION = 10  # 阈值差值 ≤ 10 视为等价


def _norm_rule(text):
    t = text.lower().strip()
    t = re.sub(r'(\w+)\.(\w+)\(.*?\)', r'\1.\2', t)
    t = re.sub(r'\bcall\b', '', t)
    t = t.replace('→', '->')
    t = re.sub(r'\bbelow\b', '<', t).replace('<=', '<=')
    t = re.sub(r'\babove\b', '>', t).replace('>=', '>=')
    t = re.sub(r'\bless than\b', '<', t)
    t = re.sub(r'\bgreater than\b', '>', t)
    t = re.sub(r'\bno more than\b', '<=', t)
    t = re.sub(r'\bat least\b', '>=', t)
    t = re.sub(r'\bhp\b', 'hp', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def _cls_action(act_text):
    for act, kws in ACTION_KEYWORDS.items():
        if any(kw in act_text for kw in kws):
            return act
    return None


def _parse_rule(text):
    p = {'skill': None, 'action': None, 'cond_domain': None,
         'cond_op': None, 'cond_val': None}
    t = _norm_rule(text).lower().strip()
    parts = re.split(r'\s*->\s*', t, maxsplit=1)
    cond = parts[0] if len(parts) > 1 else t
    act  = parts[1] if len(parts) > 1 else ''

    for sn in SKILL_NAMES:
        if sn.lower() in t:
            p['skill'] = sn
            break
    if act:
        p['action'] = _cls_action(act)

    m = re.search(r'(hp|health)\s*(<|>|<=|>=|=)?\s*(\d+)', cond)
    if m:
        p['cond_domain'] = 'HP'
        p['cond_op'] = m.group(2) or '<'
        p['cond_val'] = int(m.group(3))
        return p
    m = re.search(r'distance\D*(<|>|<=|>=)\s*(\d+)', cond)
    if m:
        p['cond_domain'] = 'DISTANCE'
        p['cond_op'] = m.group(1)
        p['cond_val'] = int(m.group(2))
        return p
    m = re.search(r'between\s*(\d+)\s*and\s*(\d+)', cond)
    if m:
        p['cond_domain'] = 'DISTANCE'
        p['cond_op'] = 'BETWEEN'
        p['cond_val'] = (int(m.group(1)), int(m.group(2)))
        return p
    m = re.search(r'within\s*(\d+)', cond)
    if m:
        p['cond_domain'] = 'DISTANCE'
        p['cond_op'] = '<'
        p['cond_val'] = int(m.group(1))
        return p
    if re.search(r'(self_x|enemy_x)\s*[<>=]', cond) or 'past' in cond:
        p['cond_domain'] = 'POSITION'
        return p
    return p


def _field_match(pa, pb):
    if not pa or not pb:
        return 0.0
    total = 0.0
    hits  = 0.0

    skill_ok = pa['skill'] and pb['skill']
    action_ok = pa['action'] and pb['action']
    domain_ok = pa['cond_domain'] and pb['cond_domain']
    val_ok = pa['cond_val'] is not None and pb['cond_val'] is not None

    if skill_ok:
        total += 3
        if pa['skill'] == pb['skill']:
            hits += 3
    if action_ok:
        total += 3
        if pa['action'] == pb['action']:
            hits += 3
    if domain_ok:
        total += 1
        if pa['cond_domain'] == pb['cond_domain']:
            hits += 1
    if val_ok:
        total += 1.5
        if isinstance(pa['cond_val'], tuple) and isinstance(pb['cond_val'], tuple):
            d1 = abs(pa['cond_val'][0] - pb['cond_val'][0])
            d2 = abs(pa['cond_val'][1] - pb['cond_val'][1])
            if d1 <= THRESHOLD_ACTION and d2 <= THRESHOLD_ACTION:
                hits += 1.5
        else:
            if abs(pa['cond_val'] - pb['cond_val']) <= THRESHOLD_ACTION:
                hits += 1.5
    return hits / max(total, 1e-10)


def _read_trajectory(path):
    entries = []
    if not os.path.isfile(path):
        return entries
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    obj = json.loads(line)
                    if "frame" in obj:
                        entries.append(obj)
                except json.JSONDecodeError:
                    pass
    return entries


def _extract_key_events(traj_entries):
    events = []
    last_hp_self = last_hp_enemy = None
    last_gold_self = 0
    tower_had_zero = set()
    for entry in traj_entries:
        d = entry.get("delta", {})
        frame = entry.get("frame", 0)
        dh = d.get("self_hp", {}); deh = d.get("enemy_hp", {})
        dg = d.get("self_gold", {}); deg = d.get("enemy_gold", {})

        hs = dh.get("new") if dh else None
        he = deh.get("new") if deh else None
        gs = dg.get("new") if dg else last_gold_self

        if he is not None and last_hp_enemy is not None and he == 0 and last_hp_enemy > 0:
            events.append({"frame": frame, "type": "kill"})
        if hs is not None and last_hp_self is not None and hs == 0 and last_hp_self > 0:
            events.append({"frame": frame, "type": "death"})
        if last_gold_self > 0 and gs - last_gold_self >= 200:
            events.append({"frame": frame, "type": "gold_spike", "delta": gs - last_gold_self})
        if last_gold_self > 0 and gs - last_gold_self >= 1000:
            events.append({"frame": frame, "type": "power_spike", "delta": gs - last_gold_self})

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
    from prompts import build_full_prompt
    return build_full_prompt(hero_ai, hero_bot, extra_proto, experience=experience)


class MemorySystem:
    def __init__(self, path=None):
        self.path = path or MEMORY_JSON
        self.episodic = []
        self.semantic = []
        self._load()

    def _load(self):
        if not os.path.isfile(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.episodic = data.get("episodic", [])
            self.semantic = data.get("semantic", [])
        except (json.JSONDecodeError, Exception):
            self.episodic = []
            self.semantic = []

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"episodic": self.episodic, "semantic": self.semantic},
                      f, ensure_ascii=False, indent=2)

    def _similar_episodic(self, a, b):
        """比较两条情节记忆是否相似（使用_similar的语义判断）"""
        lesson_a = (a.get("lesson") or "").strip()
        lesson_b = (b.get("lesson") or "").strip()
        if not lesson_a or not lesson_b:
            return False
        return self._similar(lesson_a, lesson_b)

    def _dedup_episodic(self, new_item):
        """去重：找到相似的情节记忆，合并分数，返回True表示已合并"""
        for existing in self.episodic:
            if existing.get("hero_ai") != new_item.get("hero_ai"):
                continue
            if existing.get("hero_bot") != new_item.get("hero_bot"):
                continue
            if existing.get("source_event") != new_item.get("source_event"):
                continue
            if self._similar_episodic(existing, new_item):
                existing["supported"] = existing.get("supported", 0) + new_item.get("supported", 1)
                existing["contradicted"] = existing.get("contradicted", 0) + new_item.get("contradicted", 0)
                existing["updated_at"] = time.time()
                return True
        return False

    def _dedup_semantic(self, hero_ai, hero_bot, rule_text, ai_id, bot_id, outcome, game_id):
        """语义规则去重（原_merge_semantic逻辑+分数更新）"""
        self._merge_semantic(hero_ai, hero_bot, rule_text, ai_id, bot_id, outcome, game_id)

    def prune(self, min_supported=1, max_age_days=30):
        """策展清理：移除低质量/过期记忆"""
        now = time.time()
        cutoff = now - max_age_days * 86400

        before_epi = len(self.episodic)
        self.episodic = [
            e for e in self.episodic
            if e.get("supported", 0) + e.get("contradicted", 0) >= min_supported
            and e.get("timestamp", now) > cutoff
        ]
        after_epi = len(self.episodic)

        before_sem = len(self.semantic)
        self.semantic = [
            s for s in self.semantic
            if s.get("supported", 0) + s.get("contradicted", 0) >= min_supported
            and s.get("updated_at", now) > cutoff
        ]
        after_sem = len(self.semantic)

        return {"episodic_removed": before_epi - after_epi,
                "semantic_removed": before_sem - after_sem}

    def _get_humantic(self, hero_ai, hero_bot):
        from skill_db import get_matchup
        mu = get_matchup(hero_ai, hero_bot)
        if not mu:
            return ""
        return "\n".join(f"  {k}: {mu[k]}" for k in
                         ["summary", "advantage", "danger", "tip_offense",
                          "tip_defense", "power_spike", "key_skill"] if k in mu)

    @staticmethod
    def _importance_score(item):
        """事件重要性打分（Generative Agents 灵感）"""
        ev = item.get("source_event", "seed") if item.get("kind") == "episodic" else "semantic"
        importance = {
            "kill": 5, "death": 4, "tower_fall": 4,
            "power_spike": 3, "gold_spike": 2,
            "minion_wave": 1, "seed": 2, "GLOBAL": 3, "semantic": 2,
        }.get(ev, 2)
        # 支持率越高越重要
        sup = item.get("supported", 1)
        ctr = item.get("contradicted", 0)
        support_ratio = sup / max(sup + ctr, 1)
        return importance * (0.5 + 0.5 * support_ratio)

    @staticmethod
    def _recency_factor(timestamp):
        """时效性衰减（半衰期7天）"""
        if not timestamp:
            return 0.5
        days_old = (time.time() - timestamp) / 86400
        return 0.5 ** (days_old / 7)

    @staticmethod
    def _retrieval_score(item):
        """综合检索评分 = 重要性 × 时效性"""
        imp = MemorySystem._importance_score(item)
        rec = MemorySystem._recency_factor(item.get("timestamp"))
        return imp * rec

    def retrieve(self, hero_ai, hero_bot):
        sections = []
        hum = self._get_humantic(hero_ai, hero_bot)
        if hum:
            sections.append("--- HUMANTIC (human guide, reference only, do not score) ---\n" + hum)

        epi = [e for e in self.episodic
               if (e.get("hero_ai") == hero_ai and e.get("hero_bot") == hero_bot)
               or (e.get("hero_ai") is None and e.get("hero_bot") is None)]
        epi.sort(key=lambda e: e.get("timestamp", 0), reverse=True)
        if epi:
            sec = ["--- EPISODIC ---"]
            for e in epi[:5]:
                sup = e.get("supported", 0); ctr = e.get("contradicted", 0)
                sec.append(f"  {e.get('case_id','')} ({sup}/{sup+ctr} supported)")
                if e.get("lesson"): sec.append(f"    lesson: {e['lesson'][:200]}")
            sections.append("\n".join(sec))

        sem = [s for s in self.semantic
               if (s.get("hero_ai") == hero_ai and s.get("hero_bot") == hero_bot)
               or (s.get("hero_ai") is None and s.get("hero_bot") is None)]
        sem.sort(key=lambda s: s.get("supported", 0) / max(s.get("contradicted", 0) + s.get("supported", 0), 1), reverse=True)
        if sem:
            sec = ["--- SEMANTIC ---"]
            for s in sem[:10]:
                sup = s.get("supported", 0); ctr = s.get("contradicted", 0)
                sec.append(f"  {s.get('rule','')} ({sup}/{sup+ctr} supported)")
            sections.append("\n".join(sec))

        if not sections:
            return ""
        return "\n\n" + "\n\n".join(sections)

    def reflect(self, hero_ai, hero_bot, outcome, duration_frames,
                trajectory_path, llm_client=None, reflect_path=None):
        from hero_db import hero_name
        from prompts import PROMPT_SYS2_EVENT, PROMPT_SYS3_GLOBAL, PROMPT_AUDIT

        ai_name = hero_name(hero_ai)
        bot_name = hero_name(hero_bot)
        model = os.environ.get("MODEL_NAME", "deepseek-v4-flash")
        traj = _read_trajectory(trajectory_path)
        game_id = f"game_{int(time.time())}"
        experience = self.retrieve(hero_ai, hero_bot) or ""
        buffer = []  # list of dicts: {type, kind, content, game_id, source}

        def _log_reflect(phase, system_prompt, user_msg, llm_reply, **extra):
            if not reflect_path:
                return
            try:
                entry = {"phase": phase, "step": str(time.time()),
                         "system_prompt": system_prompt, "user_msg": user_msg,
                         "llm_reply": llm_reply, "parsed_results": ""}
                entry.update(extra)
                with open(reflect_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            except Exception:
                pass

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
            _log_reflect("SYS2", sys2_sys, user, reply, event_type=ev_type, event_frame=ev_frame)
            items = _parse_episodic_semantic(reply, game_id, ev_type, ev_frame)
            buffer.extend(items)

        # ── SYS3: Global Review ──
        sys3_sys = _format_sys_prompt(hero_ai, hero_bot, PROMPT_SYS3_GLOBAL, experience)
        full_detail = self._slice_trajectory(traj, 0, len(traj) * 1000)
        user3 = f"Match: {ai_name} vs {bot_name}, {outcome}, {duration_frames} frames\n\n"
        user3 += "=== DETAIL (full game) ===\n" + full_detail
        reply3 = self._retry(sys3_sys, user3, llm_client, model)
        _log_reflect("SYS3", sys3_sys, user3, reply3)
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
        _log_reflect("AUDIT", audit_sys, audit_user, reply4)
        if reply4:
            kept = _parse_audit_scores(reply4, buffer, self.episodic, self.semantic)

        # ── Merge kept BUFFER items to DB (带过去重) ──
        for item in kept:
            if item["kind"] == "episodic":
                item["hero_ai"] = hero_ai
                item["hero_bot"] = hero_bot
                item["hero_ai_name"] = ai_name
                item["hero_bot_name"] = bot_name
                item["timestamp"] = time.time()
                if not self._dedup_episodic(item):
                    self.episodic.append(item)
            else:
                self._dedup_semantic(hero_ai, hero_bot, item.get("rule", ""),
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
            f = entry.get("frame", 0)
            if not f_start <= f <= f_end:
                continue
            d = entry.get("delta", {})
            dh = d.get("self_hp", {}); deh = d.get("enemy_hp", {})
            dg = d.get("self_gold", {}); deg = d.get("enemy_gold", {})
            dp = d.get("self_pos", {}); dep = d.get("enemy_pos", {})
            ev = entry.get("events", [])
            ph = entry.get("phase", "?")
            llm = entry.get("llm_reply", "")
            snippet = f"[Frame {f}] {ph}"
            if dh: snippet += f" HP:{dh.get('old',0):.0f}->{dh.get('new',0):.0f}"
            if dg: snippet += f" G:{dg.get('old',0):.0f}->{dg.get('new',0):.0f}"
            if dp: snippet += f" POS:{dp.get('old',[0,0])[0]:.0f},{dp.get('old',[0,0])[1]:.0f}"
            if deh: snippet += f" | ENEMY HP:{deh.get('old',0):.0f}->{deh.get('new',0):.0f}"
            if ev: snippet += f" EV:{[e['type'] for e in ev]}"
            if llm: snippet += f" LLM:{llm[:100]}"
            lines.append(snippet)
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

    @staticmethod
    def _normalize(text):
        """预处理：小写、去标点、去停用词、术语归一化"""
        import re
        stops = {"the", "a", "an", "to", "in", "of", "for", "on", "and", "or",
                 "is", "are", "was", "were", "be", "been", "do", "does", "did",
                 "then", "than", "that", "this", "with", "at", "from", "as",
                 "when", "while", "not", "no", "but", "by", "if", "it", "its",
                 "so", "up", "all", "just", "very", "too", "also", "can", "get"}
        # 游戏术语归一化
        synonyms = {
            "ult": "ultimate", "ulti": "ultimate", "r": "ultimate",
            "hp": "health", "health": "health",
            "cd": "cooldown", "cooldown": "cooldown",
            "fow": "fog", "fog": "fog",
            "atk": "attack", "attack": "attack",
            "def": "defense", "defense": "defense",
            "move": "movement", "movement": "movement",
            "enemy": "enemy", "enemies": "enemy",
            "dmg": "damage", "damage": "damage",
            "burst": "burst", "nuke": "burst",
            "tower": "tower", "turret": "tower",
            "recall": "recall", "back": "recall", "retreat": "recall",
            "engage": "engage", "initiate": "engage",
            "poke": "poke", "harass": "poke",
        }
        text = re.sub(r"[^\w\s>]", " ", text.lower())
        tokens = text.split()
        # 同义词替换
        tokens = [synonyms.get(w, w) for w in tokens]
        # 停用词过滤
        tokens = [w for w in tokens if w not in stops and len(w) > 1]
        return tokens

    @staticmethod
    def _ngrams(tokens, n=3):
        """生成字符n-gram用于结构相似度"""
        text = " ".join(tokens)
        return {text[i:i+n] for i in range(len(text)-n+1)}

    @staticmethod
    def _extract_key_phrases(text):
        """提取关键动作模式: condition -> action / skill.func() 模式"""
        import re
        phrases = set()
        # 提取 SKILL_CALL 模式
        for m in re.finditer(r"[A-Z]+\.\w+\(\)", text):
            phrases.add(m.group())
        # 提取 -> 前后的关键短语
        parts = re.split(r"->|→", text)
        for p in parts:
            p = p.strip().lower()
            if len(p) > 3 and len(p) < 100:
                phrases.add(p)
        return phrases

    def _similar(self, a, b):
        """方案二：结构化字段匹配（归一化 + field_score）"""
        if not a or not b:
            return False
        if a == b:
            return True
        # Level 1: 归一化精确匹配
        na, nb = _norm_rule(a), _norm_rule(b)
        if na == nb:
            return True
        ca = na.split('->')[0].strip() if '->' in na else na
        cb = nb.split('->')[0].strip() if '->' in nb else nb
        if ca == cb:
            return True
        # Level 2: 结构化字段匹配
        pa, pb = _parse_rule(a), _parse_rule(b)
        return _field_match(pa, pb) >= 0.7

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
