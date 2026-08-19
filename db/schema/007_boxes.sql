CREATE TABLE [{{schema}}].[boxes] (
    box_id BIGINT IDENTITY(1,1) NOT NULL,
    box_code NVARCHAR(60) NOT NULL,
    lot_id BIGINT NOT NULL,
    employee_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    production_line NVARCHAR(20) NOT NULL,
    presentation NVARCHAR(40) NOT NULL,
    units_per_box INT NOT NULL,
    gross_weight_kg DECIMAL(18,3) NOT NULL,
    net_weight_kg DECIMAL(18,3) NOT NULL,
    produced_at DATETIME2(0) NOT NULL,
    status NVARCHAR(20) NOT NULL CONSTRAINT DF_boxes_status DEFAULT ('CREATED'),
    created_at DATETIME2(0) NOT NULL CONSTRAINT DF_boxes_created_at DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_boxes PRIMARY KEY (box_id),
    CONSTRAINT UQ_boxes_box_code UNIQUE (box_code),
    CONSTRAINT FK_boxes_lots FOREIGN KEY (lot_id)
        REFERENCES [{{schema}}].[lots] (lot_id),
    CONSTRAINT FK_boxes_employees FOREIGN KEY (employee_id)
        REFERENCES [{{schema}}].[employees] (employee_id),
    CONSTRAINT FK_boxes_products FOREIGN KEY (product_id)
        REFERENCES [{{schema}}].[products] (product_id),
    CONSTRAINT CK_boxes_status CHECK (status IN ('CREATED', 'PALLETIZED', 'SHIPPED', 'BLOCKED')),
    CONSTRAINT CK_boxes_units CHECK (units_per_box > 0),
    CONSTRAINT CK_boxes_weights CHECK (gross_weight_kg >= net_weight_kg AND net_weight_kg > 0)
)
