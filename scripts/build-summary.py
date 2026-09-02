# -*- coding: utf-8 -*-
"""เขียนตัวเลขที่เอกสารประกาศไว้ใหม่จากข้อมูลจริง — ทั้งตารางสรุปท้าย HELL-CATALOG.md
และตัวเลขในเนื้อความของเอกสารทุกไฟล์

ตารางนี้เคยผิดมาก่อน (หมวด SSOT 18 ข้อหายไปทั้งหมวด และยอดรวมค้างที่เลขเก่า)
เพราะไม่มีใครแก้ตอนเพิ่มข้อ วิธีกันคือไม่ให้แก้มืออีกเลย

ตัวเลขในเนื้อความก็เดินมาแล้วสามครั้งด้วยเหตุเดียวกัน (กฎอัตโนมัติ 68 ทั้งที่มี 67 ·
P1 215 ทั้งที่มี 136 · จำนวน check 10 ทั้งที่มี 13) เดิมกันด้วย assertion ห้าชุดใน
validate-catalog.sh ข้อ 8 ย้ายมารวมที่นี่เพราะไฟล์นี้เป็นเจ้าของเรื่อง "ประกาศ vs ของจริง"
อยู่แล้ว และ build ของมัน *แก้ให้ถูก* ไม่ใช่แค่บอกว่าผิด

    python scripts/build-summary.py            # เขียนทุกตัวเลขใหม่ให้ตรงของจริง
    python scripts/build-summary.py --check    # แค่ตรวจ ไม่แก้ (คืน exit 1 ถ้าไม่ตรง)

⚠️ โหมดที่ไม่ใส่ --check *เขียนไฟล์ทับ* ต่างจากตัวตรวจเดิมที่แค่ฟ้อง แถวใน FACTS ที่ scope
หรือ pattern กว้างเกินจะไปแก้เลขผิดที่โดยที่ไม่มีใครเห็น เพิ่มแถวใหม่ต้องวัดจุดที่มันจับได้
จริงก่อน (ดู least) และ CI ต้องรัน --check เท่านั้น
"""
import glob, io, os, re, sys

PATH = 'skills/nohell/HELL-CATALOG.md'
RULES = 'skills/nohell/hell-rules.yaml'
MARK = '<!-- generate ด้วย scripts/build-summary.py ห้ามแก้มือ -->'

# เอกสารในรีโปนี้มีสองชนิดที่หน้าที่ต่างกัน และตัวนี้แตะได้ชนิดเดียว
#   ทะเบียน  ประกาศ *สถานะปัจจุบัน* — ต้อง generate ทับ ไม่งั้นมันเดิน
#   บันทึก   อ้าง *สถานะในอดีต* หรือเขียนกฎเป็นตัวเลข — เขียนทับเมื่อไหร่คือทำลายเนื้อหา
# ค่าเริ่มต้นเดิมถือว่าทุกไฟล์ .md เป็นทะเบียน แล้วยกเว้นทีละชื่อ ซึ่งพังมาแล้วสองครั้ง
#   CHANGELOG            บันทึกประวัติ ต้องอ้างเลขที่ตกยุคได้
#   NOHELL-NEXT-MISSION  เอกสารแผน ข้อตัดสินใจ D5 เขียนว่า "28 หมวดพอแล้ว" ซึ่งเป็น *กฎ*
#                        ไม่ใช่สถานะ — generator เคยแก้เป็น 29 แล้วเปลี่ยนความหมายของกฎไปเลย
#   BACKLOG              บันทึกหลักฐาน B26 อ้างข้อความผิดของเดิมไว้ตรง ๆ ว่า "447 entries
#                        across 28 categories" แล้ว generator เขียนทับเป็นเลขปัจจุบัน
#                        บันทึกจึงกลายเป็นบอกว่าข้อความที่เคยผิดคือข้อความที่ถูก
#   docs/impact/         Impact Map ต่องาน = ภาพ ณ วันที่ทำ ยังไม่มีเลขที่ตรงแพตเทิร์นตอนนี้
#                        แต่เป็นชนิดเดียวกัน กันทั้งโฟลเดอร์ดีกว่ารอให้พังก่อนแล้วค่อยเติมชื่อ
SKIP_DOCS = {'CHANGELOG.md', 'NOHELL-NEXT-MISSION.md', 'BACKLOG.md'}
#   docs/research/       รายงานวิจัย = บันทึก อ้างสถานะ *ณ วันที่ค้น* และคัดข้อความจากโจทย์
#                        มาตรง ๆ (โจทย์เขียน "488 ข้อ" ไว้ ซึ่งตอนนี้เป็น 490 แล้ว)
#                        วัดแล้วว่าถ้าไม่กัน --check แดง 7 จุด และตัวที่แดงคือเลขในร้อยแก้ว
#                        ที่ pattern อ่านผิดเรื่อง เช่น "4" กับ "1" ถูกอ่านว่าเป็นจำนวนหมวด
#                        ⇒ โหมดเขียนจะแก้เป็น 31 ทั้งหมด = ทำลายเนื้อหาของรายงาน
#   docs/proposals/      ข้อเสนอ อ้าง ID และเลขของข้อที่ *ยังไม่มี* ในแคตตาล็อก
SKIP_DIRS = ('docs/impact', 'docs/archaeology', 'docs/adr',
             'docs/research', 'docs/proposals')

