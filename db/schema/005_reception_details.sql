CREATE TABLE [{{schema}}].[reception_details] (
    reception_detail_id BIGINT IDENTITY(1,1) NOT NULL,
    reception_id BIGINT NOT NULL,
    line_no INT NOT NULL,
    product_id BIGINT NOT NULL,
    variety NVARCHAR(120) NULL,
    size NVARCHAR(80) NULL,
    package_type NVARCHAR(80) NULL,
    received_units INT NOT NULL,
    gross_weight_kg DECIMAL(18,3) NOT NULL,
    net_weight_kg DECIMAL(18,3) NOT NULL,
    created_at DATETIME2(0) NOT NULL CONSTRAINT DF_reception_details_created_at DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_reception_details PRIMARY KEY (reception_detail_id),
    CONSTRAINT UQ_reception_details_line UNIQUE (reception_id, line_no),
    CONSTRAINT FK_reception_details_receptions FOREIGN KEY (reception_id)
        REFERENCES [{{schema}}].[receptions] (reception_id),
    CONSTRAINT FK_reception_details_products FOREIGN KEY (product_id)
        REFERENCES [{{schema}}].[products] (product_id),
    CONSTRAINT CK_reception_details_units CHECK (received_units > 0),
    CONSTRAINT CK_reception_details_weights CHECK (gross_weight_kg >= net_weight_kg AND net_weight_kg > 0)
)
