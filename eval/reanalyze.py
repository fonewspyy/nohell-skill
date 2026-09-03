# -*- coding: utf-8 -*-
"""ตอบจุดขัดแย้งใน §9 ของรายงานที่ **ตอบได้จากคำตอบที่เก็บไว้แล้ว** โดยไม่ยิงเพิ่มสักสาย

ที่มา: docs/research/2026-09-02-accuracy-speed-eval.md §9 ตาราง C1-C16
รายงานปฏิเสธที่จะเลือกข้างให้ทุกข้อ โดยบอกว่า "ถ้าต้องตัดสินใจ ต้องวัดเอง"
ไฟล์นี้วัดสามข้อที่ **ข้อมูลในมือพอตอบอยู่แล้ว** — ไม่ต้องใช้โควตา ไม่ต้องรอ

    C6   N-vote คุ้มไหม            รวมคำตอบ 3 รอบด้วยกติกาต่าง ๆ แล้วเทียบกับรอบเดียว
    C11  eval ต้องมีกี่เคส          bootstrap หาช่วงความเชื่อมั่น + ผลต่างที่เล็กที่สุดที่ชุดนี้จับได้
    C15  stdev 0.0385 แปลว่าอะไร    แยกความแปรปรวนรอบต่อรอบ ออกจากความแปรปรวนเคสต่อเคส

⚠️ ไฟล์นี้ **ไม่ตัดสินคะแนนเอง** — มันสร้างบรรทัดคำตอบสังเคราะห์แล้วส่งเข้า judge() ตัวจริง
   ใน run.py ถ้าเขียนกติกาให้คะแนนซ้ำที่นี่ วันหนึ่งสองที่จะเดินจากกันแล้วไม่มีอะไรฟ้อง
   (ARCH-08 ในแคตตาล็อกตัวเอง) ทางเดียวที่คะแนนเข้ามาได้คือผ่าน judge() เดิม

    python eval/reanalyze.py                 # ใช้ธนาคารของแขน full
    python eval/reanalyze.py --arm routed --runs 1
    python eval/reanalyze.py --compare routed
"""
import argparse, os, random, statistics, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run import judge, load_bank, load_cases, load_keys, parse_answer, timing_path  # noqa: E402


def as_reply(ids, said_ask):
    """ประกอบบรรทัดคำตอบสังเคราะห์ เพื่อส่งกลับเข้า judge() ตัวจริง

    ต้องผ่าน WELLFORMED_RE ของ run.py ไม่งั้นจะถูกนับเป็น malformed แล้วตัวเลขเพี้ยน
    ลำดับ ID ถูกเรียงเพื่อให้ผลซ้ำได้ (set ของ python สลับลำดับข้ามการรัน)
    """
    if said_ask and not ids:
        return 'ASK'
    if not ids:
        return 'NONE'
    return ('ASK ' if said_ask else '') + ' '.join(sorted(ids))


def score_set(cases, keys, reply_of):
    """ให้คะแนนทั้งชุดหนึ่งครั้ง · reply_of(case) คืนข้อความคำตอบ

    คืนทั้งยอดรวม **และ** คะแนนรายเคส เพราะ C11/C15 ต้องการรายเคส
    การมีแต่ยอดรวมคือสาเหตุที่ sd ของ run.py ตอบคำถามผิดข้อมาตลอด
    """
    per_case, rec, ask = {}, [], []
    fa = okay = on_bug = 0
    for c in cases:
        j = judge(c, reply_of(c), keys)
        per_case[c['id']] = j
        if j['recall'] is not None:
            rec.append(j['recall'])
        if j['ask_ok'] is not None:
            ask.append(j['ask_ok'])
        fa += j['false_alarm']
        okay += j['acceptable']
        on_bug += j['ask_on_bug']
    return {
        'recall': sum(rec) / len(rec) if rec else 0.0,
        'must_ask_hit': sum(ask) / len(ask) if ask else 0.0,
        'false_alarm_ids': fa, 'acceptable_ids': okay, 'ask_on_bug': on_bug,
        'n_recall_cases': len(rec), 'n_ask_cases': len(ask), 'per_case': per_case,
    }


