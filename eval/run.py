# -*- coding: utf-8 -*-
"""eval ของตัว skill — ยิงเคสใน eval/cases/ แล้ววัดว่าแคตตาล็อกถูกใช้ได้จริงแค่ไหน

ตัดสินด้วย **exact match ของ ID** ไม่ใช้ LLM judge (D4) เพราะ judge ที่เป็นโมเดล
จะกลายเป็นตัวแปรอีกตัวที่เราคุมไม่ได้ และทำให้ตัวเลข regression เชื่อไม่ได้

provider คือ `claude -p` (headless) ที่ล็อกอินอยู่แล้ว — **ไม่ต้องใช้ API key**
และไม่มีการอ่านหรือเก็บ credential ใด ๆ ในไฟล์นี้

    python eval/run.py                    # 3 รอบ แล้วรายงาน variance
    python eval/run.py --runs 1           # รอบเดียว ตอนแก้เคส
    python eval/run.py --baseline         # เขียน eval/baseline.json

เกณฑ์ที่วัด
    recall        เคสบั๊ก: เจอ ID ที่ควรเจอกี่ % (ตัวเลขหลักที่ห้ามตกหลังแก้ skill)
    false_alarm_ids  จำนวน ID ที่รายงานเกินมาทั้งชุด (นับ ID ไม่ใช่นับเคส)
    must_ask_hit  เคสที่คำตอบถูกคือ "หยุดถาม": ตอบ ASK กี่ %
"""
import argparse, glob, io, json, os, re, shutil, statistics, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CASES = os.path.join(HERE, 'cases')
BASELINE = os.path.join(HERE, 'baseline.json')
ID_RE = re.compile(r'\b([A-Z]{2,6}-\d{2})\b')

PROMPT = '''อ่าน skills/nohell/HELL-CATALOG.md ในโฟลเดอร์นี้ก่อน แล้วตอบโจทย์ข้างล่าง

โจทย์: {task}

```{lang}
{snippet}
```

กติกาการตอบ ตอบบรรทัดเดียว ห้ามอธิบาย
- ถ้าละเมิดข้อในแคตตาล็อก ตอบเป็น ID คั่นด้วยช่องว่าง เช่น: SQL-15 ERR-02
- ถ้าไม่ละเมิดข้อใดเลย ตอบ: NONE
- ถ้ายังตัดสินไม่ได้เพราะขาดกฎธุรกิจที่เดาแทนไม่ได้ ตอบ: ASK'''


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


def ask(case):
    prompt = PROMPT.format(task=case['task'], lang=case['lang'], snippet=case['snippet'])
    try:
        r = subprocess.run(['claude', '-p', prompt], cwd=sandbox(), capture_output=True,
                           text=True, encoding='utf-8', errors='replace', timeout=300)
    except FileNotFoundError:
        sys.stderr.write('ไม่พบคำสั่ง claude — eval ตัวนี้ใช้ Claude Code headless เป็น provider\n')
        raise SystemExit(2)
    except subprocess.TimeoutExpired:
        return '', 'timeout หลัง 300 วินาที'
    if r.returncode != 0:
        # ห้ามกลืน — คำตอบว่างจะถูกนับเป็น recall 0 แล้วสรุปออกมาเป็นตัวเลขที่ดูเหมือนผลวัด
        # วัดจริงมาแล้ว: session limit หมด 21/24 เคสล้ม แต่รายงานยังพิมพ์ "recall 8.3%" ออกมา
        # เอา stdout ก่อน — claude -p พิมพ์ error ที่คนอ่านรู้เรื่องลงที่นั่น
        # ("You've hit your session limit") ส่วน stderr มักเป็น noise ของ hook/ปลั๊กอินอื่น
        why = (r.stdout or '').strip().split('\n')[0][:120]
        if not why:
            why = (r.stderr or '').strip().split('\n')[0][:120]
        return '', why or ('exit %d' % r.returncode)
    return r.stdout.strip(), None


def judge(case, reply):
    """คืน (recall, false_alarm, ask_ok) — ตัดสินจาก ID ที่เจอในคำตอบเท่านั้น"""
    said_ask = bool(re.search(r'\bASK\b', reply))
    found = set(ID_RE.findall(reply))
    want = set(case['expected_ids'])
    if case['must_ask']:
        return None, 0, 1 if said_ask else 0
    if want:
        return len(found & want) / float(len(want)), len(found - want), None
    return None, len(found), None


