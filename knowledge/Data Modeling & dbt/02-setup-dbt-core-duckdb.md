---
title: "Data Modeling & dbt - Bài 2: Setup dbt Core với DuckDB và build project đầu tiên"
type: tutorial
domain: data-engineering
level: beginner
series: data-modeling-dbt
order: 2
tags:
  - data-engineering
  - dbt
  - duckdb
  - analytics-engineering
  - dimensional-modeling
  - data-warehouse
  - dbt-seed
  - dbt-test
  - dbt-docs
---

# Data Modeling & dbt

## Bài 2 — Setup dbt Core với DuckDB và build project đầu tiên

Mục tiêu bài này: bạn sẽ tạo một project dbt local, dùng **DuckDB** làm warehouse mini, load dữ liệu CSV bằng `dbt seed`, rồi build các model:

```text
stg_customers
stg_orders
stg_payments
dim_customers
fact_orders
fact_payments
mart_daily_revenue
```

DuckDB là lựa chọn rất tốt cho học dbt local vì không cần server database riêng, còn dbt có quickstart chính thức cho dbt Core + DuckDB. ([dbt Developer Hub][1])

---

# 1. Kiến trúc bài thực hành

```text
CSV files
  ↓
dbt seed
  ↓
DuckDB database file
  ↓
staging models
  ↓
fact / dimension models
  ↓
mart_daily_revenue
  ↓
dbt test + dbt docs
```

Trong bài này:

```text
seeds/     = dữ liệu đầu vào dạng CSV
staging/   = chuẩn hóa tên cột, kiểu dữ liệu
marts/     = bảng phục vụ phân tích
tests      = kiểm tra chất lượng dữ liệu
docs       = tài liệu và lineage graph
```

---

# 2. Cài đặt môi trường

## 2.1. Tạo folder project

```bash
mkdir dbt_ecommerce_modeling
cd dbt_ecommerce_modeling
```

## 2.2. Tạo Python virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 2.3. Cài dbt với DuckDB adapter

```bash
pip install dbt-duckdb
```

Gói `dbt-duckdb` là adapter kết nối dbt với DuckDB, cho phép chạy dbt transformation trên DuckDB local. ([GitHub][2])

Kiểm tra:

```bash
dbt --version
```

---

# 3. Khởi tạo dbt project

Chạy:

```bash
dbt init ecommerce_analytics
cd ecommerce_analytics
```

Sau khi init, project có dạng gần giống:

```text
ecommerce_analytics/
  dbt_project.yml
  models/
  macros/
  seeds/
  snapshots/
  tests/
```

Nếu `seeds/`, `snapshots/`, hoặc `tests/` chưa có thì tự tạo:

```bash
mkdir seeds snapshots tests
```

---

# 4. Cấu hình DuckDB profile

dbt dùng file `profiles.yml` để biết kết nối database nào.

Vị trí thường là:

Windows:

```text
C:\Users\<your_user>\.dbt\profiles.yml
```

macOS/Linux:

```text
~/.dbt/profiles.yml
```

Tạo nội dung:

```yaml
ecommerce_analytics:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: ecommerce.duckdb
      threads: 4
```

Ý nghĩa:

```text
type: duckdb              dùng DuckDB adapter
path: ecommerce.duckdb    database file local
threads: 4                số luồng chạy model
```

Kiểm tra connection:

```bash
dbt debug
```

Nếu thấy:

```text
All checks passed!
```

là ổn.

---

# 5. Cấu hình `dbt_project.yml`

Mở file `dbt_project.yml`, chỉnh phần chính như sau:

```yaml
name: 'ecommerce_analytics'
version: '1.0.0'
config-version: 2

profile: 'ecommerce_analytics'

model-paths: ["models"]
seed-paths: ["seeds"]
test-paths: ["tests"]
macro-paths: ["macros"]
snapshot-paths: ["snapshots"]

models:
  ecommerce_analytics:
    staging:
      +materialized: view
    marts:
      +materialized: table

seeds:
  ecommerce_analytics:
    +schema: raw
```

Giải thích:

```text
staging = view
marts   = table
seeds   = load vào schema raw
```

Với dbt, **models** thường là các file SQL `select`, còn materialization quyết định model đó thành view, table, incremental hay dạng khác. ([Analytical Platform User Guidance][3])

---

# 6. Tạo dữ liệu CSV seed

Tạo 3 file trong folder `seeds/`.

## `seeds/raw_customers.csv`

```csv
id,name,city,created_at
101,An,HCM,2026-01-01
102,Binh,Hanoi,2026-01-05
103,Chi,Da Nang,2026-01-10
```

## `seeds/raw_orders.csv`

```csv
id,user_id,order_date,status,amount
1,101,2026-07-01,Completed,200000
2,102,2026-07-01,Cancelled,150000
3,101,2026-07-02,Completed,300000
4,103,2026-07-02,Completed,500000
```

