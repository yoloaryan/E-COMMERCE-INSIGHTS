-- ==============================================================================
-- E-Commerce Customer Intelligence & Sales Prediction System
-- Production Analytical SQL Marts & Business Intelligence Queries
-- ==============================================================================

-- 1. Create Staging & Core Analytical Schema
CREATE TABLE IF NOT EXISTS ecommerce_transactions (
    invoice_no VARCHAR(20) NOT NULL,
    stock_code VARCHAR(30) NOT NULL,
    description TEXT,
    quantity INT NOT NULL,
    invoice_date TIMESTAMP NOT NULL,
    unit_price DECIMAL(10, 4) NOT NULL,
    customer_id VARCHAR(20),
    country VARCHAR(100),
    is_cancelled BOOLEAN DEFAULT FALSE,
    is_guest BOOLEAN DEFAULT FALSE,
    total_price DECIMAL(12, 4) GENERATED ALWAYS AS (quantity * unit_price) STORED,
    INDEX idx_customer (customer_id),
    INDEX idx_invoice_date (invoice_date),
    INDEX idx_stock_code (stock_code)
);

-- ------------------------------------------------------------------------------
-- 2. Query: Monthly Sales Velocity & Average Order Value (AOV)
-- ------------------------------------------------------------------------------
SELECT 
    DATE_FORMAT(invoice_date, '%Y-%m') AS sales_month,
    COUNT(DISTINCT invoice_no) AS total_orders,
    SUM(quantity) AS total_units_sold,
    ROUND(SUM(quantity * unit_price), 2) AS gross_revenue,
    ROUND(SUM(quantity * unit_price) / COUNT(DISTINCT invoice_no), 2) AS average_order_value
FROM ecommerce_transactions
WHERE is_cancelled = FALSE 
  AND quantity > 0 
  AND unit_price > 0
GROUP BY sales_month
ORDER BY sales_month ASC;

-- ------------------------------------------------------------------------------
-- 3. Query: Top 10 High-Velocity Products (Gross Revenue & Units)
-- ------------------------------------------------------------------------------
SELECT 
    stock_code,
    description,
    SUM(quantity) AS total_units_sold,
    ROUND(SUM(quantity * unit_price), 2) AS gross_revenue,
    COUNT(DISTINCT invoice_no) AS order_frequency
FROM ecommerce_transactions
WHERE is_cancelled = FALSE 
  AND quantity > 0
GROUP BY stock_code, description
ORDER BY gross_revenue DESC
LIMIT 10;

-- ------------------------------------------------------------------------------
-- 4. Query: RFM Raw Feature Aggregation (SQL-Based)
-- ------------------------------------------------------------------------------
-- Reference date: Max transaction timestamp + 1 day
WITH reference_table AS (
    SELECT MAX(invoice_date) + INTERVAL 1 DAY AS ref_date
    FROM ecommerce_transactions
)
SELECT 
    t.customer_id,
    DATEDIFF((SELECT ref_date FROM reference_table), MAX(t.invoice_date)) AS recency_days,
    COUNT(DISTINCT t.invoice_no) AS frequency_orders,
    ROUND(SUM(t.quantity * t.unit_price), 2) AS monetary_value,
    MIN(t.invoice_date) AS first_purchase_date,
    MAX(t.invoice_date) AS last_purchase_date
FROM ecommerce_transactions t
WHERE t.customer_id IS NOT NULL 
  AND t.is_cancelled = FALSE 
  AND t.quantity > 0
GROUP BY t.customer_id
ORDER BY monetary_value DESC;

-- ------------------------------------------------------------------------------
-- 5. Query: Customer Inactivity / Churn Rule Audit (>90 Days Inactive)
-- ------------------------------------------------------------------------------
WITH customer_last_purchase AS (
    SELECT 
        customer_id,
        MAX(invoice_date) AS last_purchase_date,
        COUNT(DISTINCT invoice_no) AS lifetime_orders,
        SUM(quantity * unit_price) AS lifetime_spend
    FROM ecommerce_transactions
    WHERE customer_id IS NOT NULL 
      AND is_cancelled = FALSE 
      AND quantity > 0
    GROUP BY customer_id
),
churn_evaluated AS (
    SELECT 
        customer_id,
        last_purchase_date,
        lifetime_orders,
        lifetime_spend,
        DATEDIFF('2011-12-10', last_purchase_date) AS days_since_last_purchase,
        CASE 
            WHEN DATEDIFF('2011-12-10', last_purchase_date) > 90 THEN 1 
            ELSE 0 
        END AS is_churned
    FROM customer_last_purchase
)
SELECT 
    is_churned,
    COUNT(customer_id) AS total_customers,
    ROUND(COUNT(customer_id) * 100.0 / (SELECT COUNT(*) FROM churn_evaluated), 2) AS customer_percentage,
    ROUND(AVG(lifetime_spend), 2) AS avg_historical_spend,
    ROUND(AVG(lifetime_orders), 1) AS avg_orders
FROM churn_evaluated
GROUP BY is_churned;