# ข้อเท็จจริงเชิงตัวเลขที่เอกสารประกาศ — ที่เดียว เพิ่มเรื่องใหม่ = เพิ่มหนึ่งแถว
#   scope  ไฟล์ที่คำประกาศนี้อยู่ได้ (None = เอกสารทุกไฟล์)
#   pats   ต้องมีกลุ่มเดียวคือตัวเลข ที่เหลือเป็น lookaround กว้างศูนย์ จึงแทนที่ตรงเลขได้
#   least  จำนวนจุดขั้นต่ำที่ต้องเจอ (วัดจากของจริง) เจอน้อยกว่า = วลีถูก reword แล้ว
#          ตัวตรวจกำลังเงียบ ซึ่งแย่กว่าเลขผิดเพราะไม่มีใครรู้
FACTS = [
    # scope แคบที่ SKILL.md เพราะ "NNN ข้อ" ที่อื่นเป็นเลขอื่น — ยอดต่อระดับ P1/P2/P3 ·
    # ยอดที่ใช้ได้ทุก stack · ยอดที่ร้าน Go + PostgreSQL อ่าน
    # ⛔ ห้ามเขียนตัวเลขจริงลงคอมเมนต์นี้ — คอมเมนต์ไม่ถูก build-summary เขียนทับ มันจะค้าง
    #    แล้วกลายเป็นคำอธิบายที่ขัดกับไฟล์ที่มันอธิบายเอง (CODE-19 · CODE-27)
    ('จำนวนข้อรวม', ['skills/nohell/SKILL.md'], [r'(\d{3,})(?= ข้อ)'], 3),
    # เลขตัวหลังในวลี "NNN จาก NNN ข้อเป็น P1" คือยอดรวม อยู่คนละไฟล์กับ scope ข้างบน
    # ไม่ใส่ไว้ทำให้ README เขียน "143 จาก 447" ทั้งที่ยอดจริงเป็น 460 — ผิดกว่าเดิม
    ('จำนวนข้อรวมในวลี P1', None, [r'(?<= จาก )(\d+)(?= ข้อเป็น P1)',
                                   r'(?<= of )(\d+)(?= entries are P1)'], 2),
    # ⚠️ ยอดรวมถูกประกาศอีกเจ็ดจุดที่ scope ข้างบนมองไม่เห็น ทั้งเจ็ดค้างที่ 447 ข้ามมาสองรุ่น
    # (447 → 460 → 473) รวมถึงบรรทัดพาดหัวของ README ทั้งสองภาษา — least กันได้แค่วลีที่เคย
    # ประกาศไว้ จุดที่ไม่เคยอยู่ในตารางนี้จึงโกหกเงียบตลอดกาล ทางแก้คือให้ที่นี่เป็นเจ้าของทุกจุด
    # ต้อง anchor รายวลี ห้ามใช้ pattern กว้าง เพราะ README.md:202 เขียน "473 จาก 1,413 ไฟล์"
    # ซึ่งเป็นจำนวน *ไฟล์* ที่บังเอิญเท่ากับยอดรวมพอดี และ README.en.md:188 มี "2.66x"
    ('จำนวนข้อรวมนอก SKILL.md', None, [
        r'(?<=anti-pattern )(\d+)(?= ข้อ)',
        r'(?<=ไล่ใหม่ทั้ง )(\d+)(?= ข้อ)',
        r'(?<= จาก )(\d+)(?= ข้อ — )',
        r'(\d+)(?=-entry anti-pattern)',
        r'(\d+)(?= entries across )',
        r'(?<=All )(\d+)(?= entries)',
        r'(?<= of )(\d+)(?= and skips)',
    ], 7),
    # least ลดจาก 3 เป็น 2 ตอนกัน NOHELL-NEXT-MISSION ออก — จุดที่สามอยู่ในไฟล์แผนนั้น
    # แล้วขึ้นเป็น 4 ตอนเติมวลีอังกฤษ ซึ่งค้างที่ 28 หมวดอยู่สองรุ่นเพราะ pattern เดิมเป็นไทยล้วน
    ('จำนวนหมวด', None, [r'(\d+)(?= หมวด)',
                          r'(?<=across )(\d+)(?= categories)'], 4),
    ('จำนวน P1', None, [r'(?<=\*\*P1\*\* )(\d+)',
                        r'(\d+)(?= จาก \d+ ข้อเป็น P1)',
                        r'(\d+)(?= of \d+ entries are P1)'], 4),
    ('จำนวน P2', None, [r'(?<=\*\*P2\*\* )(\d+)'], 2),
    ('จำนวน P3', None, [r'(?<=\*\*P3\*\* )(\d+)'], 2),
    ('จำนวนกฎอัตโนมัติ', None, [r'(?<=ตรวจอัตโนมัติได้ )(\d+)',
                                r'(\d+)(?= of the entries are machine-checkable)'], 2),
    # เลขชุด "ใช้กับ" — เอกสารบอกผู้อ่านว่าข้ามได้กี่ข้อ ซึ่งเปลี่ยนทุกครั้งที่เพิ่มหมวดที่ผูก stack
    # ตอนเพิ่ม MOBILE กับ ML สองหมวดนี้เลื่อนไป 26 ข้อ แต่ HELL-CATALOG ยังบอก "ข้ามอีก 40"
    ('จำนวนข้อที่ใช้ได้ทุก stack', None, [r'(?<=`ทุกที่` )(\d+)(?= ข้อ)',
                                          r'(\d+)(?= entries \()'], 2),
    ('สัดส่วนข้อที่ใช้ได้ทุก stack', None, [r'(?<= ข้อ \()(\d+)(?=%\))',
                                            r'(?<= entries \()(\d+)(?=%\))'], 2),
    # 🪤 จุดที่สี่ (`อ่าน NNN จาก NNN ข้อ` ใน SKILL.md) หลุดการเฝ้ามาตลอด
    #    ตอนรวม 483 มันเขียน 407 ซึ่งถูก พอรวมเป็น 488 มันควรเป็น 412 แต่ไม่มีใครแก้
    #    ผลคือไฟล์เดียวกันขัดกันเอง "407 จาก 488" กับ "412 จาก 488" — เติม pattern แล้วดันขั้นต่ำเป็น 4
    ('จำนวนข้อที่ร้าน RDBMS อ่านได้', None, [r'(?<=`RDBMS` = )(\d+)',
                                             r'(?<=อ่าน )(\d+)(?= ข้อ ข้ามอีก)',
                                             r'(?<=reads )(\d+)(?= of )',
                                             r'(?<=อ่าน )(\d+)(?= จาก \d+ ข้อ)'], 4),
    ('จำนวนข้อที่ข้ามได้', None, [r'(?<=ข้ามอีก )(\d+)',
                                  r'(?<=the other )(\d+)'], 3),
    # CONTRIBUTING เคยเขียนว่า "หมวดใหม่ทั้งห้า (TYPE AGG MEAS REG TOOL) ยังไม่มีกฎอัตโนมัติ"
    # ซึ่งจริงตอนเขียน แต่เป็น snapshot ที่แต่งเป็นประโยค พอเพิ่มหมวดมันไม่ผิดแบบดัง มันแค่เล็กลง
    # จนบอกงานที่เหลือต่ำกว่าจริงสามเท่า (ของจริง 16 หมวด) — แทนที่ด้วยเลขที่คำนวณได้
    ('จำนวนหมวดที่ยังไม่มีกฎ', None, [r'(?<=สักข้อมี )(\d+)'], 1),
    # รายการ `ใช้กับ` พร้อมจำนวน มีสามสำเนาสามรูปแบบ — legend ในแคตตาล็อก · ตารางใน SKILL.md
    # (ทั้งคู่ agent/คนใช้กรองก่อนอ่าน คนละจังหวะโหลด จึงต้องมีทั้งคู่) · ร้อยแก้วใน README สองภาษา
    # เซสชันเดียวต้องไล่แก้มือสามรอบตอนเพิ่ม MOBILE/ML/PDPA และรอบที่สาม `PII` หายจาก README
    # ทั้งสองภาษาโดยไม่มีด่านไหนฟ้อง — คือ REG-07 ในแคตตาล็อกนี้เอง
    # แถวนี้เป็น fact แบบ dict: regex จับ *คีย์* แล้วเปิดหาค่า เพิ่ม stack ใหม่จึงไม่ต้องมาเพิ่มแถวที่นี่
    # (การมี *แถว* ครบเป็นเรื่องรูปร่าง อยู่ที่ validate-catalog.sh ข้อ 14 ไม่ใช่ที่นี่)
    ('จำนวนข้อต่อ stack', None, [
        r'`(?P<key>[^`]+)` \((?P<num>\d+)\)',
        r'\| `(?P<key>[^`]+)` \| (?P<num>\d+) \|',
        r'`(?P<key>[^`]+)` (?P<num>\d+)(?= ·)',
    ], 35),
]


