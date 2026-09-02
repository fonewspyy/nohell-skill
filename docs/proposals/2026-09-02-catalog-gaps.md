# ข้อเสนอ: ช่องว่างในแคตตาล็อกที่ eval พบ (b02, c03/g4)

สถานะ: ข้อเสนอ (proposal) — ยังไม่ได้แก้ `HELL-CATALOG.md` หรือ `hell-rules.yaml`
อ้างอิง: `eval/cases/b02-or-chain.json`, `eval/cases/c03-idempotent-upsert.json`, `eval/keys/g4.json`, `eval/keys/merged.json` (`exclude_reason` ของ `b02-or-chain`)

ตัดสินตามด่าน D1/D2 ของ `CONTRIBUTING.md` บรรทัด 21-102 ค่า `ใช้กับ` ทั้งหมดอ้างจากตัวแปร `ok=`
ใน `scripts/validate-catalog.sh` บรรทัด 110 (`ทุกที่|RDBMS|SQL Server|มี SP|TS/JS|.NET|เว็บ|mobile|ML|PII`)
ไม่มีการแก้ `HELL-CATALOG.md`/`hell-rules.yaml` ในเอกสารนี้

---

## อาการที่ 1 — OR คร่อมหลายคอลัมน์ทิ้ง index ทุกตัว (`b02-or-chain`)

```sql
SELECT TransportNo, LoadNo FROM dbo.Shipment
WHERE  TransportNo = @key OR LoadNo = @key OR RefNo = @key;
```

วัดจริง: 21,014 logical reads → 20 เมื่อเขียนใหม่เป็น `UNION ALL` แยกสามเงื่อนไข แต่ละเงื่อนไขเดี่ยว ๆ sargable
ปกติ ไม่มีฟังก์ชันครอบคอลัมน์เลย ปัญหาคือ optimizer เลือก scan ทั้งตารางแทนที่จะรวมผลจาก index seek สามตัว
คนละกลไกกับ SQL-10 (ซึ่ง `merged.json` ระบุไว้แล้วว่าเฉลยเดิมผิด และกันเคสนี้ออกจากการวัด)

### ก) ตาราง D1

| ID ที่ใกล้ที่สุด | กฎแทนของมันว่าอย่างไร | ทำตามแล้วบั๊กนี้ยังเกิดไหม | เพราะอะไร |
|---|---|---|---|
| `SQL-10` | "เขียนเป็นช่วง `d >= @from AND d < @to` ให้ใช้ index ได้" | เกิด | กฎนี้แก้เฉพาะ predicate ที่ถูกฟังก์ชัน/การแปลงชนิดครอบ (`CONVERT`, `YEAR(...)`) ทั้งสามเงื่อนไขใน snippet เป็น equality ตรง ๆ ไม่มีฟังก์ชันครอบเลย ทำตามกฎนี้แล้วไม่มีอะไรให้แก้ — บั๊กยังอยู่เหมือนเดิม |
| `SQL-11` | "ให้ชนิดข้อมูลของ parameter ตรงกับคอลัมน์เสมอ" | เกิด | ปัญหาไม่ใช่ implicit conversion ระหว่าง `varchar`/`nvarchar` — `@key` เทียบกับสามคอลัมน์ด้วย operator เดียวกันไม่มีหลักฐานว่าเกิดการแปลงชนิด ต่อให้ชนิดตรงกันสนิททุกตัว ปัญหา OR ข้ามคอลัมน์ก็ยังอยู่ |
| `PERF-05` | "ดู execution plan ของ query หลักแล้วใส่ index ตามจริง" | เกิด | ข้อความของเคสเองระบุว่า "รวมผลจาก index หลายตัว" คือทางที่ควรได้ — หมายความว่าแต่ละคอลัมน์มี index รองรับอยู่แล้ว การ "ใส่ index ตามจริง" จึงทำไปแล้วตั้งแต่ต้น บั๊กไม่ได้มาจากการไม่มี index แต่มาจากที่ optimizer ไม่รวมผลจาก index หลายตัวเมื่อเชื่อมด้วย `OR` ข้ามคอลัมน์ |

ค้นทั้งแคตตาล็อกด้วยคำว่า "ดัชนี/index/UNION/scan" เพิ่มเติม (`DATA-08`, `DATA-10`, `DATA-18`, `DATA-19`, `INT-11`,
`MEAS-01`) ไม่มีข้อไหนพูดถึงรูปแบบ "OR ข้ามคอลัมน์ทำให้ optimizer เลือก scan แทน index union/seek" ทั้งสามข้อที่ใกล้ที่สุดตอบ
"เกิด" ครบ → **ต้องมีข้อใหม่**

