# -*- coding: utf-8 -*-
"""สร้างตารางสรุปจำนวนท้าย HELL-CATALOG.md ใหม่จากข้อมูลจริง

ตารางนี้เคยผิดมาก่อน (หมวด SSOT 18 ข้อหายไปทั้งหมวด และยอดรวมค้างที่เลขเก่า)
เพราะไม่มีใครแก้ตอนเพิ่มข้อ วิธีกันคือไม่ให้แก้มืออีกเลย

    python scripts/build-summary.py            # เขียนทับตารางในไฟล์
    python scripts/build-summary.py --check    # แค่ตรวจ ไม่แก้ (คืน exit 1 ถ้าไม่ตรง)
"""
import io, re, sys

PATH = 'skills/nohell/HELL-CATALOG.md'
MARK = '<!-- generate ด้วย scripts/build-summary.py ห้ามแก้มือ -->'


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
    return '\n'.join(rows), sum(count.values()), len(order)


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


def main():
    text = io.open(PATH, encoding='utf-8').read()
    table, total, ncat = build(text)
    out = splice(text, table)
    if '--check' in sys.argv:
        if out != text:
            sys.stderr.write('ตารางสรุปไม่ตรงกับข้อมูลจริง — รัน python scripts/build-summary.py\n')
            return 1
        print('OK    ตารางสรุปตรง: %d ข้อ %d หมวด' % (total, ncat))
        return 0
    io.open(PATH, 'w', encoding='utf-8', newline='\n').write(out)
    print('เขียนตารางสรุปใหม่: %d ข้อ %d หมวด' % (total, ncat))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
