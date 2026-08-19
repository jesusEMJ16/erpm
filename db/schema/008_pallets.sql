CREATE TABLE [{{schema}}].[pallets] (
    pallet_id BIGINT IDENTITY(1,1) NOT NULL,
    pallet_code NVARCHAR(60) NOT NULL,
    assembled_by_employee_id BIGINT NULL,
    built_at DATETIME2(0) NOT NULL CONSTRAINT DF_pallets_built_at DEFAULT (SYSUTCDATETIME()),
    closed_at DATETIME2(0) NULL,
    status NVARCHAR(20) NOT NULL CONSTRAINT DF_pallets_status DEFAULT ('OPEN'),
    lot_code NVARCHAR(50) NULL,
    variety NVARCHAR(120) NULL,
    presentation_override NVARCHAR(60) NULL,
    is_mixed BIT NOT NULL CONSTRAINT DF_pallets_is_mixed DEFAULT (0),
    is_active BIT NOT NULL CONSTRAINT DF_pallets_is_active DEFAULT (1),
    notes NVARCHAR(500) NULL,
    created_at DATETIME2(0) NOT NULL CONSTRAINT DF_pallets_created_at DEFAULT (SYSUTCDATETIME()),
    updated_at DATETIME2(0) NOT NULL CONSTRAINT DF_pallets_updated_at DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_pallets PRIMARY KEY (pallet_id),
    CONSTRAINT UQ_pallets_pallet_code UNIQUE (pallet_code),
    CONSTRAINT FK_pallets_employees FOREIGN KEY (assembled_by_employee_id)
        REFERENCES [{{schema}}].[employees] (employee_id),
    CONSTRAINT CK_pallets_status CHECK (status IN ('OPEN', 'CLOSED', 'LOADED', 'SHIPPED'))
)
