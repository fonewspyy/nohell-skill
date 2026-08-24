#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""nohell-check — ตัวรันกฎ `kind: regex` ใน hell-rules.yaml

โหมดหลักคือ **diff-only**: อ่านเฉพาะบรรทัดที่ "เพิ่ม" จาก git diff แล้วรันกฎกับบรรทัดนั้น
hit บนบรรทัดที่เพิ่มคือของใหม่โดยนิยาม ⇒ diff-only **คือ** ratchet ในตัวเอง
(`gate.mode: ratchet` = ห้ามเพิ่ม ไม่ใช่ห้ามมี) จึงไม่ต้องมี baseline ในโหมดนี้

    python scripts/nohell-check.py                    # diff-only เทียบ origin/main
    python scripts/nohell-check.py --base HEAD~1      # เทียบ ref อื่น
    python scripts/nohell-check.py --full             # สแกนทั้ง repo
    python scripts/nohell-check.py --full --baseline  # เขียน .nohell-baseline.json

exit code เป็นสัญญา
    0  ผ่าน
    1  เจอกฎระดับที่ gate.block_on บนบรรทัดที่เพิ่ม
    2  **รันไม่ได้** — ไม่มี rg / ไม่มี PCRE2 / pattern compile ไม่ผ่าน / git ใช้ไม่ได้
       ห้ามกลืนเป็น 0 เด็ดขาด เพราะ gate ที่เงียบแล้วผ่านทุกอย่างแย่กว่าไม่มี gate

กฎที่ตัวนี้ **ไม่** รัน และจะขึ้นในรายงานทุกครั้ง (ไม่หายเงียบ)
    kind: cmd                เรียกเครื่องมือนอก (eslint / gitleaks / pnpm audit / nohell CLI)
                             การรันคำสั่งจากคอนฟิกเป็นทางเปิดให้ arbitrary execution
    kind: sql                ต้องต่อฐานข้อมูล — ใช้ detect-sqlserver.sql เอง
    kind: manual-checklist   ต้องคนอ่าน
