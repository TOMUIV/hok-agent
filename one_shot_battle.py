"""一键跑对战：清理→启动→对战→保存ABS"""
import sys, os, subprocess, time, glob, shutil

HOK_DIR = r"C:\Users\张腾达\Desktop\Hok"
os.chdir(HOK_DIR)

# 1. Kill everything
print("[1/5] Kill stale processes...")
os.system("taskkill /f /im gamecore-server.exe 2>nul")
os.system("taskkill /f /im sgame_simulator_remote_zmq.exe 2>nul")
subprocess.run(["docker", "exec", "hok", "sh", "-c", "pkill -9 -f sgame 2>/dev/null; pkill -9 -f zmq 2>/dev/null"], capture_output=True)

# 2. Kill & recreate container 
print("[2/5] Recreate container...")
subprocess.run(["docker", "rm", "-f", "hok"], capture_output=True)
r = subprocess.run(["docker", "run", "-d", "--name", "hok", "-p", "35500:35500", "-p", "35501:35501",
    "-v", f"{HOK_DIR}\\src:/workspace",
    "tencentailab/hok_env:latest", "sh", "-c", "sleep infinity"], capture_output=True, text=True)
print(f"  Container: {r.stdout.strip()}")
time.sleep(3)

# 3. Install deps
print("[3/5] Install deps...")
subprocess.run(["docker", "exec", "hok", "sh", "-c", "pip install openai -q 2>/dev/null"], capture_output=True)

# 4. Start gamecore server
print("[4/5] Start gamecore-server...")
os.system('start /B "" "C:\\hok_env\\gamecore\\gamecore-server.exe" server --server-address :23432')
time.sleep(6)

# 5. Run battle
print("[5/5] Run battle...")
sys.stdout.flush()
r = subprocess.run(
    ["docker", "exec", "hok", "sh", "-c", "cd /hok_env/hok/hok1v1 && python3 -u /workspace/run_fsm.py"],
    capture_output=False, timeout=300)

# 6. Copy ABS
sim_out = r"C:\hok_env\gamecore\simulator_output"
replay_dir = r"C:\hok_env\replay_tool\Replays"
abs_files = glob.glob(os.path.join(sim_out, "*.abs"))
if abs_files:
    latest = max(abs_files, key=os.path.getmtime)
    shutil.copy2(latest, replay_dir)
    print(f"\nABS saved: {os.path.basename(latest)} ({os.path.getsize(latest)} bytes)")
else:
    print("\nNo ABS generated")
