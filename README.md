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
├── nohell/               ← แคตตาล็อก anti-pattern 401 ข้อ + กฎที่ตรวจอัตโนมัติได้ + สคริปต์สแกน DB
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
| nohell (SKILL.md) | เขียนแบบนี้แล้วจะเป็นนรกไหม | ทุกงาน โหลดตลอด (~1k token) |
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

`HELL-CATALOG.md` แบ่งตามโดเมนอยู่แล้ว 23 หมวด (`SQL`, `DATA`, `FE`, `API`, `SEC`, `PERF`, `INT`, `JOB`, ...) สิ่งที่ขาดคือ **ตัวเลือกว่างานนี้ต้องอ่านหมวดไหน** ซึ่งคือ router ใน `principal-engineer` ไม่ใช่โฟลเดอร์เพิ่ม

skill ใหม่จะสร้างก็ต่อเมื่อมันมี **กระบวนการ** ที่แคตตาล็อกให้ไม่ได้ — `business-rules` และ `archaeology` ผ่านเกณฑ์นี้ (มันเป็นวิธีทำงาน ไม่ใช่รายการสิ่งที่ห้ามทำ) ส่วน "frontend" ไม่ผ่าน เพราะมันคือรายการสิ่งที่ห้ามทำล้วนๆ

## เอกสารอ้างอิง (ไม่ใช่ skill)

`docs/` เก็บของที่คนอ่าน ไม่ใช่ของที่ agent โหลด — `llm-reality.md` คือชุดความเข้าใจผิดที่คนใช้เครื่องมือพวกนี้ทุกวันยังเชื่ออยู่ พร้อมสิ่งที่ควรทำแทน · `tooling-2026.md` คือเครื่องมือที่คัดแล้วว่าคุ้มสำหรับคนดูแลระบบคนเดียว พร้อมข้อว่าไม่เหมาะกับใคร

## โดเมนที่ยังไม่ครอบคลุม

แคตตาล็อกตอนนี้ยังไม่มีหมวดสำหรับ **MOBILE** (offline/sync/scanner/duplicate submit บนเน็ตโรงงาน), **AI-ML** (dataset, leakage, preprocessing parity, threshold, drift), **INFRA** (container, reverse proxy, TLS, backup/DR), **NET** (connection pool, keep-alive, proxy timeout, backpressure — ตอนนี้กระจายอยู่ใน ERR/PERF)

สามอันแรกเป็นช่องว่างจริงสำหรับงานคลังสินค้าที่มี Flutter RF และงาน AI — ควรเพิ่มเป็นหมวดใหม่ในแคตตาล็อกเดิม ไม่ใช่ skill ใหม่

## ติดตั้ง

```sh
git clone https://github.com/fonewspyy/nohell-skill.git
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

## ตรวจความสอดคล้องของแคตตาล็อก

repo นี้ห้าม `SSOT-01` กับคนอื่น ก็ต้องไม่ทำกับตัวเอง — สคริปต์นี้ตรวจ 8 อย่าง:
จำนวนในหัวไฟล์ · จำนวนท้ายหัวข้อหมวด · ID ซ้ำ · เลขขาดช่วง · ระดับ P ที่หายไป · แถวที่ไม่ครบช่อง ·
**ID ที่ skill/docs อ้างถึงแต่ไม่มีจริงในแคตตาล็อก** · **ตัวเลขที่ประกาศไว้ในไฟล์อื่นแล้วเดินจากของจริง**

```sh
sh scripts/validate-catalog.sh
```

CI รันตัวเดียวกันนี้ทุก push

## ร่วมพัฒนา

ดู [CONTRIBUTING.md](CONTRIBUTING.md) — เกณฑ์การเพิ่มข้อในแคตตาล็อก เกณฑ์การสร้าง skill ใหม่ และรายการช่องว่างที่ยังรับ contribution

## License

[MIT](LICENSE)
