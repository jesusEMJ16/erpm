CREATE TABLE [{{schema}}].[shipments] (
    shipment_id BIGINT IDENTITY(1,1) NOT NULL,
    shipment_code NVARCHAR(50) NOT NULL,
    client_id BIGINT NOT NULL,
    destination_name NVARCHAR(220) NOT NULL,
    scheduled_departure DATETIME2(0) NULL,
    departed_at DATETIME2(0) NULL,
    arrival_eta DATETIME2(0) NULL,
    status NVARCHAR(20) NOT NULL CONSTRAINT DF_shipments_status DEFAULT ('DRAFT'),
    created_at DATETIME2(0) NOT NULL CONSTRAINT DF_shipments_created_at DEFAULT (SYSUTCDATETIME()),
    updated_at DATETIME2(0) NOT NULL CONSTRAINT DF_shipments_updated_at DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_shipments PRIMARY KEY (shipment_id),
    CONSTRAINT UQ_shipments_shipment_code UNIQUE (shipment_code),
    CONSTRAINT FK_shipments_clients FOREIGN KEY (client_id)
        REFERENCES [{{schema}}].[clients] (client_id),
    CONSTRAINT CK_shipments_status CHECK (status IN ('DRAFT', 'READY', 'IN_TRANSIT', 'CLOSED', 'CANCELLED'))
)
