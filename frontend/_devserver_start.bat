@echo off
cd /d D:\gitcangku\deepassetlens\frontend
set PORT=23000
set BROWSER=none
set ESLINT_NO_DEV_ERRORS=1
call npx react-scripts start > _devserver.log 2>&1
