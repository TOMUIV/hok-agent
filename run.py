"""HOK Agent runner: start gamecore + launch agent in Docker.

Usage:
  python run.py --hero-ai 169 --hero-bot 112 --decisions 10
  python run.py --hero-ai 199 --hero-bot 169 --max-tokens 4096 --no-thinking
  python run.py --list                    # list supported heroes
  python run.py --gamecore-only           # just start gamecore, don't run agent
"""
import subprocess, sys, os, time, argparse

# ============================================================
# DEFAULT CONFIG — adjust these before running
# ============================================================
HERO_AI = 169       # AI hero ID (169=后羿)
HERO_BOT = 112      # Bot hero ID (112=鲁班)
DECISIONS = 5       # Max LLM decision calls per game (main_macro default)
MAX_FRAMES = 100   # Max env steps (-1 = unlimited) (main_macro default)
MAX_TOKENS = 2048   # Max tokens per LLM call (main_macro default)
PRINT_EVERY = 5     # Print game state every N frames (main_macro default)
NO_THINKING = False # Disable LLM reasoning mode

CONTAINER = "hok"   # Docker container name
# ============================================================

ROOT = os.path.dirname(os.path.abspath(__file__))
GAMECORE_EXE = os.path.join(ROOT, "gamecore", "gamecore", "gamecore-server.exe")
GAMECORE_CWD = os.path.join(ROOT, "gamecore", "gamecore")
SUPPORTED = {106:"小乔",107:"赵云",108:"墨子",111:"孙尚香",112:"鲁班",117:"钟无艳",
             119:"扁鹊",120:"白起",121:"芈月",123:"吕布",128:"曹操",130:"宫本武藏",
             131:"李白",132:"马可波罗",133:"狄仁杰",135:"项羽",140:"关羽",141:"貂蝉",
             146:"露娜",150:"韩信",152:"王昭君",154:"花木兰",155:"艾琳",157:"不知火舞",
             163:"橘右京",167:"孙悟空",169:"后羿",173:"李元芳",174:"盾山",175:"钟馗",
             176:"杨玉环",182:"干将莫邪",189:"鬼谷子",190:"诸葛亮",192:"黄忠",193:"凯",
             194:"苏烈",196:"百里守约",199:"公孙离",502:"裴擒虎",510:"孙策",513:"上官婉儿",522:"瑶"}


def is_gamecore_running():
    r = subprocess.run(["tasklist", "/fi", "IMAGENAME eq gamecore-server.exe", "/fo", "csv"],
                       capture_output=True, text=True, timeout=5)
    return "gamecore-server.exe" in r.stdout


def start_gamecore():
    if is_gamecore_running():
        print("[gamecore] already running", flush=True)
        return
    if not os.path.isfile(GAMECORE_EXE):
        print(f"ERROR: gamecore-server.exe not found at:\n  {GAMECORE_EXE}", flush=True)
        sys.exit(1)
    os.makedirs(GAMECORE_CWD, exist_ok=True)
    proc = subprocess.Popen(
        [GAMECORE_EXE, "server", "--server-address", ":23432"],
        cwd=GAMECORE_CWD,
        creationflags=subprocess.DETACHED_PROCESS,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    print(f"[gamecore] started (PID={proc.pid})", flush=True)
    for i in range(30):
        time.sleep(1)
        if is_gamecore_running():
            print(f"[gamecore] ready ({i+1}s)", flush=True)
            return
    print(f"[gamecore] WARNING: started but not confirmed running in 30s", flush=True)


def stop_gamecore():
    subprocess.run(["taskkill", "/f", "/im", "gamecore-server.exe"],
                   capture_output=True, timeout=5)
    print("[gamecore] stopped", flush=True)


def list_heroes():
    print("ID   Hero")
    for hid in sorted(SUPPORTED):
        print(f"{hid:>4}  {SUPPORTED[hid]}")


def main():
    parser = argparse.ArgumentParser(description="HOK Agent Runner")
    parser.add_argument("--hero-ai", type=int, default=HERO_AI, help=f"AI hero ID (default: {HERO_AI})")
    parser.add_argument("--hero-bot", type=int, default=HERO_BOT, help=f"Bot hero ID (default: {HERO_BOT})")
    parser.add_argument("--decisions", type=int, default=DECISIONS, help=f"Max LLM decisions (default: {DECISIONS})")
    parser.add_argument("--max-frames", type=int, default=MAX_FRAMES, help=f"Max env steps (default: {MAX_FRAMES}, -1=unlimited)")
    parser.add_argument("--max-tokens", type=int, default=MAX_TOKENS, help=f"Max tokens per LLM call (default: {MAX_TOKENS})")
    parser.add_argument("--print-every", type=int, default=PRINT_EVERY, help=f"Print state every N frames (default: {PRINT_EVERY})")
    parser.add_argument("--no-thinking", action="store_true", default=NO_THINKING, help="Disable reasoning mode")
    parser.add_argument("--list", action="store_true", help="List supported hero IDs")
    parser.add_argument("--gamecore-only", action="store_true", help="Only start gamecore, don't run agent")
    parser.add_argument("--stop-gamecore", action="store_true", help="Stop gamecore-server")
    parser.add_argument("--reset-memory", action="store_true", help="Delete memory.json to start fresh")
    args = parser.parse_args()

    if args.list:
        list_heroes(); return
    if args.stop_gamecore:
        stop_gamecore(); return
    if args.reset_memory:
        mp = os.path.join(ROOT, "trajectories", "memory.json")
        if os.path.isfile(mp):
            os.remove(mp)
            print(f"[reset] deleted {mp}", flush=True)
        else:
            print(f"[reset] no memory.json found", flush=True)
        return

    start_gamecore()
    if args.gamecore_only:
        print("[done] gamecore running. Use --stop-gamecore to stop.", flush=True)
        return

    # Cleanup ZMQ ports in container before starting
    subprocess.run(
        ["docker", "exec", CONTAINER, "sh", "-c",
         "fuser -k 35500/tcp 2>/dev/null; fuser -k 35501/tcp 2>/dev/null; "
         "lsof -ti :35500 2>/dev/null | xargs kill -9 2>/dev/null; "
         "lsof -ti :35501 2>/dev/null | xargs kill -9 2>/dev/null; true"],
        capture_output=True, timeout=10,
    )

    # Build docker exec command
    ai_name = SUPPORTED.get(args.hero_ai, f"hero{args.hero_ai}")
    bot_name = SUPPORTED.get(args.hero_bot, f"hero{args.hero_bot}")
    cmd_parts = [
        "docker", "exec", CONTAINER, "bash", "-c",
        f"cd /hok_env/hok/hok1v1 && python3 -u /workspace/src/main_macro.py "
        f"--decisions {args.decisions} "
        f"--max-frames {args.max_frames} "
        f"--hero-ai {args.hero_ai} --hero-bot {args.hero_bot} "
        f"--max-tokens {args.max_tokens} "
        f"--print-every {args.print_every}"
    ]
    if args.no_thinking:
        cmd_parts[-1] += " --no-thinking"

    print(f"[agent] {ai_name}(AI) vs {bot_name}(Bot)", flush=True)
    print(f"[agent] running...", flush=True)

    proc = subprocess.run(cmd_parts, timeout=600)
    if proc.returncode != 0:
        print(f"[agent] exit code {proc.returncode}", flush=True)
        sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