## `seeds/raw_payments.csv`

```csv
id,order_id,payment_date,payment_status,payment_amount
9001,1,2026-07-01,Success,200000
9002,2,2026-07-01,Failed,150000
9003,3,2026-07-02,Success,300000
9004,4,2026-07-02,Success,500000
```

Chạy:

```bash
dbt seed
```

`dbt seed` dùng để load các file CSV trong project vào warehouse thành table, thường phù hợp cho dữ liệu nhỏ, dữ liệu reference, hoặc dataset học tập. ([Datafold][4])

---

# 7. Khai báo sources

Tạo folder:

```bash
mkdir models/staging
mkdir models/marts
```

Tạo file:

```text
models/staging/sources.yml
```

Nội dung:

```yaml
version: 2

sources:
  - name: raw
    schema: raw
    tables:
      - name: raw_customers
      - name: raw_orders
      - name: raw_payments
```

Từ giờ, thay vì query trực tiếp table, ta dùng:

```sql
{{ source('raw', 'raw_orders') }}
```

Lợi ích:

```text
1. Có lineage rõ ràng
2. Có thể test source
3. Dễ đổi schema/table về sau
4. dbt docs hiển thị nguồn dữ liệu
```

---

# 8. Build staging models

## 8.1. `models/staging/stg_customers.sql`

```sql
select
    cast(id as integer) as customer_id,
    name as customer_name,
    city,
    cast(created_at as date) as customer_created_at
from {{ source('raw', 'raw_customers') }}
```

## 8.2. `models/staging/stg_orders.sql`

```sql
select
    cast(id as integer) as order_id,
    cast(user_id as integer) as customer_id,
    cast(order_date as date) as order_date,
    lower(status) as order_status,
    cast(amount as decimal(18, 2)) as order_amount
from {{ source('raw', 'raw_orders') }}
```

## 8.3. `models/staging/stg_payments.sql`

```sql
select
    cast(id as integer) as payment_id,
    cast(order_id as integer) as order_id,
    cast(payment_date as date) as payment_date,
    lower(payment_status) as payment_status,
    cast(payment_amount as decimal(18, 2)) as payment_amount
from {{ source('raw', 'raw_payments') }}
```

Chạy:

```bash
dbt run --select staging
```

---

# 9. Thêm schema test cho staging

Tạo file:

```text
models/staging/schema.yml
```

Nội dung:

```yaml
version: 2

models:
  - name: stg_customers
    description: Cleaned customer source data. One row per customer.
    columns:
      - name: customer_id
        tests:
          - not_null
          - unique
      - name: customer_name
        tests:
          - not_null

  - name: stg_orders
    description: Cleaned order source data. One row per order.
    columns:
      - name: order_id
        tests:
          - not_null
          - unique
      - name: customer_id
        tests:
          - not_null
      - name: order_status
        tests:
          - accepted_values:
              values: ['completed', 'cancelled']

  - name: stg_payments
    description: Cleaned payment source data. One row per payment transaction.
    columns:
      - name: payment_id
        tests:
          - not_null
          - unique
      - name: order_id
        tests:
          - not_null
      - name: payment_status
        tests:
          - accepted_values:
              values: ['success', 'failed']
```

Chạy test:

```bash
dbt test --select staging
```

---

# 10. Build dimension model

## `models/marts/dim_customers.sql`

```sql
with customers as (

    select *
    from {{ ref('stg_customers') }}

),

orders as (

    select *
    from {{ ref('stg_orders') }}

),

customer_order_stats as (

    select
        customer_id,
        count(*) as lifetime_orders,
        sum(
            case
                when order_status = 'completed' then order_amount
                else 0
            end
        ) as lifetime_completed_revenue,
        min(order_date) as first_order_date,
        max(order_date) as latest_order_date
    from orders
    group by customer_id

)

select
    customers.customer_id,
    customers.customer_name,
    customers.city,
    customers.customer_created_at,

    coalesce(customer_order_stats.lifetime_orders, 0) as lifetime_orders,
    coalesce(customer_order_stats.lifetime_completed_revenue, 0) as lifetime_completed_revenue,
    customer_order_stats.first_order_date,
    customer_order_stats.latest_order_date

from customers
left join customer_order_stats
    on customers.customer_id = customer_order_stats.customer_id
```

### Grain

```text
dim_customers grain = 1 row per customer
```

---

# 11. Build fact models

## 11.1. `models/marts/fact_orders.sql`

```sql
select
    order_id,
    customer_id,
    order_date,
    order_status,
    order_amount,

    case
        when order_status = 'completed' then order_amount
        else 0
    end as completed_revenue

from {{ ref('stg_orders') }}
```

### Grain

```text
fact_orders grain = 1 row per order
```

---

