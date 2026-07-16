# HOK — Honor of Kings LLM Agent

THU AI实践基石. LLM Agent 玩王者荣耀 1v1. 纯 prompt 工程, 零训练.
架构基于 TiG + WIA + Reflexion 论文思想.

## Codebase Map

| Location | Status | Contents |
|----------|--------|----------|
| `src/` | Git-tracked | Agent, prompts, memory, skills, utilities |
| `gamecore/` | Gitignored | `gamecore-server.exe`, config data (proprietary) |
| `trajectories/` | JSONL logs + replay browser | Per-game `.jsonl` logs + `memory.json` + `serve.py` |
| `README.md` | Stale — do not trust | Outdated file structure and commands |
| `PLAN.md` | Research paper draft | Architecture reference |

## Commands

```bash
# dependencies (only what's actually used)
pip install openai numpy python-dotenv

# trajectory replay browser (stdlib http.server, no fastapi needed)
python trajectories/serve.py [port]   # defaults :23456

# single game (Docker container CWD: /hok_env/hok/hok1v1)
python /workspace/src/main_macro.py --steps 100 --hero-ai 199 --hero-bot 169
```

`.env` required:
```
DASHSCOPE_API_KEY=sk-...
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL_NAME=deepseek-v4-flash
```

## Entrypoints

| File | Role |
|------|------|
| `main_macro.py` | **Primary.** Creates AILab stubs, connects gamecore SDK, runs MacroAgent + MemorySystem game loop |
| `main.py` | **Older.** Simple prompt-based decision, no MacroAgent wrapper |

## File Map

| File | Role |
|------|------|
| `prompts.py` | PROMPT_BASE + 4 system PROTOCOLs + 9 few-shot examples |
| `macro_agent.py` | SYS1: frame-by-frame LLM decision, builds TRENDS/DETAIL/DELTA memory, parses `<think>`/`<action>`, calls executor, logs JSONL trajectory |
| `memory.py` | MemorySystem: `retrieve()` (pre-game experience) + `reflect()` (post-game SYS2→SYS3→AUDIT pipeline) |
| `state_parser.py` | Protobuf → text state + MACRO ACTIONS (AVAILABLE/BLOCKED per skill sub-function with reasons) |
| `strategy_executor.py` | `ProtocolExecutor`: `@SKILL_CALL Skill.func()` parser → 6-tuple actions via `SkillContext` helpers |
| `skill_base.py` | `SKILL_REGISTRY` global + `@register_skill` decorator + `Skill` base class |
| `skills/__init__.py` | **Autoloader:** `pkgutil.iter_modules` auto-imports all skill modules, registering them into `SKILL_REGISTRY` |
| `skills/farm.py` | FARM: `last_hit`, `move_to_lane`, `retreat_to_tower` |
| `skills/poke.py` | POKE: `aim_skill`, `basic_attack`, `reposition_back` |
| `skills/all_in.py` | ALL_IN: `combo_start`, `basic_attack`, `chase` |
| `skill_db.py` | HUMANTIC matchup data + combo/positioning/mechanics rules |
| `gamecore_data.py` | Reads gamecore config files (hero skills, roles, EN names) |
| `hero_db.py` | Hero ID → name mapping (106-522, cn + en) |
| `hero_skills.py` | Per-hero skill configs (poke_skill, combo_priority, ranges, types) + `ITEM_DB` |
| `trajectory.py` | JSONL step logger |
| `fix_ailab.py` | Minimal AILab stub fixer (run after container rebuild) |

## Architecture — Four Systems

| System | Name | Trigger | Output → |
|--------|------|---------|----------|
| SYS1 | Ingame Decision | Every frame | Direct 6-tuple execution |
| SYS2 | Event Analysis | Post-game × N events | BUFFER |
| SYS3 | Game Review | Post-game × 1 | BUFFER |
| AUDIT | Experience Audit | Post-game × 1 | BUFFER → DB |

