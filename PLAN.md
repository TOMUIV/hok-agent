# HOK — Honor of Kings LLM Agent

> THU 人工智能学院 "AI实践基石" 课程项目  
> **成员**：杨坤鑫（提示词引擎、系统架构、实验平台）  
> **成员**：张腾达（记忆系统、技能迭代、评估分析）  
> **代码仓库**：https://github.com/TOMUIV/hok-agent  
> **选题报告**：`选题报告_v2生成版.docx`  
> **重要日期**：2026-07-17 现场展示  
> **最后更新**：2026-07-16

---

## 目录

1. [项目概述](#1-项目概述)
2. [研究动机与问题定义](#2-研究动机与问题定义)
3. [核心技术路线](#3-核心技术路线)
4. [四系统架构](#4-四系统架构)
5. [Prompt 体系](#5-prompt-体系)
6. [SYS1 — 局内决策](#6-sys1--局内决策)
7. [SYS2 — Event 分析](#7-sys2--event-分析)
8. [SYS3 — 全局复盘](#8-sys3--全局复盘)
9. [AUDIT — 经验审计](#9-audit--经验审计)
10. [记忆系统](#10-记忆系统)
11. [赛后数据流](#11-赛后数据流)
12. [EVENT 类型与检测规则](#12-event-类型与检测规则)
13. [SELF/ENEMY 对称结构](#13-selfenemy-对称结构)
14. [DELTA 六维度](#14-delta-六维度)
15. [HUMANTIC 人类指导](#15-humantic-人类指导)
16. [文件地图与实施状态](#16-文件地图与实施状态)
17. [文献综述引用](#17-文献综述引用)
18. [附录：Prompt 完整示例](#18-附录prompt-完整示例)

---

## 1. 项目概述

本项目在**零训练成本**（无需 GPU 集群、无需 RL 微调）的前提下，通过**提示词工程**、**分层知识库**与**智能体记忆系统**的协同设计，使纯文本大语言模型（LLM）在 MOBA 游戏（王者荣耀 1v1）中做出有效的高层决策。

核心假设：声明性知识（declarative knowledge）与过程性知识（procedural knowledge）之间的鸿沟可以通过精心设计的 prompt 结构 + 记忆系统来弥合，而不需要模型微调。

---

## 2. 研究动机与问题定义

### 现有路线的局限性

| 路线 | 代表工作 | 优势 | 劣势 |
|------|---------|------|------|
| RL 微调 | TiG (GRPO, 8×H20 GPU) | 效果好，Qwen-3-14B 达 90.91% | 需要大规模 GPU，不可复现 |
| 提示词优化 | BPO, PROMST, Plum | 零训练成本 | 仅优化提示措辞，不改决策框架 |
| 纯文本 Agent | 本工作 | 零训练，完全可复现 | 需要精心设计 prompt + 记忆系统 |

### 本研究定位

填补两条路线之间的空白：在**零训练成本**的约束下，通过**分层 prompt 架构 + 智能体记忆系统 + 人类先验知识**的协同，探索纯文本 LLM 在 MOBA 游戏中的能力上限。

---

## 3. 核心技术路线

1. **LLM 宏观决策 + 代码战术执行**：LLM 输出 `@SKILL_CALL` 高层指令，`strategy_executor.py` 转换为 6-tuple 低层动作
2. **四系统流水线**：
   - SYS1：局内每帧决策（System 1）
   - SYS2：赛后 event 级分析（System 2，每个 event 一次）
   - SYS3：赛后全局复盘（System 2，每局一次）
   - AUDIT：经验审计，校验 BUFFER vs DB
3. **继承式 Prompt 设计**：共享 `PROMPT_BASE`，各系统追加专属 PROTOCOL
4. **Reflexion 范式记忆**：赛后反思 → 提炼 EPISODIC + SEMANTIC → 注入下一局 SYS
5. **收敛机制**：agreement ratio = supported / (supported + contradicted)，自然收敛

---

## 4. 四系统架构

| 系统 | 内部名 | 触发 | 输入 | 产出 → |
|------|--------|------|------|--------|
| SYS1 | Ingame Decision | 每帧一次 | 当前帧状态 | 直接执行 6-tuple |
| SYS2 | Event Analysis | 赛后, 每个 event 一次 | BEFORE(100帧) + AFTER(100帧) | BUFFER |
| SYS3 | Game Review | 赛后, 1 次 | 全局全帧 DETAIL | BUFFER |
| AUDIT | Experience Audit | 赛后, 1 次 | DB + BUFFER + 全局 DETAIL | Score 1→DB, 0/-1→丢弃 |

每个 SYS 的 SYSTEM 消息体都包含 `=== EXPERIENCE ===` 节（运行时 `memory.retrieve()` 拼接）。

---

## 5. Prompt 体系

```
PROMPT_BASE (prompts.py)
  ├── GAME RULES (83 lines)
  │     ├── GAME MODE — 场景/阵营/技能槽/冷却范围
  │     ├── MAP CONFIG — 地图长度/中心/视野距离/参考点
  │     ├── HERO STAT RANGES — 等级/HP/EP/ATK/DEF/金钱/KDA 范围
  │     ├── STRUCTURES — 6 座建筑坐标/HP
  │     ├── SOLDIERS — 类型/属性范围
  │     ├── MONSTERS — 类型/ID/属性范围
  │     ├── KEY TIMING — 兵线出生/推塔帧常量
  │     └── SPRING — 泉水位置/恢复范围
  │
  ├── HERO INFO ({hero_info}, 运行时注入)
  │     ├── 己方英雄技能数据
  │     ├── 敌方英雄技能数据
  │     └── HUMANTIC match-up 数据（从 skill_db.py）
  │
  ├── MACRO SKILLS ({skilldoc}, 运行时注入)
  │     ├── FARM: last_hit / move_to_lane / retreat_to_tower
  │     ├── POKE: aim_skill / basic_attack / reposition_back
  │     └── ALL_IN: combo_start / basic_attack / chase
  │
  └── EXPERIENCE ({experience}, 运行时 memory.retrieve() 注入)
        ├── --- HUMANTIC (reference only, do not score) ---
        ├── --- EPISODIC --- 每条 Case (Context + Lesson)
        └── --- SEMANTIC --- 每条规则
        + WARNING: Some rules may have few tests, judge carefully.

SYS1 = BASE + PROTOCOL + 3 decision few-shot
SYS2 = BASE + EVENT_ANALYZE PROTOCOL + 2 analysis few-shot
SYS3 = BASE + GLOBAL_ANALYZE PROTOCOL + 2 analysis few-shot
AUDIT = BASE + AUDIT PROTOCOL + 2 audit few-shot
```

### EXPERIENCE 警告文本

```
Some rules may have few tests, high ratio by chance — judge carefully.
Human guide (HUMANTIC) is reference only, do NOT score it.
```

---

## 6. SYS1 — 局内决策

### SYSTEM Message

```
PROMPT_BASE + === EXPERIENCE === + === PROTOCOL === + 3 FEW-SHOTs
```

### PROTOCOL 要求

```
<think>
  - Review: what happened in the last few frames (HP changes, skills used, enemy movement)
  - WhatIf check: was the previous frame's WhatIf prediction correct? why or why not?
  - Situation: current hero stats, tower status, minion wave, positioning, FOW state
  - WhatIf: evaluate 2 candidate actions, predict outcomes for each
  - Decision: which skill(s) to call and why
</think>
<action>
  @SKILL_CALL <SKILL>.<func>()
  @SKILL_CALL <SKILL>.<func>()  # Multiple allowed
</action>
```

### USER Message — MEMORY 结构

```
=== TRENDS (last N frames) ===
--- SELF ---
  PATH: (100帧坐标序列, 格式 "(x1,y1) -> (x2,y2) -> ...")
  GOLD: start -> end (+diff)
  ITEM: (data pending)
  KDA: k/d
  SKILL: FARM:x POKE:y ALL_IN:z
--- ENEMY ---
  PATH: ...
  GOLD: ...
  ITEM: (data pending)
  KDA: ...
  SKILL: ...

=== EVENTS ===
  KILL @F420
  TOWER_FALL @F650

=== DETAIL (all N frames) ===
[Frame N] action_name
  Review: ...
  WhatIf check: ...
  Situation: ...
  WhatIf 1: ...
  WhatIf 2: ...
  Decision: ...
  Action: @SKILL_CALL ...

  === DELTA (since last call, ~X frames) ===
  --- SELF ---
    HP: ±diff (old→new)
    GOLD: ±diff (old→new)
    TOWER: ...
    MINIONS: ...
    ITEM: ...
  --- ENEMY ---
    HP: ±diff (old→new)
    GOLD: ±diff (old→new)
    TOWER: ...
    MINIONS: ...
    ITEM: ...

  SELF: @(x,y) HP h/m Gg ITEM: ...
  ENEMY: @(x,y) HP h/m Gg ITEM: ...

=== MACRO ACTIONS ===
  AVAILABLE:
    FARM.last_hit()
    FARM.move_to_lane()
    ...
  BLOCKED:
    POKE.aim_skill(): Skill1 on cooldown (3.2s)
    ALL_IN.combo_start(): enemy out of range
```

### MEMORY 数据字段

每帧 history entry 存储以下字段：

| 字段 | 来源 | 用途 |
|------|------|------|
| `frame` | protobuf.frame_no | 帧号 |
| `data.self_pos` | hero.location | TRENDS PATH + DETAIL 位置 |
| `data.self_hp` / `data.self_max_hp` | hero.hp / hero.max_hp | TRENDS + DETAIL + DELTA |
| `data.self_gold` | hero.money | TRENDS + DELTA |
| `data.self_item` | (data pending) | TRENDS + DETAIL + DELTA |
| `data.enemy_*` | 同上 | 对称 ENEMY 结构 |
| `data.tower_hp` | organ.Hp | TRENDS TOWER + DELTA |
| `data.delta_*` | 当前帧 - 上一帧 | DELTA 段 |
| `prediction` | <think> 中 WhatIf 行 | DETAIL 预测展示 |
| `actual` | 下帧状态差值 | DETAIL 实际展示 |
| `action_name` | parsed_results | DETAIL 动作展示 |

### SELF/ENEMY 对称结构

TRENDS、DELTA、DETAIL 中 SELF 和 ENEMY 完全对称：

```
--- SELF ---          --- ENEMY ---
  PATH: ...             PATH: ...
  GOLD: ...             GOLD: ...
  ITEM: ...             ITEM: ...
  KDA: k/d              KDA: k/d
  SKILL: ...            SKILL: ...
```

---

## 7. SYS2 — Event 分析

### SYSTEM Message

```
PROMPT_BASE + === EXPERIENCE === + === EVENT ANALYZE PROTOCOL === + 2 analysis FEW-SHOTs
```

### USER Message

```
---
=== EVENT: KILL @F420 ===

--- BEFORE (F320-F420) ---
(100 帧 DETAIL，每帧含5段+DELTA+状态)

--- AFTER (F420-F520) ---
(100 帧 DETAIL)
```

### ASSISTANT 输出格式

```
=== REFERENCE EPISODIC ===
--- Case: {game_id} / {event_type} @{frame} ---
  Context: (已有经验的 Context)
  Lesson: (已有经验的 Lesson)

=== NEW EPISODIC ===
--- Case: {game_id} / {event_type} @{frame} ---
  Context: (具体场景，SKILL CALL 自然融入)
  Lesson: (可复用规则，含 SKILL CALL)

=== REFERENCE SEMANTIC ===
- (已有规则的原文)

=== NEW SEMANTIC ===
- (新规则，含 SKILL CALL)
```

不是必须输出所有节。没有新发现可跳过。

### EPISODIC 格式要求

| 部分 | 要求 |
|------|------|
| Context | 聚焦一个具体场景，不写"整局经济领先"这类概括 |
| Context | SKILL CALL 自然融入叙述（"先用 POKE.aim_skill() 消耗再 ALL_IN.combo_start() 击杀"） |
| Lesson | 必须包含具体 SKILL.FUNC() |
| Lesson | 可复用，去上下文 |

### SEMANTIC 格式要求

| 要求 | 反例 | 正例 |
|------|------|------|
| 必须包含 SKILL CALL | "运营兵线" | "击杀后 FARM.move_to_lane() 把线推进塔" |
| 必须具体到操作 | "注意发育" | "敌人<30%HP -> ALL_IN.combo_start()" |

---

## 8. SYS3 — 全局复盘

### SYSTEM Message

```
PROMPT_BASE + === EXPERIENCE === + === GAME REVIEW PROTOCOL === + 2 analysis FEW-SHOTs
```

### USER Message

```
=== MATCH ===
{game_id}, {hero_ai} vs {hero_bot}, {outcome}, {total_frames} frames

=== TRENDS ===
(SELF/ENEMY 对称)

=== DETAIL ===
(全帧, 同 SYS1)
```

### ASSISTANT 输出格式

同 SYS2。结构完全一致——REFERENCE EPISODIC / NEW EPISODIC / REFERENCE SEMANTIC / NEW SEMANTIC。

---

## 9. AUDIT — 经验审计

### SYSTEM Message

```
PROMPT_BASE + === EXPERIENCE === + === EXPERIENCE AUDIT PROTOCOL === + 2 audit FEW-SHOTs
```

额外强调：
- HUMANTIC 不参与评分
- 不关心 BUFFER 来源，只对内容本身评分
- 每一条都必须评分，不能跳过

### USER Message

```
=== MATCH ===
{game_id}, heroes, outcome, frames

=== TRENDS ===
(同 SYS3)

=== DETAIL ===
(同 SYS3)

=== BUFFER EXPERIENCE (candidates) ===
=== NEW EPISODIC ===
--- Case: ... ---
  Context: ...
  Lesson: ...
=== NEW SEMANTIC ===
- rule
```

### ASSISTANT 输出格式

```
=== DB EXPERIENCE SCORES ===
--- EPISODIC ---
--- Case: {game_id} / {event_type} @{frame} ---
  Context: ...
  Lesson: ...
  Score: 1
  Score reason: this game confirmed the pattern.

--- SEMANTIC ---
- rule
  Score: -1
  Score reason: contradicts this game's outcome.

=== BUFFER EXPERIENCE SCORES ===
=== NEW EPISODIC ===
--- Case: ... ---
  Context: ...
  Lesson: ...
  Score: 1
  Score reason: ...

=== NEW SEMANTIC ===
- rule
  Score: 0
  Score reason: not tested in this game.
```

### 评分决策

| Score | 含义 | 动作 |
|-------|------|------|
| 1 | 验证 | → KEEP → similarity check → DB |
| -1 | 证伪 | → DISCARD |
| 0 | 未测试 | → DISCARD |

---

## 10. 记忆系统

### 存储结构

文件：`trajectories/memory.json`

```json
{
  "episodic": [
    {
      "case_id": "game_20260717_154200 / KILL @F420",
      "hero_ai": 199,
      "hero_bot": 169,
      "hero_ai_name": "公孙离",
      "hero_bot_name": "后羿",
      "context": "enemy 30%HP under tower, didn't recall. POKE.aim_skill() then ALL_IN.combo_start() killed.",
      "lesson": "when enemy <30%HP + ult up -> POKE.aim_skill() then ALL_IN.combo_start()",
      "game_id": "game_20260717_154200",
      "source_event": "kill",
      "source_frame": 420,
      "supported": 3,
      "contradicted": 1,
      "timestamp": 1784118420.0,
      "reference": false
    }
  ],
  "semantic": [
    {
      "rule": "enemy <30%HP + ult up -> ALL_IN.combo_start()",
      "hero_ai": 199,
      "hero_bot": 169,
      "supported": 5,
      "contradicted": 1,
      "source_games": ["game_20260717_154200", "game_20260717_152100"],
      "created_at": 1784118420.0,
      "updated_at": 1784118420.0,
      "active": true
    }
  ]
}
```

### 三层记忆

| 层级 | 内容 | 生命周期 | 持久化 |
|------|------|----------|--------|
| **Working Memory** | 最近 100 次 LLM 调用，含 TRENDS + DETAIL + DELTA | 单局 | 不持久（macro_agent.history） |
| **Episodic Memory** | 每 event 的 Case（Context + Lesson），带 supported/contradicted | 跨局 | trajectories/memory.json |
| **Semantic Memory** | 去上下文的规则，带 supported/contradicted | 跨局 | trajectories/memory.json |

### 检索（`retrieve()`）

```
retrieve(hero_ai, hero_bot):
  1. HUMANTIC: 从 skill_db.get_matchup() 取 match-up 人类指导
  2. EPISODIC: 按 (hero_ai, hero_bot) 过滤，按 timestamp 降序，全量返回
  3. SEMANTIC: 按 (hero_ai, hero_bot) 过滤，按 agreement ratio 降序，全量返回
```

### 收敛机制

| 机制 | 触发 | 动作 |
|------|------|------|
| AUDIT 评分 | 每局赛后 | 每条 Score=1 → supported+=1, Score=-1 → contradicted+=1 |
| 检索排序 | 每次 retrieve | 按 agreement ratio = supported/(supported+contradicted) 降序 |
| 自然淘汰 | 持续 contradicted | agreement ratio 趋近 0，检索时排名垫底 |
| 文本相似度合并 | `_merge_semantic()` | Jaccard 词重叠 > 60% 视为相同规则，合并计数 |
| REFERENCE 机制 | SYS2/SYS3 输出 | LLM 发现已有经验覆盖时走 REFERENCE 节，不重复产出 |

---

## 11. 赛后数据流

```
trajectory JSONL
  │
  ├── detect events()
  │     └── 返回 [{type, frame, delta?}, ...]
  │
  ├── for each event:
  │     └── SYS2 (PROMPT_BASE + EXPERIENCE + EVENT_ANALYZE)
  │           └── BUFFER[] += NEW_EPISODIC + NEW_SEMANTIC
  │
  ├── SYS3 × 1
  │     └── (PROMPT_BASE + EXPERIENCE + GLOBAL_ANALYZE)
  │           └── BUFFER[] += ...
  │
  ├── AUDIT × 1
  │     └── (PROMPT_BASE + EXPERIENCE + AUDIT_PROTOCOL)
  │           └── for each item:
  │                 Score=1 → KEEP
  │                 Score=0/-1 → discard
  │
  └── SimilarityCheck (teammate stub)
        └── dedup merge → write memory.json
```

### 统一设施

| 设施 | 行为 |
|------|------|
| **Retry** | `_retry(max_retries=3)` 共享所有 LLM 调用。fallback: SYS1 随机动作，SYS2/SYS3 跳过该条产出，AUDIT 该条记为 0 |
| **Parser** | 每个 SYS 对应结构化解析器：`_parse_episodic_semantic()` / `_parse_audit_scores()` |
| **EXPERIENCE 注入** | `memory.retrieve()` 格式化 → `PROMPT_BASE` 的 `{experience}` 占位符拼接 |

---

## 12. EVENT 类型与检测规则

| event | code field | 检测条件 | 代码行 |
|-------|-----------|---------|--------|
| `kill` | `type: "kill"` | 敌方 HP 从 >0 变 0 | `_extract_key_events` |
| `death` | `type: "death"` | 己方 HP 从 >0 变 0 | 同上 |
| `gold_spike` | `type: "gold_spike", delta: N` | 单帧金币变化 ≥ 200 | 同上 |
| `power_spike` | `type: "power_spike", delta: N` | 单帧金币变化 ≥ 1000 | 同上 |
| `tower_fall` | `type: "tower_fall"` | 塔 HP 从 >0 变 0 | ❌ 待实现 |
| `minion_wave` | `type: "minion_wave"` | 场上敌方小兵数 > 6 | ❌ 待实现 |

### EVENT 在 MEMORY 中的呈现

DETAIL 的每帧末尾不标注。EVENT 统一在 MEMORY 的 `=== EVENTS ===` 节：

```
=== EVENTS ===
  KILL @F420
  GOLD_SPIKE @F420 (+500 gold)
  POWER_SPIKE @F780 (+1200 gold diff reversed)
```

SYS2 对每个 event 独立调用。

---

## 13. SELF/ENEMY 对称结构

所有涉及双方数据的节（TRENDS、DELTA、DETAIL 帧尾）都采用完全相同的结构：

### TRENDS 内

```
--- SELF ---                --- ENEMY ---
  PATH: (100帧坐标)            PATH: (100帧坐标)
  GOLD: 起始→结束              GOLD: 起始→结束
  ITEM: (data pending)         ITEM: (data pending)
  KDA: k/d                     KDA: k/d
  SKILL: 计数                  SKILL: 计数
```

### DETAIL 帧尾

```
  SELF: @(x,y) HP h/m Gg ITEM: ...
  ENEMY: @(x,y) HP h/m Gg ITEM: ...
```

### DELTA 内

```
--- SELF ---                  --- ENEMY ---
  HP: ±diff                     HP: ±diff
  GOLD: ±diff                   GOLD: ±diff
  TOWER: 变化                   TOWER: 变化
  MINIONS: 变化                 MINIONS: 变化
  ITEM: (data pending)          ITEM: (data pending)
```

ITEM 在有接口后自动补齐，当前为 `(data pending)`。

---

## 14. DELTA 六维度

| 维度 | SELF | ENEMY | 数据来源 |
|------|------|-------|---------|
| HP | ✅ | ✅ | hero.hp 前后帧差值 |
| GOLD | ✅ | ✅ | hero.money 前后帧差值 |
| TOWER | ✅ | — | organ.Hp 前后帧差值 |
| MINIONS | ✅ | — | soldier_list 前后帧差值（暂缺） |
| ITEM | ✅ | ✅ | 预留行，当前 (data pending) |
| (BUF) | 预留 | 预留 | 暂无数据 |

DELTA = 上次调用时的状态 → 本次调用时的状态，不管中间隔了多少帧。

---

## 15. HUMANTIC 人类指导

### 定位

- 硬编码的 match-up 先验知识
- 存储于 `skill_db.py:SKILL_DB["matchup"]`
- 每个 match-up 包含 7 个字段：summary, advantage, danger, tip_offense, tip_defense, power_spike, key_skill

### 在系统中的角色

| 系统 | 出现位置 | 作用 |
|------|---------|------|
| SYS1 SYS | EXPERIENCE 节 | 作为决策参考 |
| SYS2 SYS | EXPERIENCE 节 | 作为分析参考对照 |
| SYS3 SYS | EXPERIENCE 节 | 作为分析参考对照 |
| AUDIT SYS | EXPERIENCE 节 | **不参与评分**，仅参考 |

### 格式

```
--- HUMANTIC (human guide, reference only, do not score) ---
  summary: 公孙离 vs 后羿 — 灵活射手 vs 站桩射手
  advantage: 公孙离, 前4级利用位移换血优势
  danger: 后羿3技能全图箭可眩晕3秒, 残血别走河道中线
  tip_offense: 用2技能格挡后羿大招, 1技能突进贴脸
  tip_defense: 保持移动不要站撸, 后羿被动叠满后伤害翻倍
  power_spike: 公孙离4级(有大招)和末世出完后是强势期
  key_skill: Skill2 霜叶舞: 格挡所有飞行物
```

### 扩展

当前仅 2 组 match-up（`199_vs_169`、`132_vs_169`）。后续可在 `skill_db.py` 中添加更多英雄组合，结构不变。

---

## 16. 文件地图与实施状态

| 文件 | 功能 | 状态 |
|------|------|------|
| `prompts.py` | PROMPT_BASE + 4 系统 PROTOCOL + 9 few-shot + EXPERIENCE_WARNING | ✅ 完成 |
| `macro_agent.py` | SYS1 决策循环 + MEMORY 渲染（TRENDS/EVENTS/DETAIL/DELTA/MACRO ACTIONS） | ✅ 完成 |
| `memory.py` | MemorySystem: retrieve/reflect(SYS2/SYS3/AUDIT) + retry + parser | ✅ 完成 |
| `state_parser.py` | 状态文本化 + MACRO ACTIONS AVAILABLE/BLOCKED + 原因 | ✅ 完成 |
| `strategy_executor.py` | @SKILL_CALL 解析 → 6-tuple | 🔧 另一位成员调试中 |
| `skill_base.py` | SKILL_REGISTRY + @register_skill + get_doc() | ✅ 完成 |
| `skills/farm.py` | FARM: last_hit / move_to_lane / retreat_to_tower | ✅ 完成 |
| `skills/poke.py` | POKE: aim_skill / basic_attack / reposition_back | ✅ 完成 |
| `skills/all_in.py` | ALL_IN: combo_start / basic_attack / chase | ✅ 完成 |
| `skill_db.py` | HUMANTIC matchup + combo + wave + positioning + game_mechanics | 🔧 需扩展 match-up 数据 |
| `gamecore_data.py` | gamecore 配置文件读取 | ✅ 完成 |
| `main_macro.py` | Docker 入口 + MemorySystem 集成 | ✅ 完成 |
| `main.py` | 简单 Docker 入口 (FinalAction 协议) | ✅ 完成 |
| `trajectory.py` | JSONL 轨迹记录 | ✅ 完成 |
| `trajectories/serve.py` | 轨迹回放浏览器 | ✅ 完成 |
| `pathfinding.py` | A* 寻路（`astar()` 函数） | ✅ 完成 |
| `fix_ailab.py` | AILab stub 修复（容器重建后） | ✅ 完成 |

### 待完成

| 任务 | 优先级 | 说明 |
|------|--------|------|
| strategy_executor 调试 | 高 | 另一位成员进行中 |
| ITEM 数据接口 | 高 | protobuf 字段待确认 |
| Similarity check | 中 | 队友 review 相关论文后实现 |
| AUDIT 输出解析器完善 | 中 | `_parse_audit_scores` 当前为初步实现 |
| tower_fall 检测 | 低 | organ.Hp 前后帧对比 |
| minion_wave 检测 | 低 | soldier_list 按 camp 分类计数 |
| HUMANTIC 数据扩展 | 低 | 当前仅 2 组 match-up |

---

## 17. 文献综述引用

完整综述见 `papers/LR.md`。核心引用：

| 论文 | 核心思想 | 在本项目中的应用 |
|------|---------|----------------|
| **TiG** (Liao et al., 2025) | GRPO 训练 LLM 做 40 种宏观策略决策 | SYS1 `<think>` 的盘面分析 + WhatIf 格式受 TiG 启发 |
| **WiA-LLM** (Sui et al., 2026) | 世界模型 + 双系统架构（System1反应/System2规划） | SYS1（高频决策）+ SYS2/3（低频分析）分离 |
| **Reflexion** (Shinn et al., 2023) | Actor-Evaluator-SelfReflection + 情景记忆 | 赛后反思→EPISODIC/SEMANTIC 的范式 |
| **Generative Agents** (Park et al., 2023) | 记忆流 + 反思 + 规划三元组 | 记忆系统三层架构（working/episodic/semantic） |
| **BPO** (Cheng et al., 2024) | 黑盒提示优化器 | 提示自动优化方向 |
| **Mem-alpha** (Wang et al., 2025) | RL 训练记忆管理，三层（core/episodic/semantic） | 三层记忆架构设计的参考 |

---

## 18. 附录：Prompt 完整示例

（本节列出 SYS1/SYS2/SYS3/AUDIT 完整渲染示例，避免歧义。）

### SYS1 SYSTEM 渲染后

```
You control GongSunLi(shooter) vs HouYi(shooter) in Honor of Kings 1v1.

=== GAME RULES ===
(83 行, 游戏模式/地图/属性范围/建筑/兵/野/时间/泉水)

=== HERO INFO ===
GongSunLi (shooter) ... HouYi (shooter) ...
Matchup: 公孙离 vs 后羿 — 灵活射手 vs 站桩射手 ...

=== MACRO SKILLS ===
FARM, POKE, ALL_IN 技能文档

=== EXPERIENCE ===
--- HUMANTIC (human guide, reference only, do not score) ---
  summary: 公孙离 vs 后羿 ...
--- EPISODIC ---
  [KILL @F420] lesson: enemy <30%HP -> ALL_IN (3/4 supported)
--- SEMANTIC ---
  enemy <30%HP -> ALL_IN.combo_start() (3/4)
  Some rules may have few tests, high ratio by chance -- judge carefully.

=== PROTOCOL ===
...
```

### SYS1 USER 渲染后

```
=== TRENDS (last 80 frames) ===
--- SELF ---
  PATH: (-32000,48) -> (-31000,48) -> ... (80帧坐标)
  GOLD: 300 -> 1800 (+1500)
  ITEM: (data pending)
  KDA: 1/0
  SKILL: FARM:3 POKE:5 ALL_IN:1
--- ENEMY ---
  PATH: (100000,48) -> (50000,48) -> ... (80帧坐标)
  GOLD: 300 -> 1200 (+900)
  ITEM: (data pending)
  KDA: 0/1
  SKILL:

TOWER: RED outer 5000->3000(-2000)

=== EVENTS ===
  KILL @F420
  GOLD_SPIKE @F420

=== DETAIL (all 80 frames) ===
[Frame 0] none
  (初始状态)

[Frame 420] @SKILL_CALL ALL_IN.combo_start()
  Review: enemy at 30%HP didn't recall after poke.
  WhatIf check: previous poke prediction correct.
  Situation: SELF 75% vs enemy 30%, ult off CD.
  WhatIf 1: combo_start() -> kill threat
  WhatIf 2: last_hit() -> safe farm waste pressure
  Decision: ALL_IN.combo_start
  Action: @SKILL_CALL ALL_IN.combo_start()
  === DELTA (since last call, ~5 frames) ===
  --- SELF ---
    HP: -100 (2700->2600)
    GOLD: +300 (900->1200)
  --- ENEMY ---
    HP: -1200 (1600->0)
    GOLD: +0 (900->900)
  SELF: @(-2000,48) HP 2600/3500 G1200 ITEM: (data pending)
  ENEMY: @(500,48) HP 0/3200 G900 ITEM: (data pending)

=== MACRO ACTIONS ===
  AVAILABLE:
    FARM.last_hit()
    FARM.move_to_lane()
    ...
  BLOCKED:
    POKE.aim_skill(): Skill1 on cooldown (3.2s)
    ALL_IN.combo_start(): enemy dead
```