def build(text):
    order, count = [], {}
    for m in re.finditer(r'^\| ([A-Z]+)-\d+ \|', text, re.M):
        c = m.group(1)
        if c not in count:
            order.append(c)
            count[c] = 0
        count[c] += 1

    half = (len(order) + 1) // 2
    left, right = order[:half], order[half:]
    rows = [MARK, '| หมวด | จำนวน | หมวด | จำนวน |', '|---|---|---|---|']
    for k in range(half):
        a = '| %s | %d ' % (left[k], count[left[k]])
        b = '| %s | %d |' % (right[k], count[right[k]]) if k < len(right) else '|  |  |'
        rows.append(a + b)
    rows.append('| **รวม** | **%d** | **หมวด** | **%d** |' % (sum(count.values()), len(order)))
    return '\n'.join(rows), sum(count.values()), len(order), count


# เลขในตัวแคตตาล็อกเอง (หัวไฟล์ · ท้ายหัวข้อหมวด) เดิมเป็นข้อ 1 กับข้อ 2 ใน validate-catalog.sh
# ทั้งคู่เป็นเลขที่คำนวณจาก build() ได้อยู่แล้ว จึง generate ทิ้งไปเลย ไม่ต้อง assert
HEAD = re.compile(r'^(## ([A-Z]+) [^\n]*?\()(\d+)(\))$', re.M)