### ข) ระดับ P (บันได D2)

1. ทำให้ข้อมูลที่บันทึกแล้วผิด/หาย/ซ้ำโดยระบบไม่ฟ้องเอง หรือรั่ว หรือเงินเคลื่อนผิด? — **ไม่ใช่** เป็น `SELECT` อย่างเดียว ไม่มีการเขียนข้อมูล ไม่มีการรั่วหรือเงินเคลื่อน
2. ทำให้พังแบบดัง (ล่ม/error ค้าง/ช้าจนใช้ไม่ได้) และกู้ได้โดยไม่ต้องแตะข้อมูลย้อนหลัง? — **ใช่** reads พุ่งจากหลักสิบเป็นสองหมื่นกว่าต่อคำขอ บนตารางที่ถูกเรียกถี่จะทำให้ query ช้า/บล็อกคิว การแก้คือ rewrite เป็น `UNION ALL` ล้วน ๆ ไม่ต้องแตะข้อมูลเดิมเลย
3. → หยุดที่ข้อ 2 = **P2** (ตรงกับ `SQL-10`/`SQL-11` ที่เป็นตระกูลเดียวกันและก็เป็น P2 ทั้งคู่)

### ค) แถวใหม่

หมวด: เลือก **SQL** ไม่ใช่ PERF เพราะอาการนี้เป็นพฤติกรรม query-plan/index ของ T-SQL/RDBMS โดยเฉพาะ (คนละกลุ่มกับ
`PERF` ที่คุมเรื่อง N+1, pagination, memory ระดับแอป) อยู่ในกลุ่มเดียวกับ `SQL-08` (scalar UDF), `SQL-09`
(multi-statement TVF), `SQL-10`/`SQL-11` (sargability/conversion) ซึ่งทั้งหมดคือ "เขียน query แบบนี้แล้ว
optimizer เลือกแผนที่แพงกว่าที่ควร" เลขถัดไปในหมวด SQL: ข้อสุดท้ายจริงคือ `SQL-31` (นับจากหัวข้อ "## SQL —
Stored Procedure / T-SQL (31)" และแถวสุดท้าย `SQL-31 | ... | RDBMS`) → ID ใหม่ = `SQL-32`

| ID | P | Hell | อาการ | กฎแทน | ใช้กับ |
|---|---|---|---|---|---|
| `SQL-32` | P2 | OR คร่อมหลายคอลัมน์ | `WHERE A=@x OR B=@x OR C=@x` บนสามคอลัมน์ที่มี index แยกกันคนละตัว แต่ execution plan เลือก Clustered Index Scan/Table Scan ทั้งตารางแทนที่จะรวมผลจาก index seek สามตัว — วัดจริง logical reads พุ่งจากหลักสิบเป็นหลักหมื่นทั้งที่แต่ละเงื่อนไขเดี่ยว ๆ sargable ปกติ | แยกเป็น `UNION ALL` ทีละเงื่อนไข (`SELECT ... WHERE A=@x UNION ALL SELECT ... WHERE B=@x UNION ALL SELECT ... WHERE C=@x` — ใช้ `UNION` แทนถ้าค่าคีย์อาจซ้ำข้ามคอลัมน์จนเกิดแถวซ้ำ) ให้แต่ละท่อน seek index ของคอลัมน์นั้นแยกกัน ห้ามฝาก `OR` ข้ามคอลัมน์ให้ optimizer ตัดสินใจเอง | RDBMS |

`ใช้กับ` เลือก `RDBMS` ไม่ใช่ `ทุกที่`: นี่คือพฤติกรรม query planner ของฐานข้อมูลเชิงสัมพันธ์ล้วน ๆ (SQL Server/Oracle/
Postgres/MySQL ต่างมีข้อจำกัดคล้ายกันเรื่อง OR ข้ามคอลัมน์กับการรวมผล index) ไม่เกี่ยวกับภาษาแอปเลย จึงไม่ใช่
`ทุกที่` แต่ก็ไม่ผูกกับ SQL Server เท่านั้น (ตัวอย่างในเคสเป็น T-SQL แต่กลไก OR-defeats-index-union เป็นเรื่องทั่วไป
ของ RDBMS ไม่ใช่ syntax เฉพาะของ SQL Server แบบ `SQL-14`/`SQL-27`)

