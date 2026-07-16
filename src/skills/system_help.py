from skill_base import Skill, register_skill

@register_skill
class SYSTEM_HELP(Skill):
    name = "SYSTEM_HELP"
    description = "Review system prompt, game rules, available skills, hero config, and key bindings. Call this when uncertain about rules or available actions."
    when = "Unsure about what to do, need to review game rules, skills, or hero config."
    until = "Got the needed information."
    sub_func_returns = {
        "summary": "dict: action/status/detail. status: ok.",
        "rules": "dict: action/status/rule_summary. status: ok.",
        "skills_doc": "dict: action/status/skills/list. status: ok.",
        "hero_config": "dict: action/status/config. status: ok.",
    }

    def func_summary(self, ctx):
        """Overview of hero, game mode, and available skills."""
        cfg = ctx.hero_config
        name = cfg.get("name", "?") if cfg else "?"
        role = cfg.get("role", "?") if cfg else "?"
        lines = [f"Hero: {name} ({role})"]
        lines.append(f"Game mode: 1v1, map: 墨家机关道")
        lines.append(f"Win condition: destroy enemy crystal or more kills")
        from skill_base import SKILL_REGISTRY
        sk_names = sorted(SKILL_REGISTRY.keys())
        lines.append(f"Available macro skills ({len(sk_names)}): {', '.join(sk_names)}")
        return {"action": "summary", "status": "ok", "detail": "\n".join(lines)}

    def func_rules(self, ctx):
        """Game mode rules, map info, and win conditions."""
        from skill_db import SKILL_DB
        wave = SKILL_DB.get("wave", {})
        pos = SKILL_DB.get("positioning", {})
        mech = SKILL_DB.get("game_mechanics", {})
        rules = [
            "1v1 墨家机关道, 推掉敌方水晶获胜",
            f"兵线: {wave.get('push', '每25秒一波')}",
            f"塔下: {pos.get('under_tower', '塔攻击范围 X±2500')}",
            f"塔仇恨: {mech.get('tower_aggro', '塔优先攻击攻击己方英雄的单位')}",
            f"治疗: {mech.get('heal', '治疗术回复自身+附近队友HP')}",
            f"闪现: {mech.get('flash', '闪现瞬移一段距离, CD120秒')}",
            f"回城: {mech.get('recall', '回城引导4秒, 被打断需重新开始')}",
            f"金币: {mech.get('gold', '补刀全额, 未补刀40%')}",
        ]
        return {"action": "rules", "status": "ok", "rule_summary": "\n".join(rules)}

    def func_skills_doc(self, ctx):
        """List all available macro skills with descriptions."""
        from skill_base import SKILL_REGISTRY
        items = []
        for name in sorted(SKILL_REGISTRY.keys()):
            sk = SKILL_REGISTRY[name]
            funcs = sk.get_sub_functions()
            items.append({
                "name": name,
                "description": sk.description,
                "when": sk.when,
                "until": sk.until,
                "sub_functions": list(funcs.keys()),
            })
        return {"action": "skills_doc", "status": "ok", "skills": items, "detail": f"{len(items)} skills available"}

    def func_hero_config(self, ctx):
        """Current hero's skill configuration, items, and matchup tips."""
        cfg = ctx.hero_config
        if not cfg:
            return {"action": "hero_config", "status": "error", "detail": "no hero config"}
        from skill_db import get_matchup, SKILL_DB
        lines = [f"Hero: {cfg.get('name', '?')} ({cfg.get('role', '?')})"]
        lines.append(f"Items: {', '.join(cfg.get('items', []))}")
        lines.append(f"Combo priority: {cfg.get('combo_priority', [])}")
        lines.append(f"Poke skill: {cfg.get('poke_skill', '?')}")
        lines.append(f"Escape skill: {cfg.get('escape_skill', 'None')}")
        for sn, desc in cfg.get("skill_descs", {}).items():
            lines.append(f"  S{sn}: {desc}")
        pn = cfg.get("skill_passive_note", "")
        if pn:
            lines.append(f"  Passive: {pn}")
        mu = get_matchup(ctx.self_hero_id, 0)
        if mu:
            lines.append(f"Matchup: {mu.get('summary', '')}")
        return {"action": "hero_config", "status": "ok", "config": "\n".join(lines)}
