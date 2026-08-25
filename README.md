# engineering-skills — ชุด skill ที่บังคับให้ agent คิดแบบ senior ก่อนลงมือ

[![validate](https://github.com/fonewspyy/nohell-skill/actions/workflows/validate.yml/badge.svg)](https://github.com/fonewspyy/nohell-skill/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

> *[English README](README.en.md) — เนื้อหา skill เป็นภาษาไทย หน้านั้นอธิบายว่า repo นี้คืออะไรและใช้ยังไง*

ปัญหาไม่ใช่ agent เขียนโค้ดไม่เป็น ปัญหาคือ **agent ลงมือเร็วเกินไป** แล้วสร้างหนี้เร็วกว่าคนทั่วไปหลายเท่า
repo นี้จึงไม่ใช่คลังกฎเพิ่มเติม แต่เป็นลำดับการคิดที่บังคับใช้ได้

```
skills/
├── principal-engineer/   ← เข้าที่นี่ก่อนเสมอ: Impact Map, Ask Gate, router
├── kickoff/              ← เริ่มโปรเจกต์ใหม่: agent เป็นฝ่ายพาเดินทีละเฟส
├── nohell/               ← แคตตาล็อก anti-pattern 483 ข้อ + กฎที่ตรวจอัตโนมัติได้ + สคริปต์สแกน DB
├── nohell-dig/           ← `/nohell-dig` ขุดประวัติ repo หา "นรกซ้ำซาก" ที่เจ็บจริง
├── business-rules/       ← SSOT ของกฎ, effective date, read/write symmetry, workflow, เงิน
├── archaeology/          ← ระดับหลักฐาน, บัญชีผู้เรียก, ค้นสำเนากฎด้วยรูปร่าง
├── data-migration/       ← ย้ายข้อมูลหกขั้นที่หยุดได้ทุกขั้น: expand-contract, dual-write,
│                            backfill ที่ resume ได้, shadow-read, cutover, ปิดทางเขียนเก่า
└── conventions/          ← ชื่อ, คำศัพท์ธุรกิจ, โครง SP มาตรฐาน, การตั้งชื่อตัวแปร
    └── templates/        ← เทมเพลต SP ที่คัดลอกไปใช้ได้เลย (แบบพารามิเตอร์แยก และแบบรับ JSON)

docs/
├── llm-reality.md        ← 60 คู่ ความเชื่อ vs ของจริง เรื่อง LLM/agent
└── tooling-2026.md       ← เครื่องมือที่คุ้มจริงสำหรับคนทำคนเดียว + เกณฑ์เปลี่ยนแผน
```

## ลำดับการทำงาน

```
งานเข้ามา
   ↓
principal-engineer  → Impact Map 13 ช่อง + Ask Gate     ← ตอบไม่ครบ ห้ามเขียนโค้ด
   ↓
router เลือกเลนส์ตามชนิดงาน
   ↓
ponytail (ภายนอก)   → ต้องเขียนไหม อย่า over-engineer
   ↓
nohell กฎแกน 12 ข้อ → เขียนแล้วจะกลายเป็นนรกไหม
   ↓
เลนส์เฉพาะทาง       → business-rules / archaeology / หมวดใน HELL-CATALOG
   ↓
ปิดงานด้วย Impact Map ตัวเดิม เป็น checklist
```

## แต่ละตัวรับผิดชอบอะไร

| skill | คำถามที่ตอบ | โหลดเมื่อไหร่ |
|---|---|---|
| principal-engineer | จะกระทบอะไรบ้าง และยังไม่รู้อะไร | ทุกงาน โหลดตลอด |
| nohell (SKILL.md) | เขียนแบบนี้แล้วจะเป็นนรกไหม | ทุกงาน โหลดตลอด (~3–4k token) |
| nohell (HELL-CATALOG) | นรกข้อไหนบ้างในหมวดนี้ | เฉพาะหมวดที่งานแตะ ตอนรีวิว/audit |
| business-rules | กฎนี้ใครเป็นเจ้าของ ใช้ ณ วันไหน | งานที่แตะเงิน สต็อก สิทธิ์ สถานะ ย้อนหลัง |
| archaeology | ตอนนี้ระบบทำงานยังไงจริง | ก่อนแตะโค้ดเก่า ก่อนรวมโค้ด เวลาไม่แน่ใจ |
| conventions | ของใหม่นี้ควรชื่ออะไร หน้าตายังไง | ทุกครั้งที่สร้าง SP ตาราง ไฟล์ ฟังก์ชัน endpoint ใหม่ |
| kickoff | จะเริ่มยังไง และยังไม่ได้ถามอะไร | เริ่มโปรเจกต์ใหม่ หรือฟีเจอร์ใหญ่ที่ยังไม่มีอะไรเลย |

## skill ภายนอกที่ใช้ร่วม

| skill | หน้าที่ | ทับกับ repo นี้ไหม |
|---|---|---|
| [ponytail](https://github.com/DietrichGebert/ponytail) | ลดสิ่งที่ agent สร้าง | ไม่ทับ — ponytail คุมปริมาณ nohell คุมรูปแบบ |
| [caveman](https://github.com/JuliusBrussee/caveman) | ลดสิ่งที่ agent พูด | ไม่ทับเลย คนละครึ่ง |
| impeccable | งาน UI | ใช้คู่กับหมวด FE ในแคตตาล็อก |

## ทำไมไม่มีโฟลเดอร์ frontend/ backend/ database/ security/ แยก

เพราะจะกลายเป็น **SSOT-01 ในตัวเอง**: สร้าง C (skill ใหม่) โดยไม่ลบ A (หมวดใน HELL-CATALOG) แล้วสุดท้ายกฎเรื่อง SQL จะอยู่สองที่และเดินจากกัน

`HELL-CATALOG.md` แบ่งตามโดเมนอยู่แล้ว 31 หมวด (`SQL`, `DATA`, `FE`, `API`, `SEC`, `PERF`, `INT`, `JOB`, `TYPE`, `AGG`, `MEAS`, `REG`, `TOOL`, ...) สิ่งที่ขาดคือ **ตัวเลือกว่างานนี้ต้องอ่านหมวดไหน** ซึ่งคือ router ใน `principal-engineer` ไม่ใช่โฟลเดอร์เพิ่ม

skill ใหม่จะสร้างก็ต่อเมื่อมันมี **กระบวนการ** ที่แคตตาล็อกให้ไม่ได้ — `business-rules` และ `archaeology` ผ่านเกณฑ์นี้ (มันเป็นวิธีทำงาน ไม่ใช่รายการสิ่งที่ห้ามทำ) ส่วน "frontend" ไม่ผ่าน เพราะมันคือรายการสิ่งที่ห้ามทำล้วนๆ

## เอกสารอ้างอิง (ไม่ใช่ skill)

`docs/` เก็บของที่คนอ่าน ไม่ใช่ของที่ agent โหลด — `llm-reality.md` คือชุดความเข้าใจผิดที่คนใช้เครื่องมือพวกนี้ทุกวันยังเชื่ออยู่ พร้อมสิ่งที่ควรทำแทน · `tooling-2026.md` คือเครื่องมือที่คัดแล้วว่าคุ้มสำหรับคนดูแลระบบคนเดียว พร้อมข้อว่าไม่เหมาะกับใคร

## โดเมนที่ยังไม่ครอบคลุม

`MOBILE` (offline/sync/scanner/duplicate submit บนเน็ตโรงงาน) และ `ML` (dataset, leakage, preprocessing parity, threshold, drift) เพิ่มเข้าแคตตาล็อกแล้ว ที่ยังไม่มีคือ **INFRA** (container, reverse proxy, TLS, backup/DR) และ **NET** (connection pool, keep-alive, proxy timeout, backpressure — ตอนนี้กระจายอยู่ใน `ERR`/`PERF`)

ทั้งสองควรเพิ่มเป็นหมวดใหม่ในแคตตาล็อกเดิม ไม่ใช่ skill ใหม่ — เกณฑ์ว่าเมื่อไหร่ถึงควรเป็น skill อยู่ใน [CONTRIBUTING.md](CONTRIBUTING.md)

## ติดตั้ง

**ติดตั้งด้วย tag เสมอ ห้าม track `main`** — กฎในแคตตาล็อกเปลี่ยนได้ระหว่างทาง ถ้า agent อ่านจาก `main`
พฤติกรรมจะเปลี่ยนกลาง sprint โดยไม่มีใครรู้ว่าทำไมผลไม่เหมือนเมื่อวาน (ดู [CHANGELOG.md](CHANGELOG.md))

เลือกทางใดทางหนึ่ง ทั้งสามทางได้ครบทุก skill รวม `/nohell-dig`

```sh
# 1) npx skills — ต้องเป็น git URL เต็มพร้อม #tag เพราะรูปย่อ owner/repo จะไปเอา main
npx skills add "https://github.com/fonewspyy/nohell-skill.git#v1.0.2" --skill '*'

# 2) GitHub CLI v2.90.0 ขึ้นไป
gh skill install fonewspyy/nohell-skill --all --pin v1.0.2

# 3) clone เองแล้วคัดลอก
git clone --branch v1.0.2 --depth 1 https://github.com/fonewspyy/nohell-skill.git
cp -r nohell-skill/skills/* ~/.claude/skills/          # ใช้ได้ทุกโปรเจกต์
cp -r nohell-skill/skills/* .claude/skills/            # หรือเฉพาะโปรเจกต์นี้
```

ทาง 1 เขียน `skills-lock.json` ที่จดทั้ง `ref` และ hash ของเนื้อหาไว้ จึงรู้ทีหลังได้ว่าติดตั้งอะไรไป
`frontmatter` ของทุก skill ยึดหกฟิลด์ของมาตรฐาน [Agent Skills](https://agentskills.io)
(`name` `description` `license` `compatibility` `metadata` `allowed-tools`) จึงอัปโหลดขึ้น claude.ai
และแพ็กด้วย Skills API ได้โดยไม่ต้องแก้ — `scripts/validate-skills.py` เฝ้าข้อนี้ไว้

ทาง 2 ฉีดที่มาลงในช่อง `metadata` ของสำเนาที่ติดตั้ง (`github-repo` `github-ref` `github-pinned`
`github-tree-sha`) ซึ่งเป็นช่อง free-form ของมาตรฐานเอง จึงไม่หลุดสเปก และเป็นเหตุผลที่รีโปนี้
**ไม่** เขียน `version` ลง `metadata` ด้วยมือ — เครื่องมือเป็นคนเขียนช่องนั้นตอนติดตั้ง

> วัดเองแล้วบนเครื่องนี้ ทั้งสองทาง กับ tag `v1.0.0` ที่เผยแพร่จริง
> ทาง 1 ขึ้น `Source: … @ v1.0.0` ลงครบ 8 skills · ทาง 2 ขึ้น `Using ref v1.0.0 (ae8642fe)`
> ลงครบ 8 skills เช่นกัน exit 0 ทั้งคู่ และไม่ต้องล็อกอิน `gh` สำหรับรีโปสาธารณะ
> (ทดสอบด้วย `gh` 2.98.0 — คำสั่ง `gh skill` ยังอยู่ในสถานะ preview ตามที่ `--help` ของมันบอกเอง)
>
> คำสั่งข้างบนชี้รุ่นล่าสุด ส่วนที่วัดคือ `v1.0.0` — รุ่นหลังจากนั้นต่างกันแค่เอกสาร ไม่มีอะไรใน
> กลไกติดตั้งเปลี่ยน จึงไม่แก้เลขในกล่องนี้ให้ตรงกับคำสั่ง เพราะนั่นคือการเคลมว่าวัดสิ่งที่ยังไม่ได้วัด

⚠️ `gh skill install --all` เรียก GitHub API หนึ่งครั้งต่อหนึ่ง skill และโควตาของคนที่ยังไม่ล็อกอิน
หมดเร็วมาก — เจอมาแล้วตอนทดสอบซ้ำ ๆ ว่ามันหยุดกลางคันที่ skill ที่ห้าพร้อม `HTTP 403: API rate
limit exceeded` แล้ว exit 1 โดยที่บางตัวลงไปแล้ว ถ้าเจอให้ `gh auth login` ก่อน หรือใช้ทาง 1
ซึ่ง clone ทีเดียวจึงไม่ติดโควตา

ตัวรันกฎอยู่ที่ `scripts/nohell-check.py` **ไม่ได้อยู่ใน `skills/`** จึงไม่ถูกคัดลอกไปด้วย
ให้เก็บโฟลเดอร์ที่ clone ไว้แล้วเรียกจากที่นั่น หรือคัดลอกเฉพาะไฟล์นั้นไปไว้ที่ไหนก็ได้ —
มันหา `hell-rules.yaml` เองจาก `~/.claude/skills/nohell/` ที่เพิ่งติดตั้ง

```sh
cd /path/to/repo-ที่จะตรวจ
python /path/to/nohell-skill/scripts/nohell-check.py        # diff-only
```

แล้วให้ `AGENTS.md`/`CLAUDE.md` ของโปรเจกต์ชี้มาที่ `skills/principal-engineer/SKILL.md` เป็นด่านแรก

`/nohell-dig` มาพร้อมกันแล้ว ไม่ต้องคัดลอกแยกเหมือนก่อน — Claude Code รวม custom command
เข้ากับ skill แล้ว ไฟล์ที่ `skills/nohell-dig/SKILL.md` จึงสร้างคำสั่ง `/nohell-dig` ให้เอง
ถ้าไม่อยากให้ Claude หยิบไปใช้เอง ให้ตั้ง `skillOverrides` เป็น `"user-invocable-only"` ในไฟล์ตั้งค่า
(ไม่ได้ใส่ `disable-model-invocation` ไว้ในไฟล์ เพราะเป็นฟิลด์นอกมาตรฐาน จะทำให้ช่องทางอื่นปฏิเสธทั้งไฟล์)

ไฟล์ที่ต้องคัดลอกไปไว้ที่ **repo เป้าหมาย** ไม่ใช่ที่นี่:

- `CONSOLIDATIONS.yaml` (จาก `skills/nohell/CONSOLIDATIONS.example.yaml`) — ทะเบียนวง C ที่ยังเปิดอยู่
- `docs/impact/` — Impact Map ต่องาน
- `docs/adr/` — การตัดสินใจที่ย้อนยาก
- `docs/archaeology/` — ผลการสืบ

## ระดับความรุนแรง

**P1** 155 ข้อ (ข้อมูลผิด/หาย/ซ้ำแบบเงียบ · รั่ว · เงินเคลื่อนผิด) · **P2** 169 ข้อ (พังแบบดัง กู้ได้โดยไม่แตะข้อมูลย้อนหลัง) · **P3** 159 ข้อ (ต้นทุนการอ่าน/ดูแล)

ระดับถูกไล่ใหม่ทั้ง 483 ข้อตามเกณฑ์เดียวที่เขียนไว้ใน [CONTRIBUTING.md](CONTRIBUTING.md) —
**"ร้ายแรงมาก" ไม่ใช่เหตุผลให้เป็น P1** ระบบล่มทั้งวันยังเป็น P2 ถ้ากู้แล้วข้อมูลถูกต้องเหมือนเดิม
สิ่งที่ทำให้เป็น P1 คือ *ข้อมูลที่ผิดไปแล้วโดยไม่มีใครรู้* เพราะนั่นคือสิ่งที่ย้อนกลับไม่ได้

## ตรวจความสอดคล้องของแคตตาล็อก

repo นี้ห้าม `SSOT-01` กับคนอื่น ก็ต้องไม่ทำกับตัวเอง — งานแบ่งเป็นสามตัวที่ไม่ทับกัน

`validate-catalog.sh` ตรวจ **รูปร่าง** ของแคตตาล็อก: ID ซ้ำ · เลขขาดช่วง · ระดับ P ที่หายไป · แถวที่ไม่ครบช่อง · **ID ที่ skill/docs อ้างถึงแต่ไม่มีจริงในแคตตาล็อก** ·
**pattern ที่ใช้ lookaround แต่ไม่ประกาศ `engine: pcre2`** · **คำอ้างขนาด token ที่เดินจากขนาดไฟล์จริง** ·
ค่าในช่อง `ใช้กับ` ที่ไม่อยู่ในชุดที่อนุญาต · severity ใน `hell-rules.yaml` ที่ไม่ตรงกับแคตตาล็อก ·
**pattern ที่จับข้ามบรรทัดแต่ไม่ประกาศ `multiline: true`** · **ค่า `ใช้กับ` ที่ใช้จริง
แต่ไม่มีในรายการที่ผู้อ่านใช้กรองก่อนอ่าน (legend หัวแคตตาล็อก และตารางใน `SKILL.md`)**

`build-summary.py` เป็นเจ้าของ **ทุกตัวเลขที่ถูกประกาศไว้** — เลขในหัวแคตตาล็อก · เลขท้ายหัวข้อหมวด ·
ตารางสรุป · และตัวเลขในเนื้อความของเอกสาร (จำนวนข้อ · หมวด · P1/P2/P3 · กฎอัตโนมัติ ·
จำนวนต่อ stack ในรายการ `ใช้กับ` ทั้งสามสำเนา) ตาราง `FACTS`
ในไฟล์นั้นคือที่เดียวที่บอกว่าเลขไหนต้องตรงกับอะไร และถ้ารันโดยไม่ใส่ `--check` มันจะ **แก้ให้ถูก**
ไม่ใช่แค่ฟ้อง — เลขที่คนต้องแก้มือคือเลขที่จะเดิน

`validate-skills.py` ตรวจ **การแพ็กเกจ**: frontmatter ของทุก `SKILL.md` ต้องอยู่ในหกฟิลด์ของมาตรฐาน
Agent Skills · `name` ต้องตรงกับชื่อโฟลเดอร์ (ชื่อคำสั่งมาจากโฟลเดอร์ ไม่ได้มาจากฟิลด์) ·
ความยาวของ `description`/`compatibility` ต้องไม่เกินเพดาน — ฟิลด์ที่หลุดมาตรฐานพังตอน *คนอื่น*
ติดตั้ง ไม่ใช่ตอนเราแก้ จึงไม่มีทางรู้เองถ้าไม่มีด่าน

```sh
sh scripts/validate-catalog.sh
python scripts/validate-skills.py
python scripts/build-summary.py --check   # ตารางสรุปท้ายไฟล์ตรงกับของจริงไหม
```

CI รันทั้งสามตัวนี้ทุก push · ตารางสรุปท้าย `HELL-CATALOG.md` generate จากข้อมูลจริง ห้ามแก้มือ

## รันกฎอัตโนมัติ — `nohell-check`

โหมดหลักคือ **diff-only**: อ่านเฉพาะบรรทัดที่ *เพิ่ม* จาก `git diff` แล้วรันกฎกับบรรทัดนั้น
hit บนบรรทัดที่เพิ่มคือของใหม่โดยนิยาม จึงเป็น `ratchet` (ห้ามเพิ่ม ไม่ใช่ห้ามมี) ในตัวเอง
**ไม่ต้องล้าง hit เก่าก่อนเปิด gate** ซึ่งเป็นเหตุผลที่ gate แบบ absolute ถูกปิดทิ้งเสมอ

```sh
pip install pyyaml                                  # ต้องมี ไม่ใช่ stdlib
python scripts/nohell-check.py                      # diff เทียบ origin/main
python scripts/nohell-check.py --base HEAD~1
python scripts/nohell-check.py --full               # ทั้ง repo (ไฟล์ที่ git ติดตาม)
python scripts/nohell-check.py --full --baseline    # เขียน .nohell-baseline.json
```

exit code เป็นสัญญา: `0` ผ่าน · `1` เจอกฎระดับ `gate.block_on` บนบรรทัดที่เพิ่ม ·
**`2` รันไม่ได้** (ไม่มี `rg` / ไม่มี PCRE2 / pattern compile ไม่ผ่าน) — ห้ามกลืน `2` เป็น `0`
เพราะ gate ที่เงียบแล้วผ่านทุกอย่างแย่กว่าไม่มี gate

| ตัวนี้รัน | ตัวนี้ **ไม่** รัน (ขึ้นในรายงานทุกครั้ง) |
|---|---|
| `kind: regex` 40 ข้อ พร้อม flag ที่แต่ละกฎประกาศ (`engine: pcre2` → `-P` · `multiline: true` → `-U`) | `kind: cmd` 13 ข้อ — เรียกของนอก (eslint / gitleaks / pnpm audit) การรันคำสั่งจากคอนฟิกเป็นทางเปิดให้ arbitrary execution |
| `allow_comment` และ `exclude` ของแต่ละกฎ | `kind: sql` 12 ข้อ — ต้องต่อฐานข้อมูล ใช้ `detect-sqlserver.sql` เอง |
| `.nohellignore` ระดับ repo | `kind: manual-checklist` 2 ข้อ — ต้องคนอ่าน |

`.nohellignore` มีไว้เพื่อกรณีเดียว: **ไฟล์ที่นิยามกฎย่อมตรงกับกฎของตัวเอง** — ห้ามใช้เลี่ยงงาน
ถ้าจะยกเว้นรายจุดให้ใช้ `allow_comment` ของกฎนั้น

เทสอยู่ที่ `scripts/test-nohell-check.sh` (เคส diff ที่รู้คำตอบ) และ `scripts/test-build-summary.sh`
(เคสที่รู้คำตอบของตัวเขียนตัวเลข ซึ่งเขียนทับเอกสารจริง) ทั้งคู่ตรวจสองทางเสมอ — ผิดแล้วต้องจับได้
และถูกแล้วต้องไม่แตะไฟล์ · ไม่ประกาศจำนวนเคสไว้ตรงนี้ เพราะเลขที่คนต้องแก้มือคือเลขที่จะเดิน · CI รันทั้งคู่

## ข้อจำกัดที่รู้อยู่ — อ่านก่อนเอาไปต่อ CI

ผ่านการทดสอบจริงบน repo enterprise (SQL Server 389 ไฟล์ + .NET + TypeScript) แล้ว สิ่งที่พบ:

**1. 6 กฎต้องใช้ PCRE2 เท่านั้น** — `SQL-16`, `SQL-30`, `ERR-11`, `CFG-03`, `SHIP-05`, `FE-07` ใช้ lookahead/lookbehind
Rust regex (`rg` ปกติ) และ `grep -E` จะ **parse error** ถ้าตัวรันกลืน error ไว้ gate จะเงียบแล้วผ่านทุกอย่าง
ซึ่งแย่กว่าไม่มี gate ต้องรันด้วย `rg -P` และกฎพวกนี้ประกาศ `engine: pcre2` ไว้แล้ว (validator บังคับ)

**1b. อีก 2 กฎต้องใช้ multiline** — `SQL-26`, `ERR-09` จับข้ามบรรทัด (มี `\n` เป็นสิ่งที่ต้อง match)
ต้องรันด้วย `rg -U` พังแบบเดียวกันเป๊ะถ้าไม่ใส่ วัดจริง: `SQL-26` รายงาน **0** บน `rg` ปกติ แต่ได้
**11 hit ใน 7 ไฟล์** เมื่อใส่ `-U` ทั้งสองประกาศ `multiline: true` ไว้แล้ว (validator ข้อ 13 บังคับ)
หมายเหตุ: `[^\n]` อย่างเดียว **ไม่ต้อง** ใช้ `-U` — มันกันบรรทัดใหม่ ไม่ได้ match มัน

**2. `gate.mode` เริ่มต้นเป็น `ratchet` ไม่ใช่ `absolute`** — 155 จาก 483 ข้อเป็น P1
เปิดแบบ absolute วันแรกบน repo เก่าจะได้ P1 หลักพัน (วัดจริง: `NOLOCK` ข้อเดียว 6,355 hit ใน 219/389 ไฟล์)
นั่นไม่ใช่ gate แต่เป็น backlog แล้วคนจะปิดทิ้ง — `ratchet` บังคับว่า **ห้ามเพิ่ม** ไม่ใช่ **ห้ามมี**

**0. ทุกข้อประกาศ stack ที่มันใช้ได้** — ช่อง `ใช้กับ` ในแคตตาล็อก: `ทุกที่` 358 ข้อ (74%) ที่เหลือผูกกับ
`RDBMS` 49 · `เว็บ` 17 · `SQL Server` 13 · `mobile` 13 · `ML` 13 · `PII` 10 · `มี SP` 7 · `TS/JS` 2 · `.NET` 1
เพิ่มหลังทดสอบกับ repo MySQL แล้วพบว่า 17 จาก 31 ข้อในหมวด `SQL` ใช้ไม่ได้เลยโดยไม่มีอะไรบอกไว้
กรองก่อนอ่านเสมอ — ร้าน Python + PostgreSQL ที่ไม่มีแอปมือถือและไม่มีโมเดล อ่าน 407 ข้อ ข้ามอีก 76 ไปได้

**3. ชั้นอัตโนมัติคือ triage ไม่ใช่ gate** — วัดบน repo จริง (MySQL + TS, 1,413 ไฟล์):
กฎ P1 ชี้ไป 473 จาก 1,413 ไฟล์ (33%) ซึ่งมีไฟล์ที่มีบั๊กจริงอยู่ 16 จาก 18 → **lift เหนือการสุ่มแค่ 2.66 เท่า**
และ **จับบั๊กที่ verify แล้วทั้ง 21 ข้อได้ 0 ข้อ** เพราะทุกข้อเป็นบั๊กเชิงความหมายที่ regex เข้าไม่ถึง
ส่วนที่ทำงานจริงคือ **เลนส์แคตตาล็อกที่คนหรือ agent อ่าน** — recall 71% (86% ถ้านับที่จับได้ครึ่งเดียว)
ใช้ regex คัดว่าจะอ่านไฟล์ไหนก่อน ไม่ใช่ใช้ block

**3b. regex คือด่านแรก ไม่ใช่คำตัดสิน** — หลายกฎ over-match โดยตั้งใจ (`SQL-31` จับทุก `@iJson nvarchar(max)`)
ตามปรัชญาในหัวไฟล์: false positive ถูกกว่า false negative ผลที่ได้ต้องมีคนหรือ agent อ่านต่อ
ไม่ใช่เอาไป block ตรงๆ

**4. recall บนบั๊กจริง ~42%** — ทดสอบกับบั๊ก production ที่บันทึกไว้ 19 ข้อ จับตรงๆ ได้ 8 (63% ถ้านับที่จับได้ครึ่งเดียว)
ที่จับได้กระจุกในหมวดเงิน/SSOT ซึ่งเป็นจุดที่เจ็บซ้ำที่สุด ส่วนที่พลาดเป็นก้อนที่ยังไม่มีหมวดรองรับ
(เครื่องมือวัดที่ตั้งค่าไม่เหมือน prod · aggregate บนเซ็ตที่ปนคนละชนิด · type inference ในเลขคณิต · registry สองชั้นเดินจากกัน)
ดู [CONTRIBUTING.md](CONTRIBUTING.md)

## ร่วมพัฒนา

ดู [CONTRIBUTING.md](CONTRIBUTING.md) — เกณฑ์การเพิ่มข้อในแคตตาล็อก เกณฑ์การสร้าง skill ใหม่ และรายการช่องว่างที่ยังรับ contribution

## License

[MIT](LICENSE)