"""
import argparse, json, os, re, subprocess, sys

RULES = os.path.join('skills', 'nohell', 'hell-rules.yaml')
BASELINE = '.nohell-baseline.json'
IGNORE = '.nohellignore'


def die(msg):
    sys.stderr.write('nohell-check: %s\n' % msg)
    raise SystemExit(2)


def load_rules():
    try:
        import yaml
    except ImportError:
        die('ต้องมี pyyaml — ติดตั้งด้วย `pip install pyyaml`\n'
            '  (เขียน YAML parser เองคือ reinvent library และ parser ที่ผิดเงียบ '
            'คือบั๊กที่ตัวนี้ตั้งใจกัน)')
    if not os.path.exists(RULES):
        die('ไม่พบ %s — ต้องรันจากรากของ repo' % RULES)
    with open(RULES, encoding='utf-8') as fh:
        return yaml.safe_load(fh)


def check_engine():
    try:
        out = subprocess.run(['rg', '--version'], capture_output=True, text=True)
    except FileNotFoundError:
        die('ไม่พบ ripgrep (rg) — ตัวนี้ต้องใช้ rg ไม่มีทางเลี่ยง')
    if out.returncode != 0:
        die('rg --version ล้ม: %s' % out.stderr.strip())
    if '+pcre2' not in out.stdout:
        die('ripgrep ตัวนี้ build มาโดยไม่มี PCRE2 (%s)\n'
            '  กฎที่ประกาศ engine: pcre2 จะ parse error แล้วถ้ากลืนไว้ gate จะเงียบ '
            'ผ่านทุกอย่าง จึงหยุดที่นี่' % out.stdout.splitlines()[0])


def git(*args):
    out = subprocess.run(('git',) + args, capture_output=True, text=True)
    if out.returncode != 0:
        die('git %s ล้ม: %s' % (' '.join(args), out.stderr.strip()))
    return out.stdout


def added_lines(base):
    """{path: set(เลขบรรทัดที่เพิ่ม)} จาก git diff -U0"""
    diff = git('diff', '-U0', '--no-color', '--diff-filter=d', base)
    out, path, ln = {}, None, 0
    for line in diff.split('\n'):
        if line.startswith('+++ b/'):
            path = line[6:]
        elif line.startswith('@@'):
            m = re.search(r'\+(\d+)', line)
            ln = int(m.group(1)) if m else 0
        elif line.startswith('+') and not line.startswith('+++') and path:
            out.setdefault(path, set()).add(ln)
            ln += 1
    return out


def glob_re(glob):
    """glob แบบ ripgrep -> regex

    ทำเองเพราะ fnmatch ทำ `{a,b}` และแยก `**` กับ `*` ไม่ได้ และกฎในไฟล์นี้ใช้ทั้งสองอย่าง
    (`**/*.{test,spec}.{ts,tsx,js}` · `**/routes/**/*.ts` · `migrations/**/*.sql`)
    """
    out, i, n = [], 0, len(glob)
    while i < n:
        if glob.startswith('**/', i):
            out.append('(?:[^/]+/)*'); i += 3
        elif glob.startswith('**', i):
            out.append('.*'); i += 2
        elif glob[i] == '*':
            out.append('[^/]*'); i += 1
        elif glob[i] == '?':
            out.append('[^/]'); i += 1
        elif glob[i] == '{':
            j = glob.index('}', i)
            out.append('(?:%s)' % '|'.join(re.escape(x) for x in glob[i + 1:j].split(',')))
            i = j + 1
        else:
            out.append(re.escape(glob[i])); i += 1
    return re.compile('^' + ''.join(out) + '$')


def load_ignores():
    """glob ระดับ repo จาก .nohellignore

    จำเป็นเพราะไฟล์ที่ *นิยาม* กฎย่อมตรงกับกฎของตัวเอง (`hell-rules.yaml` มี pattern
    เป็นข้อความ · แคตตาล็อกบรรยายสิ่งที่ห้ามทำ) ถ้าไม่มีทางยกเว้น การกินยาตัวเองจะบล็อก
    ทุก PR ที่แก้แคตตาล็อก — เก็บไว้ในไฟล์ไม่ฝังใน runner เพราะ runner ห้ามมีกฎของตัวเอง
    """
    if not os.path.exists(IGNORE):
        return []
    pats = []
    with open(IGNORE, encoding='utf-8') as fh:
        for line in fh:
            line = line.split('#')[0].strip()
            if line:
                pats.append(glob_re(line))
    return pats


def files_for(rule, candidates, ignores=()):
    """กรองไฟล์ตาม glob ของกฎเอง

    ห้ามส่งงานนี้ให้ `rg -g` — วัดแล้วว่า rg **ไม่ใช้ glob กับ path ที่ระบุใน command line**
    (`rg -g '**/*.sql' -- a.md` ยัง match a.md) ⇒ กฎจะรั่วไปจับไฟล์ผิดชนิดแบบเงียบ
    """
    det = rule['detect']
    inc = glob_re(det['glob']) if det.get('glob') else None
    exc = [glob_re(g) for g in (rule.get('exclude') or [])] + list(ignores)
    keep = []
    for p in candidates:
        q = p.replace('\\', '/')
        if inc and not inc.match(q):
            continue
        if any(e.match(q) for e in exc):
            continue
        keep.append(p)
    return keep


def rg_flags(rule):
    flags = []
    if rule.get('engine') == 'pcre2':
        flags.append('-P')
    if rule.get('multiline') is True:
        flags += ['-U'] + ([] if '-P' in flags else ['-P'])
    return flags


def scan(rule, paths):
    """คืน [(path, line, text)] — exit 2 ทันทีถ้า pattern compile ไม่ผ่าน"""
    hits, flags = [], rg_flags(rule)
    # แบ่งเป็นก้อน — command line ของ Windows จำกัด 32k ไฟล์เยอะ ๆ จะยิงไม่ออก
    for k in range(0, len(paths), 200):
        cmd = (['rg', '--json', '--no-messages'] + flags
               + ['-e', rule['detect']['pattern'], '--'] + paths[k:k + 200])
        out = subprocess.run(cmd, capture_output=True, text=True,
                             encoding='utf-8', errors='replace')
        if out.returncode == 2:
            die('กฎ %s รันไม่ผ่าน (flag ที่ประกาศ: %s)\n  %s'
                % (rule['id'], ' '.join(flags) or 'ไม่มี',
                   (out.stderr.strip().split('\n') or [''])[0]))
        for row in out.stdout.split('\n'):
            if not row.strip():
                continue
            try:
                ev = json.loads(row)
            except ValueError:
                continue
            if ev.get('type') != 'match':
                continue
            d = ev['data']
            hits.append((d['path'].get('text', ''), d['line_number'],
                         d['lines'].get('text', '').rstrip('\n')))
    return hits


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--base', default='origin/main', help='ref ที่ใช้เทียบ (ค่าเริ่มต้น origin/main)')
    ap.add_argument('--full', action='store_true', help='สแกนทั้ง repo ไม่ใช่แค่ diff')
    ap.add_argument('--baseline', action='store_true', help='เขียน %s (ใช้กับ --full)' % BASELINE)
    args = ap.parse_args()

    cfg = load_rules()
    check_engine()
    gate = cfg.get('gate') or {}
    block_on = set(gate.get('block_on') or [])
    warn_on = set(gate.get('warn_on') or [])

    rules = cfg['rules']
    runnable = [r for r in rules if (r.get('detect') or {}).get('kind') == 'regex']
    skipped = {}
    for r in rules:
        k = (r.get('detect') or {}).get('kind')
        if k != 'regex':
            skipped[k] = skipped.get(k, 0) + 1

    if args.full:
        # ไฟล์ที่ git ติดตาม — ได้ผลของ .gitignore ฟรี และเป็นชุดเดียวกันทุกเครื่อง
        added = None
        candidates = [p for p in git('ls-files').split('\n') if p and os.path.exists(p)]
    else:
        added = added_lines(args.base)
        candidates = sorted(p for p in added if os.path.exists(p))
        if not candidates:
            print('ไม่มีไฟล์ที่เปลี่ยนเทียบกับ %s — ไม่มีอะไรต้องตรวจ' % args.base)
            print(report_skipped(skipped, len(runnable)))
            return 0

    ignores = load_ignores()
    findings, counts = [], {}
    for rule in runnable:
        paths = files_for(rule, candidates, ignores)
        counts[rule['id']] = 0
        if not paths:
            continue
        keep = []
        for path, line, text in scan(rule, paths):
            allow = rule.get('allow_comment')
            if allow and allow in text:
                continue
            if added is not None and not rule.get('multiline'):
                if line not in added.get(path.replace('\\', '/'), ()):
                    continue
            keep.append((path, line, text))
        counts[rule['id']] = len(keep)
        if keep:
            findings.append((rule, keep))

    if args.baseline:
        with open(BASELINE, 'w', encoding='utf-8') as fh:
            json.dump({'mode': 'full', 'counts': counts}, fh, ensure_ascii=False, indent=2)
        print('เขียน %s แล้ว (%d กฎ)' % (BASELINE, len(counts)))

    blocked = warned = 0
    for rule, keep in sorted(findings, key=lambda f: f[0].get('severity', 'P9')):
        sev = rule.get('severity')
        mark = 'BLOCK' if sev in block_on else ('WARN' if sev in warn_on else 'REPORT')
        if sev in block_on:
            blocked += len(keep)
        elif sev in warn_on:
            warned += len(keep)
        print('%-6s %-9s %s  (%d จุด)' % (mark, rule['id'], rule.get('title', ''), len(keep)))
        for path, line, text in keep[:5]:
            print('       %s:%s  %s' % (path, line, text.strip()[:90]))
        if len(keep) > 5:
            print('       ... อีก %d จุด' % (len(keep) - 5))

    scope = 'ทั้ง repo' if args.full else 'บรรทัดที่เพิ่มเทียบ %s' % args.base
    print()
    print('ขอบเขต: %s · กฎที่รัน %d ข้อ · block %d · warn %d'
          % (scope, len(runnable), blocked, warned))
    print(report_skipped(skipped, len(runnable)))
    return 1 if blocked else 0


def report_skipped(skipped, n_run):
    if not skipped:
        return ''
    parts = ' · '.join('%s %d' % (k, v) for k, v in sorted(skipped.items()))
    return ('⚠️ ไม่ได้ตรวจ %d ข้อ (%s) — ต้องต่อเครื่องมือ/ฐานข้อมูล/คนอ่านเอง'
            % (sum(skipped.values()), parts))


if __name__ == '__main__':
    raise SystemExit(main())