def fix_catalog_numbers(text, total, count):
    text = re.sub(r'(?<=^# HELL CATALOG — )\d+', str(total), text, count=1)
    return HEAD.sub(
        lambda m: '%s%d%s' % (m.group(1), count.get(m.group(2), int(m.group(3))), m.group(4)),
        text)


def splice(text, table):
    lines = text.split('\n')
    start = next(k for k, l in enumerate(lines) if l.startswith('## สรุปจำนวน'))
    k = start + 1
    while k < len(lines) and not (lines[k].startswith('|') or lines[k].startswith('<!--')):
        k += 1
    end = k
    while end < len(lines) and (lines[end].startswith('|') or lines[end].startswith('<!--')):
        end += 1
    lines[k:end] = table.split('\n')
    return '\n'.join(lines)


def doc_files():
    out = sorted(glob.glob('*.md'))
    for d in ('skills', 'docs'):
        for root, _, files in os.walk(d):
            out += [os.path.join(root, f) for f in sorted(files) if f.endswith('.md')]
    return [p for p in out
            if os.path.basename(p) not in SKIP_DOCS
            and not p.replace('\\', '/').startswith(SKIP_DIRS)]


def usage_counts(text):
    """นับช่อง `ใช้กับ` ต่อค่า

    ต้องแทน `\\|` ก่อนแยกช่อง เพราะ SQL-29 มี pipe หนีอยู่ในโค้ด — regex ที่ไม่รู้เรื่องนี้
    นับได้ 472 จาก 473 แถวแล้วทำให้ 407 กับ 31 ดูเหมือนผิดไปหนึ่ง ทั้งที่ถูกอยู่แล้ว
    """
    out = {}
    for line in text.split('\n'):
        if re.match(r'^\| [A-Z]+-\d+ \|', line):
            cols = [c.strip() for c in line.replace('\\|', '\x01').split('|')[1:-1]]
            out[cols[-1]] = out.get(cols[-1], 0) + 1
    return out


