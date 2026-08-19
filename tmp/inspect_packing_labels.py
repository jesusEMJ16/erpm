import sys
sys.path.insert(0, ".")
from db.connection import get_connection

conn = get_connection()
cur = conn.cursor()
try:
    cur.execute("""
        SELECT TOP 1
            pl.label_id,
            pl.lot_code,
            p.product_name
        FROM erp.packing_labels pl
        LEFT JOIN erp.lots l ON pl.lot_code = l.lot_code
        LEFT JOIN erp.products p ON l.product_id = p.product_id
        WHERE pl.label_id = 1
    """)
    row = cur.fetchone()
    print("Join result for label_id 1:", row)
except Exception as e:
    print("Error:", e)
finally:
    conn.close()
