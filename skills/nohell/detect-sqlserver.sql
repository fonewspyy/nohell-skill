/* =============================================================================
   nohell — สคริปต์สแกน SQL Server
   รันแบบอ่านอย่างเดียว บน replica หรือช่วงนอกเวลาทำการ
   แต่ละบล็อกมีชื่อ query ที่ hell-rules.yaml อ้างถึง
   ปรับคำที่ใช้ค้น (Amount/Date/DocNo) ให้ตรงกับ convention ของระบบก่อนใช้
   ============================================================================= */

SET NOCOUNT ON;

/* ---------------------------------------------------------------------------
   [sp_size_ranking]  SQL-01 God SP
   ไล่ SP จากใหญ่ไปเล็ก พร้อมนับสาขาของ action parameter
   --------------------------------------------------------------------------- */
SELECT TOP (50)
    o.name                                                   AS sp_name,
    LEN(m.definition) - LEN(REPLACE(m.definition, CHAR(10), '')) + 1 AS approx_lines,
    LEN(m.definition)                                        AS chars,
    (LEN(m.definition) - LEN(REPLACE(UPPER(m.definition), 'IF @', ''))) / 4   AS if_param_branches,
    (LEN(m.definition) - LEN(REPLACE(UPPER(m.definition), 'INSERT ', ''))) / 7 AS insert_stmts,
    (LEN(m.definition) - LEN(REPLACE(UPPER(m.definition), 'UPDATE ', ''))) / 7 AS update_stmts,
    o.modify_date
FROM sys.sql_modules m
JOIN sys.objects o ON o.object_id = m.object_id
WHERE o.type IN ('P','FN','TF','IF')
ORDER BY LEN(m.definition) DESC;

/* ---------------------------------------------------------------------------
   [duplicate_sp_bodies]  SQL-02 logic ซ้ำข้าม SP — แบบตรงตัว
   normalize ช่องว่างแล้ว hash: จับเคส copy-paste ที่ต่างกันแค่การจัดรูปแบบ
   --------------------------------------------------------------------------- */
WITH norm AS (
    SELECT o.name,
           HASHBYTES('SHA2_256',
               LOWER(REPLACE(REPLACE(REPLACE(REPLACE(
                   CAST(m.definition AS nvarchar(max)),
                   CHAR(13), ''), CHAR(10), ' '), CHAR(9), ' '), '  ', ' '))
           ) AS body_hash
    FROM sys.sql_modules m
    JOIN sys.objects o ON o.object_id = m.object_id
    WHERE o.type = 'P'
)
SELECT body_hash,
       COUNT(*)                              AS sp_count,
       STRING_AGG(name, ', ')                AS duplicate_group
FROM norm
GROUP BY body_hash
HAVING COUNT(*) > 1
ORDER BY COUNT(*) DESC;

/* ---------------------------------------------------------------------------
   [duplicate_sp_dependencies]  SQL-02 logic ซ้ำ — แบบเชิงพฤติกรรม
   SP ที่แตะชุดตารางเดียวกันเป๊ะ มักเป็นงานเดียวกันที่ถูกก๊อปแล้วแก้นิดหน่อย
   --------------------------------------------------------------------------- */
WITH deps AS (
    SELECT o.name AS sp_name,
           STRING_AGG(CONVERT(nvarchar(max), d.referenced_entity_name), '|')
               WITHIN GROUP (ORDER BY d.referenced_entity_name) AS touched
    FROM sys.sql_expression_dependencies d
    JOIN sys.objects o ON o.object_id = d.referencing_id
    WHERE o.type = 'P' AND d.referenced_entity_name IS NOT NULL
    GROUP BY o.name
)
SELECT touched, COUNT(*) AS sp_count, STRING_AGG(sp_name, ', ') AS candidates
FROM deps
GROUP BY touched
HAVING COUNT(*) > 1
ORDER BY COUNT(*) DESC;

