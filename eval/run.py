# -*- coding: utf-8 -*-
"""eval ของตัว skill — ยิงเคสใน eval/cases/ แล้ววัดว่าแคตตาล็อกถูกใช้ได้จริงแค่ไหน

ตัดสินด้วย **exact match ของ ID** ไม่ใช้ LLM judge (D4) เพราะ judge ที่เป็นโมเดล
จะกลายเป็นตัวแปรอีกตัวที่เราคุมไม่ได้ และทำให้ตัวเลข regression เชื่อไม่ได้

provider คือ `claude -p` (headless) ที่ล็อกอินอยู่แล้ว — **ไม่ต้องใช้ API key**
และไม่มีการอ่านหรือเก็บ credential ใด ๆ ในไฟล์นี้

    python eval/run.py                    # 3 รอบ แล้วรายงาน variance
    python eval/run.py --runs 1           # รอบเดียว ตอนแก้เคส
    python eval/run.py --baseline         # เขียน eval/baseline.json

เกณฑ์ที่วัด — ให้คะแนนจากเฉลยสามชั้นใน keys/merged.json ไม่ใช่ expected_ids เดิม (ดู load_keys)
    recall            เคสที่มี must_find: เจอ ID ที่ควรเจอกี่ % (ตัวเลขหลักที่ห้ามตกหลังแก้ skill)
    false_alarm_ids   ID ชั้น `wrong` ที่ถูกรายงาน **รวมทั้งชุดต่อรอบ ไม่ใช่ต่อเคส**
    acceptable_ids    ID ชั้น `acceptable` ที่ถูกรายงาน — **นับแต่ไม่หักคะแนน** (ดู judge)
    must_ask_hit      เคสที่คำตอบถูกคือ "หยุดถาม": ตอบ ASK กี่ %
    ask_on_bug        ตอบ ASK บนเคสที่มีคำตอบชัด — พลาดคนละแบบ ต้องไม่ปนกับ false alarm
    unlisted_ids      ID ที่ตอบมาแต่ไม่อยู่ในชั้นใดเลย = **สัญญาณว่าเฉลยตกยุค** ขึ้นจาก 0 ต้องไปตรวจเฉลย
    malformed_replies คำตอบที่ไม่ใช่บรรทัดเดียวตามกติกา (ดู WELLFORMED_RE)

⚠️ `false_alarm_ids` และ `acceptable_ids` เป็น **ยอดรวมของทั้ง 30 เคสต่อหนึ่งรอบ**
   เคยถูกอ่านผิดเป็น "ต่อเคส" ซึ่งทำให้ขนาดของปัญหาดูใหญ่กว่าจริง 30 เท่า
   (13.67 ต่อรอบ = 0.46 ต่อเคส · 8.33 ต่อรอบ = 0.28 ต่อเคส) — หารด้วยจำนวนเคสก่อนเทียบกับที่อื่นเสมอ
   และค่าเฉลี่ยต่อเคสก็ยังหลอกอีกชั้น: วัดแยกชนิดเคสแล้วพบว่าเคส must_ask ให้ 2.0 ID/เคส
   ขณะที่เคสสะอาดให้ 0.083 — ครึ่งหนึ่งของ false alarm ทั้งชุดมาจากเคสเดียว (a01)
"""
import argparse, glob, io, json, os, re, shutil, statistics, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CASES = os.path.join(HERE, 'cases')
BASELINE = os.path.join(HERE, 'baseline.json')
ROUNDS = os.path.join(HERE, '.rounds.json')     # รอบที่สำเร็จแล้ว สะสมข้ามการรันหลายครั้ง
KEYS = os.path.join(HERE, 'keys', 'merged.json')  # เฉลยสามชั้น — ดู load_keys()


def bank_path(arm, tag=''):
    """แขน full ใช้ `.rounds.json` เดิม แขนอื่นแยกไฟล์ — ห้ามปนกัน

    คำตอบจากสองแขนตอบโจทย์ *คนละแบบ* (อ่านทั้งแคตตาล็อก vs อ่านเฉพาะหมวด)
    ถ้าเก็บรวมไฟล์เดียว การรันแขนใหม่จะถูกอ่านว่า "ครบแล้ว" แล้วเอาคำตอบของแขนเก่า
    มาให้คะแนน — ได้ตัวเลขที่ดูเหมือนผลเทียบทั้งที่ไม่เคยเทียบอะไร
    """
    if arm == 'full' and not tag:
        return ROUNDS
    return os.path.join(HERE, '.rounds-%s%s.json' % (arm, '-' + tag if tag else ''))


def timing_path(arm, tag=''):
    return os.path.join(HERE, '.timing-%s%s.json' % (arm, '-' + tag if tag else ''))


def load_bank(arm='full', tag=''):
    """คำตอบที่ยิงสำเร็จแล้ว เก็บ **รายเคส** ไม่ใช่รายรอบ — {case_id: [reply, ...]}

    หน่วยต้องเป็นเคส เพราะโควตาปล่อยมาทีละส่วน วัดมาแล้วสองครั้ง
      25/08 00:39  รอบ 1-2 สำเร็จ รอบ 3 ชน limit -> ทิ้งทั้งหมด เสีย 48 session
      25/08 01:00  ยิงได้ 16/24 เคส แล้วโควตาหมด -> ทิ้งทั้งรอบ เสีย 16 เคสที่ตอบแล้ว
    เก็บรายเคสทำให้ทุกครั้งที่รันมีความคืบหน้า และยังได้ 3 คำตอบอิสระต่อเคส
    ซึ่งเป็นสิ่งที่ variance ของ D4 ต้องการจริง ๆ
    """
    if not os.path.exists(bank_path(arm, tag)):
        return {}
    with io.open(bank_path(arm, tag), encoding='utf-8') as fh:
        return json.load(fh)


