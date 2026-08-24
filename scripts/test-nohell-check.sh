#!/bin/sh
# เทสของ scripts/nohell-check.py — เคส diff ที่รู้คำตอบ (เกณฑ์ผ่าน Phase 3 ข้อ 1)
#
# ทุกเคสสร้าง repo ชั่วคราวใหม่ ใส่ diff ที่รู้คำตอบ แล้วยืนยันสองอย่าง:
#   exit code ที่ควรได้ · ID ที่ควร/ไม่ควรโผล่ในรายงาน
# ตรวจทั้งสองทางเสมอ เพราะเทสที่ดูแค่ "จับได้" หลอกตัวเองได้ (CONTRIBUTING)
#
#   sh scripts/test-nohell-check.sh
set -u

ROOT=$(cd "$(dirname "$0")/.." && pwd)
CHECK="$ROOT/scripts/nohell-check.py"
YAML="$ROOT/skills/nohell/hell-rules.yaml"
PY=${PY:-python}
pass=0; fail=0

setup() {                       # สร้าง repo ชั่วคราวที่มี commit ตั้งต้นหนึ่งอัน
  T=$(mktemp -d)
  mkdir -p "$T/skills/nohell" "$T/scripts"
  cp "$YAML" "$T/skills/nohell/"
  cp "$CHECK" "$T/scripts/"
  ( cd "$T" && git init -q && git config user.email t@t && git config user.name t && git config core.autocrlf false \
    && printf 'SELECT 1;\n' > base.sql && git add -A && git commit -qm base )
}

# check <ชื่อเคส> <exit ที่คาด> <ID ที่ต้องมี|-> <ID ที่ต้องไม่มี|->
check() {
  name=$1; want=$2; must=$3; mustnot=$4
  out=$( cd "$T" && $PY scripts/nohell-check.py --base HEAD 2>&1 ); rc=$?
  ok=1
  # traceback ทำให้ exit เป็น 1 ได้เหมือนกับ "เจอกฎที่ block" ⇒ เคสที่คาด 1 จะผ่านทั้งที่เครื่องมือพัง
  # เจอมาแล้วจริง: keep.append() ใส่ค่าไม่ครบ แต่เทส 6 เคสยังขึ้น ok
  if printf '%s' "$out" | grep -q 'Traceback'; then
    ok=0; why="เครื่องมือ crash (Traceback) ไม่ใช่ผลตรวจ"
  fi
  [ "$rc" = "$want" ] || { ok=0; why="exit=$rc คาด $want"; }
  if [ "$must" != "-" ] && ! printf '%s' "$out" | grep -q "$must"; then
    ok=0; why="ไม่เจอ $must ในรายงาน"
  fi
  if [ "$mustnot" != "-" ] && printf '%s' "$out" | grep -q "$mustnot"; then
    ok=0; why="เจอ $mustnot ที่ไม่ควรมี"
  fi
  if [ "$ok" = 1 ]; then
    pass=$((pass+1)); printf 'ok    %s\n' "$name"
  else
    fail=$((fail+1)); printf 'FAIL  %s — %s\n' "$name" "$why"
    printf '%s\n' "$out" | sed 's/^/        /'
  fi
  rm -rf "$T"
}

# 1 — เพิ่ม NOLOCK ในไฟล์ .sql ต้อง block (SQL-15 = P1)
setup
printf 'SELECT a FROM t WITH (NOLOCK);\n' >> "$T/base.sql"
( cd "$T" && git add -A )
check 'NOLOCK บนบรรทัดที่เพิ่ม -> block' 1 'SQL-15' '-'

# 2 — เพิ่ม SELECT * ต้อง block (SQL-05 = P1)
setup
printf 'SELECT * FROM orders;\n' >> "$T/base.sql"
( cd "$T" && git add -A )
check 'SELECT * บนบรรทัดที่เพิ่ม -> block' 1 'SQL-05' '-'

# 3 — NOLOCK ในไฟล์ที่ไม่ตรง glob (**/*.sql) ต้องไม่ฟ้อง
setup
printf 'ตัวอย่างในเอกสาร: SELECT a FROM t WITH (NOLOCK)\n' > "$T/doc.md"
( cd "$T" && git add -A )
check 'NOLOCK ใน .md (ไม่ตรง glob) -> ไม่ฟ้อง' 0 '-' 'SQL-15'

