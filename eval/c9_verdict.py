# -*- coding: utf-8 -*-
"""ตัดสินการทดลอง C9 ตามเกณฑ์ที่ประกาศไว้ **ก่อน** ข้อมูลรอบ 2-3 มาถึง

เกณฑ์อยู่ใน docs/research/2026-09-03-section9-verdicts.md §6.1 และถูก commit
ไว้ที่ e1ad486 ตอนที่รอบ 2 เพิ่งยิงไป 5/46 เคส และรอบ 3 ยังไม่ได้ยิง

ไฟล์นี้เขียนขึ้นในช่วงเวลาเดียวกัน ด้วยเจตนาเดียวกัน: **ให้เครื่องตัดสินตามกฎ
แทนที่จะให้คนมองตัวเลขแล้วตีความ** ถ้าผลออกมาไม่ถูกใจแล้วอยากเปลี่ยนเกณฑ์
การเปลี่ยนนั้นจะปรากฏใน git diff ของไฟล์นี้

    python eval/c9_verdict.py

เส้นฐานที่ใช้ไม่ใช่ศูนย์ แต่คือ **ความแกว่างของแขน `full` เอง** — มันเคยทำได้ถึง
0.875 ด้วยตัวมันเอง ผลที่ 0.875 จึงไม่ใช่หลักฐานอะไร ต้องเกินนั้น
"""
import statistics, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run import judge, load_bank, load_cases, load_keys, parse_answer, BLOCKED_RE  # noqa: E402

# ── เกณฑ์ที่ตกลงไว้ล่วงหน้า ห้ามแก้หลังเห็นข้อมูล ──────────────────────
BEST_FULL = 0.875      # รอบที่ดีที่สุดที่แขน full เคยทำได้ (4 รอบ)
WORST_FULL = 0.750     # รอบที่แย่ที่สุดของ full
RECALL_FLOOR = 0.8214  # ค่าที่ทั้งสองแขนได้เท่ากันในรอบ 1
FULL_ROUNDS = [0.750, 0.875, 0.750, 0.750]


def contaminated(*banks):
    """เคสที่คำตอบเป็นคำขอสิทธิ์ ไม่ใช่คำตอบ — ต้องกันออกจากทุกแขนเท่ากัน"""
    bad = set()
    for b in banks:
        for cid, reps in b.items():
            for r in reps:
                if BLOCKED_RE.search(r) and parse_answer(r)[2]:
                    bad.add(cid)
    return bad


