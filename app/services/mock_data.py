"""Static mock data used by initial UI pages."""

from __future__ import annotations

from app.services.erp_sql import (
    fetch_dashboard_alert_rows as sql_dashboard_alert_rows,
    fetch_dashboard_client_pallet_rows as sql_dashboard_client_pallet_rows,
    fetch_dashboard_shipments_today_rows as sql_dashboard_shipments_today_rows,
    fetch_dashboard_snapshot as sql_dashboard_snapshot,
    fetch_dashboard_trend_points as sql_dashboard_trend_points,
    fetch_inventory_rows as sql_inventory_rows,
    fetch_production_employees as sql_production_employees,
    fetch_production_rows as sql_production_rows,
    fetch_reception_rows as sql_reception_rows,
    fetch_shipment_manifest_rows as sql_shipment_manifest_rows,
    fetch_shipment_rows as sql_shipment_rows,
)


def dashboard_kpis() -> list[dict]:
    return [
        {"label": "Total SKU", "value": "1,284", "sub": "+3.2% this week", "critical": False},
        {"label": "Low Stock", "value": "34", "sub": "12 need reorder today", "critical": True},
        {"label": "Orders Today", "value": "126", "sub": "Projected close: 340", "critical": False},
        {"label": "Open Tickets", "value": "09", "sub": "Warehouse + POS sync", "critical": False},
    ]


def activity_feed() -> list[tuple[str, str]]:
    return [
        ("Stock audit completed", "5 min ago"),
        ("Inbound transfer WH-A to WH-C", "17 min ago"),
        ("Cycle count scheduled for Zone 4", "42 min ago"),
        ("Price rule updated for category LAB", "1 h ago"),
    ]


def dashboard_production_kpis() -> list[dict]:
    try:
        snapshot = sql_dashboard_snapshot()
        boxes_today = int(snapshot.get("boxes_today", 0) or 0)
        pallets_total = int(snapshot.get("pallets_total", 0) or 0)
        shipments_active = int(snapshot.get("shipments_active", 0) or 0)
        weight_kg = float(snapshot.get("weight_today_kg", 0.0) or 0.0)
        weight_lb = weight_kg * 2.20462

        return [
            {
                "label": "Boxes Produced Today",
                "value": f"{boxes_today:,}",
                "sub": "Produccion real conectada a SQL Server.",
                "trend": [value for _, value in dashboard_trend_points()],
            },
            {
                "label": "Total Pallets",
                "value": f"{pallets_total:,}",
                "sub": "Pallets registrados en base de datos.",
            },
            {
                "label": "Total Shipments Today",
                "value": f"{shipments_active} Active",
                "sub": "Embarques abiertos en este momento.",
            },
            {
                "label": "Total Packed Weight (kg / lbs)",
                "value": f"{weight_kg:,.0f} kg / {weight_lb:,.0f} lbs",
                "sub": "Peso neto acumulado del dia.",
            },
        ]
    except Exception:
        pass

    return [
        {
            "label": "Boxes Produced Today",
            "value": "14,850",
            "sub": "Daily throughput is tracking above baseline.",
            "trend": [2900, 3300, 3550, 3720, 3650, 4100, 4520],
        },
        {
            "label": "Total Pallets",
            "value": "285",
            "sub": "Pallets validated and staged for dispatch.",
        },
        {
            "label": "Total Shipments Today",
            "value": "12 Active",
            "sub": "Open routes currently in execution window.",
        },
        {
            "label": "Total Packed Weight (kg / lbs)",
            "value": "41,200 kg / 90,830 lbs",
            "sub": "More information available in the production module.",
        },
    ]


def dashboard_client_pallet_rows() -> list[tuple[str, int]]:
    try:
        return sql_dashboard_client_pallet_rows()
    except Exception:
        pass

    return [
        ("GreenHarvest Co.", 285),
        ("Sun Valley Produce", 181),
        ("Organico Ltd", 95),
        ("Fresh Picks", 80),
    ]


def dashboard_trend_points() -> list[tuple[str, int]]:
    try:
        return sql_dashboard_trend_points()
    except Exception:
        pass

    return [
        ("00:00", 4500),
        ("03:00", 15000),
        ("09:00", 20000),
        ("12:00", 28000),
        ("15:00", 36000),
        ("18:00", 44850),
    ]