/* ---------------------------------------------------------------------------
   [sp_call_graph]  SQL-07 / LEG-12  ใครเรียกใคร และอะไรไม่มีคนเรียกเลย
   --------------------------------------------------------------------------- */
SELECT caller.name AS calling_sp, d.referenced_entity_name AS calls
FROM sys.sql_expression_dependencies d
JOIN sys.objects caller ON caller.object_id = d.referencing_id
JOIN sys.objects callee ON callee.name = d.referenced_entity_name AND callee.type = 'P'
WHERE caller.type = 'P'
ORDER BY caller.name;

SELECT o.name AS sp_never_referenced_in_db, o.modify_date
FROM sys.objects o
WHERE o.type = 'P'
  AND NOT EXISTS (SELECT 1 FROM sys.sql_expression_dependencies d
                  WHERE d.referenced_entity_name = o.name)
ORDER BY o.modify_date;   -- ยังต้องเช็คว่าแอปเรียกตรงหรือไม่ ก่อนสรุปว่าไม่ได้ใช้

/* ---------------------------------------------------------------------------
   [text_smells]  SQL-05 / SQL-06 / SQL-15 / SQL-20 / SQL-04
   สแกนข้อความใน definition รวดเดียว
   --------------------------------------------------------------------------- */
SELECT o.name AS object_name,
       CASE WHEN m.definition LIKE '%NOLOCK%'            THEN 1 ELSE 0 END AS has_nolock,          -- SQL-15 P1
       CASE WHEN m.definition LIKE '%CURSOR%'            THEN 1 ELSE 0 END AS has_cursor,          -- SQL-06 P2
       CASE WHEN m.definition LIKE '%SELECT *%'          THEN 1 ELSE 0 END AS has_select_star,     -- SQL-05 P2
       CASE WHEN m.definition LIKE '%PRINT %'            THEN 1 ELSE 0 END AS has_print,           -- SQL-20 P2
       CASE WHEN m.definition LIKE '%EXEC(%'
              OR m.definition LIKE '%EXECUTE(%'          THEN 1 ELSE 0 END AS has_unsafe_dynamic,  -- SQL-04 P1
       CASE WHEN m.definition LIKE '%WHILE %'            THEN 1 ELSE 0 END AS has_while_loop,      -- SQL-26 P2
       CASE WHEN m.definition LIKE '%@Debug%'            THEN 1 ELSE 0 END AS has_debug_flag       -- SQL-20 P2
FROM sys.sql_modules m
JOIN sys.objects o ON o.object_id = m.object_id
WHERE o.type IN ('P','FN','TF','IF','V','TR')
  AND (m.definition LIKE '%NOLOCK%' OR m.definition LIKE '%CURSOR%'
       OR m.definition LIKE '%SELECT *%' OR m.definition LIKE '%PRINT %'
       OR m.definition LIKE '%EXEC(%' OR m.definition LIKE '%EXECUTE(%'
       OR m.definition LIKE '%WHILE %' OR m.definition LIKE '%@Debug%')
ORDER BY o.name;

/* ---------------------------------------------------------------------------
   [tx_without_xact_abort]  SQL-17 P1
   SP ที่เปิด transaction แต่ไม่มี XACT_ABORT และ/หรือไม่มี TRY-CATCH
   --------------------------------------------------------------------------- */
SELECT o.name AS sp_name,
       CASE WHEN m.definition LIKE '%XACT_ABORT%' THEN 'yes' ELSE 'NO' END AS xact_abort,
       CASE WHEN m.definition LIKE '%BEGIN TRY%'  THEN 'yes' ELSE 'NO' END AS has_try_catch,
       CASE WHEN m.definition LIKE '%XACT_STATE%' THEN 'yes' ELSE 'NO' END AS checks_xact_state
FROM sys.sql_modules m
JOIN sys.objects o ON o.object_id = m.object_id
WHERE o.type = 'P'
  AND m.definition LIKE '%BEGIN TRAN%'
  AND (m.definition NOT LIKE '%XACT_ABORT%' OR m.definition NOT LIKE '%BEGIN TRY%')