def truth(text):
    """ค่าจริงของทุกข้อเท็จจริงใน FACTS — คำนวณจากแคตตาล็อกและ hell-rules.yaml เท่านั้น"""
    ids = re.findall(r'^\| ([A-Z]+)-\d+ \|', text, re.M)
    sev = re.findall(r'^\| [A-Z]+-\d+ \| (P[123]) \|', text, re.M)
    # นับกฎทุกข้อ แต่ผูกกับหมวดได้เฉพาะ id ที่เข้ารูป [A-Z]+-NN — `PR-CHECKLIST` เป็นกฎจริง
    # ที่ไม่ได้อ้างข้อในแคตตาล็อก การเอาไปนับรวมในหมวดจะทำให้ทั้งสองเลขผิดคนละทาง
    nrules, ruled = 0, set()
    if os.path.exists(RULES):
        for l in io.open(RULES, encoding='utf-8'):
            if not l.startswith('  - id: '):
                continue
            nrules += 1
            m = re.match(r'  - id: ([A-Z]+)-\d+\s*$', l)
            if m:
                ruled.add(m.group(1))
    use = usage_counts(text)
    anywhere = use.get('ทุกที่', 0)
    rdbms = anywhere + use.get('RDBMS', 0)
    return {
        'จำนวนข้อรวม': len(ids),
        'จำนวนข้อรวมในวลี P1': len(ids),
        'จำนวนข้อรวมนอก SKILL.md': len(ids),
        'จำนวนหมวด': len(set(ids)),
        'จำนวน P1': sev.count('P1'),
        'จำนวน P2': sev.count('P2'),
        'จำนวน P3': sev.count('P3'),
        'จำนวนกฎอัตโนมัติ': nrules,
        'จำนวนข้อที่ใช้ได้ทุก stack': anywhere,
        'สัดส่วนข้อที่ใช้ได้ทุก stack': int(round(100.0 * anywhere / len(ids))) if ids else 0,
        'จำนวนข้อที่ร้าน RDBMS อ่านได้': rdbms,
        'จำนวนข้อที่ข้ามได้': len(ids) - rdbms,
        'จำนวนหมวดที่ยังไม่มีกฎ': len(set(ids) - ruled),
        'จำนวนข้อต่อ stack': use,
    }


def num_group(m):
    """กลุ่มที่เก็บตัวเลข — `num` ถ้า pattern ประกาศไว้ ไม่งั้นกลุ่ม 1 ตามรูปเดิม"""
    return 'num' if 'num' in m.re.groupindex else 1


def want_of(values, name, m):
    """ค่าที่ควรเป็นของ match นี้

    fact ธรรมดามีค่าเดียว ส่วน fact ที่ค่าเป็น dict ให้ regex จับ *คีย์* มาเปิดหาเอา
    ใช้กับรายการที่หนึ่งบรรทัดมีหลายค่า เช่นรายการ `ใช้กับ` ที่มีสามสำเนาในสามรูปแบบ
    คืน None ถ้าคีย์ไม่มีอยู่จริง เพื่อให้ผู้เรียกข้ามไปโดยไม่แตะข้อความ
    """
    v = values[name]
    if not isinstance(v, dict):
        return str(v)
    k = m.group('key')
    return str(v[k]) if k in v else None


