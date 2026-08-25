#!/bin/sh
# ตรวจว่า HELL-CATALOG.md และไฟล์ที่อ้างถึงมัน ยังสอดคล้องกันอยู่
# repo นี้ห้าม SSOT-01 กับคนอื่น ก็ต้องไม่ทำกับตัวเอง
set -u

CATALOG="${1:-skills/nohell/HELL-CATALOG.md}"
fail=0
say() { printf '%s\n' "$*"; }
bad() { say "FAIL  $*"; fail=1; }

[ -f "$CATALOG" ] || { say "FAIL  ไม่พบไฟล์ $CATALOG"; exit 1; }

ids=$(grep -oE '^\| [A-Z]+-[0-9]+' "$CATALOG" | sed 's/^| //')
total=$(printf '%s\n' "$ids" | grep -c .)
ncat=$(printf '%s\n' "$ids" | sed 's/-[0-9]*$//' | sort -u | grep -c .)
p1=$(grep -cE '^\| [A-Z]+-[0-9]+ \| P1 ' "$CATALOG")
p2=$(grep -cE '^\| [A-Z]+-[0-9]+ \| P2 ' "$CATALOG")
p3=$(grep -cE '^\| [A-Z]+-[0-9]+ \| P3 ' "$CATALOG")
skillmd=$(dirname "$CATALOG")/SKILL.md

# 1, 2 — (เลิกใช้ 2026-08-24 — ย้ายไป scripts/build-summary.py)
#     เลขในหัวไฟล์และเลขท้ายหัวข้อหมวดคำนวณจากแคตตาล็อกได้อยู่แล้ว จึง generate ทิ้งไป
#     ไม่ต้อง assert — ตอนนี้ตัวเลขที่ประกาศทุกตัว ทั้งในแคตตาล็อกและในเอกสาร
#     มีเจ้าของเดียวคือ build-summary.py ไม่แยกสองที่อีก

# 3 — ห้าม ID ซ้ำ
dupes=$(printf '%s\n' "$ids" | sort | uniq -d | tr '\n' ' ')
[ -z "$dupes" ] || bad "ID ซ้ำ: $dupes"

