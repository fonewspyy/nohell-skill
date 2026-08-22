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

# 1 — ตัวเลขในหัวไฟล์ต้องเท่ากับจำนวน row จริง
titled=$(sed -n '1s/.*— \([0-9]*\) .*/\1/p' "$CATALOG")
[ "$titled" = "$total" ] || bad "หัวไฟล์บอก ${titled:-ไม่ระบุ} ข้อ แต่นับ row ได้ $total"

# 2 — ตัวเลขท้ายหัวข้อหมวดต้องเท่ากับจำนวน row ในหมวดนั้น
hdrmiss=$(awk '
  /^## [A-Z]+ / {
    c = $2
    declared[c] = match($0, /\([0-9]+\)[ \t]*$/) ? substr($0, RSTART + 1, RLENGTH - 2) : "?"
    sub(/[^0-9?]*$/, "", declared[c])
    order[++n] = c
    next
  }
  /^\| [A-Z]+-[0-9]+ \|/ { split($2, p, "-"); actual[p[1]]++ }
  END {
    for (i = 1; i <= n; i++)
      if (declared[order[i]] != actual[order[i]] + 0)
        printf "%s(%s/%d) ", order[i], declared[order[i]], actual[order[i]]
  }' "$CATALOG")
[ -z "$hdrmiss" ] || bad "จำนวนท้ายหัวข้อหมวดไม่ตรง (หัวข้อ/จริง): $hdrmiss"

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

# 8 — ตัวเลขที่ประกาศไว้ในไฟล์อื่นต้องตรงกับของจริง (ดริฟต์มาแล้วสามรอบ)
wrongcat=$(grep -rhoE '[0-9]+ หมวด' skills docs ./*.md 2>/dev/null \
           | grep -oE '^[0-9]+' | sort -u | grep -vx "$ncat" | tr '\n' ' ')
[ -z "$wrongcat" ] || bad "มีไฟล์เขียนจำนวนหมวดผิด (จริง $ncat): $wrongcat"

skillmd=$(dirname "$CATALOG")/SKILL.md
if [ -f "$skillmd" ]; then
  # เลขแคตตาล็อกเป็นสามหลักเสมอ "กฎแกน 12 ข้อ" จึงไม่โดนจับ
  wrongn=$(grep -oE '[0-9]{3,} ข้อ' "$skillmd" | grep -oE '^[0-9]+' \
           | sort -u | grep -vx "$total" | tr '\n' ' ')
  [ -z "$wrongn" ] || bad "$skillmd เขียนจำนวนข้อผิด (จริง $total): $wrongn"
fi

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
badstack=$(awk -v ok="|ทุกที่|RDBMS|SQL Server|มี SP|TS/JS|.NET|เว็บ|" '
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

if [ "$fail" -eq 0 ]; then
  p1=$(grep -cE '^\| [A-Z]+-[0-9]+ \| P1 ' "$CATALOG")
  p2=$(grep -cE '^\| [A-Z]+-[0-9]+ \| P2 ' "$CATALOG")
  p3=$(grep -cE '^\| [A-Z]+-[0-9]+ \| P3 ' "$CATALOG")
  say "OK    $total ข้อ · $ncat หมวด · P1 $p1 · P2 $p2 · P3 $p3 · สอดคล้องกันทั้งหมด"
else
  say ""
  say "แคตตาล็อกไม่สอดคล้องกับตัวเอง — แก้ก่อน commit"
fi
exit "$fail"