def c6_vote(cases, keys, bank, runs):
    """C6 - 3 รอบ + majority vote คุ้มไหม

    ฝ่าย ก (#19 Tencent) ใช้ 3 รอบ + majority vote เป็นโปรโตคอล
    ฝ่าย ข (#12) ถูกหักล้าง 0-3 · งานอื่นใช้ temperature-0 ไม่โหวต
    รายงานสรุปว่า "หลักฐานไม่พอ" จึงต้องวัดกับข้อมูลของเราเอง

    สามกติกาที่เทียบ
      single    ค่าเฉลี่ยของแต่ละรอบเดี่ยว ๆ = สิ่งที่ run.py รายงานอยู่ทุกวันนี้
      union     ID ที่โผล่ **อย่างน้อย 1 ใน 3 รอบ** เพิ่ม recall แลกกับ false alarm
      majority  ID ที่โผล่ **อย่างน้อย 2 ใน 3 รอบ** โปรโตคอลของ #19
      unanimous ID ที่โผล่ **ครบทุกรอบ** ปลายอีกด้านของสเปกตรัม
    """
    singles = [score_set(cases, keys, lambda c, i=i: bank[c['id']][i]) for i in range(runs)]

    def agg(threshold):
        def reply_of(c):
            votes, ask = {}, 0
            for i in range(runs):
                ids, said_ask, _ = parse_answer(bank[c['id']][i])
                for x in ids:
                    votes[x] = votes.get(x, 0) + 1
                ask += 1 if said_ask else 0
            return as_reply({x for x, n in votes.items() if n >= threshold}, ask >= threshold)
        return score_set(cases, keys, reply_of)

    keys_of_interest = ('recall', 'must_ask_hit', 'false_alarm_ids',
                        'acceptable_ids', 'ask_on_bug')
    return {
        'single': {k: statistics.mean([s[k] for s in singles]) for k in keys_of_interest},
        'single_sd': {k: (statistics.stdev([s[k] for s in singles]) if runs > 1 else 0.0)
                      for k in keys_of_interest},
        'union': agg(1), 'majority': agg(2), 'unanimous': agg(runs),
        'n_recall_cases': singles[0]['n_recall_cases'],
        'n_ask_cases': singles[0]['n_ask_cases'],
    }