def save_bank(bank, arm='full', tag=''):
    with io.open(bank_path(arm, tag), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(json.dumps(bank, ensure_ascii=False, indent=2) + '\n')


ID_RE = re.compile(r'\b([A-Z]{2,6}-\d{2})\b')

# คำตอบที่บอกว่า "ยังอ่านไฟล์ไม่ได้" **ไม่ใช่คำตอบ** — มันคือการรันที่ไม่เคยเห็นแคตตาล็อกเลย
# แล้วถูกเก็บลงธนาคารและให้คะแนน recall 0 ตามปกติ = ตัวเลขที่ดูเหมือนผลวัด แต่วัดการขอสิทธิ์
#
# วัดจริง 2026-09-03 · แขน full tag t1 ปนเปื้อน 1/44 · แขน full_ask tag c9 ปนเปื้อน **6/46**
#   b05  "ต้องขออนุญาตอ่านไฟล์ skills/nohell/HELL-CATALOG.md ก่อน ระบบแจ้งว่าพาธนี้ต้องอนุมัติด้วยมือ"
#   b13  "ต้องขออนุมัติแบบ manual สำหรับ path นี้ก่อนถึงจะอ่านไฟล์ได้"
# ถ้าไม่กันออก แขน full_ask จะอ่านว่า recall ตก 11.8 จุด ทั้งที่กันปนเปื้อนแล้ว **recall เท่ากันเป๊ะ**
# ⇒ สิ่งประดิษฐ์ตัวนี้ใหญ่พอที่จะพลิกข้อสรุปของการทดลองทั้งอัน
#
# เกณฑ์ตั้งไว้ให้ **แคบ**: ต้องไม่มีบรรทัดคำตอบที่ถูกรูปเลย *และ* มีคำที่ชี้เรื่องสิทธิ์
# คำตอบที่ถูกรูปแล้วบังเอิญมีคำเหล่านี้ในร้อยแก้วประกอบ จะไม่ถูกทิ้ง
BLOCKED_RE = re.compile(
    r'claude-pools|permission prompt|permission denied|not permitted to read'
    r'|ยังไม่อนุมัติ|ขออนุมัติ|ขออนุญาต|ต้องการสิทธิ์|ไม่มีสิทธิ์อ่าน|อนุมัติการอ่าน', re.I)

# คำตอบที่ทำตามกติกาคือ *บรรทัดเดียว* มีแต่ ID / NONE / ASK
# ผิดรูปแล้วยังถูกขูด ID จากร้อยแก้ว = นับข้อที่โมเดลบอกว่า *ไม่* เข้า ว่ารายงานมา
# วัดแล้ว: b05 รอบ 1 ตอบ 495 ตัวอักษร ขึ้นต้นด้วยบล็อก "★ Insight" ในนั้นมีประโยค
#   "ต่างจาก MEAS-10 (ไม่มีค่าตั้งต้นเลย) — เคสนี้ *มี* การเก็บ baseline แต่คีย์ไม่เสถียร"
# ⇒ MEAS-10 ถูกนับเป็น false alarm ทั้งที่ประโยคนั้นบอกว่ามันไม่เข้า
# ผิดรูป 2 จาก 90 คำตอบ แต่หนึ่งในนั้นผลิต false alarm ปลอม — อัตราต่ำจึงไม่มีใครเห็น
# ตัวนับนี้ทำให้มันโผล่ทุกรอบ ยังไม่เปลี่ยนวิธีขูด ID เพราะการเปลี่ยนกระทบตัวเลขย้อนหลัง
WELLFORMED_RE = re.compile(r'^\s*(?:NONE|ASK|(?:[A-Z]{2,6}-\d{2}[ ,]*)+)\s*$')


def parse_answer(reply):
    """คืน (ids, said_ask, malformed) — อ่านจาก **บรรทัดคำตอบ** ไม่ใช่ทั้งข้อความ

    ID ที่โผล่ในร้อยแก้วเป็น *เหตุผล* ไม่ใช่ *ข้อกล่าวหา* การขูดทั้งข้อความจึงนับผิด
    วัดมาแล้วสองกรณี และทั้งคู่โมเดลตอบถูกแล้วถูกนับว่าผิด
      b05  ขึ้นต้นด้วยบล็อก "★ Insight" ในนั้นเขียนว่า "ต่างจาก MEAS-10 (ไม่มีค่าตั้งต้นเลย)"
           ⇒ MEAS-10 ถูกนับว่ารายงานมา ทั้งที่ประโยคนั้นบอกว่ามันไม่เข้า
      a08  บรรทัดแรกเป็น `ASK` เป๊ะ ซึ่งเป็นคำตอบที่ถูกต้อง แล้วอธิบายต่อว่า "AI-06 คือข้อที่
           บังคับให้หยุด" และ "ORDER BY จะกลายเป็น AGG-05 *ทันทีที่ยืนยันว่าใช้ FIFO*"
           ⇒ ask_ok = 0 เพราะ found ไม่ว่าง ทั้งที่เป็นคำตอบที่ดีที่สุดในชุด

    บรรทัดแรกที่ตรงรูปแบบคือคำตอบ · ถ้าไม่มีบรรทัดไหนตรงเลย ⇒ นับเป็น malformed **และ**
    ถอยไปขูดทั้งข้อความ เพื่อไม่ให้คำตอบที่ผิดรูปกลายเป็น "ไม่ได้ตอบอะไร" แบบเงียบ ๆ
    """
    # ปอก markdown ที่ห่อบรรทัดคำตอบออกก่อนเทียบ — วัดแล้ว: c05 ในแขน routed ตอบ
    # `**API-09 PERF-03**` ซึ่ง *เป็นคำตอบจริง* แค่ถูกห่อด้วย bold แล้วตกเป็นผิดรูป
    # แล้วถอยไปขูดร้อยแก้วข้างบนซึ่งมี ID ที่โมเดลกำลังอธิบายว่า "ก็เข้าด้วย"
    # การปอก `*` และ backtick ไม่ได้ขยายว่าอะไรนับเป็นคำตอบ แค่ทนรูปแบบการนำเสนอ
    for line in reply.strip().split('\n'):
        bare = line.strip().strip('*`_ ')
        if WELLFORMED_RE.match(bare):
            return set(ID_RE.findall(bare)), bool(re.search(r'\bASK\b', bare)), 0
    return set(ID_RE.findall(reply)), bool(re.search(r'\bASK\b', reply)), 1

_ANSWER_RULES = '''
กติกาการตอบ ตอบบรรทัดเดียว ห้ามอธิบาย
- ถ้าละเมิดข้อในแคตตาล็อก ตอบเป็น ID คั่นด้วยช่องว่าง เช่น: SQL-15 ERR-02
- ถ้าไม่ละเมิดข้อใดเลย ตอบ: NONE
- ถ้ายังตัดสินไม่ได้เพราะขาดกฎธุรกิจที่เดาแทนไม่ได้ ตอบ: ASK'''

# สองแขนของการทดลอง C1 — ต่างกัน **แค่วิธีเข้าถึงแคตตาล็อก** ส่วนโจทย์ กติกาการตอบ
# และเฉลยเหมือนกันเป๊ะ เพื่อให้ผลต่างที่วัดได้มาจากตัวแปรเดียว
#
# ที่มาของการทดลอง: docs/research/2026-09-02-accuracy-speed-eval.md §9 ข้อ C1
# ฝ่าย ก  Anthropic: ใต้ 200K token ไม่ต้องสร้าง retrieval · prefix ใหญ่ยิ่งได้กำไรจาก cache
# ฝ่าย ข  NoLiMa วัดว่า effective length ของ Sonnet คือ ~4K · distractor ตัดเหลือ ~1K ·
#         เกิน 20 เอกสารแย่กว่าไม่ใส่ · และเอกสาร Anthropic เองก็มีฝ่ายที่พูดเรื่อง context rot
# ทั้งสองฝ่ายมีเอกสาร Anthropic หนุน รายงานจึงปฏิเสธที่จะเลือกข้างให้ ⇒ ต้องวัดเอง
PROMPTS = {
    'full': '''อ่าน skills/nohell/HELL-CATALOG.md ในโฟลเดอร์นี้ก่อน แล้วตอบโจทย์ข้างล่าง

โจทย์: {task}

```{lang}
{snippet}
```
''' + _ANSWER_RULES,

    'routed': '''อ่าน skills/nohell/SKILL.md ในโฟลเดอร์นี้ก่อน — ในนั้นมีรหัสหมวดทั้ง 31 หมวด
เลือกหมวดที่เกี่ยวกับโจทย์ข้างล่าง แล้วอ่าน **เฉพาะหัวข้อของหมวดที่เลือก** ใน
skills/nohell/HELL-CATALOG.md (ใช้ grep หรือ sed อ่านเฉพาะช่วงบรรทัดของหมวดนั้น)

**ห้ามอ่าน HELL-CATALOG.md ทั้งไฟล์** — จุดประสงค์ของการทดลองนี้คือวัดว่าการอ่านเฉพาะ
หมวดที่เกี่ยวข้องให้ผลต่างจากการอ่านทั้งก้อนอย่างไร ถ้าอ่านทั้งไฟล์ผลจะใช้เทียบไม่ได้

โจทย์: {task}

```{lang}
{snippet}
```
''' + _ANSWER_RULES,
}

# แขนของการทดลอง C9 — ต่างจาก `full` **แค่ประโยคเดียวท้ายกติกาการตอบ** ส่วนวิธีเข้าถึง
# แคตตาล็อก โจทย์ และเฉลย เหมือน `full` เป๊ะ
#
# ที่มา: docs/research/2026-09-02-accuracy-speed-eval.md §9 ข้อ C9
# ฝ่าย ก  #2 สั่งใน system prompt ให้ abstain ได้ผลจริงและวัดได้
# ฝ่าย ข  #42 scaffold ที่ดีที่สุดกลับ *ถามน้อยลง* (344 vs 369) แต่ถามลึกกว่า
# รายงานบอกว่าสองข้อนี้ไม่ได้ขัดกันจริง (อัตราการถาม vs การเลือกว่าจะถามอะไร)
# แต่ชี้ไปการแก้คนละทาง และผู้ตรวจตายทั้ง 3/3 ทั้งคู่ ⇒ ต้องวัดเอง
#
# ⚠️ เกณฑ์ตัดสินของการทดลองนี้ **ไม่ใช่ must_ask_hit ตัวเดียว** การดัน ask-rate ให้ขึ้น
#    ทำได้ง่ายมากด้วยการสั่งให้ถามบ่อยขึ้น แล้วมันจะไปโผล่เป็น `ask_on_bug` แทน
#    (ถาม ในเคสที่มีคำตอบชัด = ผลักภาระกลับไปหาคนโดยไม่จำเป็น ซึ่งเป็นสิ่งที่
#    เจ้าของรีโปประกาศว่าอยากลด) ⇒ ต้องอ่านสามตัวพร้อมกันเสมอ:
#    must_ask_hit ขึ้น · ask_on_bug ต้องไม่ขึ้น · recall ต้องไม่ตก
PROMPTS['full_ask'] = PROMPTS['full'] + '''
- กฎธุรกิจที่โจทย์ไม่ได้ระบุมา ห้ามเดาแทน ถ้าการตัดสินต้องใช้กฎแบบนั้น ให้ตอบ ASK
  แม้จะเห็นข้อที่น่าจะเข้าอยู่ก็ตาม การเดากฎธุรกิจแล้วฝังลงโค้ดแก้ยากกว่าการถามมาก'''


def load_cases():
    out = []
    for f in sorted(glob.glob(os.path.join(CASES, '*.json'))):
        with io.open(f, encoding='utf-8') as fh:
            out.append(json.load(fh))
    return out


_SANDBOX = []


def sandbox():
    """โฟลเดอร์ที่มีแต่ `skills/` — ไม่มี `eval/` และไม่มีเฉลย

    วัดแล้วว่าถ้าตั้ง cwd เป็นรากรีโป agent จะเปิด `eval/cases/` ระหว่างหาบริบท
    ซึ่งมี `expected_ids` อยู่ข้างใน เท่ากับวางเฉลยไว้ในห้องสอบ แล้วตัวเลขที่ได้
    ไม่ได้วัดแคตตาล็อก แต่วัดว่ามันอ่านไฟล์เฉลยเจอหรือไม่ (หมวด MEAS)
    """
    if not _SANDBOX:
        d = tempfile.mkdtemp(prefix='nohell-eval-')
        shutil.copytree(os.path.join(ROOT, 'skills'), os.path.join(d, 'skills'))
        _SANDBOX.append(d)
    return _SANDBOX[0]


def claude_bin():
    """หา executable ของ claude แบบที่ทำงานบน Windows ด้วย

    `subprocess.run(['claude', ...])` **ใช้ไม่ได้บน Windows**: `CreateProcess` เติมให้แค่
    `.exe` ไม่ไล่ `PATHEXT` ⇒ `claude.CMD` ที่ npm ติดตั้งไว้หาไม่เจอ ได้ FileNotFoundError
    ทั้งที่พิมพ์ `claude` ในเชลล์รันได้ปกติ และ `shutil.which('claude')` ก็คืนพาธได้
    วัดแล้ว: which -> `...\\npm\\claude.CMD` · `subprocess(['claude'])` -> WinError 2

    อาการนี้อ่านจาก error ไม่ออกเลย มันบอกว่า "ไม่พบคำสั่ง claude" ซึ่งพาไปแก้ PATH
    ทั้งที่ PATH ถูกอยู่แล้ว — ส่งพาธเต็มที่ which คืนมาให้ subprocess ตรง ๆ จบเรื่อง
    """
    return shutil.which('claude') or 'claude'


def ask(job):
    """ยิงหนึ่งเคส · `job` = (case, arm) — prompt ไปทาง **stdin** ไม่ใช่ argv

    ⚠️ ห้ามเปลี่ยนกลับไปเป็น `[exe, '-p', prompt]` เด็ดขาด บน Windows ตัวที่ which เจอคือ
    `claude.CMD` ซึ่งเป็น batch wrapper: ขึ้นบรรทัดใหม่ = จบคำสั่ง ⇒ **prompt เหลือแค่บรรทัดแรก**
    แล้วไม่มีอะไรฟ้อง exit code = 0 มีคำตอบกลับมาเป็นภาษาคน ดูเหมือนสำเร็จทุกอย่าง

    วัดมาแล้วด้วย prompt สองบรรทัด ("ทักทาย" / "ตอบ 2+2 เป็นตัวเลขเดียว")
        argv  -> ทักทายเฉย ๆ ไม่เคยเห็นบรรทัดสอง
        stdin -> ทักทาย + ตอบ 4
    และเคยทำให้เก็บคำตอบขยะลงธนาคารจริง: เคส b02 ได้คำตอบสามรอบที่เขียนว่า
    "โจทย์ไม่ได้มาด้วย ข้อความจบที่ 'แล้วตอบโจทย์ข้างล่าง'" — ซึ่งถูกนับเป็นผลวัดไปแล้ว
    ก่อนจะจับได้ นี่คือ MEAS ที่ทำร้ายที่สุด: เครื่องวัดที่พังแล้วยังคืนตัวเลขหน้าตาปกติ

    บน POSIX ไม่มี `.CMD` ขั้นกลาง argv จึงส่งหลายบรรทัดได้ปกติ — คำตอบที่เก็บไว้ก่อนหน้านี้
    (89 เคส) เก็บมาจากทางนั้น จึงยังใช้ได้ ไม่ต้องล้าง
    """
    case, arm = job
    prompt = PROMPTS[arm].format(task=case['task'], lang=case['lang'], snippet=case['snippet'])
    t0 = time.time()
    try:
        r = subprocess.run([claude_bin(), '-p'], input=prompt, cwd=sandbox(),
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=300)
    except FileNotFoundError:
        sys.stderr.write('ไม่พบคำสั่ง claude — eval ตัวนี้ใช้ Claude Code headless เป็น provider\n')
        raise SystemExit(2)
    except subprocess.TimeoutExpired:
        return '', 'timeout หลัง 300 วินาที', time.time() - t0
    if r.returncode != 0:
        # ห้ามกลืน — คำตอบว่างจะถูกนับเป็น recall 0 แล้วสรุปออกมาเป็นตัวเลขที่ดูเหมือนผลวัด
        # วัดจริงมาแล้ว: session limit หมด 21/24 เคสล้ม แต่รายงานยังพิมพ์ "recall 8.3%" ออกมา
        # เอา stdout ก่อน — claude -p พิมพ์ error ที่คนอ่านรู้เรื่องลงที่นั่น
        # ("You've hit your session limit") ส่วน stderr มักเป็น noise ของ hook/ปลั๊กอินอื่น
        why = (r.stdout or '').strip().split('\n')[0][:120]
        if not why:
            why = (r.stderr or '').strip().split('\n')[0][:120]
        return '', why or ('exit %d' % r.returncode), time.time() - t0
    reply = r.stdout.strip()
    # exit 0 แต่ไม่ได้ตอบโจทย์ — คืนเป็น error เพื่อไม่ให้ลงธนาคาร (ดู BLOCKED_RE)
    # ยิงใหม่ได้เรื่อย ๆ เพราะเคสที่ไม่ลงธนาคารจะถูกหยิบมายิงซ้ำในรอบถัดไปเอง
    if BLOCKED_RE.search(reply) and parse_answer(reply)[2]:
        return '', ('ถูกบล็อกไม่ให้อ่านไฟล์ ไม่ใช่คำตอบ: '
                    + reply[:90].replace('\n', ' ')), time.time() - t0
    return reply, None, time.time() - t0


def load_keys():
    """เฉลยสามชั้นจาก keys/merged.json — must_find / acceptable / wrong

    `expected_ids` ในไฟล์เคสวัดแล้วว่าใช้เป็นไม้บรรทัดไม่ได้: 13 จาก 30 เคสเฉลยไม่ครบ
    และ b02 ID ที่ให้มา (SQL-10) ไม่ตรงกลไกจริงเลย ผลคือ ID ที่เครื่องมือหาถูก
    ถูกนับเป็น false alarm — recall จริง 0.9556 ถูกรายงานเป็น 0.8445

    สามชั้นแยกสิ่งที่ต่างกันจริง ๆ ออกจากกัน
      must_find   ไม่เจอ = เครื่องมือพลาด (เข้าสูตร recall)
      acceptable  ละเมิดจริงแต่ไม่ใช่ประเด็นหลัก — **นับแต่ไม่หัก** ดู judge()
      wrong       รายงานมา = มั่ว (เข้าสูตร false alarm)

    หายไปคือ **รันไม่ได้** ไม่ใช่รันแล้วได้ศูนย์ — ตัวเลขที่ออกมาจากเฉลยที่ไม่มี
    จะดูเหมือนผลวัดทั้งที่ไม่ใช่ ซึ่งเป็นความผิดพลาดที่ไฟล์นี้เจอมาแล้วรอบหนึ่ง
    """
    if not os.path.exists(KEYS):
        sys.stderr.write(
            'ไม่พบ %s — eval ตัวนี้ให้คะแนนจากเฉลยสามชั้น ไม่ใช่ expected_ids เดิม\n'
            '  สร้างจากผลตรวจใน eval/keys/g1..g5.json ก่อน\n' % KEYS)
        raise SystemExit(2)
    with io.open(KEYS, encoding='utf-8') as fh:
        return json.load(fh)['cases']


def judge(case, reply, keys):
    """คืน dict ของเกณฑ์ต่อเคสหนึ่ง — ตัดสินจาก ID ที่เจอในคำตอบเท่านั้น

    `acceptable` ถูก **นับแยกไม่หักคะแนน** เพราะวัดแล้วว่ามันเฉลี่ย 0.97 ID/เคส
    (ภาระอ่านเพิ่มไม่ถึงบรรทัด) แต่ 37.9% ของมันเป็น P1 (ข้อมูลผิด/ล่ม/รั่ว)
    การหักคะแนนมันคือการสอนให้เครื่องมือเงียบเรื่อง P1 เพื่อให้ตัวเลขสวย
    ตัวเลขทั้งสองขึ้นทุกรอบ ให้คนอ่านตัดสินเองว่าเป็นภาระหรือมูลค่า
    """
    k = keys[case['id']]
    found, said_ask, malformed = parse_answer(reply)
    must = {x['id'] for x in k.get('must_find') or []}
    okay = {x['id'] for x in k.get('acceptable') or []}
    bad = {x['id'] for x in k.get('wrong') or []}

    out = {'recall': None, 'false_alarm': len(found & bad),
           'acceptable': len(found & okay), 'ask_ok': None, 'ask_on_bug': 0,
           'excluded': False, 'malformed': malformed,
           'unlisted': sorted(found - must - okay - bad)}

    if k.get('excluded'):
        # เคสที่ไม่มี ground truth ให้เทียบ — ต้องไม่นับเป็น "สะอาด" โดยปริยาย
        # b02: เฉลยเดิมผิดกลไก และแคตตาล็อกยังไม่มีข้อที่ครอบอาการจริง
        # ถ้าปล่อยให้ตกลงกลุ่มสะอาด การรายงานสิ่งที่ *ถูก* จะถูกนับเป็น false alarm
        return {'recall': None, 'false_alarm': 0, 'acceptable': 0, 'ask_ok': None,
                'ask_on_bug': 0, 'excluded': True, 'unlisted': [],
                'malformed': malformed}

    if case['must_ask']:
        # บั๊กเดิม: `return None, 0, ...` ทำให้เคสนี้ได้ false alarm 0 เสมอ
        # a01 ตอบ ID มา 4-5 ตัวทุกรอบแทนที่จะ ASK แล้วได้ 0 — การเดาแทนที่จะถาม
        # คือความผิดพลาดที่แพงที่สุดในชุดนี้ และเป็นข้อเดียวที่ไม่เคยถูกนับ
        out['ask_ok'] = 1 if said_ask and not found else 0
        return out

    if must:
        out['recall'] = len(found & must) / float(len(must))
        # ตอบ ASK บนเคสที่มีคำตอบชัด = พลาดคนละแบบ ต้องแยกตัวเลข ไม่ใช่ปล่อยฟรี
        if said_ask and not found:
            out['ask_on_bug'] = 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runs', type=int, default=3)
    ap.add_argument('--baseline', action='store_true')
    ap.add_argument('-q', '--quiet', action='store_true')
    ap.add_argument('--jobs', type=int, default=4, help='ยิงกี่เคสพร้อมกัน (ค่าเริ่มต้น 4)')
    ap.add_argument('--arm', choices=sorted(PROMPTS), default='full',
                    help='full = อ่านแคตตาล็อกทั้งก้อน · routed = อ่านเฉพาะหมวดที่เลือก (ทดลอง C1)')
    # --only + --tag มีไว้ให้กระจายงานข้ามบัญชีได้ (ดู skill orchestra)
    # ⚠️ ถ้าหลาย process ยิงพร้อมกันต้องให้ **แต่ละตัวมี --tag ของตัวเอง** ไม่งั้นทั้งหมด
    #    จะอ่าน-เขียนธนาคารไฟล์เดียวกันแล้วทับกันเงียบ ๆ (คนละปัญหากับ --jobs ที่คุมภายใน
    #    process เดียว) ไฟล์แยกกันสนิทจึงไม่ต้องประสานงานอะไรเลย แล้วรวมทีหลังด้วย --merge
    ap.add_argument('--only', default='',
                    help='ยิงเฉพาะเคสที่ระบุ คั่นด้วยช่องว่างหรือจุลภาค (ค่าว่าง = ทุกเคส)')
    ap.add_argument('--tag', default='',
                    help='ต่อท้ายชื่อไฟล์ธนาคาร/เวลา — บังคับใช้เมื่อยิงหลาย process พร้อมกัน')
    ap.add_argument('--merge', default='',
                    help='รวมธนาคารจาก tag ที่ระบุ (คั่นด้วยจุลภาค) เข้าไฟล์หลักของแขนนั้น แล้วจบ')
    a = ap.parse_args()

    if a.merge:
        merged, tmerged = {}, {}
        for tag in [t.strip() for t in a.merge.split(',') if t.strip()]:
            bp, tp = bank_path(a.arm, tag), timing_path(a.arm, tag)
            if not os.path.exists(bp):
                sys.stderr.write('ไม่พบ %s — tag นี้ยังไม่มีผล\n' % os.path.basename(bp))
                continue
            with io.open(bp, encoding='utf-8') as fh:
                for cid, reps in json.load(fh).items():
                    merged.setdefault(cid, []).extend(reps)
            if os.path.exists(tp):
                with io.open(tp, encoding='utf-8') as fh:
                    for cid, secs in json.load(fh).items():
                        tmerged.setdefault(cid, []).extend(secs)
        # ⚠️ --merge **เขียนทับ** ไฟล์หลัก ไม่ได้เขียนต่อท้าย ถ้าผู้ใช้พิมพ์ tag มาไม่ครบ
        # คำตอบรอบก่อน ๆ ที่อยู่ในไฟล์หลักจะหายไปเงียบ ๆ แล้วรอบถัดไปจะยิงใหม่ทับ
        # โดยไม่มีอะไรบอกว่าเพิ่งทำข้อมูลหายไปกี่รอบ — ตายตรงนี้ดีกว่าเงียบ
        # ⚠️ เทียบ **ตัวคำตอบ** ไม่ใช่จำนวน — วัดมาแล้วว่าเทียบจำนวนอย่างเดียวไม่พอ
        # `--merge r2` ที่มี 1 คำตอบต่อเคสเท่ากับของเดิมพอดี ผ่านด่านที่นับจำนวน
        # แล้วเขียนทับคำตอบรอบ 1 ทิ้งทั้งชุด โดยพิมพ์ว่า "รวมแล้ว 44 เคส" และคืน exit 0
        # (ตัวด่านเองเป็นบั๊กคลาสเดียวกับที่มันถูกเขียนมากัน — ตรวจตัวแทนแทนของจริง)
        from collections import Counter
        cur = load_bank(a.arm)
        lost = sorted(cid for cid, reps in cur.items()
                      if Counter(reps) - Counter(merged.get(cid, [])))
        if lost:
            sys.stderr.write(
                'ยกเลิกการรวม — จะทำให้ %d เคสมีคำตอบน้อยลงกว่าที่มีอยู่ใน %s\n'
                '  เช่น %s\n'
                '  --merge เขียนทับไฟล์หลักด้วยผลของ tag ที่ระบุเท่านั้น ไม่ได้เขียนต่อท้าย\n'
                '  ⇒ ต้องใส่ tag ของรอบเก่าเข้าไปด้วย เช่น --merge เก่า,ใหม่\n'
                % (len(lost), os.path.basename(bank_path(a.arm)), ' '.join(lost[:5])))
            return 2
        io.open(bank_path(a.arm), 'w', encoding='utf-8', newline='\n').write(
            json.dumps(merged, ensure_ascii=False, indent=2) + '\n')
        io.open(timing_path(a.arm), 'w', encoding='utf-8', newline='\n').write(
            json.dumps(tmerged, ensure_ascii=False, indent=2) + '\n')
        print('รวมแล้ว %d เคส เข้า %s (คำตอบต่อเคส %d-%d)'
              % (len(merged), os.path.basename(bank_path(a.arm)),
                 min(len(v) for v in merged.values()) if merged else 0,
                 max(len(v) for v in merged.values()) if merged else 0))
        return 0

    cases = load_cases()
    keys = load_keys()
    missing = [c['id'] for c in cases if c['id'] not in keys]
    if missing:
        # เฉลยขาดบางเคส = คะแนนที่ออกมาไม่ได้วัดชุดที่คิดว่าวัด ห้ามรันต่อเงียบ ๆ
        sys.stderr.write('เฉลยใน %s ขาด %d เคส: %s\n'
                         % (os.path.basename(KEYS), len(missing), ' '.join(missing[:5])))
        raise SystemExit(2)

    # เฉลยอยู่สองที่: `expected_ids`/`must_ask` ในไฟล์เคส กับสามชั้นใน keys/merged.json
    # judge() อ่านจาก merged.json เท่านั้น ⇒ ถ้าสองแหล่งเดินจากกัน คนที่แก้ไฟล์เคส
    # จะไม่เห็นผลอะไรและไม่มีอะไรบอก (silent no-op — ARCH-08 ในแคตตาล็อกตัวเอง)
    # ตายดังตรงนี้ ดีกว่ารายงานตัวเลขที่ไม่รู้ว่าวัดชุดไหน
    drift = []
    for c in cases:
        k = keys[c['id']]
        want = [] if k.get('excluded') else sorted({x['id'] for x in k.get('must_find') or []})
        if sorted(c['expected_ids']) != want:
            drift.append('%s: expected_ids=%s แต่เฉลยว่า %s'
                         % (c['id'], sorted(c['expected_ids']) or '[]', want or '[]'))
        if bool(c['must_ask']) != bool(k.get('must_ask')):
            drift.append('%s: must_ask=%s แต่เฉลยว่า %s'
                         % (c['id'], c['must_ask'], k.get('must_ask')))
    if drift:
        sys.stderr.write('ไฟล์เคสกับ %s เดินจากกัน %d จุด — แก้ให้ตรงก่อนวัด\n'
                         % (os.path.basename(KEYS), len(drift)))
        for d in drift:
            sys.stderr.write('  %s\n' % d)
        raise SystemExit(2)

    # นับจากเฉลยสามชั้น ไม่ใช่ expected_ids เดิม — c10 เคยถูกจัดเป็น "สะอาด"
    # แต่มี DATA-18 จริง (index ซ้ำกับ PK) การนับจากของเดิมจะรายงานชุดผิดประเภท
    def _skip(c):
        return bool(keys[c['id']].get('excluded'))

    def _has_must(c):
        return bool(keys[c['id']].get('must_find'))
    n_bug = sum(1 for c in cases if _has_must(c) and not _skip(c))
    n_clean = sum(1 for c in cases
                  if not _has_must(c) and not c['must_ask'] and not _skip(c))
    n_ask = sum(1 for c in cases if c['must_ask'] and not _skip(c))
    n_skip = sum(1 for c in cases if _skip(c))
    print('เคส %d (บั๊ก %d · สะอาด %d · ต้องหยุดถาม %d · กันออก %d) · %d รอบ · ขนาน %d'
          % (len(cases), n_bug, n_clean, n_ask, n_skip, a.runs, a.jobs))
    if n_skip:
        # เคสที่กันออกต้องเห็นทุกครั้ง ไม่ใช่ตัวเลขในไฟล์สรุปที่ไม่มีใครเปิด
        # เคสที่หายจากการวัดอย่างเงียบ ๆ คือชุดทดสอบที่เล็กลงโดยไม่มีใครรู้
        for c in cases:
            if _skip(c):
                sys.stderr.write('  กันออก %s — %s\n'
                                 % (c['id'], keys[c['id']].get('exclude_reason', 'ไม่ระบุเหตุผล')))

    from concurrent.futures import ThreadPoolExecutor
    bank = load_bank(a.arm, a.tag)
    timing = {}
    if os.path.exists(timing_path(a.arm, a.tag)):
        with io.open(timing_path(a.arm, a.tag), encoding='utf-8') as fh:
            timing = json.load(fh)
    # --only จำกัดว่า *ยิง* เคสไหน แต่การให้คะแนนยังใช้ทุกเคสเสมอ
    # ถ้าปล่อยให้ --only ตัดเคสออกจากการให้คะแนนด้วย จะได้ recall ของ subset
    # ที่หน้าตาเหมือน recall ของทั้งชุด — ตัวเลขที่ดูเหมือนผลวัดแต่วัดคนละชุด
    only = set(re.split(r'[,\s]+', a.only.strip())) - {''}
    want_cases = [c for c in cases if c['id'] in only] if only else cases
    if only:
        miss = only - {c['id'] for c in cases}
        if miss:
            sys.stderr.write('--only อ้างเคสที่ไม่มี: %s\n' % ' '.join(sorted(miss)))
            raise SystemExit(2)
        print('--only จำกัดการยิงไว้ %d เคส' % len(want_cases))

    have = min([len(bank.get(c['id'], [])) for c in want_cases] or [0])
    print('แขน %s · คำตอบที่สะสมไว้แล้ว: อย่างน้อย %d ต่อเคส (ต้องการ %d)'
          % (a.arm, have, a.runs))

    while True:
        need = [c for c in want_cases if len(bank.get(c['id'], [])) < a.runs]
        if not need:
            break
        print('\nยิง %d เคสที่ยังไม่ครบ' % len(need))
        with ThreadPoolExecutor(max_workers=a.jobs) as ex:
            replies = list(ex.map(ask, [(c, a.arm) for c in need]))
        got, why = 0, []
        for c, (reply, err, secs) in zip(need, replies):
            if err:
                if err not in why:
                    why.append(err)
                continue
            bank.setdefault(c['id'], []).append(reply)
            timing.setdefault(c['id'], []).append(round(secs, 2))
            got += 1
            if not a.quiet:
                print('  ok  %-28s %5.1fs  %s'
                      % (c['id'], secs, reply[:52].replace('\n', ' ')))
        save_bank(bank, a.arm, a.tag)
        io.open(timing_path(a.arm, a.tag), 'w', encoding='utf-8', newline='\n').write(
            json.dumps(timing, ensure_ascii=False, indent=2) + '\n')
        print('  ยิงสำเร็จ %d/%d — เก็บลง %s แล้ว'
              % (got, len(need), os.path.basename(bank_path(a.arm, a.tag))))
        if got == 0:
            # ยิงไม่ออกเลยแม้แต่เคสเดียว รันต่อก็เผาเปล่า
            for w in why:
                sys.stderr.write('  %s\n' % w)
            break

    have = min([len(bank.get(c['id'], [])) for c in cases] or [0])
    if have < a.runs:
        short = [c['id'] for c in cases if len(bank.get(c['id'], [])) < a.runs]
        sys.stderr.write('\nยังไม่ครบ — ต้องการ %d คำตอบต่อเคส ตอนนี้อย่างน้อย %d\n'
                         '  เหลืออีก %d เคส เช่น %s\n'
                         '  รันซ้ำเมื่อโควตากลับมา เคสที่ตอบแล้วจะไม่ถูกยิงซ้ำ\n'
                         % (a.runs, have, len(short), ' '.join(short[:5])))
        if _SANDBOX:
            shutil.rmtree(_SANDBOX[0], ignore_errors=True)
        return 2

    # ประกอบเป็นรอบ: รอบที่ i ใช้คำตอบที่ i ของทุกเคส
    rounds = []
    for i in range(a.runs):
        rec, fa, okay, ask_hit, on_bug, unlisted, malf, detail = [], 0, 0, [], 0, 0, 0, {}
        for c in cases:
            reply = bank[c['id']][i]
            j = judge(c, reply, keys)
            if j['recall'] is not None:
                rec.append(j['recall'])
            if j['ask_ok'] is not None:
                ask_hit.append(j['ask_ok'])
            fa += j['false_alarm']
            okay += j['acceptable']
            on_bug += j['ask_on_bug']
            unlisted += len(j['unlisted'])
            malf += j['malformed']
            detail[c['id']] = dict(j, reply=reply[:200])
        rounds.append({
            'recall': round(sum(rec) / len(rec), 4) if rec else 0.0,
            'false_alarm_ids': fa,
            'acceptable_ids': okay,
            'must_ask_hit': round(sum(ask_hit) / len(ask_hit), 4) if ask_hit else 0.0,
            'ask_on_bug': on_bug,
            'unlisted_ids': unlisted,
            'malformed_replies': malf,
            'detail': detail,
        })
        print('  รอบ %d: recall %.1f%% · false alarm %d · acceptable %d · '
              'must-ask %.0f%% · ask-on-bug %d · ไม่อยู่ในเฉลย %d · ตอบผิดรูป %d'
              % (i + 1, rounds[-1]['recall'] * 100, fa, okay,
                 rounds[-1]['must_ask_hit'] * 100, on_bug, unlisted, malf))

    summary = {}
    for k in ('recall', 'false_alarm_ids', 'acceptable_ids', 'must_ask_hit',
              'ask_on_bug', 'unlisted_ids', 'malformed_replies'):
        vals = [r[k] for r in rounds]
        summary[k] = {'mean': round(statistics.mean(vals), 4),
                      'min': min(vals), 'max': max(vals),
                      'stdev': round(statistics.stdev(vals), 4) if len(vals) > 1 else 0.0}
    # se เคสต่อเคสของรอบสุดท้าย — sd ข้างล่างตอบว่า "ยิงชุดเดิมซ้ำจะต่างกันแค่ไหน"
    # ซึ่ง **ไม่ใช่ความไม่แน่นอนของตัวเลข** วัดแล้วว่า se ใหญ่กว่า sd 3.8 เท่า
    # และแขน routed เคยได้ sd 0.0000 ทั้งที่โมเดลเปลี่ยนคำตอบไป 13 จาก 37 เคส
    # (ความผันผวนหักล้างกันในค่าเฉลี่ย) ⇒ พิมพ์ทั้งสองตัวคู่กันเสมอ
    _rec = [d['recall'] for d in rounds[-1]['detail'].values() if d['recall'] is not None]
    _se = (statistics.stdev(_rec) / (len(_rec) ** 0.5)) if len(_rec) > 1 else 0.0
    print('\nสรุปจาก %d รอบ' % a.runs)
    print('  ** recall se เคสต่อเคส %.4f (n=%d เคส) = ความไม่แน่นอนของตัวเลข **' % (_se, len(_rec)))
    print('     ผลต่างที่เล็กกว่า ~%.0f จุด แยกจาก noise ไม่ได้ที่จำนวนเคสเท่านี้' % (2.8 * _se * 100))
    print('     sd ข้างล่างวัดความแปรปรวน *ระหว่างรอบ* เท่านั้น ห้ามอ่านว่าเป็นความแม่นยำ'
          ' — ดู eval/reanalyze.py')
    for k, v in summary.items():
        print('  %-18s mean %-8s min %-6s max %-6s sd %s'
              % (k, v['mean'], v['min'], v['max'], v['stdev']))

    if a.baseline:
        out = {'cases': len(cases), 'runs': a.runs, 'summary': summary,
               'per_case': rounds[-1]['detail']}
        with io.open(BASELINE, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
        print('\nเขียน %s แล้ว — นี่คือเลขที่การแก้ skill หลังจากนี้ต้องไม่ทำให้แย่ลง' % BASELINE)
    if _SANDBOX:
        shutil.rmtree(_SANDBOX[0], ignore_errors=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
