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

# CHANGELOG เป็นบันทึกประวัติ หน้าที่ของมันคืออ้างเลขที่ตกยุคได้ จึงไม่ใช่คำประกาศสถานะ
SKIP_DOCS = {'CHANGELOG.md'}

# ข้อเท็จจริงเชิงตัวเลขที่เอกสารประกาศ — ที่เดียว เพิ่มเรื่องใหม่ = เพิ่มหนึ่งแถว
#   scope  ไฟล์ที่คำประกาศนี้อยู่ได้ (None = เอกสารทุกไฟล์)
#   pats   ต้องมีกลุ่มเดียวคือตัวเลข ที่เหลือเป็น lookaround กว้างศูนย์ จึงแทนที่ตรงเลขได้
#   least  จำนวนจุดขั้นต่ำที่ต้องเจอ (วัดจากของจริง) เจอน้อยกว่า = วลีถูก reword แล้ว
#          ตัวตรวจกำลังเงียบ ซึ่งแย่กว่าเลขผิดเพราะไม่มีใครรู้
FACTS = [
    # scope แคบที่ SKILL.md เพราะ "NNN ข้อ" ที่อื่นเป็นเลขอื่น (136/154/157 ต่อระดับ ·
    # 358 ใช้ได้ทุก stack · 407 จำนวนที่ร้าน Go + PostgreSQL อ่าน)
    ('จำนวนข้อรวม', ['skills/nohell/SKILL.md'], [r'(\d{3,})(?= ข้อ)'], 3),
    ('จำนวนหมวด', None, [r'(\d+)(?= หมวด)'], 3),
    ('จำนวน P1', None, [r'(?<=\*\*P1\*\* )(\d+)',
                        r'(\d+)(?= จาก \d+ ข้อเป็น P1)',
                        r'(\d+)(?= of \d+ entries are P1)'], 4),
    ('จำนวน P2', None, [r'(?<=\*\*P2\*\* )(\d+)'], 2),
    ('จำนวน P3', None, [r'(?<=\*\*P3\*\* )(\d+)'], 2),
    ('จำนวนกฎอัตโนมัติ', None, [r'(?<=ตรวจอัตโนมัติได้ )(\d+)',
                                r'(\d+)(?= of the entries are machine-checkable)'], 2),
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
    return [p for p in out if os.path.basename(p) not in SKIP_DOCS]


def truth(text):
    """ค่าจริงของทุกข้อเท็จจริงใน FACTS — คำนวณจากแคตตาล็อกและ hell-rules.yaml เท่านั้น"""
    ids = re.findall(r'^\| ([A-Z]+)-\d+ \|', text, re.M)
    sev = re.findall(r'^\| [A-Z]+-\d+ \| (P[123]) \|', text, re.M)
    nrules = 0
    if os.path.exists(RULES):
        nrules = sum(1 for l in io.open(RULES, encoding='utf-8') if l.startswith('  - id: '))
    return {
        'จำนวนข้อรวม': len(ids),
        'จำนวนหมวด': len(set(ids)),
        'จำนวน P1': sev.count('P1'),
        'จำนวน P2': sev.count('P2'),
        'จำนวน P3': sev.count('P3'),
        'จำนวนกฎอัตโนมัติ': nrules,
    }


def sync_facts(values, check):
    problems, edited = [], []
    for name, scope, pats, least in FACTS:
        want = str(values[name])
        paths = [p for p in (scope if scope else doc_files()) if os.path.exists(p)]
        found = {}
        for path in paths:
            text = io.open(path, encoding='utf-8').read()
            for pat in pats:
                for m in re.finditer(pat, text):
                    found.setdefault(path, []).append(
                        (text[:m.start()].count('\n') + 1, m.group(1)))
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
                             for ln, got in hits if got != want]
                continue
            if any(got != want for _, got in hits):
                text = io.open(path, encoding='utf-8').read()
                for pat in pats:
                    text = re.sub(pat, want, text)
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
