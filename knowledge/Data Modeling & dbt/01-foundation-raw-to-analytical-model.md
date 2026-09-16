---
title: "Data Modeling & dbt - Bài 1: Tư duy nền tảng từ raw data đến analytical model"
type: tutorial
domain: data-engineering
tags:
  - data-modeling
  - dbt
  - oltp
  - olap
  - dimensional-modeling
  - fact-table
  - dimension-table
  - grain
---

# Data Modeling & dbt

## Bài 1 — Tư duy nền tảng: từ raw data đến analytical model

---

## 1. Mục tiêu bài học

Sau bài này, bạn cần hiểu được:

```text
1. Data modeling là gì và vì sao Data Engineer cần giỏi phần này
2. Khác nhau giữa OLTP và OLAP
3. Vì sao không nên cho BI/dashboard query trực tiếp raw table
4. Grain là gì và tại sao grain là concept cực kỳ quan trọng
5. Fact table và dimension table khác nhau như thế nào
```

---

# 2. Data Modeling là gì?

Nói đơn giản:

> **Data modeling là cách mình thiết kế dữ liệu để người khác có thể phân tích, báo cáo, và ra quyết định một cách đúng, nhanh, dễ hiểu.**

Raw data thường được sinh ra từ hệ thống vận hành:

```text
CRM
App backend
Payment system
E-commerce system
Call center system
Marketing platform
ERP
SFTP files
API logs
```

Nhưng raw data thường:

```text
Tên cột khó hiểu
Kiểu dữ liệu không chuẩn
Nhiều duplicate
Có null
Có logic nghiệp vụ bị ẩn
Khó join
Không phù hợp để dashboard query trực tiếp
```

Ví dụ raw order table:

```text
id
uid
amt
stt
created
updated
src
```

Người business sẽ không muốn nhìn bảng như vậy. Họ muốn bảng rõ ràng hơn:

```text
order_id
customer_id
order_amount
order_status
order_created_at
order_updated_at
source_system
```

Đây là bước đầu của data modeling.

---

# 3. Ví dụ đời thực

Giả sử bạn làm cho một công ty bán sữa online.

Hệ thống backend có các bảng raw:

```text
raw_customers
raw_orders
raw_order_items
raw_products
raw_payments
raw_campaigns
```

Business hỏi:

```text
Doanh thu tháng này là bao nhiêu?
Campaign nào tạo nhiều đơn hàng nhất?
Khách hàng nào mua lại nhiều nhất?
Sản phẩm nào bán chạy nhất?
Tỷ lệ hoàn tiền là bao nhiêu?
```

Nếu query trực tiếp raw tables, mỗi analyst có thể viết logic khác nhau:

```sql
-- Analyst A
select sum(amount)
from raw_orders
where status = 'completed';
```

```sql
-- Analyst B
select sum(payment_amount)
from raw_payments
where payment_status = 'success';
```

```sql
-- Analyst C
select sum(order_total - discount_amount)
from raw_orders
where status not in ('cancelled');
```

Kết quả: **3 số doanh thu khác nhau**.

Data modeling giải quyết vấn đề này bằng cách tạo một model chính thức:

```text
fact_orders
```

Trong đó business logic được chuẩn hóa:

```text
net_revenue = completed_payment_amount - refund_amount
```

Từ đó dashboard, analyst, data scientist đều dùng cùng một nguồn.

---

# 4. OLTP vs OLAP

Đây là concept nền tảng.

## OLTP — Online Transaction Processing

OLTP là hệ thống phục vụ giao dịch vận hành hằng ngày.

Ví dụ:

```text
Tạo đơn hàng
Thanh toán
Cập nhật thông tin khách hàng
Giao hàng
Tạo ticket support
```

Đặc điểm:

```text
Nhiều insert/update/delete nhỏ
Cần nhanh cho từng transaction
Dữ liệu thường normalized
Thiết kế để app chạy ổn định
Không tối ưu cho phân tích lớn
```

Ví dụ bảng OLTP:

