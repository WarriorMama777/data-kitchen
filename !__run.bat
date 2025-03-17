@echo off
title VirtualEnv Activated Console
cd /d %~dp0
call .\venv\Scripts\activate
cmd /k "cd /d %~dp0"
