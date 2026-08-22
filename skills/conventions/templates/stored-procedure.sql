/* =============================================================================
   เทมเพลตมาตรฐานของ stored procedure ที่ "เขียนข้อมูล"
   คัดลอกไปใช้ทั้งก้อน แล้วแก้เฉพาะส่วนที่ทำเครื่องหมาย <...>
   ทุกบรรทัดที่มีอยู่ในนี้มีเหตุผล ถ้าจะลบต้องเขียนเหตุผลไว้แทนที่
   ============================================================================= */

CREATE OR ALTER PROCEDURE <Domain>_<Verb><Object>
    @<ParamName>   <ชนิดตรงกับคอลัมน์เป๊ะ รวมความยาว>,
    @ActionBy      nvarchar(50)          -- ใครเป็นคนทำ บังคับทุก SP ที่เขียนข้อมูล
AS
/* -----------------------------------------------------------------------------
   ทำอะไร   : <ประโยคเดียวที่คนที่ไม่รู้จักระบบอ่านแล้วเข้าใจ>
   กฎธุรกิจ : <กฎที่ยึด + ใครยืนยัน + เมื่อไหร่>  เช่น BR-014 ยืนยันโดยหัวหน้าคลัง 2026-08-20
   คืนอะไร  : result set 1 ชุด — (DocNo nvarchar(20), DocId bigint)
              ไม่มี result set อื่น ถ้าจะเพิ่มต้องแก้บรรทัดนี้ด้วย
   ปฏิเสธเมื่อ:
              50001 ไม่พบคลังที่ระบุ
              50002 จำนวนต้องมากกว่าศูนย์
              50003 เอกสารนี้ยืนยันไปแล้ว
   ผลข้างเคียง: เขียน GoodsReceipt, GoodsReceiptItem, StockBalance
              ส่ง event ผ่านตาราง Outbox (ไม่ยิงงานภายนอกในนี้)
   รันซ้ำได้ : ได้ — กันซ้ำด้วย UQ_GoodsReceipt_DocNo
   แก้ล่าสุด : <วันที่> <ใคร/agent>
----------------------------------------------------------------------------- */
BEGIN
    SET NOCOUNT ON;      -- ไม่ให้ rowcount รบกวน client และลด round-trip
    SET XACT_ABORT ON;   -- error กลางทางแล้ว transaction ต้องไม่ค้าง (SQL-17)

    ---------------------------------------------------------------------------
    -- 1. ตรวจ input ให้จบก่อน ยังไม่เปิด transaction
    --    ล้มเร็วและไม่ถือ lock ระหว่างตรวจ
    ---------------------------------------------------------------------------
    IF @ActionBy IS NULL OR LTRIM(RTRIM(@ActionBy)) = ''
        THROW 50000, N'ต้องระบุผู้ทำรายการ', 1;

    IF NOT EXISTS (SELECT 1 FROM dbo.Warehouse WHERE WarehouseId = @WarehouseId)
        THROW 50001, N'ไม่พบคลังที่ระบุ', 1;

    IF @Quantity IS NULL OR @Quantity <= 0
        THROW 50002, N'จำนวนต้องมากกว่าศูนย์', 1;

    ---------------------------------------------------------------------------
    -- 2. เตรียมข้อมูลที่อ่านอย่างเดียว ก่อนเปิด transaction
    --    ยิ่งเปิด transaction สั้นเท่าไหร่ยิ่งดี (TXN-02)
    ---------------------------------------------------------------------------
    DECLARE @DocDate     date = CAST(SYSDATETIME() AS date);
    DECLARE @DocNo       nvarchar(20);
    DECLARE @DocId       bigint;

    -- ค่าที่เปลี่ยนตามเวลา ต้องเลือกด้วยวันที่ของเอกสาร ไม่ใช่วันนี้ (TIME-15)
    DECLARE @TaxRate decimal(9,4) =
    (
        SELECT TOP (1) Rate
        FROM   dbo.TaxRate
        WHERE  ValidFrom <= @DocDate
          AND  (ValidTo IS NULL OR @DocDate < ValidTo)
        ORDER BY ValidFrom DESC
    );

    IF @TaxRate IS NULL
        THROW 50004, N'ไม่พบอัตราภาษีที่มีผล ณ วันที่ของเอกสาร', 1;

    ---------------------------------------------------------------------------
    -- 3. งานที่เขียนข้อมูล
    ---------------------------------------------------------------------------
    BEGIN TRY
        BEGIN TRANSACTION;

            -- เลขที่เอกสารต้องมาจากตัวสร้างที่ทนการแข่งขัน
            -- ห้ามใช้ MAX(id)+1 เด็ดขาด (TXN-07)
            EXEC dbo.Document_NextNumber
                 @DocType = 'GR', @DocDate = @DocDate, @DocNo = @DocNo OUTPUT;

            INSERT dbo.GoodsReceipt (DocNo, DocDate, WarehouseId, TaxRate,
                                     Status, CreatedAt, CreatedBy)
            VALUES (@DocNo, @DocDate, @WarehouseId, @TaxRate,
                    'PENDING', SYSDATETIME(), @ActionBy);

            SET @DocId = SCOPE_IDENTITY();

            -- เขียนเป็นชุด ห้ามวนทีละแถว (SQL-26)
            INSERT dbo.GoodsReceiptItem (DocId, ProductId, Quantity)
            SELECT @DocId, s.ProductId, s.Quantity
            FROM   @Items AS s;

            -- ผลข้างเคียงที่ต้องให้ระบบอื่นรู้ ให้ลง outbox ในทรานแซกชันเดียวกัน
            -- ห้ามยิง HTTP หรือส่งเมลในนี้ (TXN-01, INT-08)
            INSERT dbo.Outbox (EventType, PayloadJson, CreatedAt)
            VALUES ('GoodsReceiptCreated',
                    (SELECT @DocId AS docId, @DocNo AS docNo FOR JSON PATH),
                    SYSDATETIME());

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        -- ตรวจสถานะจริงก่อน rollback — อาจถูก abort ไปแล้ว
        IF XACT_STATE() <> 0
            ROLLBACK TRANSACTION;

        -- ห้ามกลืน error ห้าม RETURN 0 (SQL-16)
        -- THROW เปล่า ๆ ส่ง error เดิมพร้อมบรรทัดที่เกิดจริงขึ้นไป
        THROW;
    END CATCH;

    ---------------------------------------------------------------------------
    -- 4. result set ชุดเดียวตามที่ประกาศไว้ที่หัวไฟล์
    --    ระบุคอลัมน์เสมอ ห้าม SELECT * (SQL-05)
    ---------------------------------------------------------------------------
    SELECT DocNo = @DocNo,
           DocId = @DocId;
END
GO

/* -----------------------------------------------------------------------------
   ก่อน merge ตรวจให้ครบ
   [ ] ไม่มี PRINT / SELECT * FROM #tmp / IF @Debug ค้างอยู่          (SQL-20)
   [ ] ไม่มี NOLOCK                                                    (SQL-15)
   [ ] ไม่มีพารามิเตอร์ที่เปลี่ยนความหมายทั้ง SP (@Mode/@ActionType)   (SQL-01)
   [ ] ชนิดพารามิเตอร์ตรงกับคอลัมน์ทุกตัว                              (SQL-11)
   [ ] เงื่อนไข WHERE ใช้ index ได้ ไม่มีฟังก์ชันครอบคอลัมน์            (SQL-10)
   [ ] รันสองครั้งด้วย input เดิม ผลลัพธ์ไม่ซ้ำ                         (TXN-06)
   [ ] มีคนอ่านและอนุมัติก่อนรันนอกเครื่อง dev                          (AI-18)
   [ ] มี SP อื่นที่ทำเรื่องเดียวกันอยู่แล้วหรือไม่ ค้นก่อนตอบ          (SQL-02, SSOT-01)
----------------------------------------------------------------------------- */