# 4 — เลขในแต่ละหมวดต้องเรียงต่อกันจาก 01 ไม่มีรู
gaps=$(printf '%s\n' "$ids" | sort -t- -k1,1 -k2,2n | awk -F- '
  { if ($1 != p) { p = $1; e = 1 }
    if ($2 + 0 != e) printf "%s-%02d ", $1, e
    e = $2 + 1 }')
[ -z "$gaps" ] || bad "เลขขาดช่วง (คาดว่าจะมี): $gaps"

# 5 — ทุกข้อต้องมีระดับ P1/P2/P3
noprio=$(grep -E '^\| [A-Z]+-[0-9]+ \|' "$CATALOG" \
         | grep -vE '^\| [A-Z]+-[0-9]+ \| P[123] \|' \
         | grep -oE '^\| [A-Z]+-[0-9]+' | sed 's/^| //' | tr '\n' ' ')
[ -z "$noprio" ] || bad "ไม่มีระดับ P1/P2/P3: $noprio"

# 6 — ทุกแถวต้องมีครบ 6 ช่อง และ "กฎแทน" กับ "ใช้กับ" ต้องไม่ว่าง
#     ในเนื้อความมี pipe ที่ escape ไว้ (\|) ซึ่งไม่ใช่ตัวแบ่งช่อง ต้องตัดทิ้งก่อนนับ
#     ใช้ index() ไม่ใช้ regex เพราะ [\] ใน gawk ไปจับ pipe ที่ไม่ได้ escape ด้วย
thin=$(awk '
  /^\| [A-Z]+-[0-9]+ \|/ {
    out = ""; rest = $0
    bs = sprintf("%c", 92)          # backslash โดยไม่ต้องเขียน escape ให้หายระหว่างทาง
    while ((at = index(rest, bs "|")) > 0) {
      out = out substr(rest, 1, at - 1)
      rest = substr(rest, at + 2)
    }
    out = out rest
    n = split(out, f, "|")
    gsub(/^[ \t]+|[ \t]+$/, "", f[6])
    gsub(/^[ \t]+|[ \t]+$/, "", f[7])
    if (n != 8 || f[6] == "" || f[7] == "") { gsub(/^[ \t]+|[ \t]+$/, "", f[2]); printf "%s ", f[2] }
  }' "$CATALOG")
[ -z "$thin" ] || bad "แถวไม่ครบช่อง หรือไม่มี 'กฎแทน': $thin"

# 7 — ทุก ID ที่ skill/docs อ้างถึง ต้องมีอยู่จริงในแคตตาล็อก
#     CONSOLIDATIONS.example.yaml ใช้เลขวงผูกปี (SSOT-2026-001) คนละ namespace จึงกันออก
if [ -d skills ]; then
  prefixes=$(printf '%s\n' "$ids" | sed 's/-[0-9]*$//' | sort -u | tr '\n' '|' | sed 's/|$//')
  refs=$(grep -rhowE "($prefixes)-[0-9]+" skills docs \
         --include='*.md' --include='*.yaml' --include='*.sql' \
         --exclude='CONSOLIDATIONS.example.yaml' --exclude="$(basename "$CATALOG")" \
         2>/dev/null | sort -u)
  dangling=$(printf '%s\n' "$refs" | grep -v '^$' \
             | grep -vxF "$(printf '%s\n' "$ids" | sort -u)" | tr '\n' ' ')
  [ -z "$dangling" ] || bad "มี ID ที่ถูกอ้างถึงแต่ไม่มีในแคตตาล็อก: $dangling"
fi

# 8 — (เลิกใช้ 2026-08-24 — ย้ายไป scripts/build-summary.py)
#     เดิมเป็น assertion ห้าชุดว่าตัวเลขที่เอกสารประกาศยังตรงกับของจริง ตอนนี้ build-summary.py
#     เป็นเจ้าของเรื่องนี้ทั้งหมด และมันแก้ให้ถูก ไม่ใช่แค่บอกว่าผิด ตาราง FACTS ในไฟล์นั้น
#     คือที่เดียวที่ประกาศว่าเลขไหนต้องตรงกับอะไร
#     ไม่ renumber ไม่ reuse เลข 8 ตามกฎการเลิกใช้แถวในแคตตาล็อก (CONTRIBUTING.md)

# 9 — pattern ที่ใช้ lookahead/lookbehind ต้องประกาศ engine: pcre2
#     ไม่งั้นตัวรันบน Rust regex/grep -E จะ parse error แล้ว gate เงียบ = ผ่านทุกอย่าง
rules="$(dirname "$CATALOG")/hell-rules.yaml"
if [ -f "$rules" ]; then
  unmarked=$(awk '
    /^  - id: / { if (id != "" && look && !pcre) printf "%s ", id; id = $3; look = 0; pcre = 0; next }
    /engine: pcre2/ { pcre = 1 }
    /pattern:/ {
      if (index($0, "(?=") || index($0, "(?!") || index($0, "(?<")) look = 1
    }
    END { if (id != "" && look && !pcre) printf "%s ", id }
  ' "$rules")
  [ -z "$unmarked" ] || bad "pattern ใช้ lookaround แต่ไม่ได้ประกาศ engine: pcre2 — gate จะเงียบบน rg/grep ปกติ: $unmarked"
fi

# 10 — คำอ้างขนาด token ของไฟล์ที่ "โหลดตลอด" ต้องยังตรงกับขนาดจริง
#      เนื้อหาผสมไทย/อังกฤษของ repo นี้ ≈ 3.4 ไบต์ต่อ token (วัดจากสัดส่วนอักขระไทย)
if [ -f "$skillmd" ]; then
  declared=$(grep -oE 'โหลดตลอด, ~[0-9]+–[0-9]+k' "$skillmd" | grep -oE '[0-9]+–[0-9]+')
  if [ -n "$declared" ]; then
    lo=${declared%%–*}; hi=${declared##*–}
    est=$(( $(wc -c < "$skillmd") / 3400 ))
    if [ "$est" -lt "$lo" ] || [ "$est" -gt "$hi" ]; then
      bad "$skillmd อ้างว่า ~${lo}–${hi}k tokens แต่ประมาณจากขนาดไฟล์จริงได้ ~${est}k"
    fi
  fi
fi

# 11 — ค่าในช่อง "ใช้กับ" ต้องอยู่ในชุดที่อนุญาต ไม่งั้น router กรองตาม stack ไม่ได้
badstack=$(awk -v ok="|ทุกที่|RDBMS|SQL Server|มี SP|TS/JS|.NET|เว็บ|mobile|ML|" '
  /^\| [A-Z]+-[0-9]+ \|/ {
    out = ""; rest = $0
    bs = sprintf("%c", 92)
    while ((at = index(rest, bs "|")) > 0) {
      out = out substr(rest, 1, at - 1)
      rest = substr(rest, at + 2)
    }
    out = out rest
    n = split(out, f, "|")
    if (n == 8) {
      v = f[7]; gsub(/^[ \t]+|[ \t]+$/, "", v)
      if (index(ok, "|" v "|") == 0) { gsub(/^[ \t]+|[ \t]+$/, "", f[2]); printf "%s(%s) ", f[2], v }
    }
  }' "$CATALOG")
[ -z "$badstack" ] || bad "ช่อง 'ใช้กับ' มีค่าที่ไม่อยู่ในชุดที่อนุญาต: $badstack"

# 12 — severity ใน hell-rules.yaml ต้องเดินตามแคตตาล็อก ห้ามมีสองแหล่งที่ไม่ตรงกัน
if [ -f "$rules" ]; then
  sevmiss=$(awk '
    FNR == NR {
      if ($0 ~ /^\| [A-Z]+-[0-9]+ \| P[123] \|/) {
        split($0, f, "|"); id = f[2]; sv = f[3]
        gsub(/^[ 	]+|[ 	]+$/, "", id); gsub(/^[ 	]+|[ 	]+$/, "", sv)
        cat[id] = sv
      }
      next
    }
    /^  - id: / { cur = $3; next }
    /^    severity: / { if (cur != "" && cat[cur] != "" && cat[cur] != $2) printf "%s(กฎ %s/แคตตาล็อก %s) ", cur, $2, cat[cur]; cur = "" }
  ' "$CATALOG" "$rules")
  [ -z "$sevmiss" ] || bad "severity ใน hell-rules ไม่ตรงกับแคตตาล็อก: $sevmiss"
fi

# 13 — pattern ที่จับข้ามบรรทัด (มี \n เป็นสิ่งที่ต้อง match) ต้องประกาศ multiline: true
#      เหตุผลเดียวกับข้อ 9: rg ปกติ parse error แล้วถ้าตัวรันกลืน error gate จะรายงาน 0
#      ทั้งที่มีของจริง — วัดแล้ว SQL-26 หายไป 11 hit ใน 7 ไฟล์
#      ต้องตัด [^...] ออกก่อนตรวจ เพราะ [^\n] "กัน" บรรทัดใหม่ ไม่ได้ "match" มัน จึงไม่ต้องใช้ -U
if [ -f "$rules" ]; then
  nomulti=$(awk '
    /^  - id: / { if (id != "" && need && !ml) printf "%s ", id; id = $3; need = 0; ml = 0; next }
    /multiline: true/ { ml = 1 }
    /pattern:/ {
      bs = sprintf("%c", 92)
      esc = bs bs "n"                          # สามอักขระดิบที่อยู่ในไฟล์
      s = $0
      while ((a = index(s, "[^")) > 0) {       # ตัด negated class ทิ้งก่อน
        rest = substr(s, a + 2)
        b = index(rest, "]")
        if (b == 0) break
        s = substr(s, 1, a - 1) substr(rest, b + 1)
      }
      if (index(s, esc) > 0) need = 1
    }
    END { if (id != "" && need && !ml) printf "%s ", id }
  ' "$rules")
  [ -z "$nomulti" ] || bad "pattern จับข้ามบรรทัดแต่ไม่ได้ประกาศ multiline: true — gate จะเงียบบน rg ปกติ: $nomulti"
fi

if [ "$fail" -eq 0 ]; then
  say "OK    $total ข้อ · $ncat หมวด · P1 $p1 · P2 $p2 · P3 $p3 · สอดคล้องกันทั้งหมด"
else
  say ""
  say "แคตตาล็อกไม่สอดคล้องกับตัวเอง — แก้ก่อน commit"
fi
exit "$fail"