## 11.2. `models/marts/fact_payments.sql`

```sql
select
    payment_id,
    order_id,
    payment_date,
    payment_status,
    payment_amount,

    case
        when payment_status = 'success' then payment_amount
        else 0
    end as successful_payment_amount

from {{ ref('stg_payments') }}
```

### Grain

```text
fact_payments grain = 1 row per payment transaction
```

---

# 12. Build mart model

## `models/marts/mart_daily_revenue.sql`

```sql
with orders_daily as (

    select
        order_date,
        count(*) as total_orders,
        sum(
            case
                when order_status = 'completed' then 1
                else 0
            end
        ) as completed_orders,
        sum(order_amount) as gross_order_amount,
        sum(completed_revenue) as completed_revenue
    from {{ ref('fact_orders') }}
    group by order_date

),

payments_daily as (

    select
        payment_date,
        sum(successful_payment_amount) as successful_payment_amount
    from {{ ref('fact_payments') }}
    group by payment_date

)

select
    orders_daily.order_date,
    orders_daily.total_orders,
    orders_daily.completed_orders,
    orders_daily.gross_order_amount,
    orders_daily.completed_revenue,
    coalesce(payments_daily.successful_payment_amount, 0) as successful_payment_amount

from orders_daily
left join payments_daily
    on orders_daily.order_date = payments_daily.payment_date
```

### Grain

```text
mart_daily_revenue grain = 1 row per order_date
```

Chạy:

```bash
dbt run --select marts
```

Hoặc chạy toàn bộ:

```bash
dbt build
```

`dbt build` tiện hơn `dbt run` khi học production workflow vì nó chạy nhiều resource theo dependency order: seeds, snapshots, models, tests.

---

# 13. Thêm schema test cho marts

Tạo file:

```text
models/marts/schema.yml
```

Nội dung:

```yaml
version: 2

models:
  - name: dim_customers
    description: Customer dimension. One row per customer.
    columns:
      - name: customer_id
        tests:
          - not_null
          - unique

  - name: fact_orders
    description: Order fact table. One row per order.
    columns:
      - name: order_id
        tests:
          - not_null
          - unique
      - name: customer_id
        tests:
          - not_null
          - relationships:
              to: ref('dim_customers')
              field: customer_id
      - name: completed_revenue
        tests:
          - not_null

  - name: fact_payments
    description: Payment fact table. One row per payment transaction.
    columns:
      - name: payment_id
        tests:
          - not_null
          - unique
      - name: order_id
        tests:
          - not_null
          - relationships:
              to: ref('fact_orders')
              field: order_id

  - name: mart_daily_revenue
    description: Daily revenue mart. One row per order date.
    columns:
      - name: order_date
        tests:
          - not_null
          - unique
```

Chạy:

```bash
dbt test
```

---

# 14. Kiểm tra kết quả bằng DuckDB CLI hoặc Python

Nếu có DuckDB CLI:

```bash
duckdb ecommerce.duckdb
```

Query:

```sql
select * from mart_daily_revenue;
```

Expected output:

| order_date | total_orders | completed_orders | gross_order_amount | completed_revenue | successful_payment_amount |
| ---------- | -----------: | ---------------: | -----------------: | ----------------: | ------------------------: |
| 2026-07-01 |            2 |                1 |             350000 |            200000 |                    200000 |
| 2026-07-02 |            2 |                2 |             800000 |            800000 |                    800000 |

Nếu dùng Python:

```python
import duckdb

con = duckdb.connect("ecommerce.duckdb")

df = con.execute("""
    select *
    from mart_daily_revenue
    order by order_date
""").fetchdf()

print(df)
```

---

# 15. Generate documentation

Chạy:

```bash
dbt docs generate
dbt docs serve
```

Bạn sẽ thấy:

```text
Lineage graph
Model descriptions
Column descriptions
Tests
Sources
Dependencies
```

Đây là điểm dbt rất mạnh: model không chỉ là SQL, mà có cả **documentation + lineage + quality checks**.

---

# 16. Bài học quan trọng từ project nhỏ này

## 1. `source()` dùng cho raw input

```sql
from {{ source('raw', 'raw_orders') }}
```

Dùng khi lấy dữ liệu từ source/raw table.

## 2. `ref()` dùng cho model do dbt quản lý

```sql
from {{ ref('stg_orders') }}
```

Dùng khi model này phụ thuộc model khác.

## 3. Staging không nên chứa quá nhiều business logic

Staging nên làm:

```text
rename columns
cast types
standardize status
basic cleaning
```

Không nên làm:

```text
calculate complex revenue
join nhiều bảng
build final metrics
```

## 4. Fact cần grain rõ ràng

```text
fact_orders     = 1 row per order
fact_payments   = 1 row per payment
```

Không nên trộn order-level và payment-level vào một fact nếu quan hệ không phải 1-1.

