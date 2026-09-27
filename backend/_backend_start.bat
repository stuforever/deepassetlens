@echo off
cd /d D:\gitcangku\deepassetlens\backend
set ENABLE_AUTH=1
set PYTHONUTF8=1
call python __start_8000.py > _backend28000.log 2>&1