def main():
    cases, keys = load_cases(), load_keys()
    old = load_bank('full', '')
    t1 = load_bank('full', 't1')
    rounds = [('ร1', load_bank('full_ask', 'c9')),
              ('ร2', load_bank('full_ask', 'c9b')),
              ('ร3', load_bank('full_ask', 'c9c'))]

    # ⚠️ **ห้ามให้คะแนนรอบที่ยังยิงไม่ครบ** — ธนาคารถูกเขียนสะสมทีละก้อน และก้อนถูกเรียง
    # ตามชื่อเคส ⇒ รอบที่ยิงไปครึ่งเดียวจะมีแต่เคส a*/b* ซึ่งเป็น subset ที่เอียงโดยสิ้นเชิง
    # วัดมาแล้ว: ตอนรอบ 2 มี 15/46 เคส สคริปต์นี้คำนวณ recall ได้ 0.7500 แล้วตัดสินว่า
    # "ต้นทุนพัง" ทั้งที่ยังไม่ได้วัดอะไรเลย — เป็นบั๊กคลาสเดียวกับที่เอกสารทั้งฉบับไล่จับอยู่
    # (ตัวเลขหน้าตาปกติจากการคำนวณที่ไม่มีความหมาย)
    n_all = len(cases)
    have, partial = [], []
    for n, b in rounds:
        if not b:
            continue
        (have if len(b) >= n_all else partial).append((n, b, len(b)))
    for n, _, k in partial:
        sys.stderr.write('ข้าม %s — ยิงได้ %d/%d เคส ยังไม่ครบ ให้คะแนนไม่ได้\n' % (n, k, n_all))
    have = [(n, b) for n, b, _ in have]
    if len(have) < 3:
        sys.stderr.write('มีรอบที่ครบ %d/3 — ตัดสินได้เมื่อครบ 3 รอบ (แสดงเท่าที่มี)\n'
                         % len(have))

    bad = contaminated(t1, *[b for _, b in have])
    # เคส must-ask ที่ *ทุก* ธนาคารมีครบ เพื่อให้เทียบข้ามรอบได้จริง
    pool = [c for c in cases if c['must_ask'] and c['id'] in old and c['id'] in t1
            and all(c['id'] in b for _, b in have) and c['id'] not in bad]
    print('เคส must-ask ที่เทียบได้ทุกธนาคาร: %d ใบ %s'
          % (len(pool), [c['id'][:3] for c in pool]))
    print('กันเคสปนเปื้อนออก %d ใบ: %s\n' % (len(bad), sorted(bad)))

    def ask(bank, i=0):
        v = [judge(c, bank[c['id']][i], keys)['ask_ok'] for c in pool if len(bank[c['id']]) > i]
        return sum(v) / len(v) if v else 0.0

    def recall_and_bug(bank, i=0):
        rec = [judge(c, bank[c['id']][i], keys)['recall'] for c in cases
               if c['id'] in bank and c['id'] not in bad and len(bank[c['id']]) > i]
        rec = [x for x in rec if x is not None]
        bug = sum(judge(c, bank[c['id']][i], keys)['ask_on_bug'] for c in cases
                  if c['id'] in bank and c['id'] not in bad and len(bank[c['id']]) > i)
        return (sum(rec) / len(rec) if rec else 0.0), bug

    print('เส้นฐาน — แขน full 4 รอบ: %s' % FULL_ROUNDS)
    print('  ดีที่สุด %.3f · แย่ที่สุด %.3f · sd %.4f\n'
          % (BEST_FULL, WORST_FULL, statistics.stdev(FULL_ROUNDS)))

    print('%-6s %-10s %-12s %-12s %s' % ('รอบ', 'must_ask', 'recall', 'ask_on_bug', 'ผ่านเกณฑ์'))
    verdicts = []
    for name, bank in have:
        a = ask(bank)
        r, bug = recall_and_bug(bank)
        ok_ask = a > BEST_FULL
        ok_cost = (bug == 0) and (r >= RECALL_FLOOR - 1e-9)
        verdicts.append((name, a, r, bug, ok_ask, ok_cost))
        mark = ('ผ่าน' if (ok_ask and ok_cost) else
                ('ต้นทุนพัง' if ok_ask else
                 ('ต่ำกว่าเส้นฐาน' if a < WORST_FULL else 'อยู่ในช่วงที่ full ทำเองได้')))
        print('%-6s %-10.4f %-12.4f %-12d %s' % (name, a, r, bug, mark))

    print()
    if len(verdicts) < 3:
        print('⏸ ยังไม่ครบ 3 รอบ — ยังตัดสินไม่ได้')
        return 2
    later = verdicts[1:]           # เกณฑ์พูดถึง "รอบ 2 และ 3"
    all_above = all(v[4] for v in later)
    any_below_floor = any(v[1] < WORST_FULL for v in later)
    cost_ok = all(v[5] for v in verdicts)

    if not cost_ok:
        print('❌ **ไม่ผ่าน** — ต้นทุนพัง (ask_on_bug ขึ้น หรือ recall ต่ำกว่า %.4f)' % RECALL_FLOOR)
        print('   เกณฑ์ระบุว่าถ้าต้นทุนพัง ให้ถือว่าไม่ผ่านแม้ must_ask จะสูง')
        return 1
    if any_below_floor:
        print('❌ **ทิ้งข้อเสนอ** — มีรอบที่ต่ำกว่ารอบแย่สุดของ full (%.3f)' % WORST_FULL)
        return 1
    if all_above:
        print('✅ **ผ่าน** — รอบ 2 และ 3 สูงกว่ารอบที่ดีที่สุดของ full (%.3f) ทั้งคู่' % BEST_FULL)
        print('   ⇒ ผลไม่ใช่ความแกว่างของแขน · เสนอเอาประโยคนี้เข้า skills/nohell/SKILL.md')
        print('   ⚠️ ยังไม่ใช่นัยสำคัญทางสถิติ — เกณฑ์นี้ใช้ %d เคส' % len(pool))
        return 0
    print('⚠️ **ยังไม่พอ** — มีรอบที่ไม่เกิน %.3f ซึ่งเป็นค่าที่ full ไปถึงได้เอง' % BEST_FULL)
    print('   ⇒ ต้องเพิ่มเคส must-ask ก่อน ไม่ใช่เพิ่มรอบ (ดู §4.2 ของเอกสาร)')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