### ง) ตรวจอัตโนมัติได้ไหม

**ไม่ควรทำเป็น regex** การจะรู้ว่า snippet นี้ "ผิด" ต้องรู้อย่างน้อยสองอย่างที่ regex มองไม่เห็น:

1. แต่ละคอลัมน์ที่ OR กันมี index แยกกันจริงไหม (ถ้าไม่มี ก็เป็นเรื่องของ `PERF-05` ไม่ใช่เรื่องนี้)
2. optimizer เลือก scan จริงไหม (ต้องดู execution plan — คนละ artifact จากซอร์สโค้ด)

ทางไวยากรณ์ล้วน ๆ `WHERE a = @x OR b = @x OR c = @x` แยกไม่ออกจากกรณีที่ไม่ผิดเลย เช่น ตารางเล็กมาก, มี composite
index ที่คลุมทั้งสามคอลัมน์อยู่แล้ว, หรือ query รันวันละครั้งตอนไม่มีโหลด — สามกรณีนี้หน้าตาซอร์สโค้ดเหมือนกันทุก
ตัวอักษรกับเคสที่ผิดจริง regex จะจับ "รูปร่างของ SQL" ไม่ใช่ "พฤติกรรมของ optimizer" precision จะต่ำมากจนคนเลิก
อ่านผลทั้งชุด (CONTRIBUTING บรรทัด 84: "กฎที่ over-match แย่กว่าไม่มีกฎ") จึงเสนอว่า **ไม่เพิ่มกฎใน
`hell-rules.yaml` สำหรับข้อนี้**

---

## อาการที่ 2 — MERGE ที่ไม่มี HOLDLOCK แข่งกันเองแล้วข้อมูลผิด (`c03-idempotent-upsert` / `g4`)

```sql
MERGE dbo.DriverPhone AS t
USING (SELECT @driverId AS DriverID, @phone AS Phone) AS s
   ON t.DriverID = s.DriverID
WHEN MATCHED THEN UPDATE SET Phone = s.Phone
WHEN NOT MATCHED THEN INSERT (DriverID, Phone) VALUES (s.DriverID, s.Phone);
```

`g4.json` บันทึกไว้ตรง ๆ ว่า `TXN-17` "ตามตัวอักษรถือว่า MERGE เป็นรูปแบบที่ทำถูกแล้ว" เพราะ MERGE เช็คและเขียนใน
คำสั่งเดียวจริง — แต่ SQL Server ไม่ล็อกแถวที่ยังไม่ commit แน่นพอระหว่างช่วง evaluate เงื่อนไข `ON` ถ้าไม่มี
`WITH (HOLDLOCK)` (หรือ `SERIALIZABLE`) สอง MERGE ที่ชนกันสามารถเห็น `NOT MATCHED` พร้อมกันทั้งคู่ ถ้าตารางไม่มี
unique constraint หนุนหลัง `DriverID` ผลคือแทรกซ้ำสองแถวเงียบ ๆ โดยไม่มี error ใด ๆ

### ก) ตาราง D1