```text
customers
orders
order_items
payments
products
addresses
```

Một đơn hàng được tách ra nhiều bảng để tránh lặp dữ liệu.

---

## OLAP — Online Analytical Processing

OLAP là hệ thống phục vụ phân tích.

Ví dụ:

```text
Doanh thu theo tháng
Top sản phẩm theo khu vực
Customer lifetime value
Campaign performance
Churn rate
Conversion funnel
```

Đặc điểm:

```text
Đọc nhiều hơn ghi
Query aggregate lớn
Join nhiều bảng
Phục vụ dashboard/report
Dữ liệu thường denormalized
Tối ưu cho phân tích
```

Ví dụ bảng OLAP:

```text
fact_orders
dim_customers
dim_products
dim_date
dim_campaigns
```

---

## So sánh nhanh

| Tiêu chí   | OLTP                     | OLAP                       |
| ---------- | ------------------------ | -------------------------- |
| Mục đích   | Vận hành giao dịch       | Phân tích, báo cáo         |
| Người dùng | App, backend service     | Analyst, BI, manager       |
| Query      | Nhỏ, nhanh, nhiều update | Lớn, nhiều aggregate       |
| Thiết kế   | Normalized               | Dimensional / denormalized |
| Ví dụ      | orders, payments         | fact_orders, dim_customers |

---

# 5. Vì sao không nên query trực tiếp raw/OLTP?

Có 5 lý do chính.

## 1. Raw data khó hiểu

Tên cột có thể như:

```text
cust_id
amt
stt
src
dt
flg
```

Không có business meaning rõ ràng.

---

## 2. Logic bị lặp lại ở nhiều nơi

Nếu không có model chuẩn, mỗi dashboard tự tính metric riêng.

Ví dụ metric “active customer”:

```text
Có người tính là khách mua trong 30 ngày
Có người tính là khách login trong 30 ngày
Có người tính là khách có payment thành công
```

Nếu không chuẩn hóa, dashboard sẽ mâu thuẫn.

---

## 3. Dễ double count

Ví dụ:

```text
orders: 1 row per order
order_items: nhiều row per order
payments: có thể nhiều row per order
```

Nếu join sai:

```sql
select
    sum(o.order_amount)
from orders o
join order_items oi
    on o.order_id = oi.order_id;
```

Một order có 3 items sẽ bị nhân doanh thu lên 3 lần.

---

## 4. Performance kém

Dashboard query trực tiếp raw nhiều bảng lớn sẽ chậm.

Thay vào đó, mình tạo sẵn marts:

```text
mart_daily_revenue
mart_customer_lifetime_value
mart_campaign_performance
```

---

## 5. Không có kiểm soát chất lượng

Raw data có thể có:

```text
Duplicate order_id
Missing customer_id
Negative revenue
Invalid status
Late-arriving data
```

dbt giúp thêm test để phát hiện lỗi trước khi dữ liệu lên dashboard.

---

# 6. Concept quan trọng nhất: Grain

## Grain là gì?

> **Grain là định nghĩa “một dòng trong bảng đại diện cho cái gì”.**

Ví dụ:

```text
fact_orders:
1 dòng = 1 order

fact_order_items:
1 dòng = 1 item trong 1 order

fact_payments:
1 dòng = 1 payment transaction

fact_customer_daily_activity:
1 dòng = 1 customer trong 1 ngày
```

Nếu không định nghĩa grain rõ, model sẽ rất dễ sai.

---

## Ví dụ grain sai

Bạn có bảng:

```text
order_id | customer_id | product_id | payment_id | revenue
```

Nhìn có vẻ tiện, nhưng grain không rõ.

Một order có thể có:

```text
3 products
2 payments
```

Khi join order_items với payments, bạn có thể tạo ra:

```text
3 x 2 = 6 rows
```

Doanh thu bị nhân lên.

---

## Grain đúng hơn

Tách ra:

```text
fact_orders
1 dòng = 1 order
```

```text
fact_order_items
1 dòng = 1 product trong 1 order
```

