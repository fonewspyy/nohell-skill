# เครื่องมือที่คุ้มจริงสำหรับคนดูแลระบบ enterprise คนเดียว

> คัดมาเฉพาะที่เปลี่ยนวิธีทำงานได้จริง ไม่ใช่ทุกอย่างที่มีในตลาด
> ทุกอันบอกด้วยว่า **ไม่เหมาะกับใคร** เพราะรายการที่มีแต่ข้อดีคือรายการที่เชื่อไม่ได้
> ราคาและสถานะเปลี่ยนบ่อย ตรวจหน้าเว็บทางการก่อนตัดสินใจเสมอ

---

## ลำดับที่ควรทำ

| เมื่อไหร่ | ทำอะไร | ทำไมอันนี้ก่อน |
|---|---|---|
| สัปดาห์นี้ | Serena MCP + repomix + AGENTS.md กระชับ + กฎ "ยืนยันด้วยผลลัพธ์" | ฟรีทั้งหมด และแก้ปัญหาที่เจ็บที่สุดคือ agent ไม่เข้าใจ codebase กับ agent เคลมว่าทำเสร็จ |
| สองสัปดาห์ถัดไป | promptfoo 20-50 เคส + Langfuse + ตรวจ cache hit rate | เริ่มมีตัววัดว่าอะไรถอยหลัง แทนการเดา |
| เดือนหน้า | spec-kit นำร่องหนึ่งฟีเจอร์ + characterization test บน SP หนึ่งตัว + worktree workflow | ของที่ต้องลงแรงเรียนรู้ ควรเริ่มหลังจากมีตัววัดแล้ว |
| ตลอดเวลา | ตรึงเวอร์ชัน MCP/skill, รันในกล่องแยก, ปิดอัปเดตอัตโนมัติ | ความปลอดภัยไม่ใช่เฟส |

---

## 1. Context engineering — ฟรี และคุ้มที่สุด

### Serena MCP — https://github.com/oraios/serena (MIT, ฟรี)
MCP toolkit ที่ใช้ language server ให้ agent เดินโค้ดระดับ symbol ไม่ใช่ระดับไฟล์ — `find_symbol`, `find_referencing_symbols`, `replace_symbol_body` คืนเฉพาะตัวฟังก์ชันที่ต้องการ ไม่ใช่ทั้งไฟล์
- **แทนอะไร**: การยัดไฟล์ทั้งก้อนเข้า context
- **คุ้มตรงไหน**: ประหยัดโทเคนมหาศาลบน codebase ใหญ่ และแก้ปัญหา agent หา caller ไม่เจอ
- **ไม่เหมาะ**: ภาษาที่ language server อ่อน — T-SQL แทบไม่ได้ประโยชน์ ต้องใช้คู่กับเครื่องมือ SQL ข้างล่าง

### repomix — https://github.com/yamadashy/repomix (ฟรี)
แพ็ก repo เป็นไฟล์เดียวสำหรับป้อน LLM นับโทเคนต่อไฟล์ เคารพ `.gitignore` มีตัวกันเผลอส่ง secret และรันออฟไลน์ได้
- **แทนอะไร**: การก๊อปไฟล์ทีละอันเข้าแชต
- **ไม่เหมาะ**: การยัดทั้ง repo ใหญ่เข้าไปจริง ๆ (จะเจอ context rot) ให้ใช้เลือกเฉพาะส่วน

### ตัวเลือกอื่นในกลุ่มเดียวกัน
- **code2prompt** — https://github.com/mufeedvh/code2prompt — CLI ที่ทำ template ได้ยืดหยุ่นกว่า ใส่ git diff ได้
- **files-to-prompt** — https://github.com/simonw/files-to-prompt — เรียบง่ายที่สุด
- **gitingest** — https://github.com/coderamp-labs/gitingest — เปลี่ยน `github.com` เป็น `gitingest.com` ในลิงก์ ได้เนื้อหาทันที เหมาะกับการดูโค้ดคนอื่นเร็ว ๆ
- **ast-grep** — https://github.com/ast-grep/ast-grep-mcp — ค้นและแก้โค้ดตามโครงสร้างไวยากรณ์ ไม่ใช่ตามข้อความ เหมาะกับ refactor แพตเทิร์นซ้ำ ๆ

---

## 2. SQL Server และระบบเก่า

### `sys.sql_expression_dependencies` (ฟรี ในตัว SQL Server)
ฐานของการทำ dependency graph ของ stored procedure เอง ใช้คู่กับ `sys.dm_sql_referencing_entities`
- **ข้อควรระวังใหญ่**: dynamic SQL ไม่ถูกจับ — ถ้า God procedure ประกอบชื่อตารางเป็นสตริง กราฟจะไม่ครบและคุณจะเชื่อผิด
- ใช้ร่วมกับการค้นแบบ "รูปร่างของกฎ" ใน `archaeology/SKILL.md` เพื่อปิดช่องนี้

### Redgate SQL Dependency Tracker — https://www.red-gate.com/products/sql-dependency-tracker/
เชิงพาณิชย์ ทดลองฟรี วาดแผนภาพความสัมพันธ์แบบโต้ตอบได้
- **คุ้มเมื่อ**: ต้องเห็นภาพจริงว่า procedure พันกันแค่ไหน เพื่อไปคุยกับคนอื่น
- **ไม่เหมาะ**: งบศูนย์ — ทำเองด้วย query ข้างบนได้ผลราว 80%

### ทำเอง (ฟรี)
โหลด definition ของ procedure และ view เข้ากราฟ แล้วหาชื่อ object ที่อ้างถึงกัน มีคนทำกับระบบคลังสินค้าเก่าสำเร็จมาแล้ว
- **ข้อควรระวัง**: ชื่อตารางสั้น ๆ จะให้ผลบวกปลอมเยอะ ต้องกรองด้วยมือรอบหนึ่ง

