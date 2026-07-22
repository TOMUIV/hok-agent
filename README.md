# HOK LLM Agent

LLM Agent plays Honor of Kings 1v1.

## 快速开始

### 1. 安装依赖

```bash
pip install openai fastapi uvicorn numpy python-dotenv
```

### 2. 运行 MockEnv Demo（无需 Docker）

```bash
python src/demo.py
```

或指定英雄：

```bash
python -c "from src.demo import run_demo; run_demo(hero_ids=[199, 169], max_steps=100)"
```

### 3. Web UI

```bash
python src/web_demo.py
```

打开 http://localhost:13187

### 4. 真实游戏引擎（需要 Docker）

详见下方 [架构与部署](#架构与部署)。

## 项目结构

```
├── src/                    # 核心代码
│   ├── main.py             # 主入口：LLM Agent vs Bot（真实引擎）
│   ├── react_agent.py      # ReAct 决策循环
│   ├── agent.py            # 简单 Agent（JSON 决策）
│   ├── mock_env.py         # 纯 Python 仿真环境
│   ├── web_demo.py         # Web UI（FastAPI + WebSocket）
│   ├── web/index.html      # 前端页面
│   ├── state_parser.py     # 游戏状态 → 文本描述
│   ├── text_adapter.py     # LLM 交互协议
│   ├── protocol.py         # 动作协议定义
│   ├── tool_set.py         # ReAct 工具集
│   ├── hero_db.py          # 英雄 ID → 名称映射
│   └── test_*.py           # 测试/实验脚本
├── gamecore/               #（本地）游戏引擎二进制
├── AGENTS.md               # OpenCode 开发指南
└── .env                    # API Key（勿提交）
```

## Agent 实现

| 文件 | 协议 | 说明 |
|------|------|------|
| `agent.py` | 文字 → JSON | 简单 prompt，输出结构化决策 |
| `react_agent.py` | ReAct (Thought→Action→Observation) | 多步推理 + 工具调用 |
| `main.py` | 文字 → FinalAction | 最简实现，直接输出动作 |

## 架构与部署

```
Windows 主机                        Docker 容器
┌──────────────────┐               ┌─────────────────────┐
│ gamecore-server   │──HTTP :23432→│ Python SDK (hok)     │
│  (端口 23432)     │               │  + LLM Agent        │
│  sgame_simulator  │←──ZMQ :35500─│  (deepseek-v4-flash) │
└──────────────────┘               └─────────────────────┘
```

### 部署步骤

**1. 启动 gamecore-server（Windows）**

```powershell
Start-Process -WindowStyle Hidden -FilePath "gamecore\gamecore\gamecore-server.exe" -ArgumentList "server","--server-address :23432"
```

**2. 启动 Docker 容器**

```bash
docker run -d --name hok \
  -v "项目绝对路径:/workspace" \
  -p 35500:35500 -p 35501:35501 \
  tencentailab/hok_env:latest \
  bash -c "sleep infinity"
```

**3. 容器内运行**

```bash
docker exec hok bash -c "cd /hok_env/hok/hok1v1 && python3 -u /workspace/src/main.py"
```

> ⚠️ 必须在 `/hok_env/hok/hok1v1` 目录下执行 — SDK 的 `config.dat` 从此目录解析相对路径。

### 清理

```powershell
taskkill /f /im gamecore-server.exe   # 停止 gamecore
docker stop hok                         # 停止容器（勿删除）
```

## 环境变量（`.env`）

```
DASHSCOPE_API_KEY=sk-...
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL_NAME=deepseek-v4-flash
```

## 英雄 ID 速查

| ID | 英雄 | ID | 英雄 | ID | 英雄 |
|----|------|----|------|----|------|
| 106 | 小乔 | 133 | 狄仁杰 | 175 | 钟馗 |
| 107 | 赵云 | 135 | 项羽 | 176 | 杨玉环 |
| 108 | 墨子 | 140 | 关羽 | 182 | 干将莫邪 |
| 111 | 孙尚香 | 141 | 貂蝉 | 189 | 鬼谷子 |
| 112 | 鲁班 | 146 | 露娜 | 190 | 诸葛亮 |
| 117 | 钟无艳 | 150 | 韩信 | 192 | 黄忠 |
| 119 | 扁鹊 | 152 | 王昭君 | 193 | 凯 |
| 120 | 白起 | 154 | 花木兰 | 194 | 苏烈 |
| 121 | 芈月 | 155 | 艾琳 | 196 | 百里守约 |
| 123 | 吕布 | 157 | 不知火舞 | 199 | 公孙离 |
| 128 | 曹操 | 163 | 橘右京 | 502 | 裴擒虎 |
| 130 | 宫本武藏 | 167 | 孙悟空 | 510 | 孙策 |
| 131 | 李白 | 169 | 后羿 | 513 | 上官婉儿 |
| 132 | 马可波罗 | 173 | 李元芳 | 522 | 瑶 |
