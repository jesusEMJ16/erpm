CREATE TABLE [{{schema}}].[pallet_boxes] (
    pallet_box_id BIGINT IDENTITY(1,1) NOT NULL,
    pallet_id BIGINT NOT NULL,
    box_id BIGINT NOT NULL,
    position_index INT NOT NULL,
    assigned_at DATETIME2(0) NOT NULL CONSTRAINT DF_pallet_boxes_assigned_at DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT PK_pallet_boxes PRIMARY KEY (pallet_box_id),
    CONSTRAINT UQ_pallet_boxes_box_id UNIQUE (box_id),
    CONSTRAINT UQ_pallet_boxes_position UNIQUE (pallet_id, position_index),
    CONSTRAINT FK_pallet_boxes_pallets FOREIGN KEY (pallet_id)
        REFERENCES [{{schema}}].[pallets] (pallet_id),
    CONSTRAINT FK_pallet_boxes_boxes FOREIGN KEY (box_id)
        REFERENCES [{{schema}}].[boxes] (box_id),
    CONSTRAINT CK_pallet_boxes_position CHECK (position_index > 0)
)