def dashboard_live_summary() -> dict[str, int]:
    try:
        snapshot = sql_dashboard_snapshot()
        active_pallets = int(snapshot.get("pallets_total", 0) or 0)
        shipments_active = int(snapshot.get("shipments_active", 0) or 0)
        return {
            "Active Pallets": active_pallets,
            "Completed Pallets": active_pallets,
            "Shipments in Progress": shipments_active,
        }
    except Exception:
        pass

    return {
        "Active Pallets": 285,
        "Completed Pallets": 285,
        "Shipments in Progress": 12,
    }


def dashboard_alert_rows() -> list[dict]:
    try:
        return sql_dashboard_alert_rows()
    except Exception:
        pass

    return [
        {"label": "Incomplete Pallets", "count": 0},
        {"label": "Boxes Without Label", "count": 0},
        {"label": "Duplicates Detected", "count": 0},
    ]


def dashboard_shipments_today_rows() -> list[dict]:
    try:
        return sql_dashboard_shipments_today_rows()
    except Exception:
        pass

    return [
        {
            "shipment_id": "AS8h-2138D2-D03",
            "client": "GreenHarvest Co.",
            "pallets": 285,
            "boxes": 14850,
            "status": "In Progress",
        },
        {
            "shipment_id": "AS8h-2136D4-D03",
            "client": "Sun Valley Produce",
            "pallets": 285,
            "boxes": 4850,
            "status": "Closed",
        },
        {
            "shipment_id": "AS8h-2138D5-C05",
            "client": "Organico Ltd",
            "pallets": 285,
            "boxes": 1850,
            "status": "Closed",
        },
    ]


def inventory_rows() -> list[dict]:
    try:
        return sql_inventory_rows()
    except Exception:
        pass

    return [
        {
            "id": 1001,
            "name": "Thermal Label Roll",
            "description": "80mm x 60mm",
            "price": 7.40,
            "stock": 220,
            "status": "In Stock",
        },
        {
            "id": 1002,
            "name": "RF Scanner",
            "description": "Industrial hand-held",
            "price": 149.00,
            "stock": 8,
            "status": "Low Stock",
        },
        {
            "id": 1003,
            "name": "Warehouse Tablet",
            "description": "10-inch rugged",
            "price": 389.99,
            "stock": 0,
            "status": "Out of Stock",
        },
        {
            "id": 1004,
            "name": "Receipt Printer",
            "description": "USB + Ethernet",
            "price": 119.50,
            "stock": 34,
            "status": "In Stock",
        },
    ]


def reception_rows() -> list[dict]:
    try:
        return sql_reception_rows()
    except Exception:
        pass

    return [
        {
            "receipt_id": "REC-260531-001",
            "lot": "LOT-BB-26-118",
            "product": "Blueberry",
            "variety": "Emerald",
            "field_block": "Campo Norte / Cuadro 07",
            "bales": 186,
            "weight_kg": 3348.0,
            "size": "12 mm",
            "pallet": "PLT-1042",
        },
        {
            "receipt_id": "REC-260531-002",
            "lot": "LOT-AV-26-044",
            "product": "Avocado",
            "variety": "Hass",
            "field_block": "Campo Sur / Cuadro 03",
            "bales": 124,
            "weight_kg": 2728.0,
            "size": "16 ct",
            "pallet": "PLT-1048",
        },
        {
            "receipt_id": "REC-260531-003",
            "lot": "LOT-GR-26-302",
            "product": "Table Grape",
            "variety": "Sweet Globe",
            "field_block": "Campo Este / Cuadro 11",
            "bales": 210,
            "weight_kg": 3990.0,
            "size": "XL",
            "pallet": "PLT-1055",
        },
        {
            "receipt_id": "REC-260531-004",
            "lot": "LOT-MG-26-090",
            "product": "Mango",
            "variety": "Kent",
            "field_block": "Campo Central / Cuadro 02",
            "bales": 98,
            "weight_kg": 1764.0,
            "size": "10 ct",
            "pallet": "PLT-1061",
        },
        {
            "receipt_id": "REC-260531-005",
            "lot": "LOT-LM-26-227",
            "product": "Lime",
            "variety": "Persian",
            "field_block": "Campo Oeste / Cuadro 09",
            "bales": 156,
            "weight_kg": 2652.0,
            "size": "42 mm",
            "pallet": "PLT-1072",
        },
    ]