### MCPQL — https://glama.ai/mcp/servers/@hendrickcastro/MCPQL
MCP server ที่ให้ agent เรียก dependency query ได้ตรง ถ้าอยากให้ agent สืบเองโดยไม่ต้องคัดลอกผลมาให้

---

## 3. Eval — ถูกพอสำหรับคนเดียว

### promptfoo (MIT, ฟรี) — https://www.promptfoo.dev
เขียนเทสเป็น YAML รันในเครื่องหรือใน CI เริ่มได้ด้วย `npx promptfoo@latest init`
- **แทนอะไร**: การเปลี่ยน prompt แล้วเดาว่าดีขึ้น
- **ต้นทุนตั้งต้น**: หลักนาที นี่คือเหตุผลที่แนะนำอันนี้ก่อนเพื่อน
- **ไม่เหมาะ**: การดู trace ของ production — คนละงาน

### DeepEval (ฟรี)
สไตล์ pytest มี metric สำเร็จรูปเยอะ เหมาะถ้าอยู่ฝั่ง Python และอยากให้ eval อยู่ในชุดเทสเดิม

### Braintrust
แพลตฟอร์มครบทั้ง trace, eval, cost แต่แผนที่ใช้งานได้จริงแพงสำหรับคนเดียว
- **ไม่เหมาะ**: คนเดียวที่ยังไม่มี eval เลย — เริ่มที่ promptfoo ก่อน แล้วค่อยดูว่าติดตรงไหน

---

## 4. Observability

### Langfuse (MIT, self-host ฟรีด้วย Docker) — https://langfuse.com
trace, ติดตามต้นทุน, จัดเวอร์ชัน prompt, dataset
- **คุ้มตรงไหน**: เห็นว่าแต่ละ session ส่งอะไรไปและจ่ายเท่าไหร่ — ตอบคำถาม "ทำไมเดือนนี้บิลบาน" ได้จริง
- **ไม่เหมาะ**: คนที่ไม่อยากรัน service เพิ่มในเครื่อง (มี cloud แต่ต้องดูราคา)

### Helicone
วางเป็น proxy แก้โค้ดน้อยที่สุด เน้นติดตามต้นทุนแยกตามโมเดลและผู้ใช้ — เร็วที่สุดถ้าปัญหาเดียวคือค่าใช้จ่าย

### OpenLLMetry
ส่ง trace ตามมาตรฐาน OpenTelemetry เข้าระบบที่มีอยู่แล้ว เหมาะถ้ามี observability stack อยู่แล้ว

---

## 5. งานขนานและ orchestration

### git worktree (ในตัว git, ฟรี)
ฐานของการรัน agent หลายตัวพร้อมกัน
- **ข้อควรระวังที่สำคัญที่สุด**: worktree กันไฟล์ชนกันในโฟลเดอร์ แต่ **ไม่กันการชนกันเชิงตรรกะ** agent สองตัวคนละ worktree แก้กฎเดียวกันได้โดยไม่มีอะไรเตือน
- เสริมด้วยการตรวจก่อนปล่อยงานว่าสองงานจะแตะไฟล์เดียวกันไหม

### Claude Code plugins / marketplace — https://code.claude.com/docs/en/discover-plugins
ติดตั้ง skill, command, hook, MCP เป็นชุดเดียว มี directory ทางการที่ https://github.com/anthropics/claude-plugins-official
- **ไม่เหมาะ**: การติดตั้งจาก marketplace ชุมชนโดยไม่อ่านโค้ด — ดู S2 ในเอกสาร myth

---

## 6. มาตรฐานและแหล่งติดตาม

- **AGENTS.md** — https://agents.md — ฟอร์แมตกลางแบบ "README สำหรับ agent" ใช้ข้ามเครื่องมือได้ (Claude Code ยังอ่าน `CLAUDE.md` ด้วย)
- **GitHub Spec Kit** — https://github.com/github/spec-kit — workflow spec-driven ที่ใช้ได้กับ agent หลายตัว ดูรายละเอียดใน `skills/kickoff/SKILL.md`
- **แหล่งที่ควรตาม** (ไม่ใช่คอนเทนต์ผู้เริ่มต้น): Simon Willison · Anthropic Engineering blog · Cognition blog · Chroma Research · seangoedecke.com

---

## เกณฑ์ที่บอกว่าถึงเวลาเปลี่ยนแผน

| สัญญาณ | แปลว่า | ทำอะไร |
|---|---|---|
| eval ตกเมื่อสลับโมเดลใหม่ | รุ่นใหม่ไม่ได้ดีกว่าสำหรับ *งานคุณ* | อย่าอัปเกรด (ขัดกับ M5) |
| cache hit rate ต่ำกว่า 50% | มีของที่เปลี่ยนบ่อยอยู่ข้างหน้า prompt | ย้ายไปท้าย (K2, K3) |
| เวลาจริงต่องานไม่ลดลงหลังวัดก่อนหลัง | agent ไม่ได้ช่วยในงานประเภทนี้ | ลดการใช้กับส่วน legacy ที่คุณเชี่ยว (H1, F4) |
| context เกินราวสามแสนโทเคนบ่อย | เข้าเขต context rot แล้ว | บีบหรือแยก subagent (K7, X2) |
| จำนวนวง C ที่เปิดค้างเพิ่มขึ้น | สร้างของใหม่เร็วกว่าลบของเก่า | หยุดสร้าง ปิดวงก่อน (SSOT-01) |
