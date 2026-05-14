CREATE TABLE IF NOT EXISTS customers (
    customer_id INT PRIMARY KEY,
    name        VARCHAR(100),
    email       VARCHAR(100),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    order_id      INT PRIMARY KEY,
    customer_id   INT,
    product_name  TEXT,
    status        VARCHAR(50),
    order_date    TIMESTAMP,
    delivery_date TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS complaints (
    complaint_id   INT AUTO_INCREMENT PRIMARY KEY,
    customer_id    INT,
    order_id       INT,
    issue          TEXT,
    status         VARCHAR(50),
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (order_id)    REFERENCES orders(order_id)
);

CREATE TABLE IF NOT EXISTS customer_memory (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT,
    `key`       VARCHAR(255),
    value       TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    UNIQUE KEY uq_customer_key (customer_id, `key`)
);

CREATE TABLE IF NOT EXISTS sessions (
    thread_id   VARCHAR(100) PRIMARY KEY,
    customer_id INT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at    TIMESTAMP NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS session_messages (
    message_id INT AUTO_INCREMENT PRIMARY KEY,
    thread_id  VARCHAR(100),
    role       VARCHAR(20),
    content    TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (thread_id) REFERENCES sessions(thread_id)
);

-- Seed customers
INSERT INTO customers (customer_id, name, email) VALUES
    (1, 'Ahmad Rifqi', 'customer1@example.com'),
    (2, 'Jane Doe',    'customer2@example.com');

-- Seed orders (all under customer 1; covers tests 1-2 and 4-6)
-- test 1: intent parsing — order in transit
-- test 2: order lookup
-- test 4: refund eligible (delivered)
-- test 5: complaint target (delivered)
-- test 6: conditional refund — must be delivered
-- order 0000 intentionally absent (test 11: verifier rejects)
INSERT INTO orders (order_id, customer_id, product_name, status, order_date, delivery_date) VALUES
    (12345, 1, 'Wireless Headphones', 'pending',    '2026-04-01 10:00:00', NULL),
    (1001,  1, 'Mechanical Keyboard', 'processing', '2026-04-05 09:00:00', NULL),
    (5678,  1, 'USB-C Hub',           'delivered',  '2026-03-10 08:00:00', '2026-03-15 14:00:00'),
    (2222,  1, 'Laptop Stand',        'delivered',  '2026-03-20 11:00:00', '2026-03-25 16:00:00'),
    (7890,  1, 'Monitor Arm',         'delivered',  '2026-03-01 07:00:00', '2026-03-07 12:00:00');

-- Seed customer_memory for customer 1
-- test 8:  long-term memory read — prior delivery problems
-- test 10: personalization — repeated late delivery pattern
INSERT INTO customer_memory (customer_id, `key`, value) VALUES
    (1, 'delivery_history_1001', 'Order 1001 was delivered 3 days late in March 2026'),
    (1, 'delivery_history_12345', 'Order 12345 shipping was delayed due to warehouse backlog'),
    (1, 'late_delivery_pattern', 'Customer has a late delivery pattern across fulfilled orders'),
    (1, 'complaint_count',      '2');

-- Seed complaints for customer 1
-- test 8: complaint history available for memory/personalization lookups
INSERT INTO complaints (customer_id, order_id, issue, status) VALUES
    (1, 5678, 'Package arrived two days later than promised', 'resolved'),
    (1, 7890, 'Repeated late delivery on delivered order',    'closed');

-- ─── Customer 2 (Jane Doe) — mirrors the 11 test cases with different IDs ───

-- Seed orders for customer 2
-- test 1: intent parsing — order in transit (pending)
-- test 2: order lookup (processing)
-- test 4: refund eligible (delivered)
-- test 5: complaint target (delivered)
-- test 6: conditional refund — must be delivered
-- order 0000 intentionally absent (test 11: verifier rejects)
INSERT INTO orders (order_id, customer_id, product_name, status, order_date, delivery_date) VALUES
    (20001, 2, 'Bluetooth Speaker',  'pending',    '2026-04-10 08:00:00', NULL),
    (20002, 2, 'Ergonomic Chair',    'processing', '2026-04-12 09:00:00', NULL),
    (20003, 2, 'Smart Watch',        'delivered',  '2026-03-05 07:00:00', '2026-03-12 15:00:00'),
    (20004, 2, 'Air Purifier',       'delivered',  '2026-03-18 10:00:00', '2026-03-25 13:00:00'),
    (20005, 2, 'Standing Desk',      'delivered',  '2026-02-20 06:00:00', '2026-02-28 11:00:00');

-- Seed customer_memory for customer 2
-- test 8:  long-term memory read — prior delivery problems
-- test 10: personalization — repeated late delivery pattern
INSERT INTO customer_memory (customer_id, `key`, value) VALUES
    (2, 'delivery_history_20001', 'Order 20001 shipping was delayed 5 days due to stock shortage'),
    (2, 'delivery_history_20002', 'Order 20002 was rerouted and arrived 3 days late'),
    (2, 'late_delivery_pattern',  'Customer has experienced repeated late deliveries across orders'),
    (2, 'complaint_count',        '2');

-- Seed complaints for customer 2
-- test 8: complaint history available for memory/personalization lookups
INSERT INTO complaints (customer_id, order_id, issue, status) VALUES
    (2, 20003, 'Received wrong color variant of item',         'resolved'),
    (2, 20005, 'Delivery arrived 4 days past the promised date', 'closed');
