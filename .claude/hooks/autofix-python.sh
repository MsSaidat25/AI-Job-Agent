#!/usr/bin/env bash
# Auto-fix lint issues on saved Python files
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r ".tool_input.file_path // empty")

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

if [[ "$FILE_PATH" == *.py ]]; then
  cd backend && ruff check --fix "$FILE_PATH" 2>&1 || true
fi

exit 0
