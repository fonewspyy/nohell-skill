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
├── nohell/               ← แคตตาล็อก anti-pattern 447 ข้อ + กฎที่ตรวจอัตโนมัติได้ + สคริปต์สแกน DB
│   └── commands/nohell-dig.md   ← ขุดประวัติ repo หา "นรกซ้ำซาก" ที่เจ็บจริง
├── business-rules/       ← SSOT ของกฎ, effective date, read/write symmetry, workflow, เงิน
├── archaeology/          ← ระดับหลักฐาน, บัญชีผู้เรียก, ค้นสำเนากฎด้วยรูปร่าง
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

`HELL-CATALOG.md` แบ่งตามโดเมนอยู่แล้ว 28 หมวด (`SQL`, `DATA`, `FE`, `API`, `SEC`, `PERF`, `INT`, `JOB`, `TYPE`, `AGG`, `MEAS`, `REG`, `TOOL`, ...) สิ่งที่ขาดคือ **ตัวเลือกว่างานนี้ต้องอ่านหมวดไหน** ซึ่งคือ router ใน `principal-engineer` ไม่ใช่โฟลเดอร์เพิ่ม

skill ใหม่จะสร้างก็ต่อเมื่อมันมี **กระบวนการ** ที่แคตตาล็อกให้ไม่ได้ — `business-rules` และ `archaeology` ผ่านเกณฑ์นี้ (มันเป็นวิธีทำงาน ไม่ใช่รายการสิ่งที่ห้ามทำ) ส่วน "frontend" ไม่ผ่าน เพราะมันคือรายการสิ่งที่ห้ามทำล้วนๆ

## เอกสารอ้างอิง (ไม่ใช่ skill)

`docs/` เก็บของที่คนอ่าน ไม่ใช่ของที่ agent โหลด — `llm-reality.md` คือชุดความเข้าใจผิดที่คนใช้เครื่องมือพวกนี้ทุกวันยังเชื่ออยู่ พร้อมสิ่งที่ควรทำแทน · `tooling-2026.md` คือเครื่องมือที่คัดแล้วว่าคุ้มสำหรับคนดูแลระบบคนเดียว พร้อมข้อว่าไม่เหมาะกับใคร

## โดเมนที่ยังไม่ครอบคลุม

แคตตาล็อกตอนนี้ยังไม่มีหมวดสำหรับ **MOBILE** (offline/sync/scanner/duplicate submit บนเน็ตโรงงาน), **AI-ML** (dataset, leakage, preprocessing parity, threshold, drift), **INFRA** (container, reverse proxy, TLS, backup/DR), **NET** (connection pool, keep-alive, proxy timeout, backpressure — ตอนนี้กระจายอยู่ใน ERR/PERF)

สามอันแรกเป็นช่องว่างจริงสำหรับงานคลังสินค้าที่มี Flutter RF และงาน AI — ควรเพิ่มเป็นหมวดใหม่ในแคตตาล็อกเดิม ไม่ใช่ skill ใหม่

## ติดตั้ง

**ติดตั้งด้วย tag เสมอ ห้าม track `main`** — กฎในแคตตาล็อกเปลี่ยนได้ระหว่างทาง ถ้า agent อ่านจาก `main`
พฤติกรรมจะเปลี่ยนกลาง sprint โดยไม่มีใครรู้ว่าทำไมผลไม่เหมือนเมื่อวาน (ดู [CHANGELOG.md](CHANGELOG.md))

```sh
git clone --branch v0.9.0 --depth 1 https://github.com/fonewspyy/nohell-skill.git
cp -r nohell-skill/skills/* ~/.claude/skills/          # ใช้ได้ทุกโปรเจกต์
# หรือเฉพาะโปรเจกต์นี้
cp -r nohell-skill/skills/* .claude/skills/
```

แล้วให้ `AGENTS.md`/`CLAUDE.md` ของโปรเจกต์ชี้มาที่ `skills/principal-engineer/SKILL.md` เป็นด่านแรก

คำสั่ง `/nohell-dig` ต้องวางแยก เพราะ Claude Code อ่าน slash command จาก `commands/` ไม่ใช่จาก `skills/`:

```sh
cp nohell-skill/skills/nohell/commands/nohell-dig.md ~/.claude/commands/
```

ไฟล์ที่ต้องคัดลอกไปไว้ที่ **repo เป้าหมาย** ไม่ใช่ที่นี่:

- `CONSOLIDATIONS.yaml` (จาก `skills/nohell/CONSOLIDATIONS.example.yaml`) — ทะเบียนวง C ที่ยังเปิดอยู่
- `docs/impact/` — Impact Map ต่องาน
- `docs/adr/` — การตัดสินใจที่ย้อนยาก
- `docs/archaeology/` — ผลการสืบ