def production_employees() -> list[dict]:
    try:
        return sql_production_employees()
    except Exception:
        pass

    return [
        {"code": "123", "name": "Juan Perez", "line": "L07"},
        {"code": "124", "name": "Maria Lopez", "line": "L07"},
        {"code": "125", "name": "Carlos Ruiz", "line": "L07"},
        {"code": "126", "name": "Ana Gomez", "line": "L08"},
        {"code": "127", "name": "Pedro Salas", "line": "L08"},
        {"code": "128", "name": "Lucia Vargas", "line": "L09"},
    ]
    


def production_lot_options() -> list[str]:
    try:
        lots = sorted(
            {
                str(row.get("lot", "")).strip().upper()
                for row in sql_reception_rows(limit=500)
                if str(row.get("lot", "")).strip()
            }
        )
        return ["Sin lote asignado", *lots]
    except Exception:
        pass

    return [
        "Sin lote asignado",
        "LOT-PRD-260531-A",
        "LOT-PRD-260531-B",
        "LOT-PRD-260531-C",
    ]


def production_rows() -> list[dict]:
    try:
        return sql_production_rows()
    except Exception:
        pass

    return [
        {
            "time": "10:45:32",
            "box_id": "123-00045-L07",
            "employee_code": "123",
            "employee_name": "Juan Perez",
            "line": "L07",
            "presentation": "Jumbo",
            "lot": "Sin lote",
            "status": "Registrada",
        },
        {
            "time": "10:45:21",
            "box_id": "123-00044-L07",
            "employee_code": "123",
            "employee_name": "Juan Perez",
            "line": "L07",
            "presentation": "Medium",
            "lot": "Sin lote",
            "status": "Registrada",
        },
        {
            "time": "10:45:10",
            "box_id": "124-00043-L07",
            "employee_code": "124",
            "employee_name": "Maria Lopez",
            "line": "L07",
            "presentation": "Small",
            "lot": "Sin lote",
            "status": "Registrada",
        },
        {
            "time": "10:44:58",
            "box_id": "123-00042-L07",
            "employee_code": "123",
            "employee_name": "Juan Perez",
            "line": "L07",
            "presentation": "Jumbo",
            "lot": "Sin lote",
            "status": "Registrada",
        },
        {
            "time": "10:44:47",
            "box_id": "125-00041-L07",
            "employee_code": "125",
            "employee_name": "Carlos Ruiz",
            "line": "L07",
            "presentation": "Medium",
            "lot": "Sin lote",
            "status": "Registrada",
        },
        {
            "time": "10:44:35",
            "box_id": "123-00040-L07",
            "employee_code": "123",
            "employee_name": "Juan Perez",
            "line": "L07",
            "presentation": "Small",
            "lot": "Sin lote",
            "status": "Registrada",
        },
    ]
    


def shipment_kpis() -> list[dict]:
    try:
        rows = sql_shipment_rows()
        pending_dispatch = sum(1 for row in rows if row.get("status") == "Pending Dispatch")
        in_transit = sum(1 for row in rows if row.get("status") == "In Transit")
        delivered = sum(1 for row in rows if row.get("status") == "Delivered")
        active = pending_dispatch + in_transit

        return [
            {
                "label": "Active Shipments",
                "value": str(active),
                "sub": "Conectado a operaciones reales en SQL Server",
                "critical": False,
            },
            {
                "label": "Pending Dispatch",
                "value": f"{pending_dispatch:02d}",
                "sub": "Pendientes de salida desde embarques",
                "critical": pending_dispatch > 0,
            },
            {
                "label": "In Transit Loads",
                "value": str(in_transit),
                "sub": "Embarques en ruta actualmente",
                "critical": False,
            },
            {
                "label": "Delivered Today",
                "value": f"{delivered:02d}",
                "sub": "Cierres confirmados en base de datos",
                "critical": False,
            },
        ]
    except Exception:
        pass

    return [
        {
            "label": "Active Shipments",
            "value": "18",
            "sub": "6 departures scheduled from collection hubs",
            "critical": False,
        },
        {
            "label": "Pending Dispatch",
            "value": "06",
            "sub": "Awaiting dock authorization and route assignment",
            "critical": True,
        },
        {
            "label": "In Transit Loads",
            "value": "11",
            "sub": "Across 4 transport corridors",
            "critical": False,
        },
        {
            "label": "Delivered Today",
            "value": "07",
            "sub": "Last confirmed POD at 05:58",
            "critical": False,
        },
    ]


