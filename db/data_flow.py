"""ERP entity map and process flow."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntityRelationship:
    parent: str
    child: str
    parent_key: str
    child_key: str
    cardinality: str


ENTITY_RELATIONSHIPS: tuple[EntityRelationship, ...] = (
    EntityRelationship("receptions", "reception_details", "reception_id", "reception_id", "1:N"),
    EntityRelationship("reception_details", "lots", "reception_detail_id", "reception_detail_id", "1:N"),
    EntityRelationship("lots", "boxes", "lot_id", "lot_id", "1:N"),
    EntityRelationship("employees", "boxes", "employee_id", "employee_id", "1:N"),
    EntityRelationship("products", "boxes", "product_id", "product_id", "1:N"),
    EntityRelationship("pallets", "pallet_boxes", "pallet_id", "pallet_id", "1:N"),
    EntityRelationship("boxes", "pallet_boxes", "box_id", "box_id", "1:1"),
    EntityRelationship("shipments", "shipment_pallets", "shipment_id", "shipment_id", "1:N"),
    EntityRelationship("pallets", "shipment_pallets", "pallet_id", "pallet_id", "1:1"),
    EntityRelationship("clients", "shipments", "client_id", "client_id", "1:N"),
)


PROCESS_FLOW: tuple[str, ...] = (
    "Reception header is posted in receptions.",
    "Received product lines are posted in reception_details.",
    "Traceable lots are opened in lots from each reception detail line.",
    "Production registers boxes linked to lot, employee, and product.",
    "Boxes are assigned to physical pallets through pallet_boxes.",
    "Closed pallets are loaded into outbound shipments through shipment_pallets.",
    "Shipment lifecycle is controlled in shipments until closure.",
)


def data_flow_model() -> dict[str, tuple]:
    return {
        "relationships": ENTITY_RELATIONSHIPS,
        "flow": PROCESS_FLOW,
    }