ORDER BY o.name;

/* ---------------------------------------------------------------------------
   [scalar_udf_usage]  SQL-08 P1  scalar UDF ที่ถูกเรียกจาก SP/View
   --------------------------------------------------------------------------- */
SELECT f.name AS scalar_udf, COUNT(DISTINCT d.referencing_id) AS used_by_objects
FROM sys.objects f
JOIN sys.sql_expression_dependencies d ON d.referenced_entity_name = f.name
WHERE f.type = 'FN'
GROUP BY f.name
ORDER BY used_by_objects DESC;

/* ---------------------------------------------------------------------------
   [triggers_single_row]  SQL-14 P1
   trigger ที่ไม่ได้อ้าง inserted/deleted แบบ set-based (เดาจากการใช้ scalar assign)
   --------------------------------------------------------------------------- */
SELECT o.name AS trigger_name, OBJECT_NAME(t.parent_id) AS on_table,
       CASE WHEN m.definition LIKE '%SELECT @%FROM inserted%' THEN 'suspicious-single-row' ELSE 'review' END AS note
FROM sys.triggers t
JOIN sys.objects o ON o.object_id = t.object_id
JOIN sys.sql_modules m ON m.object_id = t.object_id
WHERE t.is_disabled = 0
ORDER BY on_table;

/* ---------------------------------------------------------------------------
   [tables_without_pk]  DATA-01 P1
   --------------------------------------------------------------------------- */
SELECT s.name AS [schema], t.name AS table_name, p.rows AS approx_rows
FROM sys.tables t
JOIN sys.schemas s ON s.schema_id = t.schema_id
JOIN sys.partitions p ON p.object_id = t.object_id AND p.index_id IN (0,1)
WHERE NOT EXISTS (SELECT 1 FROM sys.indexes i
                  WHERE i.object_id = t.object_id AND i.is_primary_key = 1)
ORDER BY p.rows DESC;

/* ---------------------------------------------------------------------------
   [float_money_columns]  DATA-04 P1
   --------------------------------------------------------------------------- */
SELECT OBJECT_SCHEMA_NAME(c.object_id) AS [schema], OBJECT_NAME(c.object_id) AS table_name,
       c.name AS column_name, ty.name AS data_type
FROM sys.columns c
JOIN sys.types ty ON ty.user_type_id = c.user_type_id
JOIN sys.tables t ON t.object_id = c.object_id
WHERE ty.name IN ('float','real')
  AND (c.name LIKE '%Amount%' OR c.name LIKE '%Price%' OR c.name LIKE '%Total%'
       OR c.name LIKE '%Cost%'  OR c.name LIKE '%Qty%'   OR c.name LIKE '%Value%'
       OR c.name LIKE '%Vat%'   OR c.name LIKE '%Discount%')
ORDER BY table_name, column_name;

/* ---------------------------------------------------------------------------
   [date_like_string_columns]  DATA-05 / TIME-06 P1
   --------------------------------------------------------------------------- */
SELECT OBJECT_SCHEMA_NAME(c.object_id) AS [schema], OBJECT_NAME(c.object_id) AS table_name,
       c.name AS column_name, ty.name AS data_type, c.max_length
FROM sys.columns c
JOIN sys.types ty ON ty.user_type_id = c.user_type_id
JOIN sys.tables t ON t.object_id = c.object_id
WHERE ty.name IN ('varchar','nvarchar','char','nchar')
  AND (c.name LIKE '%Date%' OR c.name LIKE '%Time%' OR c.name LIKE '%_dt%')
ORDER BY table_name, column_name;

