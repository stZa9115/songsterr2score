#!/usr/bin/env bash
# Stop hook: block ending the turn while tests are red.
# If we already blocked once this turn (stop_hook_active), let it stop so the
# agent can report a failure it could not fix instead of looping forever.
grep -q '"stop_hook_active": *true' && exit 0
cd "$CLAUDE_PROJECT_DIR" || exit 0
out=$(uv run pytest -q 2>&1) && exit 0
echo "$out" | tail -40 >&2
echo "測試未通過：修好再結束；若修不好，停下並回報失敗原因。" >&2
exit 2
