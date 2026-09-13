#!/bin/sh
# ด่านกันพาธเครื่องและข้อมูลส่วนตัวหลุดขึ้นรีโป — รีโปนี้เป็น **public**
#
# ทำไมต้องมี: รีโปนี้ผลิตเอกสารที่เต็มไปด้วยหลักฐานจากการวัดจริง ซึ่งมีพาธเต็ม
# ชื่อผู้ใช้ และ session id ติดมาเป็นธรรมชาติ วัดมาแล้ว 2026-09-13: มีชื่อผู้ใช้ของ
# เจ้าของเครื่องหลุดอยู่ 4 จุดใน 3 ไฟล์เอกสาร โดยไม่มีใครสังเกต
# (ไม่ใช่ credential แต่เป็นข้อมูลเครื่องที่เจ้าของไม่ได้ขอให้เผยแพร่)
#
#   sh scripts/check-no-local-paths.sh
#
# แพทเทิร์นตั้งใจให้จับ **รูปร่างของพาธ** ไม่ใช่ชื่อคนใดคนหนึ่ง จะได้ใช้ได้กับทุกเครื่อง
set -eu
cd "$(dirname "$0")/.."

fail=0
report() {
  printf 'พบ %s\n' "$1"
  printf '%s\n' "$2" | sed 's/^/  /'
  fail=1
}

# 1. พาธ home ของ Windows/POSIX ที่มีชื่อผู้ใช้จริง
#    ยกเว้นรูปที่ใส่ placeholder ไว้แล้ว เช่น C:\Users\<user>\ หรือ /home/<user>/
hits=$(git grep -n -I -E '([A-Za-z]:[\\/]+Users[\\/]+|/home/|/Users/)[A-Za-z0-9_.-]+' -- . \
  | grep -v -E '<user>|<USER|<CLAUDE_CONFIG_DIR>|<pools-dir>|<TEMP>|Users[\\/]+(x|you|me|someone)\b' \
  | grep -v '^scripts/check-no-local-paths.sh:' || true)
[ -n "$hits" ] && report 'พาธ home ที่มีชื่อผู้ใช้จริง (ใช้ <user> แทน)' "$hits"

# 2. โครงสร้าง pool ของ claude-orchestrator พร้อมชื่อ pool จริง
hits=$(git grep -n -I -E '\.claude-pools[\\/]+[A-Za-z0-9_]+' -- . \
  | grep -v -E '<pool>|<pools-dir>' \
  | grep -v '^scripts/check-no-local-paths.sh:' || true)
[ -n "$hits" ] && report 'พาธ .claude-pools พร้อมชื่อ pool จริง (ใช้ <pool> แทน)' "$hits"

# 3. session id ของ Claude Code (uuid v4 เต็มรูป) — ระบุเซสชันของเจ้าของเครื่องได้
hits=$(git grep -n -I -E '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' -- . \
  | grep -v '^scripts/check-no-local-paths.sh:' || true)
[ -n "$hits" ] && report 'uuid เต็มรูป (น่าจะเป็น session id — ใช้ <session-id> แทน)' "$hits"

# 4. รูปร่างของ credential ที่ต้องไม่มีวันอยู่ในรีโป
hits=$(git grep -n -I -E 'sk-ant-[A-Za-z0-9_-]{8,}|ORCHESTRATOR_TOKEN=[^<$"'"'"']' -- . \
  | grep -v '^scripts/check-no-local-paths.sh:' || true)
[ -n "$hits" ] && report '**รูปร่างของ token/credential**' "$hits"

if [ "$fail" -eq 0 ]; then
  echo 'OK    ไม่พบพาธเครื่อง ชื่อผู้ใช้ session id หรือรูปร่าง credential ในไฟล์ที่ track'
  exit 0
fi
echo
echo 'รีโปนี้เป็น public — แทนที่ด้วย placeholder แล้วรันซ้ำ'
echo 'ถ้าเป็นการอ้างอิงที่จำเป็นจริง ให้เขียนเป็นรูปทั่วไป เช่น <CLAUDE_CONFIG_DIR>/projects/<project-slug>'
exit 1