## ระดับความรุนแรง

**P1** 136 ข้อ (ข้อมูลผิด/หาย/ซ้ำแบบเงียบ · รั่ว · เงินเคลื่อนผิด) · **P2** 154 ข้อ (พังแบบดัง กู้ได้โดยไม่แตะข้อมูลย้อนหลัง) · **P3** 157 ข้อ (ต้นทุนการอ่าน/ดูแล)

ระดับถูกไล่ใหม่ทั้ง 447 ข้อตามเกณฑ์เดียวที่เขียนไว้ใน [CONTRIBUTING.md](CONTRIBUTING.md) —
**"ร้ายแรงมาก" ไม่ใช่เหตุผลให้เป็น P1** ระบบล่มทั้งวันยังเป็น P2 ถ้ากู้แล้วข้อมูลถูกต้องเหมือนเดิม
สิ่งที่ทำให้เป็น P1 คือ *ข้อมูลที่ผิดไปแล้วโดยไม่มีใครรู้* เพราะนั่นคือสิ่งที่ย้อนกลับไม่ได้

## ตรวจความสอดคล้องของแคตตาล็อก

repo นี้ห้าม `SSOT-01` กับคนอื่น ก็ต้องไม่ทำกับตัวเอง — สคริปต์นี้ตรวจ 10 อย่าง:
จำนวนในหัวไฟล์ · จำนวนท้ายหัวข้อหมวด · ID ซ้ำ · เลขขาดช่วง · ระดับ P ที่หายไป · แถวที่ไม่ครบช่อง ·
**ID ที่ skill/docs อ้างถึงแต่ไม่มีจริงในแคตตาล็อก** · **ตัวเลขที่ประกาศไว้ในไฟล์อื่นแล้วเดินจากของจริง** ·
**pattern ที่ใช้ lookaround แต่ไม่ประกาศ `engine: pcre2`** · **คำอ้างขนาด token ที่เดินจากขนาดไฟล์จริง**

```sh
sh scripts/validate-catalog.sh
python scripts/build-summary.py --check   # ตารางสรุปท้ายไฟล์ตรงกับของจริงไหม
```

CI รันทั้งสองตัวนี้ทุก push · ตารางสรุปท้าย `HELL-CATALOG.md` generate จากข้อมูลจริง ห้ามแก้มือ

## ข้อจำกัดที่รู้อยู่ — อ่านก่อนเอาไปต่อ CI

ผ่านการทดสอบจริงบน repo enterprise (SQL Server 389 ไฟล์ + .NET + TypeScript) แล้ว สิ่งที่พบ:

**1. 6 กฎต้องใช้ PCRE2 เท่านั้น** — `SQL-16`, `SQL-30`, `ERR-11`, `CFG-03`, `SHIP-05`, `FE-07` ใช้ lookahead/lookbehind
Rust regex (`rg` ปกติ) และ `grep -E` จะ **parse error** ถ้าตัวรันกลืน error ไว้ gate จะเงียบแล้วผ่านทุกอย่าง
ซึ่งแย่กว่าไม่มี gate ต้องรันด้วย `rg -P` และกฎพวกนี้ประกาศ `engine: pcre2` ไว้แล้ว (validator บังคับ)

**2. `gate.mode` เริ่มต้นเป็น `ratchet` ไม่ใช่ `absolute`** — 215 จาก 447 ข้อเป็น P1
เปิดแบบ absolute วันแรกบน repo เก่าจะได้ P1 หลักพัน (วัดจริง: `NOLOCK` ข้อเดียว 6,355 hit ใน 219/389 ไฟล์)
นั่นไม่ใช่ gate แต่เป็น backlog แล้วคนจะปิดทิ้ง — `ratchet` บังคับว่า **ห้ามเพิ่ม** ไม่ใช่ **ห้ามมี**

**0. ทุกข้อประกาศ stack ที่มันใช้ได้** — ช่อง `ใช้กับ` ในแคตตาล็อก: `ทุกที่` 358 ข้อ (80%) ที่เหลือผูกกับ
`RDBMS` 49 · `SQL Server` 13 · `มี SP` 7 · `เว็บ` 17 · `TS/JS` 2 · `.NET` 1
เพิ่มหลังทดสอบกับ repo MySQL แล้วพบว่า 17 จาก 31 ข้อในหมวด `SQL` ใช้ไม่ได้เลยโดยไม่มีอะไรบอกไว้
กรองก่อนอ่านเสมอ — ร้าน Python + PostgreSQL อ่าน 407 ข้อ ข้ามอีก 40 ไปได้

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
