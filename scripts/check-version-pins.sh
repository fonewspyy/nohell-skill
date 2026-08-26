#!/usr/bin/env bash
# คำสั่งติดตั้งที่ "ใช้อยู่ตอนนี้" ต้องปักรุ่นเดียวกัน และตรงกับรุ่นล่าสุดใน CHANGELOG.md
#
# ⛔ แยก **ทะเบียน** ออกจาก **บันทึก** ให้ชัด — นี่คือจุดที่ตัวตรวจรุ่นแรกพลาด
#    ทะเบียน (ต้องตรงกับรุ่นปัจจุบัน เขียนทับได้):
#      · README.md / README.en.md — บรรทัดคำสั่งติดตั้ง
#      · CHANGELOG.md — เฉพาะส่วนหัว **ก่อน** หัวข้อรุ่นแรก
#    บันทึก (ห้ามแตะ):
#      · CHANGELOG.md ใต้หัวข้อ `## [x.y.z]` — เป็นสำเนาของคำสั่งตอนรุ่นนั้น
#      · เวอร์ชันของเครื่องมืออื่น เช่น "GitHub CLI v2.90.0" ไม่ใช่การปักรุ่นของรีโปนี้
#
# ทำไมไม่ผูกกับ git tag: tag ยังไม่มีตอนคอมมิต release จึงเช็คไม่ได้ในจังหวะที่ต้องเช็ค
# หัวข้อรุ่นล่าสุดใน CHANGELOG คือสิ่งที่ตัดสินว่ากำลังจะปล่อยอะไร — ผูกกับตัวนั้น
#
# 🪤 เจ็ดจุดนี้ตรงกันมาทุกรุ่นเพราะมีคนจำได้ ไม่ใช่เพราะมีอะไรบังคับ
set -uo pipefail
cd "$(dirname "$0")/.."

want=$(grep -oE '^## \[[0-9]+\.[0-9]+\.[0-9]+\]' CHANGELOG.md | head -1 | tr -d '#[] ')
if [ -z "$want" ]; then
  echo "FAIL  หาหัวข้อรุ่นใน CHANGELOG.md ไม่เจอ — รูปแบบเปลี่ยน ตัวตรวจนี้กำลังเงียบ"
  exit 1
fi

# บรรทัดที่เป็นคำสั่งติดตั้งของรีโปนี้เท่านั้น — ไม่จับเวอร์ชันเครื่องมืออื่น
PIN='(--branch|--pin) v[0-9]+\.[0-9]+\.[0-9]+|nohell-skill\.git#v[0-9]+\.[0-9]+\.[0-9]+'

emit_registry() {
  grep -nE "$PIN" README.md    | sed 's|^|README.md:|'
  grep -nE "$PIN" README.en.md | sed 's|^|README.en.md:|'
  # CHANGELOG: ตัดที่หัวข้อรุ่นแรก ใต้นั้นเป็นบันทึก
  awk '/^## \[[0-9]+\.[0-9]+\.[0-9]+\]/{exit} {print FILENAME":"NR":"$0}' CHANGELOG.md | grep -E "$PIN"
}

bad=0
seen=0
while IFS= read -r line; do
  [ -z "$line" ] && continue
  seen=$((seen + 1))
  got=$(printf '%s' "$line" | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+' | head -1)
  if [ "$got" != "v$want" ]; then
    echo "FAIL  $(printf '%s' "$line" | cut -d: -f1-2) ปัก $got ไม่ใช่ v$want"
    bad=1
  fi
done < <(emit_registry)

if [ "$seen" -eq 0 ]; then
  echo "FAIL  ไม่เจอจุดปักรุ่นเลย — วลีติดตั้งถูก reword ตัวตรวจนี้กำลังเงียบ"
  exit 1
fi

if [ "$bad" -eq 0 ]; then
  echo "OK    ปักรุ่นตรงกัน $seen จุด · v$want"
else
  exit 1
fi