def shipment_rows() -> list[dict]:
    try:
        return sql_shipment_rows()
    except Exception:
        pass

    return [
        {
            "id": "SHP-260530-001",
            "crop": "Blueberry",
            "lot": "LOT-BB-26-118",
            "origin": "Finca Los Andes",
            "destination": "Packing Plant Norte",
            "departure": "05:40",
            "eta": "08:15",
            "status": "In Transit",
        },
        {
            "id": "SHP-260530-002",
            "crop": "Avocado",
            "lot": "LOT-AV-26-044",
            "origin": "Valle Verde Cooperative",
            "destination": "Cold Hub Sur",
            "departure": "06:10",
            "eta": "09:05",
            "status": "Pending Dispatch",
        },
        {
            "id": "SHP-260529-014",
            "crop": "Table Grape",
            "lot": "LOT-GR-26-302",
            "origin": "Santa Ines Farm",
            "destination": "Export Port West",
            "departure": "03:20",
            "eta": "11:45",
            "status": "Alert",
        },
        {
            "id": "SHP-260529-011",
            "crop": "Mango",
            "lot": "LOT-MG-26-090",
            "origin": "Agro Sol Estate",
            "destination": "Retail DC Capital",
            "departure": "00:50",
            "eta": "06:30",
            "status": "Delivered",
        },
        {
            "id": "SHP-260530-006",
            "crop": "Lime",
            "lot": "LOT-LM-26-227",
            "origin": "Rio Claro Orchards",
            "destination": "Juice Processor East",
            "departure": "07:00",
            "eta": "10:10",
            "status": "In Transit",
        },
    ]


def shipment_manifest_rows() -> list[dict]:
    try:
        return sql_shipment_manifest_rows()
    except Exception:
        pass

    return [
        {
            "manifest_id": "EMB-260530-001",
            "shipment_id": "SHP-260530-001",
            "carrier": "AgroTrans Norte",
            "driver": "Luis Cardenas",
            "vehicle": "AG-241",
            "doc_type": "Outbound",
            "issued_at": "05:22",
            "status": "Issued",
        },
        {
            "manifest_id": "EMB-260530-002",
            "shipment_id": "SHP-260529-014",
            "carrier": "FrioAndes Logistics",
            "driver": "Marta Rios",
            "vehicle": "FR-908",
            "doc_type": "Export",
            "issued_at": "03:05",
            "status": "Alert",
        },
        {
            "manifest_id": "EMB-260529-011",
            "shipment_id": "SHP-260529-011",
            "carrier": "RutaCampo Express",
            "driver": "Pedro Villanueva",
            "vehicle": "RC-514",
            "doc_type": "Outbound",
            "issued_at": "00:44",
            "status": "Signed",
        },
    ]


def traceability_kpis() -> list[dict]:
    try:
        rows = sql_shipment_rows()
        monitored_lots = len({str(row.get("lot", "")).strip() for row in rows if str(row.get("lot", "")).strip()})
        open_alerts = sum(1 for row in rows if row.get("status") == "Alert")
        validated_chain = 100.0
        if rows:
            validated_chain = max(0.0, 100.0 - ((open_alerts / len(rows)) * 100.0))
        pending_audits = sum(1 for row in rows if row.get("status") == "Pending Dispatch")

        return [
            {
                "label": "Monitored Lots",
                "value": str(monitored_lots),
                "sub": "Lotes enlazados a embarques registrados",
                "critical": False,
            },
            {
                "label": "Open Alerts",
                "value": f"{open_alerts:02d}",
                "sub": "Alertas operativas detectadas",
                "critical": open_alerts > 0,
            },
            {
                "label": "Validated Chain",
                "value": f"{validated_chain:.1f}%",
                "sub": "Cobertura de trazabilidad sobre embarques",
                "critical": False,
            },
            {
                "label": "Pending Audits",
                "value": f"{pending_audits:02d}",
                "sub": "Pendientes de confirmar antes de cierre",
                "critical": False,
            },
        ]
    except Exception:
        pass

    return [
        {
            "label": "Monitored Lots",
            "value": "42",
            "sub": "Linked to active and closed shipments",
            "critical": False,
        },
        {
            "label": "Open Alerts",
            "value": "03",
            "sub": "Temperature and documentation deviations",
            "critical": True,
        },
        {
            "label": "Validated Chain",
            "value": "91.3%",
            "sub": "Loads with complete farm-to-client checkpoints",
            "critical": False,
        },
        {
            "label": "Pending Audits",
            "value": "05",
            "sub": "Require supervisor sign-off before closure",
            "critical": False,
        },
    ]


