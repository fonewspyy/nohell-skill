#!/usr/bin/env bash
# คำสั่งติดตั้งที่ "ใช้อยู่ตอนนี้" ต้องปักรุ่นเดียวกัน และตรงกับรุ่นล่าสุดใน CHANGELOG.md
#
# ⛔ แยก **ทะเบียน** ออกจาก **บันทึก** ให้ชัด — จุดที่ตัวตรวจรุ่นแรกพลาด
#    ทะเบียน (ต้องตรงกับรุ่นปัจจุบัน เขียนทับได้):
#      · README.md / README.en.md — บรรทัดคำสั่งติดตั้ง
#      · CHANGELOG.md — เฉพาะส่วนหัว **ก่อน** หัวข้อรุ่นแรก
#    บันทึก (ห้ามแตะ):
#      · CHANGELOG.md ใต้หัวข้อ `## [x.y.z]` — สำเนาของคำสั่งตอนรุ่นนั้น
#      · เวอร์ชันของเครื่องมืออื่น เช่น "GitHub CLI v2.90.0" ไม่ใช่การปักรุ่นของรีโปนี้
#
# ทำไมไม่ผูกกับ git tag: tag ยังไม่มีตอนคอมมิต release จึงเช็คไม่ได้ในจังหวะที่ต้องเช็ค
# หัวข้อรุ่นล่าสุดใน CHANGELOG คือสิ่งที่ตัดสินว่ากำลังจะปล่อยอะไร — ผูกกับตัวนั้น
#
# 🪤 **รุ่นแรกของไฟล์นี้เงียบเองสองทาง** (จับได้ตอนรีวิวตัวเอง 2026-08-26):
#    ลบ README.md ทั้งไฟล์ -> exit 0 · ลบเฉพาะบล็อกคำสั่งติดตั้ง -> `OK 4 จุด` exit 0
#    เพราะนับ "ยอดรวมทุกไฟล์" ถ้าไฟล์หนึ่งให้ 0 แต่ไฟล์อื่นให้ 4 มันก็ยังผ่าน
#    ⇒ ต้องนับ **ต่อไฟล์** และใช้ค่าคงตัวเชิงโครงสร้าง ไม่ใช่ตัวเลขฮาร์ดโค้ด
#      (ฮาร์ดโค้ด "README ต้องมี 3 จุด" คือบั๊กเดียวกับที่ test-build-summary เคยมี)
#      ค่าคงตัวที่ใช้: สอง README ต้องมีจำนวนจุดเท่ากันและมากกว่าศูนย์ · หัว CHANGELOG ต้องมีอย่างน้อยหนึ่ง
set -uo pipefail
cd "$(dirname "$0")/.."

fail() { echo "FAIL  $1"; exit 1; }

for f in CHANGELOG.md README.md README.en.md; do
  [ -f "$f" ] || fail "ไม่พบ $f — ไฟล์ถูกย้ายหรือเปลี่ยนชื่อ ตัวตรวจนี้จะเงียบถ้าไม่ดัง"
done

want=$(grep -oE '^## \[[0-9]+\.[0-9]+\.[0-9]+\]' CHANGELOG.md | head -1 | tr -d '#[] ')
[ -n "$want" ] || fail "หาหัวข้อรุ่นใน CHANGELOG.md ไม่เจอ — รูปแบบเปลี่ยน ตัวตรวจนี้กำลังเงียบ"

# บรรทัดที่เป็นคำสั่งติดตั้งของรีโปนี้เท่านั้น — ไม่จับเวอร์ชันเครื่องมืออื่น
PIN='(--branch|--pin) v[0-9]+\.[0-9]+\.[0-9]+|nohell-skill\.git#v[0-9]+\.[0-9]+\.[0-9]+'

# หัว CHANGELOG = ทุกอย่างก่อนหัวข้อรุ่นแรก
changelog_head() { awk '/^## \[[0-9]+\.[0-9]+\.[0-9]+\]/{exit} {print}' CHANGELOG.md; }

# 🪤 รุ่นก่อนหน้าเรียกตัวตรวจใน `$(...)` ซึ่งเป็น subshell — ธง bad ไม่ทะลุกลับ
#    ผลคือมันพิมพ์ FAIL ทางจอแล้วคืน exit 0 ซึ่งเป็นความเงียบชนิดที่แย่ที่สุด
#    เพราะ CI อ่าน exit code ไม่ใช่จอ ⇒ ลูปตัดสินต้องอยู่ใน shell หลักเท่านั้น
pins_of() {               # $1 ชื่อรายงาน · $2 เนื้อหา — พิมพ์ "ชื่อ<TAB>บรรทัด" ต่อจุดที่เจอ
  printf '%s' "$2" | grep -E "$PIN" 2>/dev/null | while IFS= read -r l; do
    printf '%s\t%s\n' "$1" "$l"
  done
}

reg=$( { pins_of "README.md" "$(cat README.md)"
         pins_of "README.en.md" "$(cat README.en.md)"
         pins_of "CHANGELOG.md (หัว)" "$(changelog_head)"; } )

n_th=$(printf '%s\n' "$reg" | grep -c '^README\.md	' || true)
n_en=$(printf '%s\n' "$reg" | grep -c '^README\.en\.md	' || true)
n_cl=$(printf '%s\n' "$reg" | grep -c '^CHANGELOG\.md ' || true)

bad=0
while IFS=$'\t' read -r name line; do
  [ -z "${line:-}" ] && continue
  got=$(printf '%s' "$line" | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+' | head -1)
  [ "$got" = "v$want" ] || { echo "FAIL  $name ปัก $got ไม่ใช่ v$want"; bad=1; }
done < <(printf '%s\n' "$reg")

[ "$n_th" -gt 0 ] || fail "README.md ไม่มีบรรทัดคำสั่งติดตั้งเลย — บล็อกถูกลบหรือ reword"
[ "$n_en" -gt 0 ] || fail "README.en.md ไม่มีบรรทัดคำสั่งติดตั้งเลย — บล็อกถูกลบหรือ reword"
[ "$n_cl" -gt 0 ] || fail "หัว CHANGELOG.md ไม่มีคำสั่งติดตั้ง — วลีถูก reword"
[ "$n_th" = "$n_en" ] || fail "README.md มี $n_th จุด แต่ README.en.md มี $n_en จุด — สองภาษาเดินจากกันแล้ว"

[ "$bad" -eq 0 ] || exit 1
echo "OK    ปักรุ่นตรงกัน $((n_th + n_en + n_cl)) จุด · v$want  (th $n_th · en $n_en · changelog $n_cl)"
