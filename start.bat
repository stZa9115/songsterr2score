@echo off
chcp 65001 >nul
pushd "%~dp0"
uv run python -m songsterr2score.server
popd
pause
