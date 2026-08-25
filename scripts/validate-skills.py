# -*- coding: utf-8 -*-
"""ตรวจว่า SKILL.md ทุกไฟล์ยังติดตั้งได้ทุกช่องทางที่รีโปนี้บอกว่าติดตั้งได้

คนละหน้าที่กับอีกสองตัว — `validate-catalog.sh` คุมรูปร่างของแคตตาล็อก
`build-summary.py` คุมตัวเลขที่ประกาศ ส่วนตัวนี้คุม *การแพ็กเกจ*

ทำไมต้องมี: มาตรฐาน Agent Skills รับ frontmatter แค่หกฟิลด์ ฟิลด์เสริมของ Claude Code
(เช่น `disable-model-invocation` `argument-hint` `paths`) ทำให้ claude.ai upload,
Skills API และ package_skill.py ปฏิเสธ *ทั้งไฟล์* ด้วยข้อความ
"Unexpected key(s) in SKILL.md frontmatter" — พังตอนคนอื่นติดตั้ง ไม่ใช่ตอนเราแก้
จึงไม่มีทางรู้เองถ้าไม่มีด่าน

    python scripts/validate-skills.py
"""
import glob
import io
import os
import re
import sys

try:
    import yaml
except ImportError:                                    # ดังกว่าเงียบ
    sys.stderr.write('ต้องมี pyyaml — python -m pip install pyyaml\n')
    raise SystemExit(2)

# หกฟิลด์ที่มาตรฐาน Agent Skills รับ (agentskills.io) — Claude Code รับทั้งหกและมีของตัวเองเพิ่ม
# แต่ช่องทางอื่นไม่รับของเพิ่ม จึงยึดชุดที่แคบที่สุดเพื่อให้ติดตั้งได้ทุกที่
SPEC_FIELDS = {'name', 'description', 'license', 'compatibility', 'metadata', 'allowed-tools'}
NAME_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')


def check(path):
    """คืนรายการปัญหาของไฟล์เดียว ว่างแปลว่าผ่าน"""
    out = []
    text = io.open(path, encoding='utf-8').read()
    if not text.startswith('---\n'):
        return ['ไม่มี YAML frontmatter คั่นด้วย --- ที่บรรทัดแรก']
    try:
        end = text.index('\n---\n', 4)
    except ValueError:
        return ['frontmatter ไม่ถูกปิดด้วย ---']
    try:
        fm = yaml.safe_load(text[4:end])
    except yaml.YAMLError as e:
        return ['frontmatter ไม่ใช่ YAML ที่อ่านได้: %s' % e]
    if not isinstance(fm, dict):
        return ['frontmatter ต้องเป็น mapping']

    extra = sorted(set(fm) - SPEC_FIELDS)
    if extra:
        out.append('มีฟิลด์นอกมาตรฐาน %s — ช่องทางติดตั้งอื่นจะปฏิเสธทั้งไฟล์ '
                   'ฟิลด์ที่รับคือ %s' % (extra, sorted(SPEC_FIELDS)))

    name = fm.get('name') or ''
    folder = os.path.basename(os.path.dirname(path))
    if not NAME_RE.match(name):
        out.append('name %r ผิดรูป ต้องเป็น a-z 0-9 คั่นด้วยขีดเดียว ห้ามขึ้นหรือลงท้ายด้วยขีด' % name)
    if len(name) > 64:
        out.append('name ยาว %d เกิน 64' % len(name))
    if name != folder:
        # ชื่อคำสั่งของ personal/project skill มาจากชื่อโฟลเดอร์ ไม่ใช่จาก name
        # ต่างกันเมื่อไหร่ คนพิมพ์คำสั่งตามที่เอกสารบอกแล้วไม่เจอ
        out.append('name %r ไม่ตรงกับชื่อโฟลเดอร์ %r' % (name, folder))

    desc = fm.get('description') or ''
    if not desc.strip():
        out.append('description ว่าง — ตัวเลือก skill ตัดสินจากฟิลด์นี้')
    elif len(desc) > 1024:
        out.append('description ยาว %d เกิน 1024' % len(desc))

    compat = fm.get('compatibility') or ''
    if len(compat) > 500:
        out.append('compatibility ยาว %d เกิน 500' % len(compat))

    meta = fm.get('metadata')
    if meta is not None and not isinstance(meta, dict):
        out.append('metadata ต้องเป็น mapping ไม่งั้นจะถูกทิ้งเงียบ')
    return out


def main():
    paths = sorted(glob.glob('skills/*/SKILL.md'))
    if not paths:
        sys.stderr.write('FAIL  ไม่พบ skills/*/SKILL.md เลย — `npx skills` สแกนโครงนี้\n')
        return 1
    fail = 0
    for p in paths:
        problems = check(p)
        for msg in problems:
            sys.stderr.write('FAIL  %s — %s\n' % (p, msg))
        fail += bool(problems)
    if fail:
        return 1
    print('OK    %d skills · frontmatter อยู่ในหกฟิลด์ของมาตรฐาน ติดตั้งได้ทุกช่องทาง' % len(paths))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