Prompt hierarchy:
```
PROMPT_BASE
  ├── GAME RULES (83 lines, from gamecore config)
  ├── HERO INFO ({hero_info}, injected at runtime)
  ├── MACRO SKILLS ({skilldoc}, from SKILL_REGISTRY)
  └── EXPERIENCE ({experience}, memory.retrieve() → SYS)

SYS1 = BASE + PROTOCOL + 3 decision few-shot
SYS2 = BASE + EVENT_ANALYZE + 2 analysis few-shot
SYS3 = BASE + GLOBAL_ANALYZE + 2 analysis few-shot
AUDIT = BASE + AUDIT_PROTOCOL + 2 audit few-shot
```

LLM calls use OpenAI-compatible client (DashScope or token-plan). Retry up to 3x; fallback SYS1→random action, SYS2/SYS3→skip, AUDIT→score 0.

## Memory System

Three tiers. Same SELF/ENEMY symmetry throughout.

| Tier | Content | Persistence |
|------|---------|-------------|
| Working (ingame) | Last 100 frames, TRENDS + DETAIL + DELTA | Per-game only (`macro_agent.history`) |
| EPISODIC | Per-event Cases (Context + Lesson) + support/contradict counts | `trajectories/memory.json` |
| SEMANTIC | Reusable rules + support/contradict counts + source game IDs | `trajectories/memory.json` |

`retrieve()` → injected into SYS1/SYS2/SYS3/AUDIT `=== EXPERIENCE ===` section as HUMANTIC + EPISODIC (top 5) + SEMANTIC (top 5 by support ratio).

`reflect()` after each game: detect events → SYS2 × N events → SYS3 × 1 → AUDIT scoring → merge scores into DB. AUDIT scores: +1 keep, -1 discard, 0 discard.

## Known Code Traps

- **Skill cooldown**: `hero.skill[i].cooldown` (NOT `skill_cd_*`). Wrong field names silently return 0.
- **Action format**: `(button:0-11, move_x:1-15, move_z:1-15, skill_x:1-15, skill_z:1-15, target:0-7)`. All 4 coords **must be 1-15**.
- **Legal action**: flat `[12 buttons][16×4 coords][12×8 targets]`, target offset = `12 + 16*4 = 76`.
- **FOW**: `camp_visible[player_index] == false` → HP shows `FOW`, position is fake placeholder.
- **Map**: X axis lane. Blue (camp=0) at -X, Red (camp=1) at +X. Blue spawn ≈-32308, Red spawn ≈+100000.
- **Container CWD**: MUST be `/hok_env/hok/hok1v1` — SDK resolves `config.dat` relatively.
- **AILab stubs**: `main_macro.py` creates 11 inline stubs. Run `fix_ailab.py` after container rebuild.
- **Do NOT `docker rm -f hok`** — rebuilding re-installs all deps + AILab files.
- **Memory DB**: `trajectories/memory.json` — auto-loaded/saved by MemorySystem.
- **ITEM data**: Not available from protobuf — placeholder `(data pending)` throughout.
- **No test framework**: `test_*.py` are standalone scripts (not pytest), require running gamecore-server + HoK1v1 SDK.
- **Skills autoload**: Adding a new skill = create `skills/newskill.py` with `@register_skill` class; `__init__.py` auto-discovers it.

## Docker Deployment

```
Windows Host                          Docker (tencentailab/hok_env:latest)
gamecore-server.exe :23432 ──HTTP──→ Python SDK + Agent (CWD: /hok_env/hok/hok1v1)
sgame_simulator       ←──ZMQ :35500──
```

Ports mapped via `-p HOST:CONTAINER`, no `--network host`.

Start:
```powershell
Start-Process -WindowStyle Hidden "gamecore\gamecore\gamecore-server.exe" "server","--server-address :23432"
docker start hok
docker exec hok bash -c "cd /hok_env/hok/hok1v1 && python3 -u /workspace/src/main_macro.py --steps 100"
```

Stop:
```powershell
taskkill /f /im gamecore-server.exe
docker stop hok
```
