CREATE TABLE [{{schema}}].[receptions] (
    reception_id BIGINT IDENTITY(1,1) NOT NULL,
    reception_code NVARCHAR(40) NOT NULL,
    supplier_name NVARCHAR(180) NOT NULL,
    supplier_reference NVARCHAR(60) NULL,
    received_at DATETIME2(0) NOT NULL,
    status NVARCHAR(20) NOT NULL CONSTRAINT DF_receptions_status DEFAULT ('OPEN'),
    notes NVARCHAR(600) NULL,
    created_at DATETIME2(0) NOT NULL CONSTRAINT DF_receptions_created_at DEFAULT (SYSUTCDATETIME()),
    updated_at DATETIME2(0) NOT NULL CONSTRAINT DF_receptions_updated_at DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_receptions PRIMARY KEY (reception_id),
    CONSTRAINT UQ_receptions_reception_code UNIQUE (reception_code),
    CONSTRAINT CK_receptions_status CHECK (status IN ('OPEN', 'POSTED', 'CANCELLED'))
)