def rewrite(m, value):
    """คืน match เดิมโดยแทนเฉพาะช่วงที่เป็นตัวเลข

    pattern รูปเดิมมีแต่ lookaround กว้างศูนย์ ตัวเลขจึงเป็นทั้ง match พอดี ผลลัพธ์เท่าเดิม
    ส่วน pattern ที่จับคีย์มาด้วย ต้องคงคีย์ไว้ ไม่งั้นชื่อ stack จะถูกเขียนทับด้วยตัวเลข
    """
    s, e = m.span(num_group(m))
    return m.group(0)[:s - m.start()] + value + m.group(0)[e - m.start():]


def sync_facts(values, check):
    problems, edited = [], []
    for name, scope, pats, least in FACTS:
        paths = [p for p in (scope if scope else doc_files()) if os.path.exists(p)]
        found = {}
        for path in paths:
            text = io.open(path, encoding='utf-8').read()
            for pat in pats:
                for m in re.finditer(pat, text):
                    want = want_of(values, name, m)
                    if want is None:
                        problems.append('%s — %s:%d คีย์ %r ไม่มีอยู่จริง'
                                        % (name, path, text[:m.start()].count('\n') + 1,
                                           m.group('key')))
                        continue
                    found.setdefault(path, []).append(
                        (text[:m.start()].count('\n') + 1, m.group(num_group(m)), want))
        seen = sum(len(v) for v in found.values())

        # ด่านนี้ต้องมาก่อนเขียน — ถ้าวลีถูก reword แปลว่าชุด pattern เชื่อไม่ได้แล้ว
        # และ build จะไปแก้เลขที่เหลือทับเอกสารโดยที่คนไม่รู้ว่ามันมองไม่เห็นอะไรไปบ้าง
        if seen < least:
            problems.append('%s — เจอคำประกาศ %d จุด ต่ำกว่า %d จุดที่เคยมี '
                            'วลีถูกแก้แล้วตัวตรวจกำลังเงียบ (ไม่แตะไฟล์)' % (name, seen, least))
            continue

        for path, hits in found.items():
            if check:
                problems += ['%s — %s:%d เขียน %s ของจริง %s' % (name, path, ln, got, want)
                             for ln, got, want in hits if got != want]
                continue
            if any(got != want for _, got, want in hits):
                text = io.open(path, encoding='utf-8').read()
                for pat in pats:
                    text = re.sub(
                        pat,
                        lambda m: (rewrite(m, want_of(values, name, m))
                                   if want_of(values, name, m) is not None else m.group(0)),
                        text)
                io.open(path, 'w', encoding='utf-8', newline='\n').write(text)
                edited.append(path)
    return problems, sorted(set(edited))


def main():
    check = '--check' in sys.argv
    text = io.open(PATH, encoding='utf-8').read()
    table, total, ncat, count = build(text)
    out = fix_catalog_numbers(splice(text, table), total, count)
    rc = 0

    if out != text:
        if check:
            sys.stderr.write('FAIL  ตัวเลขในแคตตาล็อก (หัวไฟล์ · ท้ายหัวข้อหมวด · ตารางสรุป) '
                             'ไม่ตรงกับของจริง — รัน python scripts/build-summary.py\n')
            rc = 1
        else:
            io.open(PATH, 'w', encoding='utf-8', newline='\n').write(out)
            print('เขียนตัวเลขในแคตตาล็อกใหม่')
            text = out

    problems, edited = sync_facts(truth(text), check)
    for p in problems:
        sys.stderr.write('FAIL  %s\n' % p)
    if problems:
        rc = 1
    if edited:
        print('เขียนตัวเลขใหม่ใน: %s' % ', '.join(edited))
    if rc == 0:
        print('OK    ตัวเลขตรงทั้งหมด: %d ข้อ %d หมวด · เฝ้าคำประกาศ %d เรื่อง'
              % (total, ncat, len(FACTS)))
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
