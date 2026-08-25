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
ROUNDS = os.path.join(HERE, '.rounds.json')     # รอบที่สำเร็จแล้ว สะสมข้ามการรันหลายครั้ง


def load_bank():
    """คำตอบที่ยิงสำเร็จแล้ว เก็บ **รายเคส** ไม่ใช่รายรอบ — {case_id: [reply, ...]}

    หน่วยต้องเป็นเคส เพราะโควตาปล่อยมาทีละส่วน วัดมาแล้วสองครั้ง
      25/08 00:39  รอบ 1-2 สำเร็จ รอบ 3 ชน limit -> ทิ้งทั้งหมด เสีย 48 session
      25/08 01:00  ยิงได้ 16/24 เคส แล้วโควตาหมด -> ทิ้งทั้งรอบ เสีย 16 เคสที่ตอบแล้ว
    เก็บรายเคสทำให้ทุกครั้งที่รันมีความคืบหน้า และยังได้ 3 คำตอบอิสระต่อเคส
    ซึ่งเป็นสิ่งที่ variance ของ D4 ต้องการจริง ๆ
    """
    if not os.path.exists(ROUNDS):
        return {}
    with io.open(ROUNDS, encoding='utf-8') as fh:
        return json.load(fh)


def save_bank(bank):
    with io.open(ROUNDS, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(json.dumps(bank, ensure_ascii=False, indent=2) + '\n')


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

    from concurrent.futures import ThreadPoolExecutor
    bank = load_bank()
    have = min([len(bank.get(c['id'], [])) for c in cases] or [0])
    print('คำตอบที่สะสมไว้แล้ว: อย่างน้อย %d ต่อเคส (ต้องการ %d)' % (have, a.runs))

    while True:
        need = [c for c in cases if len(bank.get(c['id'], [])) < a.runs]
        if not need:
            break
        print('\nยิง %d เคสที่ยังไม่ครบ' % len(need))
        with ThreadPoolExecutor(max_workers=a.jobs) as ex:
            replies = list(ex.map(ask, need))
        got, why = 0, []
        for c, (reply, err) in zip(need, replies):
            if err:
                if err not in why:
                    why.append(err)
                continue
            bank.setdefault(c['id'], []).append(reply)
            got += 1
            if not a.quiet:
                print('  ok  %-28s %s' % (c['id'], reply[:60].replace('\n', ' ')))
        save_bank(bank)
        print('  ยิงสำเร็จ %d/%d — เก็บลง %s แล้ว' % (got, len(need), os.path.basename(ROUNDS)))
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
        rec, fa, ask_hit, detail = [], 0, [], {}
        for c in cases:
            reply = bank[c['id']][i]
            r, f, ak = judge(c, reply)
            if r is not None:
                rec.append(r)
            if ak is not None:
                ask_hit.append(ak)
            fa += f
            detail[c['id']] = {'reply': reply[:200], 'recall': r,
                               'false_alarm': f, 'ask_ok': ak}
        rounds.append({
            'recall': round(sum(rec) / len(rec), 4) if rec else 0.0,
            'false_alarm_ids': fa,
            'must_ask_hit': round(sum(ask_hit) / len(ask_hit), 4) if ask_hit else 0.0,
            'detail': detail,
        })
        print('  รอบ %d: recall %.1f%% · false alarm %d ID · must-ask %.0f%%'
              % (i + 1, rounds[-1]['recall'] * 100, rounds[-1]['false_alarm_ids'],
                 rounds[-1]['must_ask_hit'] * 100))

    summary = {}
    for k in ('recall', 'false_alarm_ids', 'must_ask_hit'):
        vals = [r[k] for r in rounds]
        summary[k] = {'mean': round(statistics.mean(vals), 4),
                      'min': min(vals), 'max': max(vals),
                      'stdev': round(statistics.stdev(vals), 4) if len(vals) > 1 else 0.0}
    print('\nสรุปจาก %d รอบ' % a.runs)
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
