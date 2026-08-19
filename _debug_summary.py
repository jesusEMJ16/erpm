"""Quick summary check for reception page indicators."""
from app.services.erp_sql import fetch_reception_rows

rows = fetch_reception_rows()
print(f"Rows returned: {len(rows)}")

total_bales = sum(r["bales"] for r in rows)
total_lots = len({r["lot"] for r in rows if r["lot"] and r["lot"] != "SIN LOTE"})
total_pallets = len({r["pallet"] for r in rows if r["pallet"]})
total_weight_kg = sum(r["weight_kg"] for r in rows)

print(f"Total bales: {total_bales}")
print(f"Unique lots: {total_lots}")
print(f"Unique pallets: {total_pallets}")
print(f"Total weight kg: {total_weight_kg:.2f}")

for r in rows:
    print(f"  lot={r['lot']!r} pallet={r['pallet']!r} bales={r['bales']} field={r['field_block']!r}")