/* [thai_text_in_varchar]  TIME-11 P1 — ข้อความไทยที่ไม่ใช่ nvarchar */
SELECT OBJECT_NAME(c.object_id) AS table_name, c.name AS column_name, ty.name AS data_type
FROM sys.columns c
JOIN sys.types ty ON ty.user_type_id = c.user_type_id
JOIN sys.tables t ON t.object_id = c.object_id
WHERE ty.name IN ('varchar','char','text')
  AND (c.name LIKE '%Name%' OR c.name LIKE '%Desc%' OR c.name LIKE '%Remark%'
       OR c.name LIKE '%Address%' OR c.name LIKE '%Note%')
ORDER BY table_name;

/* ---------------------------------------------------------------------------
   [id_columns_without_fk]  DATA-10 P1
   คอลัมน์ที่ลงท้ายด้วย Id/Code แต่ไม่มี FK ผูก
   --------------------------------------------------------------------------- */
SELECT OBJECT_NAME(c.object_id) AS table_name, c.name AS column_name
FROM sys.columns c
JOIN sys.tables t ON t.object_id = c.object_id
WHERE (c.name LIKE '%Id' OR c.name LIKE '%ID' OR c.name LIKE '%Code')
  AND c.name NOT IN ('Id','ID')
  AND NOT EXISTS (
      SELECT 1 FROM sys.foreign_key_columns fkc
      WHERE fkc.parent_object_id = c.object_id AND fkc.parent_column_id = c.column_id)
ORDER BY table_name, column_name;

/* ---------------------------------------------------------------------------
   [fk_without_index]  DATA-19 P1
   --------------------------------------------------------------------------- */
SELECT OBJECT_NAME(fk.parent_object_id) AS table_name, fk.name AS fk_name,
       COL_NAME(fkc.parent_object_id, fkc.parent_column_id) AS fk_column
FROM sys.foreign_keys fk
JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id = fk.object_id
WHERE NOT EXISTS (
    SELECT 1 FROM sys.index_columns ic
    WHERE ic.object_id = fkc.parent_object_id
      AND ic.column_id = fkc.parent_column_id
      AND ic.key_ordinal = 1)
ORDER BY table_name;

/* ---------------------------------------------------------------------------
   [identity_headroom]  DATA-21 P1  identity ที่ใกล้ล้น
   --------------------------------------------------------------------------- */
SELECT OBJECT_NAME(ic.object_id) AS table_name, ic.name AS column_name, ty.name AS data_type,
       CONVERT(bigint, ic.last_value) AS last_value,
       CASE ty.name WHEN 'int' THEN 2147483647 WHEN 'smallint' THEN 32767
                    WHEN 'tinyint' THEN 255 ELSE 9223372036854775807 END AS max_value,
       CAST(100.0 * CONVERT(float, ISNULL(CONVERT(bigint, ic.last_value), 0)) /
            CASE ty.name WHEN 'int' THEN 2147483647 WHEN 'smallint' THEN 32767
                         WHEN 'tinyint' THEN 255 ELSE 9223372036854775807 END AS decimal(5,2)) AS used_percent
FROM sys.identity_columns ic
JOIN sys.types ty ON ty.user_type_id = ic.user_type_id
JOIN sys.tables t ON t.object_id = ic.object_id
ORDER BY used_percent DESC;

/* ---------------------------------------------------------------------------
   [docno_without_unique]  DATA-25 P1  business key ที่ไม่มี unique constraint
   --------------------------------------------------------------------------- */
SELECT OBJECT_NAME(c.object_id) AS table_name, c.name AS column_name
FROM sys.columns c
JOIN sys.tables t ON t.object_id = c.object_id
WHERE (c.name LIKE '%DocNo%' OR c.name LIKE '%DocumentNo%' OR c.name LIKE '%RefNo%'
       OR c.name LIKE '%InvoiceNo%' OR c.name LIKE '%OrderNo%' OR c.name LIKE '%Barcode%')
  AND NOT EXISTS (
      SELECT 1 FROM sys.index_columns ic
      JOIN sys.indexes i ON i.object_id = ic.object_id AND i.index_id = ic.index_id
      WHERE ic.object_id = c.object_id AND ic.column_id = c.column_id AND i.is_unique = 1)
