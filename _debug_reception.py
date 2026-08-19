"""Debug why reception shows 0 when reopening the app."""
from app.services.erp_sql import fetch_reception_rows
from app.services.mock_data import reception_rows

print("=== Direct SQL fetch_reception_rows ===")
try:
    rows = fetch_reception_rows()
    print(f"Rows returned: {len(rows)}")
    for r in rows:
        print(f"  lot={r.get('lot')!r}, product={r.get('product')!r}, bales={r.get('bales')!r}, pallet={r.get('pallet')!r}")
except Exception as e:
    print(f"ERROR: {e}")

print("\n=== Via mock_data.reception_rows (with fallback) ===")
try:
    rows = reception_rows()
    print(f"Rows returned: {len(rows)}")
    for r in rows:
        print(f"  lot={r.get('lot')!r}, product={r.get('product')!r}, bales={r.get('bales')!r}")
except Exception as e:
    print(f"ERROR: {e}")

print("\n=== Data from reception_details JOIN receptions ===")
from db.connection import get_connection
conn = get_connection()
c = conn.cursor()
c.execute("""
SELECT rd.reception_detail_id, rd.variety, rd.received_units, rd.net_weight_kg, rd.size,
       r.reception_code, r.supplier_name, r.received_at,
       p.product_name,
       CAST(r.received_at AS date) as received_date, CAST(GETDATE() AS date) as today
FROM erp.reception_details rd
INNER JOIN erp.receptions r ON r.reception_id = rd.reception_id
INNER JOIN erp.products p ON p.product_id = rd.product_id
ORDER BY rd.reception_detail_id DESC
""")
cols = [col[0] for col in c.description]
for r in c.fetchall():
    print(dict(zip(cols, r)))
conn.close()