@echo off
chcp 65001 >nul
pushd "%~dp0"
uv run python -m songsterr2score %*
popd
echo.
echo Done. Output is in the "output" folder next to each html.
pause
