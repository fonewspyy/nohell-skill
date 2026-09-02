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
KEYS = os.path.join(HERE, 'keys', 'merged.json')  # เฉลยสามชั้น — ดู load_keys()


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


def ask(case):
    """ยิงหนึ่งเคส — prompt ไปทาง **stdin** ไม่ใช่ argv

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
    prompt = PROMPT.format(task=case['task'], lang=case['lang'], snippet=case['snippet'])
    try:
        r = subprocess.run([claude_bin(), '-p'], input=prompt, cwd=sandbox(),
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=300)
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
    said_ask = bool(re.search(r'\bASK\b', reply))
    found = set(ID_RE.findall(reply))
    must = {x['id'] for x in k.get('must_find') or []}
    okay = {x['id'] for x in k.get('acceptable') or []}
    bad = {x['id'] for x in k.get('wrong') or []}

    out = {'recall': None, 'false_alarm': len(found & bad),
           'acceptable': len(found & okay), 'ask_ok': None, 'ask_on_bug': 0,
           'excluded': False, 'unlisted': sorted(found - must - okay - bad)}

    if k.get('excluded'):
        # เคสที่ไม่มี ground truth ให้เทียบ — ต้องไม่นับเป็น "สะอาด" โดยปริยาย
        # b02: เฉลยเดิมผิดกลไก และแคตตาล็อกยังไม่มีข้อที่ครอบอาการจริง
        # ถ้าปล่อยให้ตกลงกลุ่มสะอาด การรายงานสิ่งที่ *ถูก* จะถูกนับเป็น false alarm
        return {'recall': None, 'false_alarm': 0, 'acceptable': 0,
                'ask_ok': None, 'ask_on_bug': 0, 'excluded': True, 'unlisted': []}

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
    a = ap.parse_args()

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
        rec, fa, okay, ask_hit, on_bug, unlisted, detail = [], 0, 0, [], 0, 0, {}
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
            detail[c['id']] = dict(j, reply=reply[:200])
        rounds.append({
            'recall': round(sum(rec) / len(rec), 4) if rec else 0.0,
            'false_alarm_ids': fa,
            'acceptable_ids': okay,
            'must_ask_hit': round(sum(ask_hit) / len(ask_hit), 4) if ask_hit else 0.0,
            'ask_on_bug': on_bug,
            'unlisted_ids': unlisted,
            'detail': detail,
        })
        print('  รอบ %d: recall %.1f%% · false alarm %d · acceptable %d · '
              'must-ask %.0f%% · ask-on-bug %d · ไม่อยู่ในเฉลย %d'
              % (i + 1, rounds[-1]['recall'] * 100, fa, okay,
                 rounds[-1]['must_ask_hit'] * 100, on_bug, unlisted))

    summary = {}
    for k in ('recall', 'false_alarm_ids', 'acceptable_ids', 'must_ask_hit',
              'ask_on_bug', 'unlisted_ids'):
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
