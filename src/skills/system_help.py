from skill_base import Skill, register_skill

@register_skill
class SYSTEM_HELP(Skill):
    name = "SYSTEM_HELP"
    description = "Review hero config, game rules, or available skills. Call when uncertain."
    when = "Unsure about hero config, rules, or what to do."
    until = "Info retrieved (one frame)."
    sub_func_returns = {
        "hero_config": "dict: action/status/config. status: ok.",
        "rules": "dict: action/status/rule_summary. status: ok.",
        "skills_doc": "dict: action/status/skills. status: ok.",
    }

    def func_hero_config(self, ctx):
        cfg = ctx.hero_config
        if not cfg: return {"action": "hero_config", "status": "error", "detail": "no hero config"}
        from skill_db import get_matchup
        lines = [f"Hero: {cfg.get('name', '?')} ({cfg.get('role', '?')})"]
        lines.append(f"Items: {', '.join(cfg.get('items', []))}")
        lines.append(f"Combo priority: {cfg.get('combo_priority', [])}")
        lines.append(f"Poke skill: {cfg.get('poke_skill', '?')}")
        lines.append(f"Escape skill: {cfg.get('escape_skill', 'None')}")
        for sn, desc in cfg.get("skill_descs", {}).items():
            lines.append(f"  S{sn}: {desc}")
        mu = get_matchup(ctx.self_hero_id, 0)
        if mu: lines.append(f"Matchup: {mu.get('summary', '')}")
        return {"action": "hero_config", "status": "ok", "config": "\n".join(lines)}

    def func_rules(self, ctx):
        from skill_db import SKILL_DB
        wave = SKILL_DB.get("wave", {})
        pos = SKILL_DB.get("positioning", {})
        mech = SKILL_DB.get("game_mechanics", {})
        rules = [
            "1v1 map, destroy enemy crystal to win",
            f"Minion wave: {wave.get('push', 'every 25s')}",
            f"Tower range: {pos.get('under_tower', 'X±2500')}",
            f"Gold: {mech.get('gold', 'last-hit full, else 40%')}",
            f"Recall: {mech.get('recall', 'channel 4s, interruptible')}",
            f"Heal: {mech.get('heal', 'heals self + nearby allies')}",
            f"Flash: {mech.get('flash', 'teleport short distance, CD 120s')}",
        ]
        return {"action": "rules", "status": "ok", "rule_summary": "\n".join(rules)}

    def func_skills_doc(self, ctx):
        from skill_base import SKILL_REGISTRY
        items = []
        for name in sorted(SKILL_REGISTRY.keys()):
            sk = SKILL_REGISTRY[name]
            items.append({"name": name, "description": sk.description, "when": sk.when, "until": sk.until})
        return {"action": "skills_doc", "status": "ok", "skills": items, "detail": f"{len(items)} skills"}
