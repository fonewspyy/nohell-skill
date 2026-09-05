# -*- coding: utf-8 -*-
"""เทสของ BLOCKED_RE — ด่านที่กันคำตอบซึ่ง "ไม่ใช่คำตอบ" ไม่ให้ลงธนาคาร

    python eval/test_blocked.py

ทำไมด่านนี้ต้องมีเทส: มันเป็นตัวชี้ขาดว่าตัวเลขไหนนับ ตัวเลขไหนทิ้ง
วัดมาแล้วว่าถ้ามันพลาด ผลจะเพี้ยนพอที่จะพลิกข้อสรุปของการทดลอง
  · แขน full_ask รอบ c9  ปนเปื้อน 7/46 — ถ้าไม่กันออกจะอ่านว่า recall ตก 11.8 จุด
  · แขน full_ask รอบ c9b ปนเปื้อน 2/46 — ตัวหนึ่ง (b01) หลุดด่านรุ่นแรกไปได้
    แล้วทำให้ recall ของรอบนั้นตก 7.1 จุด ซึ่งเกือบถูกอ่านว่าเป็น "ต้นทุนของการสั่งให้ถาม"

**ตัวอย่างทั้งหมดข้างล่างเป็นคำตอบจริงที่ธนาคารเคยเก็บไว้** ไม่ได้แต่งขึ้น
โมเดลเปลี่ยนสำนวนทุกครั้ง และมีทั้งไทยและอังกฤษ ⇒ การไล่แจงคำจึงแพ้เสมอ
ด่านจึงจับ **รูปร่าง** และบังคับว่าต้องผิดรูปด้วย

⚠️ เทสนี้ต้องผ่าน **ทั้งสองทิศ** — ทิ้งของที่ควรทิ้ง และไม่ทิ้งของที่ควรเก็บ
ถ้าเทสแต่ทิศเดียว ด่านที่ทิ้งทุกอย่างก็จะ "ผ่าน"
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run import BLOCKED_RE, parse_answer  # noqa: E402

# (ชื่อ, ข้อความ, ควรถูกทิ้งไหม)
SAMPLES = [
    # ── ต้องถูกทิ้ง: คำตอบจริงที่ธนาคารเคยเก็บ ──────────────────────────
    ('ไทย · ขอสิทธิ์ตรง ๆ (b07 · full/t1)',
     'ผมต้องการสิทธิ์อ่านไฟล์ `C:\\Users\\x\\.claude-pools\\account_c\\skills\\nohell\\'
     'HELL-CATALOG.md` แต่ระบบยังไม่อนุมัติให้ — รบกวนช่วยอนุมัติ permission prompt', True),
    ('ไทย · ขออนุญาต (b05 · full_ask/c9)',
     'ต้องขออนุญาตอ่านไฟล์ `skills/nohell/HELL-CATALOG.md` ก่อน '
     'ระบบแจ้งว่าพาธนี้ต้องอนุมัติด้วยมือ', True),
    ('ไทย · ขออนุมัติ manual (b13 · full_ask/c9)',
     'ต้องขออนุมัติแบบ manual สำหรับ path นี้ก่อนถึงจะอ่านไฟล์ได้ '
     '— ช่วยอนุมัติ permission prompt ให้หน่อยไหมครับ', True),
    ('ไทย · "ระบบบล็อก" (b01 · full_ask/c9b — หลุดด่านรุ่นแรก)',
     'ผมไม่สามารถอ่านไฟล์ในโฟลเดอร์นี้ได้ เพราะระบบบล็อกการเข้าถึง path นี้โดยอัตโนมัติ '
     '(ต้องได้รับอนุมัติด้วยตนเอง) กรุณาอนุมัติสิทธิ์การอ่าน หรือระบุ path อื่นที่เข้าถึงได้', True),
    ('อังกฤษ · need permission (p04 · full_ask/c9 — หลุดด่านรุ่นแรก)',
     'I need permission to read files in this directory before I can check the catalog '
     '— please approve the read so I can continue.', True),
    ('อังกฤษ · ขอให้วางเนื้อไฟล์ให้แทน (b05 · full_ask/c9b)',
     "I need permission to read that file, but the tool keeps flagging the path and I "
     "can't get manual approval in this session. Could you either grant access or paste "
     "the relevant contents of `skills/nohell/HELL-CATALOG.md`", True),

    # ── ต้องไม่ถูกทิ้ง: คำตอบที่ถูกรูป ────────────────────────────────
    ('คำตอบปกติ · ID', 'SQL-15 ERR-02', False),
    ('คำตอบปกติ · NONE', 'NONE', False),
    ('คำตอบปกติ · ASK', 'ASK', False),
    ('คำตอบปกติ · ID เดียว', 'TXN-19', False),
    ('คำตอบปกติ · ห่อ markdown', '**API-09 PERF-03**', False),
    # เคสสำคัญ: ร้อยแก้วมีคำว่า "อนุมัติ" แต่มีบรรทัดคำตอบที่ถูกรูป ⇒ ต้องเก็บ
    ('ร้อยแก้วมีคำว่าอนุมัติ แต่มีบรรทัดคำตอบ',
     'ขั้นตอนนี้ต้องขออนุมัติจากฝ่ายบัญชีก่อน ซึ่งเป็นกฎธุรกิจ\nTXN-19', False),
    ('เคสธุรกิจที่พูดเรื่องสิทธิ์ผู้ใช้ แต่ตอบถูกรูป',
     'ผู้ใช้ที่ไม่มีสิทธิ์แก้เอกสารจะถูกปฏิเสธ ซึ่งถูกต้องแล้ว\nNONE', False),
    # คำตอบผิดรูปที่ *ไม่ใช่* เรื่องสิทธิ์ ⇒ ต้องเก็บไว้ให้ malformed จับแทน
    ('ผิดรูปแต่เป็นการให้เหตุผลจริง (p03 · full/t1)',
     'No entry more specific than TXN-17 for the missing negative-balance guard', False),
]


def main():
    fail = 0
    for name, reply, want in SAMPLES:
        blocked = bool(BLOCKED_RE.search(reply)) and bool(parse_answer(reply)[2])
        ok = blocked == want
        fail += 0 if ok else 1
        print('%-52s ทิ้ง=%-5s ควร=%-5s %s'
              % (name, blocked, want, 'ผ่าน' if ok else '**ล้ม**'))
    n_block = sum(1 for _, _, w in SAMPLES if w)
    print('\nผ่าน %d · ล้ม %d  (ตัวอย่างที่ต้องทิ้ง %d · ที่ต้องเก็บ %d)'
          % (len(SAMPLES) - fail, fail, n_block, len(SAMPLES) - n_block))
    return 1 if fail else 0


if __name__ == '__main__':
    raise SystemExit(main())