def traceability_rows() -> list[dict]:
    try:
        rows = sql_shipment_rows()
        payloads: list[dict] = []
        for row in rows:
            status = str(row.get("status", "")).strip()
            if status == "Delivered":
                trace_state = "Closed"
                trace_score = 100
                last_stage = "Delivered"
                cold_chain = "Stable"
                docs = "Archived"
            elif status == "In Transit":
                trace_state = "Chain Verified"
                trace_score = 92
                last_stage = "Transit"
                cold_chain = "Stable"
                docs = "Complete"
            elif status == "Alert":
                trace_state = "Temp Drift"
                trace_score = 61
                last_stage = "Corrective Action"
                cold_chain = "Recovered"
                docs = "In Progress"
            else:
                trace_state = "Docs Pending"
                trace_score = 73
                last_stage = "Pre-Dispatch Audit"
                cold_chain = "Awaiting Dispatch"
                docs = "Missing Form"

            payloads.append(
                {
                    "shipment_id": str(row.get("id", "")).strip(),
                    "crop": str(row.get("crop", "")).strip() or "N/D",
                    "lot": str(row.get("lot", "")).strip() or "Sin lote",
                    "trace_state": trace_state,
                    "trace_score": trace_score,
                    "last_stage": last_stage,
                    "last_location": str(row.get("destination", "")).strip() or "Ruta activa",
                    "cold_chain": cold_chain,
                    "docs": docs,
                }
            )
        return payloads
    except Exception:
        pass

    return [
        {
            "shipment_id": "SHP-260530-001",
            "crop": "Blueberry",
            "lot": "LOT-BB-26-118",
            "trace_state": "Chain Verified",
            "trace_score": 98,
            "last_stage": "Road Checkpoint",
            "last_location": "Route N-08",
            "cold_chain": "Stable",
            "docs": "Complete",
        },
        {
            "shipment_id": "SHP-260530-002",
            "crop": "Avocado",
            "lot": "LOT-AV-26-044",
            "trace_state": "Docs Pending",
            "trace_score": 73,
            "last_stage": "Pre-Dispatch Audit",
            "last_location": "Load Bay B",
            "cold_chain": "Awaiting Dispatch",
            "docs": "Missing Form",
        },
        {
            "shipment_id": "SHP-260529-014",
            "crop": "Table Grape",
            "lot": "LOT-GR-26-302",
            "trace_state": "Temp Drift",
            "trace_score": 61,
            "last_stage": "Corrective Action",
            "last_location": "Mobile Unit",
            "cold_chain": "Recovered",
            "docs": "Complete",
        },
        {
            "shipment_id": "SHP-260529-011",
            "crop": "Mango",
            "lot": "LOT-MG-26-090",
            "trace_state": "Closed",
            "trace_score": 100,
            "last_stage": "Delivered",
            "last_location": "Retail DC Capital",
            "cold_chain": "Stable",
            "docs": "Archived",
        },
        {
            "shipment_id": "SHP-260530-006",
            "crop": "Lime",
            "lot": "LOT-LM-26-227",
            "trace_state": "Checkpoint Pending",
            "trace_score": 84,
            "last_stage": "Transit",
            "last_location": "Route E-12",
            "cold_chain": "Stable",
            "docs": "In Progress",
        },
    ]


