CREATE TABLE [{{schema}}].[shipment_pallets] (
    shipment_pallet_id BIGINT IDENTITY(1,1) NOT NULL,
    shipment_id BIGINT NOT NULL,
    pallet_id BIGINT NOT NULL,
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_shipment_pallets_loaded_at DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_shipment_pallets PRIMARY KEY (shipment_pallet_id),
    CONSTRAINT UQ_shipment_pallets_pallet_id UNIQUE (pallet_id),
    CONSTRAINT UQ_shipment_pallets_pair UNIQUE (shipment_id, pallet_id),
    CONSTRAINT FK_shipment_pallets_shipments FOREIGN KEY (shipment_id)
        REFERENCES [{{schema}}].[shipments] (shipment_id),
    CONSTRAINT FK_shipment_pallets_pallets FOREIGN KEY (pallet_id)
        REFERENCES [{{schema}}].[pallets] (pallet_id)
)
