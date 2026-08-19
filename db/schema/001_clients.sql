CREATE TABLE [{{schema}}].[clients] (
    client_id BIGINT IDENTITY(1,1) NOT NULL,
    client_code NVARCHAR(40) NOT NULL,
    legal_name NVARCHAR(200) NOT NULL,
    display_name NVARCHAR(200) NULL,
    tax_id NVARCHAR(40) NULL,
    email NVARCHAR(200) NULL,
    phone NVARCHAR(40) NULL,
    status NVARCHAR(20) NOT NULL CONSTRAINT DF_clients_status DEFAULT ('ACTIVE'),
    created_at DATETIME2(0) NOT NULL CONSTRAINT DF_clients_created_at DEFAULT (SYSUTCDATETIME()),
    updated_at DATETIME2(0) NOT NULL CONSTRAINT DF_clients_updated_at DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_clients PRIMARY KEY (client_id),
    CONSTRAINT UQ_clients_client_code UNIQUE (client_code),
    CONSTRAINT CK_clients_status CHECK (status IN ('ACTIVE', 'INACTIVE'))
)