def one_run(cases, verbose, jobs):
    # เคสเป็นอิสระต่อกัน ยิงขนานได้ — วัดจริง 101 วินาทีต่อเคส ถ้าเรียงทีละตัว
    # 24 เคส 3 รอบ = 2 ชั่วโมง ซึ่งช้าจนไม่มีใครรัน แล้ว eval ที่ไม่มีใครรันก็ไม่มีค่า
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        replies = list(ex.map(ask, cases))

    rec, fa, ask_hit, errs = [], 0, [], 0
    detail, why = {}, []
    for c, (reply, err) in zip(cases, replies):
        if err:
            errs += 1
            if err not in why:
                why.append(err)
        r, f, a = judge(c, reply)
        if r is not None:
            rec.append(r)
        if a is not None:
            ask_hit.append(a)
        fa += f
        detail[c['id']] = {'reply': reply[:200], 'recall': r, 'false_alarm': f, 'ask_ok': a}
        if verbose:
            tag = 'ok ' if (r == 1 or a == 1 or (r is None and a is None and f == 0)) else '   '
            print('  %s %-28s %s' % (tag, c['id'], reply[:60].replace('\n', ' ')))
    return {
        'recall': round(sum(rec) / len(rec), 4) if rec else 0.0,
        'false_alarm_ids': fa,
        'must_ask_hit': round(sum(ask_hit) / len(ask_hit), 4) if ask_hit else 0.0,
        'errors': errs,
        'error_reasons': why,
        'detail': detail,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runs', type=int, default=3)
    ap.add_argument('--baseline', action='store_true')
    ap.add_argument('-q', '--quiet', action='store_true')
    ap.add_argument('--jobs', type=int, default=4, help='ยิงกี่เคสพร้อมกัน (ค่าเริ่มต้น 4)')
    a = ap.parse_args()

    cases = load_cases()
    n_bug = sum(1 for c in cases if c['expected_ids'])
    n_clean = sum(1 for c in cases if not c['expected_ids'] and not c['must_ask'])
    n_ask = sum(1 for c in cases if c['must_ask'])
    print('เคส %d (บั๊ก %d · สะอาด %d · ต้องหยุดถาม %d) · %d รอบ · ขนาน %d'
          % (len(cases), n_bug, n_clean, n_ask, a.runs, a.jobs))

    runs = []
    for i in range(a.runs):
        print('\nรอบ %d/%d' % (i + 1, a.runs))
        runs.append(one_run(cases, not a.quiet, a.jobs))
        r = runs[-1]
        print('  recall %.1f%% · false alarm %d ID · must-ask %.0f%% · error %d'
              % (r['recall'] * 100, r['false_alarm_ids'], r['must_ask_hit'] * 100, r['errors']))
        if r['errors']:
            # หยุดทันที ไม่รันรอบต่อไป และไม่เอาเลขนี้ไปเฉลี่ย
            sys.stderr.write('\nFAIL  รอบนี้มี %d เคสที่ยิงไม่สำเร็จ — ตัวเลขข้างบนไม่ใช่ผลวัด\n'
                             % r['errors'])
            for w in r['error_reasons']:
                sys.stderr.write('      %s\n' % w)
            sys.stderr.write('      ไม่เขียน baseline เพราะ baseline ที่มาจากรอบที่ยิงไม่ออก\n'
                             '      คือตัวเลขที่หน้าตาเหมือนผลวัดแต่ไม่ได้วัดอะไรเลย\n')
            if _SANDBOX:
                shutil.rmtree(_SANDBOX[0], ignore_errors=True)
            return 2

    summary = {}
    for k in ('recall', 'false_alarm_ids', 'must_ask_hit'):
        vals = [r[k] for r in runs]
        summary[k] = {'mean': round(statistics.mean(vals), 4),
                      'min': min(vals), 'max': max(vals),
                      'stdev': round(statistics.stdev(vals), 4) if len(vals) > 1 else 0.0}
    print('\nสรุป %d รอบ' % a.runs)
    for k, v in summary.items():
        print('  %-18s mean %-8s min %-6s max %-6s sd %s'
              % (k, v['mean'], v['min'], v['max'], v['stdev']))

    if a.baseline:
        out = {'cases': len(cases), 'runs': a.runs, 'summary': summary,
               'per_case': runs[-1]['detail']}
        with io.open(BASELINE, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
        print('\nเขียน %s แล้ว — นี่คือเลขที่การแก้ skill หลังจากนี้ต้องไม่ทำให้แย่ลง' % BASELINE)
    if _SANDBOX:
        shutil.rmtree(_SANDBOX[0], ignore_errors=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
