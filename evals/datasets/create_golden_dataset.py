"""Creation script for the synthetic e-commerce Golden Dataset v1 in DuckDB (T-006)."""

from pathlib import Path
import duckdb


def create_golden_ecommerce_dataset(db_path: Path) -> None:
    """Generate deterministic e-commerce tables with known ground-truth metrics."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))

    # Clean existing
    con.execute("DROP TABLE IF EXISTS order_items;")
    con.execute("DROP TABLE IF EXISTS orders;")
    con.execute("DROP TABLE IF EXISTS customers;")
    con.execute("DROP TABLE IF EXISTS products;")

    # Customers
    con.execute("""
        CREATE TABLE customers AS
        SELECT 
            id AS customer_id,
            'Customer ' || id AS name,
            CASE WHEN id % 2 = 0 THEN 'Enterprise' ELSE 'SMB' END AS segment,
            CASE WHEN id % 3 = 0 THEN 'US' WHEN id % 3 = 1 THEN 'EU' ELSE 'APAC' END AS region,
            DATE '2025-01-01' + INTERVAL (id * 2) DAY AS created_at
        FROM range(1, 51) t(id);
    """)

    # Products
    con.execute("""
        CREATE TABLE products AS
        SELECT 
            id AS product_id,
            'Product ' || id AS title,
            CASE WHEN id % 3 = 0 THEN 'Software' WHEN id % 3 = 1 THEN 'Hardware' ELSE 'Services' END AS category,
            ROUND(20.0 + (id * 15.5), 2) AS unit_price
        FROM range(1, 21) t(id);
    """)

    # Orders (deterministic sequence across 2025-Q1 to 2025-Q4)
    con.execute("""
        CREATE TABLE orders AS
        SELECT 
            id AS order_id,
            1 + (id % 50) AS customer_id,
            DATE '2025-01-10' + INTERVAL (id * 3) DAY AS order_date,
            CASE 
                WHEN id % 15 = 0 THEN 'cancelled'
                WHEN id % 10 = 0 THEN 'refunded'
                ELSE 'completed'
            END AS status,
            CASE WHEN id % 4 = 0 THEN 25.0 ELSE 0.0 END AS discount_amount
        FROM range(1, 101) t(id);
    """)

    # Order Items
    con.execute("""
        CREATE TABLE order_items AS
        SELECT 
            row_number() OVER () AS item_id,
            o.order_id,
            1 + ((o.order_id + item_idx) % 20) AS product_id,
            1 + (item_idx % 3) AS quantity,
            p.unit_price,
            ROUND((1 + (item_idx % 3)) * p.unit_price, 2) AS line_total
        FROM orders o
        CROSS JOIN range(1, 3) t(item_idx)
        JOIN products p ON p.product_id = (1 + ((o.order_id + item_idx) % 20));
    """)

    con.close()


if __name__ == "__main__":
    target = Path("evals/datasets/golden_ecommerce.duckdb")
    create_golden_ecommerce_dataset(target)
    print(f"Created golden dataset at {target}")