def boot_ci(values, iters=4000, seed=7):
    """ช่วงความเชื่อมั่น 95% จากการสุ่มซ้ำ **ระดับเคส** ไม่ใช่ระดับรอบ

    C15: run.py รายงาน sd จากค่าเฉลี่ยของ 3 รอบ ซึ่งถือว่า *เคสเป็นของตายตัว*
    มันจึงตอบได้แค่ "ถ้ายิงชุดเดิมซ้ำ จะได้เลขต่างกันแค่ไหน"
    ไม่ได้ตอบ "ถ้าเปลี่ยนไปใช้เคสอีกชุดหนึ่ง จะได้เลขต่างกันแค่ไหน" ซึ่งเป็นคำถามที่คนถามจริง
    #74 ในรายงานบอกว่า clustered SE ใหญ่กว่าได้ถึง 3 เท่า ตัวเลขข้างล่างวัดของจริง
    """
    if len(values) < 2:
        return (0.0, 0.0)
    rnd = random.Random(seed)
    n = len(values)
    means = sorted(statistics.mean([values[rnd.randrange(n)] for _ in range(n)])
                   for _ in range(iters))
    return (means[int(0.025 * iters)], means[int(0.975 * iters)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--arm', default='full')
    ap.add_argument('--tag', default='')
    ap.add_argument('--runs', type=int, default=3)
    ap.add_argument('--compare', default='',
                    help='แขนที่จะเทียบแบบจับคู่รายเคส เช่น routed (ใช้รอบที่ 1 ของทั้งสองแขน)')
    ap.add_argument('--compare-tag', default='')
    a = ap.parse_args()

    cases, keys = load_cases(), load_keys()
    bank = load_bank(a.arm, a.tag)
    ready = [c for c in cases if len(bank.get(c['id'], [])) >= a.runs]
    if len(ready) < len(cases):
        miss = [c['id'] for c in cases if len(bank.get(c['id'], [])) < a.runs]
        sys.stderr.write('ใช้เฉพาะ %d/%d เคสที่มีครบ %d รอบ ขาด: %s\n'
                         % (len(ready), len(cases), a.runs, ' '.join(miss[:8])))
    if not ready:
        sys.stderr.write('ไม่มีเคสที่มีคำตอบครบ ยิง eval ก่อน\n')
        return 2
    cases = ready

    print('# วิเคราะห์ซ้ำจากคำตอบที่เก็บไว้ · แขน %s · %d เคส · %d รอบ · ไม่ยิงเพิ่ม\n'
          % (a.arm, len(cases), a.runs))

    v = c6_vote(cases, keys, bank, a.runs)
    print('## C6 - N-vote คุ้มไหม  (เคสเข้าสูตร recall %d · must-ask %d)'
          % (v['n_recall_cases'], v['n_ask_cases']))
    hdr = '%-11s %-20s %-20s %-13s %-12s %s'
    print(hdr % ('กติกา', 'recall', 'must_ask_hit', 'false_alarm', 'acceptable', 'ask_on_bug'))
    print(hdr % ('single',
                 '%.4f (sd %.4f)' % (v['single']['recall'], v['single_sd']['recall']),
                 '%.4f (sd %.4f)' % (v['single']['must_ask_hit'], v['single_sd']['must_ask_hit']),
                 '%.1f' % v['single']['false_alarm_ids'],
                 '%.1f' % v['single']['acceptable_ids'],
                 '%.1f' % v['single']['ask_on_bug']))
    # ที่ runs=2 เกณฑ์ "อย่างน้อย 2 เสียง" กับ "ครบทุกเสียง" เป็นเงื่อนไขเดียวกันเป๊ะ
    # ถ้าพิมพ์สองแถวจะดูเหมือนวัดสองอย่างแล้วบังเอิญได้เท่ากัน ทั้งที่เป็นการวัดเดียว
    # ที่ 1 รอบ กติกาโหวตทุกตัวไม่มีความหมาย และ "อย่างน้อย 2 เสียงจาก 1 รอบ" เป็นเงื่อนไข
    # ที่เป็นไปไม่ได้ ⇒ ทุกเกณฑ์ออกมา 0 แล้วถูกพิมพ์ออกมาเหมือนเป็นผลวัดว่า "แย่มาก"
    # ทั้งที่ไม่ได้วัดอะไรเลย ตัวเลข 0 ที่ไม่ได้แปลว่าศูนย์คือสิ่งที่รีโปนี้ล่ามาทั้งวัน
    rules = ([] if a.runs < 2 else
             ['union', 'majority'] if a.runs == 2 else
             ['union', 'majority', 'unanimous'])
    if a.runs < 2:
        print('  (1 รอบ ⇒ ไม่มีเสียงให้โหวต ข้ามกติกา union/majority/unanimous)')
    for name in rules:
        s = v[name]
        label = name + (' (=unanimous)' if a.runs == 2 and name == 'majority' else '')
        print(hdr % (label, '%.4f' % s['recall'], '%.4f' % s['must_ask_hit'],
                     s['false_alarm_ids'], s['acceptable_ids'], s['ask_on_bug']))
    if a.runs >= 2:
        d_rec = (v['majority']['recall'] - v['single']['recall']) * 100
        d_fa = v['majority']['false_alarm_ids'] - v['single']['false_alarm_ids']
        d_ask = (v['majority']['must_ask_hit'] - v['single']['must_ask_hit']) * 100
        print('\nmajority เทียบ single: recall %+.1f จุด · must_ask %+.1f จุด · false alarm %+.1f ID/รอบ'
              % (d_rec, d_ask, d_fa))
        print('ต้นทุนของ majority คือ **ยิง %d เท่า** เทียบกำไรข้างบนกับตัวเลขนั้นเอง' % a.runs)
    print()

    if a.compare:
        timing_report(a.arm, a.tag, a.compare, a.compare_tag)
    pair_report(cases, keys, bank, a.runs)

    r1 = score_set(cases, keys, lambda c: bank[c['id']][0])
    per_case_recall = [j['recall'] for j in r1['per_case'].values() if j['recall'] is not None]
    per_case_ask = [float(j['ask_ok']) for j in r1['per_case'].values() if j['ask_ok'] is not None]
    lo, hi = boot_ci(per_case_recall)
    sd_case = statistics.stdev(per_case_recall) if len(per_case_recall) > 1 else 0.0
    se_case = sd_case / (len(per_case_recall) ** 0.5) if per_case_recall else 0.0
    sd_round = v['single_sd']['recall']
    print('## C15 - sd ที่ run.py รายงาน แปลว่าอะไร')
    print('  sd รอบต่อรอบ (ที่ run.py พิมพ์)      %.4f   <- "ยิงชุดเดิมซ้ำจะต่างกันแค่ไหน"'
          % sd_round)
    print('  se เคสต่อเคส (clustered, n=%2d)      %.4f   <- "ถ้าใช้เคสอีกชุดจะต่างกันแค่ไหน"'
          % (len(per_case_recall), se_case))
    if sd_round > 0:
        print('  อัตราส่วน                          %.1f เท่า' % (se_case / sd_round))
    print('  recall รอบ 1 = %.4f · ช่วงเชื่อมั่น 95%% bootstrap รายเคส = [%.4f, %.4f]'
          % (r1['recall'], lo, hi))
    print('  => ตัวเลขที่รายงานได้อย่างซื่อสัตย์คือ %.2f +- %.2f ไม่ใช่ %.4f'
          % (r1['recall'], (hi - lo) / 2, r1['recall']))
    if per_case_ask:
        alo, ahi = boot_ci(per_case_ask)
        print('  must_ask_hit = %.4f · ช่วงเชื่อมั่น 95%% = [%.4f, %.4f]  (n=%d เคส)'
              % (r1['must_ask_hit'], alo, ahi, len(per_case_ask)))
    print()

    print('## C11 - eval ต้องมีกี่เคส')
    print('  ฝ่าย ก #71 ~1,000 เคส · ฝ่าย ข #48 Anthropic 20-50 คือจุดเริ่มที่ดี')
    if sd_case:
        for eff in (0.05, 0.10, 0.15):
            need = (2.8 * sd_case / eff) ** 2
            print('  จะจับผลต่าง recall %2.0f จุดได้ (power 80%%, alpha=.05) ต้องมีราว %4.0f เคส'
                  % (eff * 100, need))
        print('  => ที่ %d เคสตอนนี้ ผลต่างที่เล็กที่สุดที่ชุดนี้จับได้คือราว **%.1f จุด**'
              % (len(per_case_recall), 2.8 * se_case * 100))
        print('     ผลต่างที่เล็กกว่านี้ ถึงวัดออกมาเป็นบวก ก็แยกจาก noise ไม่ได้')
    print()

    if a.compare:
        other = load_bank(a.compare, a.compare_tag)
        both = [c for c in cases if other.get(c['id'])]
        pa = score_set(both, keys, lambda c: bank[c['id']][0])['per_case']
        pb = score_set(both, keys, lambda c: other[c['id']][0])['per_case']
        diffs = [pa[c['id']]['recall'] - pb[c['id']]['recall'] for c in both
                 if pa[c['id']]['recall'] is not None]
        adiffs = [pa[c['id']]['ask_ok'] - pb[c['id']]['ask_ok'] for c in both
                  if pa[c['id']]['ask_ok'] is not None]
        print('## เทียบจับคู่รายเคส %s ลบ %s (รอบที่ 1 ของทั้งคู่)' % (a.arm, a.compare))
        for label, dd in (('recall', diffs), ('must_ask_hit', [float(x) for x in adiffs])):
            if len(dd) > 1:
                m, sd = statistics.mean(dd), statistics.stdev(dd)
                dlo, dhi = boot_ci(dd)
                verdict = ('ช่วงไม่คร่อมศูนย์ => ผลต่างนี้ไม่ใช่ noise' if dlo * dhi > 0
                           else 'ช่วงคร่อมศูนย์ => ข้อมูลเท่านี้ยังแยกจาก noise ไม่ได้')
                print('  %-13s n=%2d · ผลต่างเฉลี่ย %+.4f · se %.4f · 95%% [%+.4f, %+.4f]  %s'
                      % (label, len(dd), m, sd / (len(dd) ** 0.5), dlo, dhi, verdict))
                print('     %s' % sign_test(dd))
    return 0


def timing_report(arm_a, tag_a, arm_b, tag_b):
    """C3 - "จ่าย token เพื่อความแม่น" ฟรีไหม

    ฝ่าย ก (#56/#94) input ที่ cache แล้วเกือบฟรี
    ฝ่าย ข (#21 Anthropic) latency สเกลตาม token ทั้ง input และ output

    ที่นี่แยก cached/uncached ไม่ได้ (claude -p ไม่บอก และบังคับไม่ได้) จึงวัด **ผลรวม**
    สองแขนต่างกันแค่ปริมาณที่ต้องอ่าน full อ่านทั้งไฟล์ 198KB · routed อ่านเฉพาะช่วงบรรทัด
    เทียบแบบจับคู่รายเคส เพื่อไม่ให้ความยาว snippet ที่ต่างกันปนเข้ามา
    """
    import json as _json
    def load(arm, tag):
        p = timing_path(arm, tag)
        if not os.path.exists(p):
            return {}
        with open(p, encoding='utf-8') as fh:
            return _json.load(fh)
    ta, tb = load(arm_a, tag_a), load(arm_b, tag_b)
    both = sorted(set(ta) & set(tb))
    if len(both) < 3:
        sys.stderr.write('ข้อมูลเวลาที่จับคู่ได้มีแค่ %d เคส ข้ามหัวข้อ C3\n' % len(both))
        return
    pa = [statistics.mean(ta[c]) for c in both]
    pb = [statistics.mean(tb[c]) for c in both]
    ratios = [x / y for x, y in zip(pa, pb) if y > 0]
    print('## C3 - เวลาต่อเคส เทียบจับคู่ %s vs %s (n=%d เคส)' % (arm_a, arm_b, len(both)))
    print('  %-10s มัธยฐาน %6.1fs · เฉลี่ย %6.1fs · ต่ำสุด %5.1f · สูงสุด %6.1f'
          % (arm_a, statistics.median(pa), statistics.mean(pa), min(pa), max(pa)))
    print('  %-10s มัธยฐาน %6.1fs · เฉลี่ย %6.1fs · ต่ำสุด %5.1f · สูงสุด %6.1f'
          % (arm_b, statistics.median(pb), statistics.mean(pb), min(pb), max(pb)))
    print('  อัตราส่วน %s/%s: มัธยฐาน %.2f เท่า · เฉลี่ย %.2f เท่า · ช่วง %.2f-%.2f'
          % (arm_a, arm_b, statistics.median(ratios), statistics.mean(ratios),
             min(ratios), max(ratios)))
    slower = sum(1 for x, y in zip(pa, pb) if x > y)
    print('  %s ช้ากว่าใน %d/%d เคส · %s' % (arm_a, slower, len(both),
          sign_test([x - y for x, y in zip(pa, pb)], (arm_a + ' ช้ากว่า', arm_b + ' ช้ากว่า'))))
    print()


def pair_report(cases, keys, bank, runs):
    """เทียบเคสฝาแฝด: ใบที่มี `pair_of` กับใบต้นฉบับของมัน

    การทดลองของ item 1 — ตัวแปรที่ขยับมีตัวเดียวคือ snippet เป็นโค้ด vs เป็นคำบรรยาย
    `task` เหมือนกันทุกตัวอักษร ความกำกวมจึงถูกตรึงไว้เท่ากันโดยการก่อสร้าง

    สมมติฐานที่ทดสอบ (จาก c1-catalog-access-experiment.md ข้อเสนอที่ 3):
      "โค้ดในเคส must-ask ดึงความสนใจไปจากคำถามเชิงนโยบาย"
    ⇒ ถ้าจริง ฝาแฝดร้อยแก้วควรตอบ ASK ในใบที่ต้นฉบับเดา
    """
    pairs = [(c, c['pair_of']) for c in cases if c.get('pair_of')]
    by_id = {c['id']: c for c in cases}
    rows, both_have = [], 0
    for twin, orig_id in pairs:
        if orig_id not in bank or twin['id'] not in bank:
            continue
        both_have += 1
        # ใช้ทุกรอบที่มีของทั้งคู่ แล้วเฉลี่ย เพื่อไม่ให้รอบเดียวตัดสินทั้งคู่
        n = min(len(bank[twin['id']]), len(bank[orig_id]), runs)
        t = sum(judge(twin, bank[twin['id']][i], keys)['ask_ok'] for i in range(n)) / float(n)
        o_case = by_id.get(orig_id)
        o = sum(judge(o_case, bank[orig_id][i], keys)['ask_ok'] for i in range(n)) / float(n)
        rows.append((orig_id, o, twin['id'], t, n))
    if not rows:
        return
    print('## item 1 - ฝาแฝดร้อยแก้ว เทียบ ต้นฉบับที่เป็นโค้ด (ask_ok · 1 = ตอบ ASK และไม่มี ID เลย)')
    print('  %-34s %-6s %-32s %-6s %s' % ('ต้นฉบับ (โค้ด)', 'ask_ok', 'ฝาแฝด (ร้อยแก้ว)', 'ask_ok', 'รอบ'))
    for oid, o, tid, t, n in rows:
        mark = '' if abs(t - o) < 1e-9 else ('  <- ร้อยแก้วดีกว่า' if t > o else '  <- โค้ดดีกว่า')
        print('  %-34s %-6.2f %-32s %-6.2f %d%s' % (oid, o, tid, t, n, mark))
    diffs = [t - o for _, o, _, t, _ in rows]
    print('  ค่าเฉลี่ย ask_ok: โค้ด %.3f · ร้อยแก้ว %.3f · ผลต่าง %+.3f (n=%d คู่)'
          % (statistics.mean([o for _, o, _, _, _ in rows]),
             statistics.mean([t for _, _, _, t, _ in rows]), statistics.mean(diffs), len(rows)))
    print('  %s' % sign_test(diffs, ('ร้อยแก้ว', 'โค้ด')))
    print()


def sign_test(diffs, names=('แขนแรก', 'แขนที่สอง')):
    """การทดสอบที่ **ถูกกับรูปทรงของข้อมูลชุดนี้** มากกว่า bootstrap ของค่าเฉลี่ย

    วัดแล้วว่า recall รายเคสของสองแขนแทบไม่สัมพันธ์กัน (corr -0.04) และเคสส่วนใหญ่
    ให้ผลเท่ากันเป๊ะ ความต่างทั้งหมดกระจุกอยู่ในเคสไม่กี่ใบ
    ค่าเฉลี่ยกับ se จึงถูกเจือจางด้วยเคสที่ไม่ให้ข้อมูลอะไรเลย
    sign test มองเฉพาะ **เคสที่สองแขนไม่เท่ากัน** ซึ่งเป็นข้อมูลจริงทั้งหมดที่มี
    """
    pos = sum(1 for d in diffs if d > 1e-9)
    neg = sum(1 for d in diffs if d < -1e-9)
    n = pos + neg
    if n == 0:
        return 'sign test: ไม่มีเคสไหนที่สองแขนต่างกันเลย ไม่มีข้อมูลให้ทดสอบ'
    from math import comb
    k = min(pos, neg)
    p = min(1.0, 2.0 * sum(comb(n, i) for i in range(k + 1)) / (2.0 ** n))
    ok = 'p<0.05 => ผลต่างมีนัย' if p < 0.05 else 'p>=0.05 => **ยังสรุปไม่ได้** ต้องเพิ่มเคส'
    # ที่คู่ต่างกันน้อยมาก p ต่ำสุดที่เป็นไปได้ยังสูงกว่า 0.05 อยู่ดี ต้องบอกให้เห็น
    # ไม่งั้นคนอ่านจะคิดว่าผลไม่ดีพอ ทั้งที่การออกแบบไม่เปิดทางให้มีนัยสำคัญได้เลย
    floor = 2.0 / (2.0 ** n)
    cap = ('  ⚠️ ที่ %d คู่ p ต่ำสุดที่เป็นไปได้คือ %.3f **ต่อให้ผลสะอาด %d-0 ก็แตะ 0.05 ไม่ได้**'
           % (n, floor, n)) if floor > 0.05 else ''
    return ('sign test: เคสที่ต่างกันมี %d ใบ (%s ชนะ %d · %s ชนะ %d) · p=%.3f  %s%s'
            % (n, names[0], pos, names[1], neg, p, ok, cap))


if __name__ == '__main__':
    raise SystemExit(main())
