# Test Cases: Intelligent Customer Service Agent

Two independent sets of 11 test cases — one per seeded customer — covering the same
functional areas with different IDs. Run each set logged in as the corresponding customer.

---

## Set A — Customer 1: Ahmad Rifqi (`customer_id = 1`)

*Source: `project-spec.md §9`. Seed data mirrors these IDs exactly.*

| # | Function | Test Query | Expected Behavior |
|---|---|---|---|
| 1 | Intent Parsing | Where is my order 12345? | Extract intent = tracking, order_id = 12345 |
| 2 | OrderLookupTool | Check status of order 1001 | Query `orders` table; return status = processing |
| 3 | CustomerProfileTool | Show my profile | Return Ahmad Rifqi's name and email |
| 4 | RefundTool | Refund order 5678 | Set status = refund_requested (order was delivered) |
| 5 | ComplaintLoggerTool | I want to complain about order 2222 | Insert new complaint row for order 2222 |
| 6 | Multi-step Reasoning | Refund order 7890 if delivered | Lookup → confirm delivered → then refund |
| 7 | Short-Term Memory (STM) | Cancel it *(after asking about order 12345)* | Resolve "it" from previous turn → cancel order 12345 |
| 8 | Long-Term Memory (Read) | What issues have I had before? | Retrieve `delivery_history_*` and `complaint_count` from `customer_memory` |
| 9 | Long-Term Memory (Write) | Remember I prefer refunds over store credit | Upsert preference key into `customer_memory` |
| 10 | Personalization | My order is late again | Detect `late_delivery_pattern` in LTM → acknowledge repeated issue |
| 11 | Verifier | Refund order 0000 | Reject — order 0000 does not exist |

---

## Set B — Customer 2: Jane Doe (`customer_id = 2`)

*Uses different order IDs (20001–20005) seeded in `backend/db/seed.sql`.*

| # | Function | Test Query | Expected Behavior |
|---|---|---|---|
| 1 | Intent Parsing | Where is my order 20001? | Extract intent = tracking, order_id = 20001 |
| 2 | OrderLookupTool | Check status of order 20002 | Query `orders` table; return status = processing |
| 3 | CustomerProfileTool | Show my profile | Return Jane Doe's name and email |
| 4 | RefundTool | Refund order 20003 | Set status = refund_requested (order was delivered) |
| 5 | ComplaintLoggerTool | I want to complain about order 20004 | Insert new complaint row for order 20004 |
| 6 | Multi-step Reasoning | Refund order 20005 if delivered | Lookup → confirm delivered → then refund |
| 7 | Short-Term Memory (STM) | Cancel it *(after asking about order 20001)* | Resolve "it" from previous turn → cancel order 20001 |
| 8 | Long-Term Memory (Read) | What issues have I had before? | Retrieve `delivery_history_*` and `complaint_count` from `customer_memory` |
| 9 | Long-Term Memory (Write) | Remember I prefer store credit over refunds | Upsert preference key into `customer_memory` |
| 10 | Personalization | My order is late again | Detect `late_delivery_pattern` in LTM → acknowledge repeated issue |
| 11 | Verifier | Refund order 0000 | Reject — order 0000 does not exist |

---

## Seed Data Coverage Summary

| Order ID | Customer | Product | Status | Covers Test(s) |
|---|---|---|---|---|
| 12345 | 1 – Ahmad | Wireless Headphones | pending | A1 |
| 1001  | 1 – Ahmad | Mechanical Keyboard | processing | A2 |
| 5678  | 1 – Ahmad | USB-C Hub | delivered | A4 |
| 2222  | 1 – Ahmad | Laptop Stand | delivered | A5 |
| 7890  | 1 – Ahmad | Monitor Arm | delivered | A6 |
| 20001 | 2 – Jane  | Bluetooth Speaker | pending | B1 |
| 20002 | 2 – Jane  | Ergonomic Chair | processing | B2 |
| 20003 | 2 – Jane  | Smart Watch | delivered | B4 |
| 20004 | 2 – Jane  | Air Purifier | delivered | B5 |
| 20005 | 2 – Jane  | Standing Desk | delivered | B6 |
| 0000  | —         | (absent) | — | A11, B11 |

Tests 3, 7, 8, 9, 10 require no dedicated order — they use the customer profile, session
context, and `customer_memory` rows seeded for each customer.