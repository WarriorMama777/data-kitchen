@echo off
title VirtualEnv Activated Console
cd /d %~dp0
call .\venv-torch\Scripts\activate
cmd /k "cd /d %~dp0"
