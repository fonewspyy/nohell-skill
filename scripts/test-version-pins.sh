#!/usr/bin/env bash
# เทสของ check-version-pins.sh — ทุกทางที่มันควร "ดัง" ต้องดังจริง
#
# ทำไมต้องมี: รุ่นแรกของ check-version-pins.sh เงียบสองทาง และรุ่นที่สองพิมพ์ FAIL
# ทางจอแล้วคืน exit 0 เพราะธงอยู่ใน subshell — ทั้งสองรอบจับได้ด้วยการลองมือในเชลล์
# ซึ่งเป็นหลักฐานที่หายไปพร้อม session ⇒ ย้ายมาเป็นเทสที่รันซ้ำได้
#
# ⛔ เทสนี้ห้ามฮาร์ดโค้ดเลขรุ่น — อ่านจาก CHANGELOG เหมือนที่ตัวถูกทดสอบทำ
#    (test-build-summary.sh เคยฮาร์ดโค้ด 483 แล้วเงียบตอนแคตตาล็อกโตเป็น 488)
set -uo pipefail
cd "$(dirname "$0")/.."

CHK=scripts/check-version-pins.sh
pass=0
fail=0
SNAP=$(mktemp -d)
cp README.md README.en.md CHANGELOG.md "$SNAP/"

restore() { cp "$SNAP/README.md" "$SNAP/README.en.md" "$SNAP/CHANGELOG.md" .; }
run_rc() { bash "$CHK" >/dev/null 2>&1; echo $?; }

check() {                 # $1 ชื่อเคส · $2 exit ที่คาด · $3 rc ที่ได้
  if [ "$3" = "$2" ]; then printf 'ok    %s\n' "$1"; pass=$((pass + 1))
  else printf 'FAIL  %s — exit %s ควรเป็น %s\n' "$1" "$3" "$2"; fail=$((fail + 1)); fi
}

PIN_RE='(--branch|--pin) v[0-9]|nohell-skill\.git#v[0-9]'

# 0 — สภาพจริงต้องผ่าน ไม่งั้นเคสที่เหลืออ่านไม่ได้ความ
check "สภาพจริงในรีโปผ่าน" 0 "$(run_rc)"

# 1 — ไฟล์หายไปเลย ต้องดัง ไม่ใช่ข้ามเงียบ
mv README.md "$SNAP/moved"
check "README.md หายทั้งไฟล์" 1 "$(run_rc)"
mv "$SNAP/moved" README.md

# 2 — ไฟล์อยู่ แต่บล็อกคำสั่งติดตั้งถูกลบ (รุ่นแรกเงียบเคสนี้ ตอบ OK 4 จุด)
sed -i -E "/$PIN_RE/d" README.md
check "บล็อกติดตั้งใน README ถูกลบ" 1 "$(run_rc)"
restore

# 3 — ปักรุ่นผิดหนึ่งจุด (รุ่นที่สองพิมพ์ FAIL แต่คืน 0 เพราะธงอยู่ใน subshell)
cur=$(grep -oE '^## \[[0-9]+\.[0-9]+\.[0-9]+\]' CHANGELOG.md | head -1 | tr -d '#[] ')
if [ -z "$cur" ]; then
  printf 'FAIL  เตรียมเคส 3 ไม่ได้ — หาหัวข้อรุ่นใน CHANGELOG ไม่เจอ\n'; fail=$((fail + 1))
else
  sed -i "0,/--pin v$cur/s//--pin v9.9.9/" README.md
  check "ปักรุ่นผิดหนึ่งจุด" 1 "$(run_rc)"
  restore
fi

# 4 — สองภาษาเดินจากกัน (จำนวนจุดไม่เท่ากัน)
sed -i -E '0,/nohell-skill\.git#v[0-9]+\.[0-9]+\.[0-9]+/s///' README.md
check "สอง README จำนวนจุดไม่เท่ากัน" 1 "$(run_rc)"
restore

# 5 — หัวข้อรุ่นถูก reword จนตัวตรวจอ่านรุ่นไม่ออก
sed -i -E 's/^## \[([0-9]+\.[0-9]+\.[0-9]+)\]/## \1/' CHANGELOG.md
check "หัวข้อรุ่นใน CHANGELOG ถูก reword" 1 "$(run_rc)"
restore

# 6 — ประวัติรุ่นเก่าใน CHANGELOG ต้องไม่ถูกนับเป็นทะเบียน
#     (ตัวตรวจรุ่นแรกฟ้อง v0.9.0/v1.0.0 ในหัวข้อรุ่นเก่า ซึ่งเป็นบันทึก ห้ามแตะ)
if grep -qE '^## \[1\.0\.0\]' CHANGELOG.md && [ "$(run_rc)" = 0 ]; then
  printf 'ok    ประวัติรุ่นเก่าไม่ถูกนับเป็นทะเบียน\n'; pass=$((pass + 1))
else
  printf 'FAIL  ประวัติรุ่นเก่าถูกนับเป็นทะเบียน หรือหาหัวข้อ [1.0.0] ไม่เจอ\n'; fail=$((fail + 1))
fi

restore
rm -rf "$SNAP"
printf '\nผ่าน %d · ล้ม %d\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
