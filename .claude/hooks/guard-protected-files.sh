#!/usr/bin/env bash
# Block modifications to .env files and migration files
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r ".tool_input.file_path // empty")

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

case "$FILE_PATH" in
  *.env|*.env.*)
    echo "BLOCKED: Do not modify .env files directly" >&2
    exit 2
    ;;
  */prisma/migrations/*|*/alembic/versions/*)
    echo "BLOCKED: Do not modify migration files directly" >&2
    exit 2
    ;;
esac

exit 0