```text
fact_payments
1 dòng = 1 payment transaction
```

Sau đó business cần metric nào thì dùng đúng bảng đó.

---

# 7. Fact Table là gì?

Fact table là bảng lưu **sự kiện kinh doanh có thể đo lường được**.

Ví dụ:

```text
Order created
Payment completed
Product viewed
Lead assigned
Call made
Invoice generated
Shipment delivered
```

Fact table thường có:

```text
Foreign keys
Date/time keys
Measures
Status
Degenerate dimensions
```

Ví dụ `fact_orders`:

```text
order_id
customer_id
campaign_id
order_date
order_status
gross_revenue
discount_amount
net_revenue
```

Measures là các số có thể tính toán:

```text
gross_revenue
net_revenue
quantity
discount_amount
call_duration
lead_count
```

---

# 8. Dimension Table là gì?

Dimension table là bảng mô tả ngữ cảnh cho fact.

Ví dụ:

```text
dim_customers
dim_products
dim_campaigns
dim_date
dim_agents
dim_teams
```

Ví dụ `dim_customers`:

```text
customer_id
customer_name
gender
age_group
city
customer_segment
created_at
```

Dimension giúp trả lời các câu hỏi:

```text
Theo khách hàng nào?
Theo sản phẩm nào?
Theo khu vực nào?
Theo campaign nào?
Theo team nào?
Theo ngày nào?
```

---

# 9. Star Schema là gì?

Star schema là mô hình phổ biến nhất trong dimensional modeling.

Nó có một fact table ở giữa, xung quanh là các dimension.

```text
                 dim_customers
                       |
dim_products — fact_order_items — dim_date
                       |
                 dim_campaigns
```

Ví dụ:

```text
fact_order_items
- order_item_id
- order_id
- customer_id
- product_id
- campaign_id
- date_id
- quantity
- revenue
```

Join với:

```text
dim_customers
dim_products
dim_campaigns
dim_date
```

---

# 10. dbt nằm ở đâu?

dbt không phải database.
dbt không phải BI tool.
dbt không phải ingestion tool.

dbt là transformation framework.

Nó giúp bạn chuyển:

```text
raw tables
```

thành:

```text
clean analytical models
```

Thông qua SQL, Jinja, tests, docs, lineage.

Luồng thường gặp:

```text
Source systems
    ↓
Ingestion tool: Airbyte / Fivetran / Python / SFTP
    ↓
Warehouse/Lakehouse: BigQuery / Snowflake / Databricks / DuckDB / Postgres
    ↓
dbt
    ↓
Staging models
    ↓
Intermediate models
    ↓
Marts
    ↓
BI dashboard / Semantic layer
```

---

# 11. dbt Layering Pattern

Một project dbt tốt thường có 3 lớp chính.

## 1. Staging

Mục tiêu:

```text
Clean column names
Cast data types
Standardize values
Remove obvious duplicates
Expose source in clean format
```

Ví dụ:

```text
raw.orders → stg_orders
```

Không nên đưa quá nhiều business logic ở staging.

---

## 2. Intermediate

Mục tiêu:

```text
Join logic
Deduplication phức tạp
Prepare reusable logic
Calculate helper fields
```

Ví dụ:

```text
int_order_payments
int_customer_orders
int_campaign_leads
```

---

## 3. Marts

Mục tiêu:

```text
Business-facing facts and dimensions
Dashboard-ready tables
Metric-ready tables
```

Ví dụ:

```text
dim_customers
dim_products
fact_orders
fact_payments
mart_daily_revenue
```

---

# 12. Minimal Example

Giả sử raw table:

```text
raw_orders
```

| id | user_id | order_date | status    | amount |
| -- | ------: | ---------- | --------- | -----: |
| 1  |     101 | 2026-07-01 | Completed | 200000 |
| 2  |     102 | 2026-07-01 | Cancelled | 150000 |
| 3  |     101 | 2026-07-02 | Completed | 300000 |

---

## Staging model

