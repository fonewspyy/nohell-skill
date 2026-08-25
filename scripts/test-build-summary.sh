#!/bin/sh
# เทสของ scripts/build-summary.py — เคสที่รู้คำตอบ
#
# ตัวนี้ *เขียนทับเอกสาร 14 ไฟล์* จึงต้องมีเทส ไม่ใช่พึ่งการตรวจด้วยตาทีละครั้ง
# ทุกเคสทำสำเนา repo ลง temp แล้วยืนยันสองทางเสมอ:
#   ผิดแล้วต้องจับได้ · ถูกแล้วต้องไม่แตะ — เทสที่ดูแค่ "จับได้" หลอกตัวเองได้ (CONTRIBUTING)
#
# สามเคสในนี้มาจากบั๊กจริงที่เจอวันเดียวกัน B26 B29 B30 ไม่ได้แต่งขึ้น
#
#   sh scripts/test-build-summary.sh
set -u

ROOT=$(cd "$(dirname "$0")/.." && pwd)
PY=${PY:-python}
pass=0; fail=0

setup() {
  T=$(mktemp -d); SNAP=$(mktemp -d)
  mkdir -p "$T/scripts" "$T/skills/nohell"
  cp "$ROOT/scripts/build-summary.py" "$T/scripts/"
  for f in HELL-CATALOG.md hell-rules.yaml SKILL.md; do
    cp "$ROOT/skills/nohell/$f" "$T/skills/nohell/"
  done
  for f in README.md README.en.md CONTRIBUTING.md BACKLOG.md; do cp "$ROOT/$f" "$T/"; done
  snap
}
snap()      { rm -rf "$SNAP"; mkdir -p "$SNAP"; cp -a "$T/." "$SNAP/"; }
cleanup()   { rm -rf "$T" "$SNAP"; }
docheck()   { ( cd "$T" && $PY scripts/build-summary.py --check 2>&1 ); }
dobuild()   { ( cd "$T" && $PY scripts/build-summary.py 2>&1 ); }
unchanged() { diff -r -q "$T" "$SNAP" >/dev/null 2>&1; }

ok()  { pass=$((pass + 1)); printf 'ok    %s\n' "$1"; }
no()  { fail=$((fail + 1)); printf 'FAIL  %s — %s\n' "$1" "$2"; }

# 1 — ของที่ถูกอยู่แล้ว ต้องผ่านและต้องไม่แตะไฟล์
setup
out=$(docheck); rc=$?
if [ "$rc" != 0 ]; then no "ของถูกอยู่แล้วต้องผ่าน" "exit=$rc | $out"
else dobuild > /dev/null
  if unchanged; then ok "ของถูกอยู่แล้ว ผ่านและไม่แตะไฟล์"
  else no "ของถูกอยู่แล้ว ต้องไม่แตะไฟล์" "build เขียนทับทั้งที่ไม่มีอะไรผิด"; fi
fi
cleanup

# 2 — เลขต่อ stack ผิด ต้องจับได้ · แก้กลับได้เป๊ะ · และ *คีย์ต้องไม่ถูกเลขทับ*
#     ข้อหลังคือสิ่งที่ fact แบบ dict ทำพังได้ง่ายที่สุด เพราะ match ไม่ได้มีแต่ตัวเลขแล้ว
setup
sed -i 's/| `ML` | 13 |/| `ML` | 99 |/' "$T/skills/nohell/SKILL.md"
out=$(docheck); rc=$?
if [ "$rc" = 0 ]; then no "เลขต่อ stack ผิดต้องจับได้" "check ผ่านทั้งที่เลขผิด"
elif ! printf '%s' "$out" | grep -q 'จำนวนข้อต่อ stack'; then
  no "เลขต่อ stack ผิดต้องจับได้" "ฟ้องผิดเรื่อง: $out"
else
  dobuild > /dev/null
  if ! grep -q '| `ML` | 13 |' "$T/skills/nohell/SKILL.md"; then
    no "เลขต่อ stack ต้องแก้กลับได้" "$(grep '| `ML` |' "$T/skills/nohell/SKILL.md")"
  elif ! unchanged; then
    no "เลขต่อ stack แก้แล้วต้องเหมือนเดิมเป๊ะ" "$(diff -r "$SNAP" "$T" | head -4)"
  else ok "เลขต่อ stack ผิด จับได้ แก้กลับเป๊ะ คีย์ไม่โดนทับ"; fi
fi
cleanup

# 3 — ยอดรวมในร้อยแก้วผิด ต้องจับได้และแก้ให้ถูก (นี่คือ B26 ที่เคยเงียบมาสองรุ่น)
setup
sed -i 's/anti-pattern 483 ข้อ/anti-pattern 999 ข้อ/' "$T/README.md"
out=$(docheck); rc=$?
if [ "$rc" = 0 ]; then no "ยอดรวมผิดต้องจับได้" "check ผ่านทั้งที่เลขผิด"
else
  dobuild > /dev/null
  if unchanged; then ok "ยอดรวมในร้อยแก้วผิด จับได้และแก้กลับเป๊ะ"
  else no "ยอดรวมแก้แล้วต้องเหมือนเดิม" "$(diff -r "$SNAP" "$T" | head -4)"; fi
fi
cleanup

# 4 — ไฟล์บันทึกหลักฐานต้องไม่ถูกแตะ แม้ในนั้นจะมีเลขที่ตกยุคอยู่จริง (B29)
#     BACKLOG อ้างข้อความผิดของเดิมไว้ตรง ๆ ว่า "447 entries across 28 categories"
#     ถ้า generator เขียนทับ บันทึกจะกลายเป็นบอกว่าข้อความที่เคยผิดคือข้อความที่ถูก
setup
before=$(cat "$T/BACKLOG.md")
dobuild > /dev/null
if [ "$before" = "$(cat "$T/BACKLOG.md")" ]; then ok "ไฟล์บันทึก (BACKLOG) ไม่ถูกแตะ"
else no "ไฟล์บันทึกต้องไม่ถูกแตะ" "$(diff <(printf '%s' "$before") "$T/BACKLOG.md" | head -4)"; fi
cleanup

# 5 — วลีถูก reword จนยิงไม่โดน ต้องฟ้องดัง ๆ และ *ห้ามแตะไฟล์*
#     โหมดพังที่แย่กว่าเลขผิดคือตัวตรวจเงียบ เพราะไม่มีใครรู้ว่ามันมองไม่เห็นอะไร
setup
sed -i 's/ (74%)//' "$T/README.md" "$T/README.en.md"
snap
out=$(docheck); rc=$?
if [ "$rc" = 0 ]; then no "วลีหายต้องฟ้อง" "check ผ่านทั้งที่ pattern ยิงไม่โดนแล้ว"
elif ! printf '%s' "$out" | grep -q 'ต่ำกว่า'; then
  no "วลีหายต้องฟ้องว่าต่ำกว่าพื้น" "ฟ้องผิดเรื่อง: $out"
else
  dobuild > /dev/null
  if unchanged; then ok "วลีถูก reword จนยิงไม่โดน ฟ้องดังและไม่แตะไฟล์"
  else no "วลีหายแล้วห้ามแตะไฟล์" "$(diff -r "$SNAP" "$T" | head -4)"; fi
fi
cleanup

printf '\nผ่าน %d · ล้ม %d\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
