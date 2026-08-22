/* =============================================================================
   เทมเพลตมาตรฐาน: stored procedure ที่รับ payload เป็น JSON (@iJson)
   ใช้เมื่อผู้เรียกส่ง JSON อยู่แล้ว หรือ payload มีรายการลูก/โครงซ้อน
   ถ้าฟิลด์คงที่และไม่มีรายการลูก ให้ใช้ stored-procedure.sql (พารามิเตอร์แยก) แทน

   JSON ทำให้ "สัญญา" หายไปจากลายเซ็นของ SP
   ทุกบล็อกในไฟล์นี้มีไว้เอาสัญญานั้นกลับคืนมา ห้ามตัดออกเพราะเห็นว่ายาว
   ============================================================================= */

CREATE OR ALTER PROCEDURE Inventory_CreateGoodsReceipt
    -- nohell-allow: SQL-31 — สัญญาของ payload ประกาศไว้ในบล็อก "สัญญา" ด้านล่าง
    -- และบังคับจริงด้วยการปฏิเสธคีย์ที่ไม่รู้จัก ไม่ได้ปล่อยให้เป็น nvarchar(max) ลอยๆ
    @iJson     nvarchar(max),
    @ActionBy  nvarchar(50)
AS
/* -----------------------------------------------------------------------------
   ทำอะไร   : สร้างใบรับเข้าพร้อมรายการสินค้า
   กฎธุรกิจ : BR-014 ใช้อัตราภาษี ณ วันที่เอกสาร · ยืนยันโดยหัวหน้าคลัง 2026-08-20

   รูปแบบ @iJson ที่รับ  ← นี่คือสัญญา ถ้าแก้ที่นี่ไม่ตรงกับโค้ดข้างล่าง ถือว่าบั๊ก
   {
     "requestId":   "uuid",        // บังคับ  ใช้กันการส่งซ้ำ
     "docDate":     "2026-08-22",  // บังคับ  รูปแบบ ISO เท่านั้น
     "warehouseId": 3,             // บังคับ
     "remark":      "ข้อความ",      // ไม่บังคับ  ยาวไม่เกิน 200
     "items": [                    // บังคับ  อย่างน้อย 1 รายการ
       { "productId": 101, "quantity": 12.5 }
     ]
   }
   ** ชื่อคีย์เป็น case-sensitive เสมอ ไม่ขึ้นกับ collation ของฐานข้อมูล **
   "warehouseID" จะไม่ match "$.warehouseId" และจะกลายเป็น NULL เงียบ ๆ

   คืนอะไร  : result set 1 ชุด — (DocNo nvarchar(20), DocId bigint, Duplicated bit)
   ปฏิเสธเมื่อ:
              50000 payload ไม่ใช่ JSON ที่ถูกต้อง
              50001 มีคีย์ที่ไม่รู้จักใน payload
              50002 ฟิลด์บังคับขาดหายหรือเป็น null
              50003 ไม่พบคลังที่ระบุ
              50004 จำนวนต้องมากกว่าศูนย์
              50005 ไม่พบอัตราภาษีที่มีผล ณ วันที่ของเอกสาร
   ผลข้างเคียง: เขียน GoodsReceipt, GoodsReceiptItem, Outbox
   รันซ้ำได้ : ได้ — ส่ง requestId เดิมจะคืนเอกสารเดิม ไม่สร้างซ้ำ
----------------------------------------------------------------------------- */
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    ---------------------------------------------------------------------------
    -- 1. payload เป็น JSON จริงไหม
    ---------------------------------------------------------------------------
    IF @iJson IS NULL OR ISJSON(@iJson) <> 1
        THROW 50000, N'payload ไม่ใช่ JSON ที่ถูกต้อง', 1;

    ---------------------------------------------------------------------------
    -- 2. ปฏิเสธคีย์ที่ไม่รู้จัก  ← บล็อกที่สำคัญที่สุดในไฟล์นี้
    --    ถ้าไม่มีบล็อกนี้ ผู้เรียกพิมพ์ "warehouseID" ผิดตัวเดียว
    --    ค่าจะกลายเป็น NULL แล้วระบบทำงานต่อเหมือนไม่มีอะไรเกิดขึ้น
    --    พารามิเตอร์แยกได้ความปลอดภัยข้อนี้ฟรีจาก engine แต่ JSON ไม่ได้
    ---------------------------------------------------------------------------
    DECLARE @UnknownKey nvarchar(200) =
    (
        -- nohell-allow: SQL-30 — ตรงนี้ต้องไม่มี WITH เพราะกำลังไล่ดูว่ามีคีย์อะไรบ้าง
        --                 ถ้าใส่ WITH จะเห็นเฉพาะคีย์ที่ประกาศ แล้วคีย์แปลกปลอมจะรอดไปเงียบๆ
        SELECT TOP (1) [key]
        FROM   OPENJSON(@iJson)
        WHERE  [key] NOT IN ('requestId','docDate','warehouseId','remark','items')
    );
    IF @UnknownKey IS NOT NULL
        THROW 50001, N'พบคีย์ที่ไม่รู้จักใน payload', 1;   -- ใส่ชื่อคีย์ใน log ไม่ใช่ใน error ที่ส่งกลับ

    ---------------------------------------------------------------------------
    -- 3. แกะส่วนหัว
    --    WITH บังคับ และชนิดต้องตรงกับคอลัมน์ปลายทางเป๊ะ
    --    ถ้าเขียน OPENJSON เปล่า ๆ ทุกค่าจะเป็น nvarchar(4000)
    --    แล้วเกิด implicit conversion ตอน join → index scan ทั้งตาราง (SQL-11)
    ---------------------------------------------------------------------------
    DECLARE @RequestId   uniqueidentifier,
            @DocDate     date,
            @WarehouseId int,
            @Remark      nvarchar(200);

    SELECT @RequestId   = h.requestId,
           @DocDate     = h.docDate,
           @WarehouseId = h.warehouseId,
           @Remark      = h.remark
    FROM OPENJSON(@iJson)
         WITH (
             requestId   uniqueidentifier '$.requestId',
             docDate     date             '$.docDate',
             warehouseId int              '$.warehouseId',
             remark      nvarchar(200)    '$.remark'
         ) AS h;

    ---------------------------------------------------------------------------
    -- 4. ตรวจฟิลด์บังคับ — ตรวจให้ครบทีเดียว ไม่ใช่ตรวจทีละอันแล้วโยน
    ---------------------------------------------------------------------------
    IF @RequestId IS NULL OR @DocDate IS NULL OR @WarehouseId IS NULL
        THROW 50002, N'ฟิลด์บังคับขาดหายหรือรูปแบบไม่ถูกต้อง', 1;

    IF @ActionBy IS NULL OR LTRIM(RTRIM(@ActionBy)) = ''
        THROW 50002, N'ต้องระบุผู้ทำรายการ', 1;

    ---------------------------------------------------------------------------
    -- 5. แกะรายการลูกลง #temp ไม่ใช่ใช้ OPENJSON ตรงใน INSERT
    --    เหตุผล: optimizer เดาจำนวนแถวของ OPENJSON แบบตายตัว
    --    ชุดใหญ่จะได้แผนที่ผิด ส่วน #temp มีสถิติจริงและใส่ index ได้ (SQL-18)
    ---------------------------------------------------------------------------
    CREATE TABLE #Item
    (
        RowNo     int identity(1,1),
        ProductId int            NOT NULL,
        Quantity  decimal(18,4)  NOT NULL
    );

    INSERT #Item (ProductId, Quantity)
    SELECT i.productId, i.quantity
    FROM   OPENJSON(@iJson, '$.items')
           WITH (
               productId int           '$.productId',
               quantity  decimal(18,4) '$.quantity'
           ) AS i;

    IF NOT EXISTS (SELECT 1 FROM #Item)
        THROW 50002, N'ต้องมีรายการสินค้าอย่างน้อยหนึ่งรายการ', 1;

    IF EXISTS (SELECT 1 FROM #Item WHERE Quantity IS NULL OR Quantity <= 0)
        THROW 50004, N'จำนวนต้องมากกว่าศูนย์', 1;

    IF EXISTS (SELECT 1 FROM #Item i
               WHERE NOT EXISTS (SELECT 1 FROM dbo.Product p
                                 WHERE p.ProductId = i.ProductId))
        THROW 50002, N'พบรหัสสินค้าที่ไม่มีในระบบ', 1;

    IF NOT EXISTS (SELECT 1 FROM dbo.Warehouse WHERE WarehouseId = @WarehouseId)
        THROW 50003, N'ไม่พบคลังที่ระบุ', 1;

    ---------------------------------------------------------------------------
    -- 6. กันส่งซ้ำ — ตรวจก่อนเข้า transaction เพื่อตอบเร็วเมื่อเป็นการส่งซ้ำ
    --    แต่ตัวกันจริงคือ unique constraint ข้างล่าง ไม่ใช่การตรวจตรงนี้ (TXN-06)
    ---------------------------------------------------------------------------
    DECLARE @DocId bigint, @DocNo nvarchar(20);

    SELECT @DocId = DocId, @DocNo = DocNo
    FROM   dbo.GoodsReceipt
    WHERE  RequestId = @RequestId;

    IF @DocId IS NOT NULL
    BEGIN
        SELECT DocNo = @DocNo, DocId = @DocId, Duplicated = CAST(1 AS bit);
        RETURN;
    END

    ---------------------------------------------------------------------------
    -- 7. อัตราภาษี ณ วันที่เอกสาร ไม่ใช่วันนี้ (TIME-15)
    ---------------------------------------------------------------------------
    DECLARE @TaxRate decimal(9,4) =
    (
        SELECT TOP (1) Rate FROM dbo.TaxRate
        WHERE ValidFrom <= @DocDate AND (ValidTo IS NULL OR @DocDate < ValidTo)
        ORDER BY ValidFrom DESC
    );
    IF @TaxRate IS NULL
        THROW 50005, N'ไม่พบอัตราภาษีที่มีผล ณ วันที่ของเอกสาร', 1;

    ---------------------------------------------------------------------------
    -- 8. เขียนข้อมูล
    ---------------------------------------------------------------------------
    BEGIN TRY
        BEGIN TRANSACTION;

            EXEC dbo.Document_NextNumber
                 @DocType = 'GR', @DocDate = @DocDate, @DocNo = @DocNo OUTPUT;

            INSERT dbo.GoodsReceipt (RequestId, DocNo, DocDate, WarehouseId,
                                     TaxRate, Remark, Status, CreatedAt, CreatedBy)
            VALUES (@RequestId, @DocNo, @DocDate, @WarehouseId,
                    @TaxRate, @Remark, 'PENDING', SYSDATETIME(), @ActionBy);

            SET @DocId = SCOPE_IDENTITY();

            INSERT dbo.GoodsReceiptItem (DocId, LineNo, ProductId, Quantity)
            SELECT @DocId, RowNo, ProductId, Quantity
            FROM   #Item;

            INSERT dbo.Outbox (EventType, PayloadJson, CreatedAt)
            VALUES ('GoodsReceiptCreated',
                    (SELECT @DocId AS docId, @DocNo AS docNo FOR JSON PATH),
                    SYSDATETIME());

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;

        -- ชนกันที่ unique constraint แปลว่ามีคนส่งพร้อมกัน คืนของเดิมไม่ใช่ error
        IF ERROR_NUMBER() IN (2601, 2627)
        BEGIN
            SELECT @DocId = DocId, @DocNo = DocNo
            FROM   dbo.GoodsReceipt WHERE RequestId = @RequestId;

            IF @DocId IS NOT NULL
            BEGIN
                SELECT DocNo = @DocNo, DocId = @DocId, Duplicated = CAST(1 AS bit);
                RETURN;
            END
        END

        THROW;
    END CATCH;

    SELECT DocNo = @DocNo, DocId = @DocId, Duplicated = CAST(0 AS bit);
END
GO

/* -----------------------------------------------------------------------------
   กฎเหล็กของ SP ที่รับ JSON

   1. ห้ามมีฟิลด์ใน JSON ที่เปลี่ยนพฤติกรรมของ SP
      "action":"create|update|cancel" คือ @ActionType ที่ย้ายไปซ่อนใน payload
      ที่นั่นไม่มี linter ไหนมองเห็น และมันคือ God SP ที่กำลังงอกใหม่ (SQL-29)

   2. OPENJSON ต้องมี WITH เสมอ และชนิดต้องตรงกับคอลัมน์ปลายทาง (SQL-30)

   3. รูปแบบ JSON ต้องเขียนไว้ที่หัวไฟล์ และต้องตรงกับโค้ด — สัญญาไม่ได้อยู่ใน
      ลายเซ็นของ SP อีกต่อไป มันอยู่ในคอมเมนต์นี้ที่เดียว (SQL-31)

   4. ต้องปฏิเสธคีย์ที่ไม่รู้จัก ไม่ใช่เมินเฉย

   5. เพิ่มฟิลด์ใหม่ได้แบบไม่ทำผู้เรียกเดิมพัง — แต่ต้องเพิ่มชื่อลง allowlist
      ในบล็อกที่ 2 ด้วย ไม่งั้นผู้เรียกใหม่จะโดนปฏิเสธ

   6. ห้ามประกอบ JSON path จากค่าที่ผู้ใช้ส่งมา

   7. เก็บ @iJson ดิบไว้ใน log/audit เมื่อเกิด error เพราะเป็นหลักฐานเดียว
      ที่บอกว่าผู้เรียกส่งอะไรมาจริง (mask ข้อมูลอ่อนไหวก่อน)
----------------------------------------------------------------------------- */