| ID ที่ใกล้ที่สุด | กฎแทนของมันว่าอย่างไร | ทำตามแล้วบั๊กนี้ยังเกิดไหม | เพราะอะไร |
|---|---|---|---|
| `TXN-17` | "ทำการเช็คและเขียนในคำสั่งเดียว หรือใช้ constraint ตัดสิน" | เกิด | MERGE ทำ "เช็คและเขียนในคำสั่งเดียว" ตามตัวอักษรอยู่แล้ว (`ON` แล้วตามด้วย `WHEN MATCHED`/`WHEN NOT MATCHED` ในสเตทเมนต์เดียว) แต่การเป็น "หนึ่งสเตทเมนต์" ไม่ได้แปลว่า atomic ในระดับ storage engine — SQL Server ต้องการ `WITH (HOLDLOCK)`/`SERIALIZABLE` เพิ่มถึงจะล็อกพอกันสอง MERGE ชนกัน วิศวกรที่ทำตามกฎนี้ตรงตัวอักษร (เขียน MERGE เดี่ยว ไม่มี HOLDLOCK) จะยังเจอบั๊กเดิม |
| `TXN-03` | "ใช้ `rowversion`/optimistic lock แล้วแจ้ง conflict ให้ผู้ใช้" | เกิด | กลไกนี้ออกแบบมาสำหรับ round-trip แบบอ่านแล้วเขียนแยกกันที่ฝั่งแอป (SELECT แล้วค่อย UPDATE) MERGE ไม่มีขั้นตอนอ่านแยกให้ผูก rowversion การครอบ optimistic lock รอบคำสั่ง MERGE ไม่ได้แก้ race ที่เกิดอยู่ข้างในสเตทเมนต์เดียวกันเอง |
| `TXN-09` | "เขียน invariant ที่ต้องการให้ชัด แล้วเลือกกลไก (constraint/lock/version) ให้ตรง" | เกิด | เป็นหลักการระดับกระบวนการ ไม่ใช่คำสั่งที่บังคับเจาะจงพอจะกันบั๊กนี้ วิศวกรที่ทำตาม TXN-09 อย่างตรงไปตรงมาจะเขียน invariant ว่า "หนึ่งแถวต่อคนขับ" แล้วเลือก "MERGE คือกลไกของฉันแล้ว" ได้เต็มที่ เพราะ TXN-17 ข้างเคียงก็ยืนยันตามตัวอักษรว่า MERGE ทำถูก — ตัว TXN-09 เองไม่ได้พูดถึง HOLDLOCK/SERIALIZABLE หรือคำเตือนเฉพาะของ MERGE เลย |

