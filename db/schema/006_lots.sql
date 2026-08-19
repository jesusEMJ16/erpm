CREATE TABLE [{{schema}}].[lots] (
    lot_id BIGINT IDENTITY(1,1) NOT NULL,
    lot_code NVARCHAR(50) NOT NULL,
    reception_detail_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    harvest_date DATE NULL,
    status NVARCHAR(20) NOT NULL CONSTRAINT DF_lots_status DEFAULT ('OPEN'),
    available_units INT NOT NULL,
    available_weight_kg DECIMAL(18,3) NOT NULL,
    created_at DATETIME2(0) NOT NULL CONSTRAINT DF_lots_created_at DEFAULT (SYSUTCDATETIME()),
    updated_at DATETIME2(0) NOT NULL CONSTRAINT DF_lots_updated_at DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_lots PRIMARY KEY (lot_id),
    CONSTRAINT UQ_lots_lot_code UNIQUE (lot_code),
    CONSTRAINT FK_lots_reception_details FOREIGN KEY (reception_detail_id)
        REFERENCES [{{schema}}].[reception_details] (reception_detail_id),
    CONSTRAINT FK_lots_products FOREIGN KEY (product_id)
        REFERENCES [{{schema}}].[products] (product_id),
    CONSTRAINT CK_lots_status CHECK (status IN ('OPEN', 'CLOSED', 'BLOCKED')),
    CONSTRAINT CK_lots_quantities CHECK (available_units >= 0 AND available_weight_kg >= 0)
)