def traceability_events(shipment_id: str) -> list[dict]:
    events = {
        "SHP-260530-001": [
            {
                "time": "04:58",
                "stage": "Lot Sealed",
                "location": "Finca Los Andes",
                "details": "Packaging line P2 sealed and QR tagged",
            },
            {
                "time": "05:40",
                "stage": "Truck Departed",
                "location": "Finca Los Andes",
                "details": "Vehicle AG-241 started route with 2.4 C cold setpoint",
            },
            {
                "time": "06:45",
                "stage": "Road Checkpoint",
                "location": "Route N-08",
                "details": "IoT telemetry verified: temp stable at 2.6 C",
            },
        ],
        "SHP-260530-002": [
            {
                "time": "05:20",
                "stage": "Harvest Closure",
                "location": "Valle Verde Cooperative",
                "details": "Field team closed lot with maturity cert attached",
            },
            {
                "time": "05:54",
                "stage": "Pre-Dispatch Audit",
                "location": "Load Bay B",
                "details": "Missing sanitary form in shipment record",
            },
        ],
        "SHP-260529-014": [
            {
                "time": "02:50",
                "stage": "Container Loaded",
                "location": "Santa Ines Farm",
                "details": "Sensor suite activated and linked to lot LOT-GR-26-302",
            },
            {
                "time": "05:15",
                "stage": "Cold Alert",
                "location": "Highway Segment 3",
                "details": "Temp rose to 8.1 C for 17 min, auto-alert raised",
            },
            {
                "time": "06:02",
                "stage": "Corrective Action",
                "location": "Mobile Unit",
                "details": "Driver adjusted cooling unit, temp restored to 4.0 C",
            },
        ],
        "SHP-260529-011": [
            {
                "time": "00:38",
                "stage": "Dispatch",
                "location": "Agro Sol Estate",
                "details": "Quality seal validated and route signed",
            },
            {
                "time": "05:58",
                "stage": "Delivered",
                "location": "Retail DC Capital",
                "details": "Proof-of-delivery uploaded with zero incidents",
            },
        ],
        "SHP-260530-006": [
            {
                "time": "06:32",
                "stage": "Loaded",
                "location": "Rio Claro Orchards",
                "details": "Pallet and lot tags synchronized to shipment",
            },
            {
                "time": "07:58",
                "stage": "Transit",
                "location": "Route E-12",
                "details": "Telemetry alive, next checkpoint pending",
            },
        ],
    }
    return events.get(shipment_id, [])


def shipment_trace_events(shipment_id: str) -> list[dict]:
    return traceability_events(shipment_id)