ทั้งสาม ID ตอบ "เกิด" — ไม่มีข้อไหนกันบั๊กนี้จริงถ้าอ่านกฎแทนตามตัวอักษร (ซึ่งเป็นมาตรฐานของ repo นี้เอง: "agent
อ่านแล้วทำตามได้ทันทีโดยไม่ต้องตีความ" — CONTRIBUTING บรรทัด 3-4) → **ต้องมีข้อใหม่** ไม่ใช่แค่ไปเสริม `TXN-17`
เพราะกลไกที่ขาดไปคือคำเตือนเฉพาะของ `MERGE`/`HOLDLOCK` ไม่ใช่หลักการ check-then-act ที่ `TXN-17` มีอยู่แล้วก็ยัง
ไม่พอ (ถ้าไปแก้ข้อความ `TXN-17` ให้ยาวขึ้นจนครอบทุก edge case ของทุก syntax แบบนี้ ข้อนั้นจะกลายเป็นย่อหน้าแทนที่จะ
เป็นกฎที่ตรวจได้ ซึ่งขัดกับเกณฑ์ "หนึ่งข้อ = หนึ่งเรื่อง" ของแคตตาล็อกนี้)

### ข) ระดับ P (บันได D2)

1. ทำให้ข้อมูลที่บันทึกแล้วผิด/หาย/ซ้ำโดยระบบไม่ฟ้องเอง หรือรั่ว หรือเงินเคลื่อนผิด? — **ใช่** ถ้า `DriverID` ไม่มี
   unique constraint หนุนหลัง (schema ที่เห็นในเคสไม่ได้ยืนยันว่ามี) สอง MERGE ที่ชนกันจะแทรกสองแถวซ้ำกันสำหรับคนขับ
   คนเดียว **โดยไม่มี exception ใด ๆ โผล่ขึ้นมาเลย** — ระบบไม่ฟ้องเอง ตรงกับเกณฑ์ P1 ข้อแรกเป๊ะ ("ทำให้ข้อมูลที่บันทึก
   แล้วผิด/หาย/ซ้ำ โดยระบบไม่ฟ้องเอง") ตระกูลเดียวกับ `TXN-07` (running number ชนกัน), `TXN-15` (กดปุ่มซ้ำ),
   `TXN-16` (at-least-once ทำให้ซ้ำ) ซึ่งทั้งหมดเป็น P1
2. → หยุดที่ข้อ 1 = **P1**

ย้ำตามกฎทบทวนระดับของ CONTRIBUTING: **ไม่ได้ตั้ง P1 เพราะ "ร้ายแรง"** แต่เพราะ path หนึ่งของบั๊กนี้ (สองแถวซ้ำ
เงียบ ๆ ไม่มี error) คือ "ข้อมูลผิดไปแล้วโดยไม่มีใครรู้" ตรงตัวตามที่ CONTRIBUTING บรรทัด 52 นิยามไว้ ส่วน path ที่
เกิด PK violation ตรง ๆ (กรณีมี unique constraint) เป็นแค่ P2 (พังแบบดัง กู้ได้โดยไม่แตะข้อมูลย้อนหลัง) — ตามกฎ "ถ้า
อาการหนึ่งเข้าหลายข้อ ให้เอาข้อที่เล็กที่สุด (P1 ชนะ P2)" จึงสรุปที่ P1

### ค) แถวใหม่

หมวด: **TXN** (Transaction และ concurrency) ตรงตัวและอยู่ในตระกูลเดียวกับ `TXN-17` ที่ D1 เพิ่งเทียบมา เลขถัดไป:
ข้อสุดท้ายจริงคือ `TXN-18` (นับจากหัวข้อ "## TXN — Transaction และ concurrency (18)") → ID ใหม่ = `TXN-19`

| ID | P | Hell | อาการ | กฎแทน | ใช้กับ |
|---|---|---|---|---|---|
| `TXN-19` | P1 | MERGE ไม่ atomic ในตัวเอง | `MERGE ... WHEN NOT MATCHED THEN INSERT` ที่ไม่มี `WITH (HOLDLOCK)`/`SERIALIZABLE` — สอง request เข้าพร้อมกันเห็น `NOT MATCHED` ทั้งคู่ เกิด PK violation กลางอากาศ หรือถ้าคีย์ที่ join ไม่มี unique constraint คุมไว้ กลายเป็นสองแถวซ้ำกันเงียบ ๆ โดยไม่มี error | ใส่ `WITH (HOLDLOCK)` (หรือรัน transaction ที่ `SERIALIZABLE`) ที่ target table ของทุก `MERGE` ที่คีย์ใน `ON` อาจถูกเขียนพร้อมกันจากหลาย request และต้องมี unique constraint หนุนหลังคีย์นั้นเป็นด่านสุดท้ายเสมอ — ห้ามพึ่งแค่ "MERGE เป็นหนึ่งสเตทเมนต์" เพราะไม่ได้แปลว่า atomic | SQL Server |

`ใช้กับ` เลือก `SQL Server` ไม่ใช่ `RDBMS`: ประโยค `WITH (HOLDLOCK)` และพฤติกรรมล็อกที่บรรยายไว้เป็นของ T-SQL/SQL
Server โดยเฉพาะ (Postgres ไม่มี `MERGE` ก่อน v15 และมี atomic `INSERT ... ON CONFLICT` ที่ปลอดภัยโดยไม่ต้องมี hint
เพิ่ม, MySQL ไม่มี `MERGE`, Oracle มี `MERGE` แต่กลไกล็อกต่างออกไป) ติด `RDBMS` จะพาไปกินเวลาทีมที่ไม่ได้ใช้ SQL
Server เห็นคำแนะนำที่ไม่มีทางใช้ได้จริงกับ engine ของตัวเอง

### ง) ตรวจอัตโนมัติได้ไหม

**partial** — ตรวจได้ระดับ heuristic เท่านั้น regex ตรวจได้แค่ "มีสเตทเมนต์ `MERGE` ที่ไม่มีคำว่า `HOLDLOCK`/
`SERIALIZABLE` อยู่ระหว่าง `MERGE` กับ `;` ปิดสเตทเมนต์" — ตรวจไม่ได้ว่าคีย์นั้นมี unique constraint หนุนหลังไหม และ
ตรวจไม่ได้ว่า MERGE ตัวนั้นเจอ concurrent writer จริงหรือเปล่า (เช่น batch job ที่รันตัวเดียวตอนกลางคืนไม่มีความเสี่ยง
นี้เลย) จึง over-match ได้ในระดับหนึ่ง — เสนอไว้แบบมี `note:`/`allow_comment:` ตามกติกาข้อ over-match ที่ตั้งใจของ
CONTRIBUTING บรรทัด 95

```yaml
- id: TXN-19
  severity: P1
  engine: pcre2       # ใช้ negative lookahead (?!...)
  multiline: true      # MERGE ...; มักคร่อมหลายบรรทัดจนถึง ; ปิดสเตทเมนต์
  pattern: 'MERGE\s+(?:INTO\s+)?(?:(?!;)(?!HOLDLOCK)(?!SERIALIZABLE).)*?;'
  note: >
    จับได้แค่ "ไม่มีคำว่า HOLDLOCK/SERIALIZABLE ในสเตทเมนต์ MERGE" ไม่รู้ว่ามี unique
    constraint หนุนหลังคีย์อยู่แล้วไหม และไม่รู้ว่า MERGE ตัวนี้เจอ concurrent writer จริง
    หรือเปล่า (เช่น batch job รันตัวเดียวไม่เสี่ยง) — ตั้งใจ over-match เพื่อให้คนตรวจ
    ยืนยันเองเป็นจุด ๆ ไป
  allow_comment: 'nohell:ignore TXN-19'
  exclude:
    - '**/node_modules/**'
    - '**/*Test*.sql'
```

ตัวอย่างที่ต้องจับ:

1. Snippet ของเคส `c03-idempotent-upsert` ทั้งก้อน (ด้านบน) — ไม่มี `HOLDLOCK`/`SERIALIZABLE` เลย
2. ```sql
   MERGE dbo.Inventory AS t
   USING (SELECT @sku AS Sku, @qty AS Qty) AS s
      ON t.Sku = s.Sku
   WHEN MATCHED THEN UPDATE SET Qty = t.Qty + s.Qty
   WHEN NOT MATCHED THEN INSERT (Sku, Qty) VALUES (s.Sku, s.Qty);
   ```
   MERGE คนละตารางแต่รูปแบบเดียวกัน — ไม่มี hint ล็อกใด ๆ

ตัวอย่างที่ต้อง **ไม่** จับ:

1. ```sql
   MERGE dbo.DriverPhone WITH (HOLDLOCK) AS t
   USING (SELECT @driverId AS DriverID, @phone AS Phone) AS s
      ON t.DriverID = s.DriverID
   WHEN MATCHED THEN UPDATE SET Phone = s.Phone
   WHEN NOT MATCHED THEN INSERT (DriverID, Phone) VALUES (s.DriverID, s.Phone);
   ```
   มี `WITH (HOLDLOCK)` ตรงตามกฎแทนแล้ว
2. ```sql
   MERGE dbo.Inventory WITH (SERIALIZABLE) AS t
   USING (SELECT @sku AS Sku, @qty AS Qty) AS s
      ON t.Sku = s.Sku
   WHEN MATCHED THEN UPDATE SET Qty = t.Qty + s.Qty
   WHEN NOT MATCHED THEN INSERT (Sku, Qty) VALUES (s.Sku, s.Qty);
   ```
   `SERIALIZABLE` ให้การล็อกเทียบเท่า `HOLDLOCK` — ต้องไม่จับเช่นกัน

**คำเตือนก่อนใส่จริง**: precision ของกฎนี้ต่ำกว่ากฎอื่นในแคตตาล็อกที่เจอ (ตัวอย่าง match ที่ต้องไม่จับมีแค่สองแบบ
ที่ทดสอบไว้ ในสถานการณ์จริงมี MERGE ที่ปลอดภัยโดยไม่ต้องมี hint อีกมาก เช่น MERGE ที่รันใน transaction ที่ตั้ง
`SET TRANSACTION ISOLATION LEVEL SERIALIZABLE` ไว้ที่ระดับ session/connection แทนที่จะเป็น table hint — pattern
นี้จับไม่ได้และจะ false-positive) ก่อนเปิดใช้จริงควรรันกับ SP ที่มี `MERGE` อยู่แล้วในแคตตาล็อกจริงของทีมก่อน แล้ว
ดูอัตรา false positive ว่าทีมรับได้ไหม ถ้าสูงเกินไปให้ตัดกฎนี้ออกและปล่อยเป็นข้อที่ตรวจด้วยรีวิวคนเท่านั้น
(`kind: cmd`/`kind: sql` แบบที่ CONTRIBUTING บรรทัด 117 บอกว่ายังไม่รองรับก็เป็นทางเลือกระยะยาวกว่านี้)

---

## สรุป

| อาการ | ผล D1 | ID ใหม่ | P | ใช้กับ | regex |
|---|---|---|---|---|---|
| 1. OR คร่อมหลายคอลัมน์ | ต้องมีข้อใหม่ | `SQL-32` | P2 | RDBMS | ไม่ควรทำ |
| 2. MERGE ไม่มี HOLDLOCK | ต้องมีข้อใหม่ | `TXN-19` | P1 | SQL Server | partial (มี note+allow_comment) |

RESULT gap1=new gap1_id=SQL-32 gap2=new gap2_id=TXN-19 regex=partial file=docs/proposals/2026-09-02-catalog-gaps.md