# 4 — ของเดิมมี NOLOCK อยู่แล้ว แต่ diff แก้บรรทัดอื่น ต้องไม่ฟ้อง (diff-only ไม่ตัดสินโค้ดเก่า)
setup
printf 'SELECT a FROM t WITH (NOLOCK);\n' >> "$T/base.sql"
( cd "$T" && git add -A && git commit -qm "ของเดิมมี NOLOCK" )
printf 'SELECT 2;\n' >> "$T/base.sql"
( cd "$T" && git add -A )
check 'NOLOCK บนบรรทัดเดิม แก้บรรทัดอื่น -> ไม่ฟ้อง' 0 '-' 'SQL-15'

# 5 — allow_comment ต้องยกเว้นให้ (SQL-04 ประกาศ nohell-allow: SQL-04)
setup
printf 'EXEC (@sql); -- nohell-allow: SQL-04\n' >> "$T/base.sql"
( cd "$T" && git add -A )
check 'allow_comment ยกเว้น SQL-04' 0 '-' 'SQL-04'
setup
printf 'EXEC (@sql);\n' >> "$T/base.sql"
( cd "$T" && git add -A )
check 'ไม่มี allow_comment -> SQL-04 ฟ้อง' 1 'SQL-04' '-'

# 6 — กฎ multiline (SQL-26) ต้องจับข้ามบรรทัดได้ ไม่ตายเงียบ
#     SQL-26 เป็น P2 และ gate.block_on = [P1] ⇒ ผลที่ถูกคือ WARN + exit 0 ไม่ใช่ block
setup
printf 'WHILE (@i < 10)\nBEGIN\n  UPDATE t SET a = 1;\nEND\n' >> "$T/base.sql"
( cd "$T" && git add -A )
check 'multiline SQL-26 จับข้ามบรรทัด (P2 -> warn)' 0 'WARN   SQL-26' '-'

# 7 — pattern ที่ compile ไม่ผ่าน ต้อง exit 2 ห้ามกลืนเป็น 0
setup
$PY - "$T/skills/nohell/hell-rules.yaml" <<'PY'
import io, sys
p = sys.argv[1]
s = io.open(p, encoding='utf-8').read()
old = 'pattern: "(?i)(WITH'
i = s.index(old)
j = s.index('"', i + len('pattern: "'))
s = s[:i] + 'pattern: "(?i)(unclosed' + s[j:]
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
PY
printf 'SELECT 3;\n' >> "$T/base.sql"
( cd "$T" && git add -A )
check 'pattern พัง -> exit 2 (ไม่กลืน)' 2 'รันไม่ผ่าน' '-'

# 7b — skip_comments: SELECT * ที่ถูก comment ทิ้ง ต้องไม่ฟ้อง (SQL-05 ประกาศ skip_comments)
setup
printf -- '--SELECT * FROM OldTable;\n' >> "$T/base.sql"
( cd "$T" && git add -A )
check 'skip_comments ข้ามโค้ดที่ comment ทิ้ง' 0 '-' 'SQL-05'

# 7c — แต่ของจริงบนบรรทัดเดียวกับคอมเมนต์ท้ายบรรทัด ต้องยังฟ้อง (ตรวจสองทาง)
setup
printf 'SELECT * FROM Orders; -- ของจริง ไม่ใช่คอมเมนต์\n' >> "$T/base.sql"
( cd "$T" && git add -A )
check 'skip_comments ไม่กลืนของจริงที่มีคอมเมนต์ท้ายบรรทัด' 1 'SQL-05' '-'

# 8 — .nohellignore ต้องยกเว้นไฟล์ที่ระบุ
setup
printf 'base.sql\n' > "$T/.nohellignore"
printf 'SELECT a FROM t WITH (NOLOCK);\n' >> "$T/base.sql"
( cd "$T" && git add -A )
check '.nohellignore ยกเว้นไฟล์ที่ระบุ' 0 '-' 'SQL-15'

# 9 — .nohellignore ต้องไม่กวาดเกินไปถึงไฟล์ที่ไม่ได้ระบุ (ตรวจสองทาง)
setup
printf 'other/path.sql\n' > "$T/.nohellignore"
printf 'SELECT a FROM t WITH (NOLOCK);\n' >> "$T/base.sql"
( cd "$T" && git add -A )
check '.nohellignore ไม่กวาดไฟล์อื่น' 1 'SQL-15' '-'

printf '\nผ่าน %d · ล้ม %d\n' "$pass" "$fail"
[ "$fail" = 0 ] || exit 1
