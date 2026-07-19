# 1. 启动 gamecore（Windows PowerShell）
powershell.exe -Command "Start-Process -WindowStyle Hidden -FilePath 'D:\资料库\文档\THU\上课！\AI实践基石\HOK\gamecore\gamecore\gamecore-server.exe' -ArgumentList 'server','--server-address :23432' -WorkingDirectory 'D:\资料库\文档\THU\上课！\AI实践基石\HOK\gamecore\gamecore'"

# 等 15 秒

# 2. 跑 agent（默认参数：5 decisions, 2048 tokens）
docker exec hok bash -c "cd /hok_env/hok/hok1v1 && python3 -u /workspace/src/main_macro.py --decisions 5 --hero-ai 169 --hero-bot 112 --print-every 5"