ORDER BY table_name;

/* ---------------------------------------------------------------------------
   [index_health]  DATA-18 index ที่ไม่ถูกใช้แต่กิน write
   ตัวเลขสะสมตั้งแต่ instance restart ครั้งล่าสุด อย่าตัดสินจากช่วงสั้น
   --------------------------------------------------------------------------- */
SELECT OBJECT_NAME(i.object_id) AS table_name, i.name AS index_name,
       ISNULL(us.user_seeks,0) + ISNULL(us.user_scans,0) + ISNULL(us.user_lookups,0) AS reads,
       ISNULL(us.user_updates,0) AS writes
FROM sys.indexes i
LEFT JOIN sys.dm_db_index_usage_stats us
       ON us.object_id = i.object_id AND us.index_id = i.index_id AND us.database_id = DB_ID()
JOIN sys.tables t ON t.object_id = i.object_id
WHERE i.type_desc = 'NONCLUSTERED' AND i.is_primary_key = 0 AND i.is_unique_constraint = 0
ORDER BY writes - (ISNULL(us.user_seeks,0) + ISNULL(us.user_scans,0) + ISNULL(us.user_lookups,0)) DESC;

/* ---------------------------------------------------------------------------
   [temp_tables_in_prod]  DATA-17
   --------------------------------------------------------------------------- */
SELECT s.name AS [schema], t.name AS table_name, t.create_date, t.modify_date, p.rows
FROM sys.tables t
JOIN sys.schemas s ON s.schema_id = t.schema_id
JOIN sys.partitions p ON p.object_id = t.object_id AND p.index_id IN (0,1)
WHERE t.name LIKE 'tmp%' OR t.name LIKE 'temp%' OR t.name LIKE '%_bak%'
   OR t.name LIKE '%_backup%' OR t.name LIKE '%_old%' OR t.name LIKE '%_test%'
   OR t.name LIKE '%_copy%' OR t.name LIKE '%2023%' OR t.name LIKE '%2024%'
ORDER BY t.create_date;

/* ---------------------------------------------------------------------------
   [rcsi_status]  SQL-15 / TXN-10  พร้อมเลิกใช้ NOLOCK หรือยัง
   --------------------------------------------------------------------------- */
SELECT name, is_read_committed_snapshot_on, snapshot_isolation_state_desc, recovery_model_desc
FROM sys.databases WHERE database_id = DB_ID();

/* ---------------------------------------------------------------------------
   [nohell_metrics]  LEG-15  ตัวเลขสรุปสำหรับ fitness function
   เก็บผลทุกสัปดาห์ แล้วห้ามให้แย่ลง
   --------------------------------------------------------------------------- */
SELECT
    (SELECT COUNT(*) FROM sys.objects WHERE type = 'P')                                    AS sp_count,
    (SELECT SUM(LEN(definition)) FROM sys.sql_modules)                                     AS total_module_chars,
    (SELECT MAX(LEN(definition)) FROM sys.sql_modules)                                     AS max_module_chars,
    (SELECT COUNT(*) FROM sys.sql_modules WHERE definition LIKE '%NOLOCK%')                AS nolock_objects,
    (SELECT COUNT(*) FROM sys.sql_modules WHERE definition LIKE '%CURSOR%')                AS cursor_objects,
    (SELECT COUNT(*) FROM sys.objects o WHERE o.type='P'
       AND NOT EXISTS (SELECT 1 FROM sys.sql_modules m
                       WHERE m.object_id=o.object_id AND m.definition LIKE '%XACT_ABORT%')) AS sp_without_xact_abort,
    (SELECT COUNT(*) FROM sys.tables t WHERE NOT EXISTS
        (SELECT 1 FROM sys.indexes i WHERE i.object_id=t.object_id AND i.is_primary_key=1)) AS tables_without_pk,
    GETDATE()                                                                              AS measured_at;