## 5. Mart là bảng phục vụ business

```text
mart_daily_revenue = bảng mà analyst/dashboard dùng trực tiếp
```

---

# 17. Cấu trúc project cuối cùng

Sau bài này, project nên giống:

```text
ecommerce_analytics/
  dbt_project.yml

  seeds/
    raw_customers.csv
    raw_orders.csv
    raw_payments.csv

  models/
    staging/
      sources.yml
      schema.yml
      stg_customers.sql
      stg_orders.sql
      stg_payments.sql

    marts/
      schema.yml
      dim_customers.sql
      fact_orders.sql
      fact_payments.sql
      mart_daily_revenue.sql

  macros/
  snapshots/
  tests/
```

---

# 18. Các lỗi thường gặp

## Lỗi 1: `dbt debug` fail vì profile sai

Kiểm tra:

```text
profile name trong dbt_project.yml
phải trùng với key trong profiles.yml
```

Ví dụ:

```yaml
profile: 'ecommerce_analytics'
```

và:

```yaml
ecommerce_analytics:
  target: dev
```

---

## Lỗi 2: `source not found`

Nếu SQL có:

```sql
{{ source('raw', 'raw_orders') }}
```

thì `sources.yml` phải có:

```yaml
sources:
  - name: raw
    tables:
      - name: raw_orders
```

---

## Lỗi 3: test `relationships` fail

Ví dụ:

```yaml
relationships:
  to: ref('dim_customers')
  field: customer_id
```

Nghĩa là mọi `customer_id` trong fact phải tồn tại trong `dim_customers`.

Nếu fail, thường do:

```text
source thiếu customer
type mismatch
join key sai
dimension bị filter mất row
```

---

## Lỗi 4: `mart_daily_revenue` bị sai số

Thường do join sai grain.

Sai phổ biến:

```sql
select
    o.order_date,
    sum(o.order_amount),
    sum(p.payment_amount)
from fact_orders o
join fact_payments p
    on o.order_id = p.order_id
group by o.order_date
```

Nếu một order có nhiều payment, order amount sẽ bị nhân lên.

Cách an toàn hơn:

```text
aggregate orders theo ngày trước
aggregate payments theo ngày trước
sau đó mới join 2 bảng daily
```

Đó là lý do bài này dùng:

```text
orders_daily
payments_daily
```

---

# 19. Bài tập nâng cấp

Sau khi chạy được bài này, hãy tự thêm:

## 1. Thêm `raw_products.csv`

```csv
id,product_name,category
501,Ensure Gold,Adult Nutrition
502,Glucerna,Diabetes Care
503,Pediasure,Child Nutrition
```

## 2. Thêm `raw_order_items.csv`

```csv
id,order_id,product_id,quantity,item_amount
1,1,501,2,200000
2,3,502,1,300000
3,4,503,5,500000
```

## 3. Build thêm model

```text
stg_products
stg_order_items
dim_products
fact_order_items
mart_product_revenue
```

## 4. Expected grain

```text
dim_products        = 1 row per product
fact_order_items    = 1 row per order item
mart_product_revenue = 1 row per product
```

## 5. Expected metric

```text
product revenue
quantity sold
number of orders containing product
```

---

# 20. Self-check cuối bài

Bạn đạt bài 2 nếu trả lời được:

```text
1. dbt seed dùng để làm gì?
2. source() khác ref() như thế nào?
3. Vì sao staging thường materialized as view?
4. Vì sao marts thường materialized as table?
5. Grain của fact_orders là gì?
6. Grain của fact_payments là gì?
7. Vì sao không join order và payment trực tiếp rồi sum?
8. dbt test relationships kiểm tra điều gì?
9. dbt docs generate tạo ra cái gì?
10. Nếu source not found thì kiểm tra file nào?
```

---

# 21. Ghi nhớ

```text
dbt project tốt không bắt đầu từ SQL phức tạp.
Nó bắt đầu từ layer rõ ràng:

source
  ↓
staging
  ↓
intermediate nếu cần
  ↓
facts / dimensions
  ↓
marts

Mỗi bảng phải có grain rõ ràng.
Mỗi key quan trọng phải có test.
Mỗi metric quan trọng phải được định nghĩa một nơi.
```

---

[1]: https://docs.getdbt.com/docs/local/connect-data-platform/duckdb-setup?utm_source=chatgpt.com "DuckDB setup | dbt Developer Hub"
[2]: https://github.com/duckdb/dbt-duckdb?utm_source=chatgpt.com "dbt-duckdb"
[3]: https://user-guidance.analytical-platform.service.justice.gov.uk/tools/create-a-derived-table/models/?utm_source=chatgpt.com "Models"
[4]: https://www.datafold.com/blog/dbt-seeds/?utm_source=chatgpt.com "dbt seeds: What they are and how to use them"
