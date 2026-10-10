from pathlib import Path
from typing import Dict
from src.tools.database import DuckDBRunner


class LegacyWarehouseHarness:
    """Generates synthetic legacy warehouse schemas and data with injected legacy antipatterns."""

    def __init__(self, db_path: str = "data/legacy/legacy_warehouse.duckdb"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.runner = DuckDBRunner(db_path)

    def seed(self) -> Dict[str, str]:
        """Seeds tables and returns a dictionary mapping table/view name to its legacy DDL."""
        ddl_map: Dict[str, str] = {}

        # 1. raw_customers: Obfuscated column names and PII (tax ID / CPF, email, phone)
        cust_ddl = """
        CREATE OR REPLACE TABLE raw_customers (
            CUST_LST_ADDR_ID_TX VARCHAR PRIMARY KEY,
            CUST_NAT_DOC_NUM_ID VARCHAR,
            CUST_COMM_EML_ADDR_TX VARCHAR,
            CUST_TEL_NUM_TX VARCHAR,
            CUST_CITY_NAME_TX VARCHAR,
            CUST_STATE_CD_TX VARCHAR
        );
        """
        self.runner.execute(cust_ddl)
        ddl_map["raw_customers"] = cust_ddl.strip()

        self.runner.execute("""
        INSERT INTO raw_customers VALUES
        ('c_101', '123.456.789-00', 'ana.silva@example.com', '+55 11 98765-4321', 'Sao Paulo', 'SP'),
        ('c_102', '987.654.321-99', 'carlos.m@example.org', '+55 21 91234-5678', 'Rio de Janeiro', 'RJ'),
        ('c_103', '111.222.333-44', 'beatriz.p@example.com', '+55 31 99887-7665', 'Belo Horizonte', 'MG'),
        ('c_104', '555.666.777-88', 'fernando.s@example.net', '+55 41 98877-6655', 'Curitiba', 'PR'),
        ('c_105', '', '', '+55 71 99999-0000', 'Salvador', 'BA');
        """)

        # 2. raw_categories: Hierarchical self-referential categories
        cat_ddl = """
        CREATE OR REPLACE TABLE raw_categories (
            category_id INTEGER PRIMARY KEY,
            category_name VARCHAR,
            parent_category_id INTEGER
        );
        """
        self.runner.execute(cat_ddl)
        ddl_map["raw_categories"] = cat_ddl.strip()

        self.runner.execute("""
        INSERT INTO raw_categories VALUES
        (1, 'Electronics', NULL),
        (2, 'Computers', 1),
        (3, 'Laptops', 2),
        (4, 'Home & Garden', NULL),
        (5, 'Furniture', 4);
        """)

        # 3. raw_orders: Dirty mixed date strings and delimited status arrays, plus duplicate entries
        orders_ddl = """
        CREATE OR REPLACE TABLE raw_orders (
            order_id VARCHAR,
            customer_id VARCHAR,
            order_status_history VARCHAR,
            order_purchase_date_str VARCHAR,
            ingest_date VARCHAR
        );
        """
        self.runner.execute(orders_ddl)
        ddl_map["raw_orders"] = orders_ddl.strip()

        # Notice mixed date formats: '2023-01-15 10:20:00' and '16/01/2023',
        # plus duplicate records for order_id 'o_1001' with identical ingest_date (tie-breaker challenge)
        self.runner.execute("""
        INSERT INTO raw_orders VALUES
        ('o_1001', 'c_101', 'NEW;PAID;SHIPPED', '2023-01-15 10:20:00', '2023-01-16 00:00:00'),
        ('o_1001', 'c_101', 'NEW;PAID;DELIVERED', '2023-01-15 10:20:00', '2023-01-16 00:00:00'),
        ('o_1002', 'c_102', 'NEW;PAID', '16/01/2023', '2023-01-17 01:00:00'),
        ('o_1003', 'c_103', 'NEW;CANCELLED', '2023-01-17 14:30:10', '2023-01-18 02:00:00'),
        ('o_1004', 'c_104', 'NEW;PAID;DELIVERED', '18/01/2023', '2023-01-19 03:00:00');
        """)

        # 4. raw_order_payments: Money amounts as unscaled DOUBLE
        payments_ddl = """
        CREATE OR REPLACE TABLE raw_order_payments (
            payment_id VARCHAR PRIMARY KEY,
            order_id VARCHAR,
            payment_sequential INTEGER,
            payment_type VARCHAR,
            payment_installments INTEGER,
            payment_value DOUBLE
        );
        """
        self.runner.execute(payments_ddl)
        ddl_map["raw_order_payments"] = payments_ddl.strip()

        self.runner.execute("""
        INSERT INTO raw_order_payments VALUES
        ('p_1', 'o_1001', 1, 'credit_card', 3, 150.7554),
        ('p_2', 'o_1002', 1, 'boleto', 1, 89.9001),
        ('p_3', 'o_1003', 1, 'voucher', 1, 45.0000),
        ('p_4', 'o_1004', 1, 'credit_card', 2, 320.5050);
        """)

        # 5. raw_order_items: Order items with price and freight value
        items_ddl = """
        CREATE OR REPLACE TABLE raw_order_items (
            order_item_id VARCHAR PRIMARY KEY,
            order_id VARCHAR,
            product_id VARCHAR,
            price DOUBLE,
            freight_value DOUBLE
        );
        """
        self.runner.execute(items_ddl)
        ddl_map["raw_order_items"] = items_ddl.strip()

        self.runner.execute("""
        INSERT INTO raw_order_items VALUES
        ('it_1', 'o_1001', 'prod_1', 130.00, 20.75),
        ('it_2', 'o_1002', 'prod_2', 75.00, 14.90),
        ('it_3', 'o_1003', 'prod_3', 35.00, 10.00),
        ('it_4', 'o_1004', 'prod_4', 290.00, 30.50);
        """)

        # 6. Legacy View v_order_summary: Oracle style functions DECODE, NVL, string concat ||
        view_ddl = """
        CREATE OR REPLACE VIEW v_order_summary AS
        SELECT 
            o.order_id,
            o.customer_id,
            CASE 
                WHEN o.order_status_history LIKE '%DELIVERED%' THEN 'COMPLETED'
                WHEN o.order_status_history LIKE '%CANCELLED%' THEN 'CANCELLED'
                ELSE 'IN_PROGRESS'
            END AS calculated_status,
            COALESCE(p.payment_value, 0.0) AS payment_amount
        FROM raw_orders o
        LEFT JOIN raw_order_payments p ON o.order_id = p.order_id;
        """
        self.runner.execute(view_ddl)
        ddl_map["v_order_summary"] = view_ddl.strip()

        return ddl_map