def traceability_module_data() -> dict[str, dict]:
    box_rows: list[dict] = []
    box_weights = [11.34, 11.28, 11.40, 11.30]
    for offset in range(24):
        sequence = 45 + offset
        weight = box_weights[offset % len(box_weights)] + (offset // 4) * 0.02
        box_rows.append(
            {
                "codigo": f"123-{sequence:05d}-L07",
                "producto": "Esparrago",
                "variedad": "California",
                "presentacion": "Jumbo",
                "peso_neto": f"{11} Lb",
                "estado": "EMBARCADA" if offset < 20 else "PENDIENTE",
            }
        )

    pallet_rows: list[dict] = []
    for offset in range(24):
        sequence = 910 + offset
        pallet_rows.append(
            {
                "codigo": f"BX-{sequence:05d}-PLT21811",
                "producto": "Esparrago",
                "variedad": "California",
                "presentacion": "Jumbo",
                "peso_neto": f"{449.056} Kg",
                "estado": "EN TRANSITO" if offset < 18 else "PENDIENTE REVISION",
            }
        )

    lot_rows: list[dict] = []
    for offset in range(24):
        sequence = 331 + offset
        lot_rows.append(
            {
                "codigo": f"L24-{sequence:05d}-CJA",
                "producto": "Esparrago",
                "variedad": "California",
                "presentacion": "Jumbo",
                "peso_neto": f"308,600 Lb",
                "estado": "VALIDADA" if offset < 16 else "ALERTA TEMPERATURA",
            }
        )

    return {
        "boxes": {
            "search_title": "Buscar Caja",
            "search_hint": "Escanear o ingresar codigo de caja",
            "search_placeholder": "Escanear codigo de caja...",
            "summary_title": "Informacion de la Caja",
            "details_title": "Informacion de la Caja",
            "relationship_title": "Informacion del Pallet y Embarque",
            "code_label": "Codigo de caja:",
            "focus_code": "123-00045-L07",
            "focus_status": "EMBARCADA",
            "focus_created": "26/05/2025 08:15",
            "focus_line": "Linea 2",
            "focus_employee": "123 - Juan Perez",
            "details_pairs": [
                ("Producto", "Esparrago"),
                ("Variedad", "California"),
                ("Presentacion", "Jumbo"),
                ("Peso neto", "11.34 Lb"),
                ("Cliente", "Fresh Asparagus Inc."),
                ("Codigo VOIS", "USA12345678"),
                ("Lote / Cosecha", "2025-05-24-01"),
                ("Fecha de empaque", "26/05/2025"),
            ],
            "left_block_title": "Pallet",
            "left_block_rows": [
                ("Codigo pallet", "PLT-21708"),
                ("Estado", "EMBARCADO"),
                ("Fecha de armado", "26/05/2025 08:40"),
                ("Total cajas", "90"),
            ],
            "right_block_title": "Embarque",
            "right_block_rows": [
                ("Folio embarque", "EMB-250527-01"),
                ("Cliente", "Fresh Asparagus Inc."),
                ("Destino", "Dallas, TX - USA"),
                ("Fecha embarque", "27/05/2025"),
            ],
            "table_title": "Cajas del Pallet PLT-21708",
            "table_rows": box_rows,
            "timeline": [
                {
                    "icon": "C",
                    "tone": "green",
                    "title": "Caja creada",
                    "time": "26/05/2025 08:15:23",
                    "line1": "Empleado: 123 - Juan Perez",
                    "line2": "Linea: Linea 2",
                },
                {
                    "icon": "E",
                    "tone": "blue",
                    "title": "Etiqueta impresa",
                    "time": "26/05/2025 08:16:02",
                    "line1": "Impresora: Zebra ZT410",
                    "line2": "Usuario: Juan Perez",
                },
                {
                    "icon": "P",
                    "tone": "amber",
                    "title": "Caja agregada a pallet",
                    "time": "26/05/2025 08:45:10",
                    "line1": "Pallet: PLT-21708",
                    "line2": "Usuario: Maria Lopez",
                },
                {
                    "icon": "S",
                    "tone": "green",
                    "title": "Pallet embarcado",
                    "time": "27/05/2025 10:30:45",
                    "line1": "Embarque: EMB-250527-01",
                    "line2": "Cliente: Fresh Asparagus Inc.",
                },
            ],
            "documents": [
                {"name": "Etiqueta de caja"},
                {"name": "Etiqueta de pallet"},
                {"name": "Documento de embarque"},
            ],
        },
        "pallets": {
            "search_title": "Buscar Pallet",
            "search_hint": "Escanear o ingresar codigo de pallet",
            "search_placeholder": "Escanear codigo de pallet...",
            "summary_title": "Informacion del Pallet",
            "details_title": "Informacion del Pallet",
            "relationship_title": "Informacion del Embarque y Ruta",
            "code_label": "Codigo de pallet:",
            "focus_code": "PLT-21811",
            "focus_status": "EN TRANSITO",
            "focus_created": "27/05/2025 06:05",
            "focus_line": "Anden 4",
            "focus_employee": "Supervisor - Ana Gomez",
            "details_pairs": [
                ("Producto", "Esparrago"),
                ("Variedad", "California"),
                ("Presentacion", "Jumbo"),
                ("Peso bruto", "1,245.30 Lb"),
                ("Cliente", "Fresh Asparagus Inc."),
                ("Codigo VOIS", "USA85320111"),
                ("Lote principal", "LOT-2025-24-12"),
                ("Fecha de armado", "27/05/2025"),
            ],
            "left_block_title": "Pallet",
            "left_block_rows": [
                ("Codigo pallet", "PLT-21811"),
                ("Estado", "EN TRANSITO"),
                ("Cajas asociadas", "90"),
                ("Ubicacion", "Ruta N-12"),
            ],
            "right_block_title": "Embarque",
            "right_block_rows": [
                ("Folio embarque", "EMB-250527-01"),
                ("Cliente", "Fresh Asparagus Inc."),
                ("Destino", "Dallas, TX - USA"),
                ("Hora salida", "27/05/2025 06:30"),
            ],
            "table_title": "Cajas del Pallet PLT-21811",
            "table_rows": pallet_rows,
            "timeline": [
                {
                    "icon": "A",
                    "tone": "blue",
                    "title": "Pallet armado",
                    "time": "27/05/2025 06:05:41",
                    "line1": "Anden: 4",
                    "line2": "Supervisor: Ana Gomez",
                },
                {
                    "icon": "V",
                    "tone": "green",
                    "title": "Verificacion de calidad",
                    "time": "27/05/2025 06:18:20",
                    "line1": "Inspector: Pedro Salas",
                    "line2": "Resultado: Sin observaciones",
                },
                {
                    "icon": "R",
                    "tone": "blue",
                    "title": "Salida de ruta",
                    "time": "27/05/2025 06:31:04",
                    "line1": "Unidad: AG-441",
                    "line2": "Ruta: N-12",
                },
                {
                    "icon": "T",
                    "tone": "amber",
                    "title": "Checkpoint pendiente",
                    "time": "27/05/2025 08:05:58",
                    "line1": "Ultimo ping: Segmento 2",
                    "line2": "Accion: Esperando confirmacion",
                },
            ],
            "documents": [
                {"name": "Checklist de carga"},
                {"name": "Bitacora de temperatura"},
                {"name": "Guia de transporte"},
            ],
        },
        "lots": {
            "search_title": "Buscar Lote",
            "search_hint": "Escanear o ingresar codigo de lote",
            "search_placeholder": "Escanear codigo de lote...",
            "summary_title": "Informacion del Lote",
            "details_title": "Informacion del Lote",
            "relationship_title": "Informacion del Lote y Embarque",
            "code_label": "Codigo de lote:",
            "focus_code": "LOT-2025-24-01",
            "focus_status": "VALIDADA",
            "focus_created": "24/05/2025 07:10",
            "focus_line": "Campo Norte / Cuadro 7",
            "focus_employee": "Jefe de Campo - Carlos Ruiz",
            "details_pairs": [
                ("Producto", "Esparrago"),
                ("Variedad", "California"),
                ("Campo / Cuadro", "Norte / 7"),
                ("Peso estimado", "26,400 Lb"),
                ("Cliente destino", "Fresh Asparagus Inc."),
                ("Codigo VOIS", "USA12345678"),
                ("Fecha de corte", "24/05/2025"),
                ("Fecha de empaque", "26/05/2025"),
            ],
            "left_block_title": "Lote",
            "left_block_rows": [
                ("Codigo lote", "LOT-2025-24-01"),
                ("Estado", "VALIDADA"),
                ("Cajas procesadas", "28,054 - 11 Lb"),
                ("Merma", "1.5%"),
            ],
            "right_block_title": "Embarque",
            "right_block_rows": [
                ("Folio embarque", "EMB-250527-01"),
                ("Cliente", "Fresh Asparagus Inc."),
                ("Destino", "Dallas, TX - USA"),
                ("Fecha cierre", "27/05/2025"),
            ],
            "table_title": "Cajas del Lote LOT-2025-24-01",
            "table_rows": lot_rows,
            "timeline": [
                {
                    "icon": "L",
                    "tone": "green",
                    "title": "Lote abierto",
                    "time": "24/05/2025 07:10:12",
                    "line1": "Campo: Norte / Cuadro 7",
                    "line2": "Responsable: Carlos Ruiz",
                },
                {
                    "icon": "Q",
                    "tone": "green",
                    "title": "Control de calidad aprobado",
                    "time": "24/05/2025 11:22:44",
                    "line1": "Muestreo: 10 de 10",
                    "line2": "Resultado: Conforme",
                },
                {
                    "icon": "T",
                    "tone": "red",
                    "title": "Alerta de temperatura",
                    "time": "26/05/2025 05:41:19",
                    "line1": "Lectura maxima: 8.1 C",
                    "line2": "Accion correctiva aplicada",
                },
                {
                    "icon": "C",
                    "tone": "amber",
                    "title": "Cierre en revision",
                    "time": "27/05/2025 12:08:03",
                    "line1": "Auditoria documental pendiente",
                    "line2": "Supervisor asignado: Maria Lopez",
                },
            ],
            "documents": [
                {"name": "Certificado de cosecha"},
                {"name": "Reporte de calidad"},
                {"name": "Resumen de lote"},
            ],
        },
    }