```sql
-- models/staging/stg_orders.sql

select
    cast(id as integer) as order_id,
    cast(user_id as integer) as customer_id,
    cast(order_date as date) as order_date,
    lower(status) as order_status,
    cast(amount as decimal(18, 2)) as order_amount
from {{ source('raw', 'orders') }}
```

Output:

| order_id | customer_id | order_date | order_status | order_amount |
| -------: | ----------: | ---------- | ------------ | -----------: |
|        1 |         101 | 2026-07-01 | completed    |       200000 |
|        2 |         102 | 2026-07-01 | cancelled    |       150000 |
|        3 |         101 | 2026-07-02 | completed    |       300000 |

---

## Fact model

```sql
-- models/marts/fact_orders.sql

select
    order_id,
    customer_id,
    order_date,
    order_status,
    order_amount,

    case
        when order_status = 'completed'
            then order_amount
        else 0
    end as completed_revenue

from {{ ref('stg_orders') }}
```

Output:

| order_id | customer_id | order_status | order_amount | completed_revenue |
| -------: | ----------: | ------------ | -----------: | ----------------: |
|        1 |         101 | completed    |       200000 |            200000 |
|        2 |         102 | cancelled    |       150000 |                 0 |
|        3 |         101 | completed    |       300000 |            300000 |

---

# 13. Bài tập thực hành

## Dataset nhỏ

Tạo 3 file CSV:

```text
raw_customers.csv
raw_orders.csv
raw_payments.csv
```

### `raw_customers.csv`

```csv
id,name,city,created_at
101,An,HCM,2026-01-01
102,Binh,Hanoi,2026-01-05
103,Chi,Da Nang,2026-01-10
```

### `raw_orders.csv`

```csv
id,user_id,order_date,status,amount
1,101,2026-07-01,Completed,200000
2,102,2026-07-01,Cancelled,150000
3,101,2026-07-02,Completed,300000
4,103,2026-07-02,Completed,500000
```

### `raw_payments.csv`

```csv
id,order_id,payment_date,payment_status,payment_amount
9001,1,2026-07-01,Success,200000
9002,2,2026-07-01,Failed,150000
9003,3,2026-07-02,Success,300000
9004,4,2026-07-02,Success,500000
```

---

## Yêu cầu bài tập

Tạo các model:

```text
stg_customers
stg_orders
stg_payments
dim_customers
fact_orders
fact_payments
mart_daily_revenue
```

Trong đó:

```text
fact_orders grain = 1 row per order
fact_payments grain = 1 row per payment
mart_daily_revenue grain = 1 row per order_date
```

---

## Expected output: `mart_daily_revenue`

| order_date | total_orders | completed_orders | gross_order_amount | completed_revenue | successful_payment_amount |
| ---------- | -----------: | ---------------: | -----------------: | ----------------: | ------------------------: |
| 2026-07-01 |            2 |                1 |             350000 |            200000 |                    200000 |
| 2026-07-02 |            2 |                2 |             800000 |            800000 |                    800000 |

---

# 14. Câu hỏi tự kiểm tra

Trả lời được các câu này là đạt bài 1:

```text
1. OLTP khác OLAP như thế nào?
2. Vì sao không nên query raw table trực tiếp cho dashboard?
3. Grain là gì?
4. fact_orders và fact_order_items khác nhau như thế nào?
5. Dimension table dùng để làm gì?
6. dbt nằm ở bước nào trong modern data stack?
7. Staging, intermediate, marts khác nhau như thế nào?
```

---

# 15. Checklist cuối bài

Bạn nên nhớ:

```text
Data modeling không phải chỉ là tạo bảng.
Nó là thiết kế logic phân tích đáng tin cậy.

Grain là concept quan trọng nhất khi thiết kế fact table.

Fact = sự kiện đo lường được.
Dimension = ngữ cảnh mô tả.

dbt giúp biến raw data thành models có test, docs, lineage và version control.

Không nên đưa toàn bộ business logic vào một SQL khổng lồ.
Hãy chia thành staging → intermediate → marts.
```