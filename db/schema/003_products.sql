CREATE TABLE [{{schema}}].[products] (
    product_id BIGINT IDENTITY(1,1) NOT NULL,
    product_code NVARCHAR(40) NOT NULL,
    product_name NVARCHAR(180) NOT NULL,
    unit_of_measure NVARCHAR(20) NOT NULL,
    is_active BIT NOT NULL CONSTRAINT DF_products_is_active DEFAULT (1),
    created_at DATETIME2(0) NOT NULL CONSTRAINT DF_products_created_at DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_products PRIMARY KEY (product_id),
    CONSTRAINT UQ_products_product_code UNIQUE (product_code)
)
