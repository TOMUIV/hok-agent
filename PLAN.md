# 项目计划：基于提示词工程与分层知识库的纯文本 LLM 游戏智能体

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
3. [文献综述](#3-文献综述)
4. [系统设计](#4-系统设计)
5. [实验平台](#5-实验平台)
6. [现有工作基础](#6-现有工作基础)
7. [实验设计](#7-实验设计)
8. [计划与分工](#8-计划与分工)
9. [预期成果与创新点](#9-预期成果与创新点)
10. [项目文件索引](#10-项目文件索引)

---

## 1. 项目概述

### 1.1 项目目标

本项目旨在**零训练成本**（无需 GPU 集群、无需 RL 微调）的前提下，通过**提示词工程**、**分层知识库**与**智能体记忆系统**的协同设计，使纯文本大语言模型（LLM）在 MOBA 游戏（王者荣耀 1v1）中做出有效的高层决策。研究核心在于探索一种此前未见发表的纯技术路线——完全不依赖模型微调，纯粹通过提示词优化与记忆管理的组合来实现游戏智能。

### 1.2 核心思想

1. **人类专家预定义分层知识库**：硬编码指导集（规则类知识）→ 策略动作集（基础技能单元）→ 策略模板集（宏观战术骨架）→ 策略技巧集（可学习经验）
2. **LLM 负责宏观决策**：在战略层面进行策略选择与模板参数化，不关注底层微操作
3. **代码算法执行底层控制**：走位使用 A* 寻路，技能释放由预定义序列约束
4. **记忆系统积累经验**：在对局迭代中积累可复用经验，实现"从失败中学习"
5. **提示词自优化**：借鉴 BPO 与 PROMST 的思路实现提示词的自动迭代优化

### 1.3 研究定位

| 维度 | TiG / WiA-LLM | BPO / PROMST / Plum | 本文 |
|------|---------------|---------------------|------|
| 训练需求 | GRPO (8×H20 GPU) / SFT+GRPO | 无（仅提示级优化） | **无** |
| 动作空间 | 40 种宏观策略 / 高层策略 | — | **四层知识库** |
| 记忆机制 | 无显式记忆 | 无 | **技能库 + 经验集** |
| 提示优化 | 固定提示 | 自动优化 | **BPO + 迭代优化** |
| 适用场景 | 有 GPU 资源 | 通用对话 | **零资源 MOBA** |

---

## 2. 研究动机与问题定义

### 2.1 背景

大语言模型在复杂推理任务中展现出令人瞩目的能力，但在需要与环境持续交互的游戏决策任务中表现远不及人类（Hu 等，2026）。这一落差揭示了**声明性知识**（declarative knowledge）与**过程性知识**（procedural knowledge）之间的根本鸿沟（Liao 等，2025）。

### 2.2 现有路线的局限性

**路线一：强化学习微调**
- TiG 框架：40 种宏观团队策略，GRPO 训练，需 8×NVIDIA H20 GPU
- WiA-LLM：世界模型预测，SFT + GRPO 两阶段训练
- 优势：效果显著，Qwen-3-14B 达 90.91% 准确率
- 劣势：需要大规模 GPU 集群和真实对局数据，不可复现

**路线二：提示词工程**
- BPO：黑盒提示优化器，ChatGPT +22%，GPT-4 +10%
- PROMST：多步任务提示优化，10.6%-29.3% 提升
- Plum / ZOT：元启发式搜索与零阶优化理论
- 优势：零训练成本，即插即用
- 劣势：效果有限，未针对游戏场景优化

### 2.3 本研究的差异化定位

填补两条路线之间的空白——在**零训练成本**的约束下，通过**分层知识库 + 智能体记忆系统 + 提示词自优化**的三位一体协同设计，探索纯文本 LLM 在 MOBA 游戏中决策能力的上限。

---

## 3. 文献综述

### 3.1 基于大语言模型的游戏智能体

#### 3.1.1 Survey：统一参考架构（Hu 等，2026）

**出处**：Hu, S., Huang, T., Liu, G., et al. (2026). A survey on large language model-based game agents. *ACM Computing Surveys*. https://arxiv.org/abs/2404.02039

**核心贡献**：
- 提出 LLMGA 的统一参考架构，将单智能体分解为**记忆系统**、**推理机制**和**感知-行动接口**三大组件
- 多智能体层面：通信协议与组织结构
- 游戏分类：Action / Adventure / RPG / Strategy / Simulation / Sandbox 六大类
- 策略游戏（含 MOBA）核心挑战为**对手感知规划**（opponent-aware planning）

**对本项目的启示**：
- 为系统设计提供了理论框架——三个组件对应我们的记忆系统、提示词引擎和策略执行层
- MOBA 被定位为 Strategy games，需要多步推理与对手建模

#### 3.1.2 TiG：宏观策略决策（Liao 等，2025）

**出处**：Liao, Y., Gu, Y., Sui, Y., et al. (2025). Think in games: Learning to reason in games via reinforcement learning with large language models. arXiv:2508.21365.

**核心贡献**：
- 定义 40 种宏观团队策略（推塔、拿龙、防守高地等）作为动作空间
- 采用组相对策略优化（GRPO）算法训练
- 游戏状态序列化为 JSON 对象
- **结果**：Qwen-3-14B + SFT + GRPO（2000 steps）→ **90.91%** 准确率，超越 Deepseek-R1（671B）的 86.67%
- 输出格式：`<think>推理过程</think><answer>行动建议</answer>`（中文）

**对本项目的启示**：
- 宏观策略模板集设计直接受 TiG 启发
- TiG 的中文提示模板可直接参考
- 区别：本项目采用纯文本路线，无需 GRPO 训练

#### 3.1.3 WiA-LLM：世界模型与双系统架构（Sui 等，2026）

**出处**：Sui, Y., Zhang, Y., Liao, Y., et al. (2026). What-if analysis of LLMs: Explore the game world using proactive thinking. arXiv:2509.04791.

**核心贡献**：
- 训练 LLM 作为显式的、基于语言的世界模型：SΔ = f(S_t, a_t)
- 两阶段训练：SFT（Deepseek-R1 蒸馏）→ GRPO（规则奖励）
- **结果**：74.2% 状态预测准确率（base 模型 47.2%）
- **双系统架构**：
  - System 1：高频反应策略（≈30ms），处理实时控制
  - System 2：低频规划器（每 5-10 秒），战略决策
- **Lookahead 搜索**：采样候选动作 → 预测结果 → 规则评估 → 选择最优

**对本项目的启示**：
- 双系统架构理念——LLM 负责低频战略，代码负责高频执行
- Lookahead 机制可在 ReAct agent 中实现
- 状态表示方法（JSON + 部分可观性）一致

### 3.2 提示词优化方法

#### 3.2.1 BPO：黑盒提示优化器（Cheng 等，2024）

**出处**：Cheng, J., Liu, X., Zheng, K., et al. (2024). Black-box prompt optimization: Aligning large language models without model training. *Proceedings of ACL 2024*. https://arxiv.org/abs/2311.04155

**核心贡献**：
- 训练 Llama2-7B-Chat 作为 Seq2Seq 提示重写器
- 基于 14K 偏好对训练（OASST1, HH-RLHF, Chatbot Arena, Alpaca-GPT4）
- **结果**：ChatGPT +22% 胜率，GPT-4 +10% 胜率
- 四种优化策略：Explanation Generation（加入推理步骤）、Prompt Elaboration（充实模糊指令）、Providing Hint（添加关键提示）、Safety Enhancement（安全约束）
- 模型无关、可叠加 PPO/DPO

**对本项目的启示**：
- 核心组件——直接可用以自动优化 System Prompt
- 无需训练，即插即用
- 可迭代优化

#### 3.2.2 PROMST：多步任务提示优化（Chen 等，2024）

**出处**：Chen, Y., Arkin, J., Hao, Y., et al. (2024). PRompt optimization in multi-step tasks (PROMST): Integrating human feedback and heuristic-based sampling. *Proceedings of EMNLP 2024*. https://aclanthology.org/2024.emnlp-main.226

**核心贡献**：
- 针对多步智能体任务（300+ tokens 提示）的优化框架
- 核心流程：TaskLLM → 错误检测 → Human Feedback Rules → SumLLM（总结）→ GenLLM（生成新提示）→ Score Model（Longformer 筛选）
- **结果**：11 个多步任务，GPT-3.5: 0.27→0.32, GPT-4: 0.61→0.69
- 错误类型：语法错误、死循环、超时、无效动作等

**对本项目的启示**：
- 错误驱动迭代的优化范式——对局失败→分析模式→更新提示→验证
- Score Model 概念可用于提示筛选

#### 3.2.3 Plum：元启发式搜索（Pan 等，2024）

**出处**：Pan, R., Xing, S., Diao, S., et al. (2024). Plum: Prompt learning using metaheuristic. *Findings of ACL 2024*. https://arxiv.org/abs/2311.08364

**核心贡献**：
- 6 种算法：Hill Climbing, Simulated Annealing, Genetic（有/无交叉）, Tabu Search, Harmony Search
- Harmony Search 最佳：59.63% 准确率，5494 API 调用
- 解释性提示发现——可发现未被探索的有效提示模式

**对本项目的启示**：
- 备选方案——当 BPO 和 PROMST 不够时，可用 Plum 搜索更优提示
- 固定决策格式（JSON / FinalAction）下调优措辞

#### 3.2.4 ZOT：零阶优化理论（Zhan 等，2024）

**出处**：Zhan, H., Chen, C., Ding, T., et al. (2024). Unlocking black-box prompt tuning efficiency via zeroth-order optimization. *Findings of EMNLP 2024*. https://aclanthology.org/2024.findings-emnlp.871

**核心贡献**：
- 零阶优化（有限差分法）用于黑盒提示调优
- 引入**有效维度**（Effective Dimension）概念：D_e = Σλ_i(∇²f(x)) / L
- 实验发现：RoBERTa 上 D_e=131 << d=38,400
- 2x 训练加速，平均 3.23% 准确率提升

**对本项目的启示**：
- 理论支撑——提示空间有效维度低，解释为何少量调整即可显著改变行为
- 实用性有限（需 soft prompt API）

### 3.3 智能体记忆系统

#### 3.3.1 Generative Agents（Park 等，2023）

**出处**：Park, J. S., O'Brien, J. C., Cai, C. J., et al. (2023). Generative agents: Interactive simulacra of human behavior. *Proceedings of UIST '23*. ACM.

**核心贡献**：
- 25 个智能体在沙盒环境中运行
- 核心机制：
  - **记忆流**（memory stream）：自然语言记录所有观察
  - **记忆检索**：时效性 × 重要性 × 相关性加权打分
  - **反思**：将低层观察抽象为高层推论
  - **规划**：基于记忆生成日常计划
- 消融实验：去除反思后，48 虚拟小时内退化为重复性反应

**对本项目的启示**：
- 奠基性工作——为记忆系统设计提供基础范式
- 反思机制可借鉴用于策略技巧集的提炼

#### 3.3.2 Reflexion（Shinn 等，2023）

**出处**：Shinn, N., Cassano, F., Berman, E., et al. (2023). Reflexion: Language agents with verbal reinforcement learning. *Advances in NeurIPS 2023*. https://arxiv.org/abs/2303.11366

**核心贡献**：
- Actor（生成动作） + Evaluator（评分） + Self-Reflection（生成反思文本）
- 情景记忆（episodic memory）缓冲区存储反思文本
- 不更新权重，通过语言反馈信号强化决策
- **结果**：
  - AlfWorld：+22%（134 任务中完成 130）
  - HotPotQA：+20%
  - HumanEval：**91% pass@1**（GPT-4 当时 80%）
- 缺陷：情景记忆仅限于同一任务的多次尝试间，缺乏跨任务持久化

**对本项目的启示**：
- "反思-压缩-存储"范式——经验集更新机制的直接参考
- 语言反馈替代权重更新——与零训练成本理念一致

#### 3.3.3 Memory-R1（Yan 等，2025）

**出处**：Yan, S., Yang, X., Huang, Z., et al. (2025). Memory-R1: Enhancing large language model agents to manage and utilize memories via reinforcement learning. arXiv:2508.19828.

**核心贡献**：
- 首个将 RL（PPO + GRPO）引入 LLM 记忆管理的框架
- 双 Agent 架构：
  - **Memory Manager**：学习 ADD / UPDATE / DELETE / NOOP 四种结构化操作
  - **Answer Agent**：记忆蒸馏（从 60 条候选中筛选），推理并回答
- **结果**：仅 152 个训练 QA 对
  - LLaMA-3.1-8B + GRPO：F1 +28%, BLEU-1 +34%, LLM-Judge +30%
  - 跨模型规模（3B-14B）、跨数据集（LoCoMo, MSC, LongMemEval）泛化
- 案例：vanilla 系统将"养了两只狗"误判为矛盾→DELETE+ADD；RL 版→UPDATE 合并

**对本项目的启示**：
- 可学习记忆管理的有效性验证
- 小模型微调方案——队友可参考此方法迭代技能库

#### 3.3.4 Mem-α（Wang 等，2025）

**出处**：Wang, Y., Takanobu, R., Liang, Z., et al. (2025). Mem-α: Learning memory construction via reinforcement learning. arXiv:2509.25911.

**核心贡献**：
- 三层记忆架构：
  - **Core Memory**：持续可访问的文本摘要（≤512 tokens）
  - **Semantic Memory**：结构化事实语句集合
  - **Episodic Memory**：时间戳事件记录
- GRPO 训练，四个奖励信号：
  - r₁ 正确性（下游 QA 准确率）
  - r₂ 工具调用格式
  - r₃ 压缩率（鼓励紧凑表示）
  - r₄ 语义质量（LLM 验证）
- **关键结果**：30k tokens 训练 → 泛化至 400k+ tokens（13× 训练长度）
- Qwen3-4B + Mem-α 超越 gpt-4.1-mini

**对本项目的启示**：
- 三层记忆架构可借鉴——与本项目的三层存储设计一致
- 长度外推能力验证了 RL 训练的有效性
- 奖励设计思路可参考（尤其 r₁ 正确性 + r₃ 压缩率）

#### 3.3.5 综述一：Memory in the Age of AI Agents（Hu 等，2025）

**出处**：Hu, Y., Liu, S., Yue, Y., et al. (2025). Memory in the age of AI agents: A survey. arXiv:2512.13564.

**核心贡献**：
- 三维分类法：
  - **Forms（形态）**：Token-level（显式离散） / Parametric（隐式权重） / Latent（隐藏状态）
  - **Functions（功能）**：Factual（事实记忆） / Experiential（经验记忆） / Working（工作记忆）
  - **Dynamics（动态）**：Formation（形成） / Evolution（演化） / Retrieval（检索）
- 107 页全面覆盖，含 200+ 参考文献
- 清晰区分 Agent Memory vs RAG vs Context Engineering

#### 3.3.6 综述二：Memory for Autonomous LLM Agents（Du，2026）

**出处**：Du, P. (2026). Memory for autonomous LLM agents: Mechanisms, evaluation, and emerging frontiers. arXiv:2603.07670.

**核心贡献**：
- write–manage–read 循环形式化
- 三维分类法：时间范围、表征载体、控制策略
- **五大机制簇**：
  1. 上下文驻留压缩（Context-Resident Compression）
  2. 检索增强存储（Retrieval-Augmented Stores）
  3. 反思性自我改进（Reflective Self-Improvement）
  4. 分层虚拟上下文（Hierarchical Virtual Context）
  5. 策略学习管理（Policy-Learned Management）
- 覆盖从静态基准到多会话 Agent 评测的演进

---

## 4. 系统设计

### 4.1 总体架构（当前实现）

```
┌─────────────────────────────────────────────────────────┐
│  SYSTEM PROMPT (预定义，运行时分发 hero_info/skilldoc)    │
│  ┌──────────────────────────────────────────────────┐   │
│  │  GAME RULES (全部从 gamecore/ config 提取)        │   │
│  │    GAME MODE / MAP CONFIG / HERO STAT RANGES     │   │
│  │    STRUCTURES / SOLDIERS / MONSTERS / TIMING     │   │
│  │    SPRING / HERO INFO (双方英雄技能数据)           │   │
│  │  MACRO SKILLS (skill_base 文档注入)               │   │
│  │  PROTOCOL + FEW-SHOT (FOW强调/多SKILL_CALL)      │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│  USER PROMPT (每帧动态构造)                               │
│  ┌──────────────────────────────────────────────────┐   │
│  │  MEMORY (过去 100 次 LLM 调用)                   │   │
│  │    [Call N | Frame n | T+t]                      │   │
│  │      State: 压缩快照 (SELF/ENEMY/塔/小兵)         │   │
│  │      <think>原始推理</think>                      │   │
│  │      <action>原始动作</action>                    │   │
│  ├──────────────────────────────────────────────────┤   │
│  │  FRAME (完整盘面)                                 │   │
│  │    HEROES (含技能冷却/属性/位置/FOW)               │   │
│  │    TOWERS (6座建筑HP/坐标)                        │   │
│  │    MINIONS / MONSTERS / LEGAL ACTIONS            │   │
│  │    DISTANCES (敌方/最近塔/最近兵)                  │   │
│  ├──────────────────────────────────────────────────┤   │
│  │  STATE CHANGES (对比10帧前的protobuf快照)          │   │
│  │    SELF: HP差/Gold差/等级变化                      │   │
│  │    RED outer: 塔HP差                              │   │
│  ├──────────────────────────────────────────────────┤   │
│  │  LAST RESULTS (上一轮技能执行结果)                  │   │
│  │    @SKILL_CALL FARM.last_hit()                   │   │
│  │      action: last_hit                            │   │
│  │      status: success                             │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│  LLM (deepseek-v4-flash)                                 │
│  输出: <think>盘面+WhatIf+决策</think>                    │
│        <action>@SKILL_CALL <SKILL>.<func>()</action>    │
└──────────────────────────┬──────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│  策略执行层 (strategy_executor.py)                        │
│  process_batch(): 解析 @SKILL_CALL → skill.execute()    │
│  step(): skill生成 6-tuple (btn, mx, mz, sx, sz, tgt)   │
│  通过 legal_action 掩码验证按钮合法性                      │
│  路径规划: skills_concrete.py (11个具体技能)               │
└──────────────────────────┬──────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│  游戏引擎层                                              │
│  ┌─────────────────────┐  ┌─────────────────────────┐   │
│  │  MockEnv (快速迭代)  │  │  Gamecore (Docker)      │   │
│  │  protobuf 协议兼容  │  │  真实游戏引擎            │   │
│  └─────────────────────┘  └─────────────────────────┘   │
└─────────────────────────────────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  数据来源: gamecore/ 配置文件 (不含 src/ 代码)
    simulator_output/*.json   → 塔坐标/HP/SubType
    para_conf.txt             → 帧常量/技能槽/怪物ID/射程
    hero_min_max.txt          → 英雄属性范围
    vec_soldier_config.txt    → 小兵属性范围
    vec_feature_organ.txt     → 建筑属性范围
    vec_feature_monster.txt   → 野怪属性范围+类型
    map_info.txt              → 地图坐标/视野距离/参考点
    soldier.txt               → 小兵类型ID
    hero_main_job.txt         → 英雄职业
    hero_skill_info.txt       → 技能范围/形状/释放类型/EP消耗
    skill_ep_consume.txt      → 技能EP消耗
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 4.2 LLM-Executor 分离

| 层级 | 频率 | 决策内容 | 实现 |
|------|------|----------|------|
| LLM 决策 | 每帧（≈30Hz） | 宏观策略 + WhatIf 分析 + 技能选择 | `macro_agent.py` → deepseek-v4-flash API |
| 策略执行 | 每帧 | 技能子函数执行、走位、技能释放 | `strategy_executor.py` + `skills_concrete.py` |

**核心分工：**
- LLM 只输出 `@SKILL_CALL <SKILL>.<func>()`，不操作底层按钮
- 执行器将每个子函数转换为合法的 6-tuple 动作
- LLM 不知道 6-tuple 格式，只知道技能文档

### 4.3 技能系统

两套并行注册表：

| 注册表 | 位置 | 数量 | 用途 |
|--------|------|------|------|
| MACRO SKILLS | `skill_base.SKILL_REGISTRY` | 3 (FARM/POKE/ALL_IN) | LLM 可调用，文档注入 SYS |
| CONCRETE SKILLS | `skills_concrete.SKILL_REGISTRY` | 11 | 执行器内部使用 |

**MACRO SKILL 设计：**
```python
@register_skill
class FARM(Skill):
    name = "FARM"
    description = "..."
    when = "..."
    until = "..."

    def func_last_hit(self, ctx):
        if in_range:
            return {"action": "last_hit", "status": "success", "detail": "..."}
        return {"action": "move_to_lane", "status": "no_target", "detail": "..."}
```
- 子函数返回结构化 dict（`{action, status, detail, ...}`）
- 文档通过 `get_doc()` 自动生成并注入 SYS 的 MACRO SKILLS 节
- LLM 无需 `@SKILL_OPEN`——所有文档已在 SYS 中

### 4.4 提示词引擎设计

#### 4.4.1 System Prompt（固定模板 + 运行时注入）

```
You control {self_name}({self_type}) vs {enemy_name}({enemy_type}) in Honor of Kings 1v1.

=== GAME RULES ===
--- GAME MODE ---     游戏模式/技能槽/冷却范围 (gamecore)
--- MAP CONFIG ---    地图坐标/视野/参考点 (map_info.txt)
--- HERO STAT RANGES --- 属性范围 (hero_min_max.txt)
--- STRUCTURES ---    塔坐标/HP/ConfigID (simulator JSON)
--- SOLDIERS ---      小兵类型/属性 (soldier.txt)
--- MONSTERS ---      野怪类型/属性 (vec_feature_monster.txt)
--- KEY TIMING ---    帧常量 (para_conf.txt)
--- SPRING ---        泉水位置 (para_conf.txt)
--- HERO INFO ---     {hero_info} 双方英雄技能数据 (gamecore_data.py)

=== MACRO SKILLS ===  {skilldoc} 技能文档注入

=== PROTOCOL ===      <think>+<action> 格式 + FEW-SHOT
```

#### 4.4.2 User Prompt（每帧动态构造）

```
=== MEMORY (last N calls) ===
[Call N | Frame n | T+t] State: ... <think>...</think> <action>...</action>

=== FRAME n (T+ts) ===
--- HEROES --- [SELF] HP/EP/Gold ATK/DEF/Range SkillCD
--- TOWERS --- 双方6座建筑
--- MINIONS --- 数量+阵营
--- MONSTERS --- 数量
--- LEGAL ACTIONS --- 可用按钮
--- DISTANCES --- 到敌方/塔/兵

=== STATE CHANGES === (对比10帧前)
  SELF: HP差/Gold差
  RED outer: 塔HP差

=== LAST RESULTS ===
  @SKILL_CALL FARM.last_hit() → structured dict
```

#### 4.4.3 关键设计决策

1. **取消 @TOOL**：所有游戏状态通过 state_parser 直接注入 USER PROMPT，LLM 无需查询
2. **取消 @SKILL_OPEN**：技能文档直接注入 SYS，LLM 直接调用
3. **结构化 SKILL 返回**：子函数返回 dict，LAST RESULTS 多行展示
4. **MEMORY 滚动窗口**：保留最近 100 次调用的完整 thought + action，每次显示调用时间
5. **STATE CHANGES 快照**：每 10 帧对比 protobuf 快照，展示累积变化
6. **游戏时间显示**：每帧显示 `(T+ts)`，基于 `frame * 0.033`
7. **技能冷却**：从 `hero.skill[i].cooldown / cooldown_max` 读取，显示剩余/最大值

### 4.5 数据来源规范

所有 SYS 数据必须来自 `gamecore/` 目录下的配置文件，禁止使用 `src/` 代码中的数据。`gamecore_data.py` 模块负责读取 gamecore 配置文件并提供查询接口。

```
gamecore/ 路径 (开发环境):
  gamecore/gamecore/core_assets/customresources/ailab/ai_config/1v1/

Docker 环境:
  AILab/ai_config/1v1/  (after AILab setup)
  或 /hok_env/hok/hok1v1/core_assets/customresources/ailab/ai_config/1v1/
```

### 4.6 可视化与回放

- **轨迹回放浏览器**：`trajectories/serve.py` + `trajectories/index.html`
  - 文件列表 → 选择 JSONL → 浏览各帧 SYS/IN(USER msg)/OUT(LLM reply)/RES(parsed_results)
  - 搜索、过滤、展开/折叠
  - 支持两种日志格式（trajectory.py 标准格式 + macro_agent 格式）
- **Web 实时面板**：`src/web_demo.py` (v1) / `src/web_demo_v2.py` (v2)
- **ABSTool 回放**：`.abs` Unity 回放渲染器

---

## 5. 实验平台

### 5.1 MockEnv（快速迭代）

- **文件**：`src/mock_env.py`
- **特性**：纯 Python 实现，无外部依赖
- **用途**：
  - 快速原型验证
  - 策略合理性检验
  - 提示词迭代的快速循环（秒级）
- **动作空间**：`[12, 16, 16, 16, 16, 8]`（按钮 + 4 个坐标 + 目标）
- **英雄模板**：5 种预设英雄（马可波罗、后羿、貂蝉、赵云、公孙离）

### 5.2 Gamecore（真实校验）

- **引擎**：腾讯 hok_env（`gamecore-server.exe`）
- **部署**：Docker 容器（`tencentailab/hok_env:latest`）
- **接口**：
  - HTTP :23432（gamecore-server）
  - ZMQ :35500-35501（帧数据传输）
- **用途**：最终性能评估、效果确认
- **英雄支持**：全部 44 个

### 5.3 双平台协作流程

```
开发阶段: MockEnv → 快速迭代提示词和策略
                ↓ 迁移
验证阶段: Gamecore → 真实环境评估
                ↓ 对比
最终报告: 双平台实验数据对比分析
```

---

## 6. 现有工作基础

### 6.1 代码库

| 文件 | 功能 | 状态 |
|------|------|------|
| `src/macro_agent.py` | **主 Agent** — SYS/USER prompt, `<think>+<action>` 协议 | ✅ 核心 |
| `src/state_parser.py` | protobuf → 完整状态文本（含 FOW/塔/兵/野/CD） | ✅ 核心 |
| `src/gamecore_data.py` | gamecore 配置文件读取（hero/skill/role） | ✅ 核心 |
| `src/strategy_executor.py` | `@SKILL_CALL` 解析 → 6-tuple 执行 | ✅ 核心 |
| `src/skill_base.py` | Skill 基类 + `SKILL_REGISTRY` | ✅ 核心 |
| `src/skills/farm.py` | FARM skill（last_hit/move_to_lane/retreat_to_tower） | ✅ 核心 |
| `src/skills/poke.py` | POKE skill（aim_skill/basic_attack/reposition_back） | ✅ 核心 |
| `src/skills/all_in.py` | ALL_IN skill（combo_start/basic_attack/chase） | ✅ 核心 |
| `src/skills/__init__.py` | 自动发现装饰器注册的技能 | ✅ 核心 |
| `src/skills_concrete.py` | 11 个具体技能实现（执行器内部使用） | ✅ 可用 |
| `src/hero_db.py` | hero_name() 映射 | ✅ 可用 |
| `src/protocol.py` | 协议格式定义 | ⚠️ 需修复（断链引用） |
| `src/text_adapter.py` | **弃用** — 导入缺失符号，运行会崩溃 | ❌ BROKEN |
| `src/mock_env.py` | MockEnv v1（5 英雄模板） | ✅ 可用 |
| `src/mock_env_v2.py` | MockEnv v2（含伤害/装备/兵线/塔/FOW） | ✅ 可用 |
| `src/agent.py` | JSON 决策 Agent（qwen-plus 硬编码） | ⚠️ 旧方案 |
| `src/react_agent.py` | ReAct 多步工具调用 Agent | ⚠️ 旧方案 |
| `src/main.py` | Gamecore 对接（deepseek-v4-flash 硬编码） | ✅ 可用 |
| `src/main_macro.py` | MacroAgent + Gamecore | ✅ 可用 |
| `src/web_demo.py` | Web v1（FastAPI :13187） | ✅ 可用 |
| `src/web_demo_v2.py` | Web v2（MockEnvV2 :13188） | ✅ 可用 |
| `src/trajectory.py` | JSONL 轨迹记录 | ✅ 可用 |
| `trajectories/serve.py` | 轨迹回放浏览器 | ✅ 可用 |
| `trajectories/index.html` | 轨迹回放前端 | ✅ 可用 |
| `gamecore/gamecore/` | 游戏引擎文件 | ✅ 可用 |
| Docker 容器 | gamecore-server + SDK | ✅ 可用 |

### 6.2 已有基础设施

- **.env 配置**：DASHSCOPE_API_KEY + BASE_URL + MODEL_NAME
- **SKILL 注册机制**：`@register_skill` 装饰器 + `skills/__init__.py` 自动发现
- **技能文档注入**：`get_doc()` 自动生成文档 → 注入 SYS 的 MACRO SKILLS 节
- **轨迹日志**：`TrajectoryLogger` 记录每步 SYS/USER/LLM_reply/parsed_results → JSONL
- **游戏状态解析**：`parse_state()` 从 protobuf 提取完整盘面 → 结构化文本
- **状态快照对比**：`compress_state()` 用于 MEMORY 快照，10 帧周期对比用于 STATE CHANGES
- **游戏引擎启动**：gamecore-server 后台进程 + Docker 容器

### 6.3 待开发模块

- [ ] 提示词引擎（BPO 集成 + PROMST 迭代）
- [ ] 四层分层知识库（当前只有两层：gamecore 规则 + macro skills）
- [ ] 记忆系统（三层存储 + 反思机制，当前只有滑动窗口）
- [ ] 策略执行层完善（skill 调用结果与 step() 动作的断链修复）

---

## 7. 实验设计

### 7.1 基线系统

| 编号 | 方案 | 说明 |
|------|------|------|
| A | 纯随机决策 | 最低基线 |
| B | 纯 LLM 直接决策 | 无宏观策略抽象 |
| C | LLM + 四层知识库 | 有宏观策略但无记忆系统 |
| D | LLM + 知识库 + 记忆系统 | 完整方案（无提示优化） |
| E | LLM + 知识库 + 记忆 + BPO | 完整方案（含提示优化） |

### 7.2 评估指标

| 指标 | 计算方式 | 说明 |
|------|----------|------|
| 胜率 | 对局胜场/总场数 | 最直接的性能指标 |
| KDA | (击杀+助攻)/死亡 | 个人表现 |
| 经济差 | 己方-敌方经济 | 发育压制力 |
| 决策合理性 | 人工评分 / 与 expert 轨迹比较 | 决策质量 |
| 提示优化效果 | 比较 BPO 前后的胜率/决策质量 | BPO 消融 |
| 记忆贡献 | 比较有/无记忆系统的提升 | 记忆消融 |

### 7.3 实验流程

```
Phase 1: MockEnv 快速实验
  ├─ 基线对比（A/B/C/D/E）
  ├─ 知识库层次消融
  └─ BPO 迭代效果

Phase 2: Gamecore 验证
  ├─ 最佳方案 vs 内置 AI
  ├─ 跨英雄泛化测试
  └─ 长对局性能

Phase 3: 数据分析
  ├─ 胜率统计
  ├─ 错误模式分析
  └─ 案例研究
```

---

## 8. 计划与分工

### 8.1 时间线

```
7/13 选题报告提交
  │
  ├─ 7/13-14 (Phase 1)
  │  ├─ 杨坤鑫：提示词模板初始设计、BPO 集成、策略动作集定义
  │  └─ 张腾达：记忆系统框架搭建、技能库数据结构设计
  │
  ├─ 7/14-15 (Phase 2)
  │  ├─ 杨坤鑫：MockEnv 联调、策略库验证、A* 寻路实现
  │  └─ 张腾达：记忆系统原型开发、反思机制实现
  │
  ├─ 7/15-16 (Phase 3)
  │  ├─ 杨坤鑫：Gamecore 部署、Web 面板完善、ABSTool 回放
  │  └─ 张腾达：RL 迭代实验、经验集优化
  │
  └─ 7/16-17 (Phase 4)
     ├─ 两人：实验对比、数据收集
     └─ 两人：最终报告撰写、PPT 准备、演示

7/17 现场展示
```

### 8.2 分工详情

**杨坤鑫（提示词引擎 + 系统架构 + 实验平台）**
- System Prompt 初始设计（参考 TiG 模板）
- BPO 优化器集成
- PROMST 迭代循环实现
- 四层知识库框架
- 策略执行层（技能映射 + A* 寻路）
- MockEnv 与 Gamecore 部署
- Web 可视化面板
- 实验设计与基线对比
- 最终报告撰写

**张腾达（记忆系统 + 技能迭代）**
- 情景缓冲区实现
- 技能库数据结构与分层索引
- 经验集更新机制（Reflexion 范式）
- 小参数模型微调（可选）
- 反思机制实现
- 记忆系统与提示词引擎接口
- 实验数据分析
- 文献综述（记忆部分）

---

## 9. 预期成果与创新点

### 9.1 创新点

1. **零训练成本的纯文本 MOBA 游戏智能体方案**
   - 无需 GPU 资源，完全基于提示词工程与记忆系统
   - 可复现、低成本、易部署

2. **四层分层知识库架构**
   - 从固定规则到可学习经验的递进式知识组织
   - LLM 参数化模板微调机制

3. **面向游戏场景的智能体记忆系统**
   - 三层存储架构（情景缓冲 + 技能库 + 经验集）
   - 对局经验的积累、提炼与复用

4. **BPO + PROMST 提示词自优化机制**
   - 将通用提示优化方法引入游戏场景
   - 错误驱动迭代范式

5. **"LLM 宏观决策 + 算法底层执行"双系统范式**
   - 参考 WiA-LLM 架构
   - 将 LLM 从微操作中解放

### 9.2 预期成果

- 可在王者荣耀 1v1 中运行的 LLM Agent 原型
- 完整的实验对比数据（胜率、KDA、消融研究）
- 基于该方案的开源框架（GitHub）
- 选题报告与最终展示

### 9.3 研究价值

本研究探索的是一条此前未见发表的纯文本路线。现有工作（TiG, WiA-LLM 等）均依赖于 RL 或 SFT 微调，而我们的方案完全基于提示词工程、分层知识库与智能体记忆系统的协同。如果在实验中获得有意义的胜率和决策质量，将证明零训练成本方案在复杂游戏中的可行性，为该领域提供一个全新的基线参考。

---

## 10. 项目文件索引

| 文件 | 说明 |
|------|------|
| `选题报告_v2生成版.docx` | 选题报告正文（APA 引用，共 60 段 + 1 表格） |
| `PLAN.md` | **本文件**——详细项目计划 |
| `AGENTS.md` | OpenCode Agent 配置文件 |
| `papers/LR.md` | 文献综述（12 篇论文，含 TiG/WiA-LLM/BPO/PROMST/Plum/ZOT/Survey + Memory-R1/Mem-α/Reflexion/Memory Survey/Memory Frontiers） |
| `papers/_related_research.md` | AGENTS.md 中的参考文献摘要 |
| `papers/texts/` | 12 篇论文全文文本 |
| `papers/*.pdf` | 12 篇论文 PDF 原文 |
| `src/` | 核心代码目录 |
| `gamecore/gamecore/` | 游戏引擎文件 |
| `tmp/scripts/build_report.py` | docx 生成脚本 |
| `.env` | API 密钥配置 |
