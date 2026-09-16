---
title: Dimensional Modeling Deep Dive
type: tutorial
domain: data-engineering
tags:
  - data-modeling
  - dimensional-modeling
  - dbt
  - grain
  - fact-table
  - dimension-table
  - star-schema
  - double-counting
---
# Data Modeling & dbt

## Bài 3 — Dimensional Modeling Deep Dive: Grain, Fact, Dimension, Star Schema và Double Counting

Ở Bài 2, bạn đã build project dbt đầu tiên:

```text id="io406i"
raw CSV
  ↓
staging
  ↓
dim_customers
fact_orders
fact_payments
mart_daily_revenue
```

Bài 3 sẽ đi sâu vào **dimensional modeling** — phần cực kỳ quan trọng khi làm analytics engineering, data warehouse, BI, dashboard, reporting.

---

# 1. Mục tiêu bài học

Sau bài này, bạn cần nắm được:

```text id="p60cjh"
1. Grain là gì và cách định nghĩa grain đúng
2. Fact table có những loại nào
3. Dimension table có những loại nào
4. Star schema hoạt động như thế nào
5. Khi nào cần fact_orders, fact_order_items, fact_payments riêng biệt
6. Vì sao double counting xảy ra
7. Cách thiết kế model để tránh sai số metric
8. Cách áp dụng các concept này trong dbt
```

---

# 2. Dimensional Modeling là gì?

**Dimensional modeling** là phương pháp thiết kế dữ liệu để phục vụ phân tích.

Nó cố gắng trả lời nhanh các câu hỏi business như:

```text id="q381x5"
Doanh thu theo ngày là bao nhiêu?
Sản phẩm nào bán chạy nhất?
Campaign nào mang lại nhiều đơn hàng nhất?
Khách hàng nào có lifetime value cao nhất?
Team nào xử lý nhiều lead nhất?
Agent nào có conversion tốt nhất?
```

Dimensional modeling thường dùng 2 nhóm bảng chính:

```text id="9z2uy4"
Fact tables
Dimension tables
```

Có thể hiểu đơn giản:

```text id="vd1d6b"
Fact = chuyện gì đã xảy ra?
Dimension = chuyện đó xảy ra với ai, cái gì, ở đâu, khi nào, thuộc nhóm nào?
```

Ví dụ:

```text id="fyggxo"
Fact:
Một đơn hàng được tạo
Một payment thành công
Một lead được assign
Một cuộc gọi được thực hiện

Dimension:
Khách hàng nào
Sản phẩm nào
Campaign nào
Team nào
Agent nào
Ngày nào
Khu vực nào
```

---

# 3. Concept quan trọng nhất: Grain

## 3.1. Định nghĩa

**Grain** là định nghĩa:

> Một dòng trong bảng đại diện cho điều gì?

Ví dụ:

```text id="kco4os"
fact_orders:
1 dòng = 1 order

fact_order_items:
1 dòng = 1 item trong 1 order

fact_payments:
1 dòng = 1 payment transaction

fact_agent_assignments:
1 dòng = 1 lead được assign cho 1 agent tại 1 thời điểm

fact_campaign_daily:
1 dòng = 1 campaign trong 1 ngày
```

Nếu bạn không định nghĩa grain, bảng sẽ rất dễ bị sai khi join hoặc aggregate.

---

## 3.2. Cách viết grain trong README / dbt docs

Mỗi fact table nên có description kiểu này:

```yaml id="ei90jb"
models:
  - name: fact_orders
    description: >
      Order fact table. Grain: one row per order.
```

Hoặc:

```yaml id="u83l51"
models:
  - name: fact_order_items
    description: >
      Order item fact table. Grain: one row per product item within an order.
```

Đây là thói quen rất tốt trong portfolio và production.

---

## 3.3. Bài test nhanh về grain

Giả sử có bảng:

```text id="uk3wum"
order_id | product_id | payment_id | revenue
```

Một order có thể có:

```text id="haxz62"
3 products
2 payments
```

Nếu bạn join `orders → order_items → payments`, một order sẽ thành:

```text id="ma7sb8"
3 x 2 = 6 rows
```

Nếu `revenue = 1,000,000`, sau join sai có thể thành:

```text id="1k2tl5"
6,000,000
```

Đây là **double counting**, hoặc chính xác hơn trong case này là **multiplicative counting**.

---

# 4. Fact Table

## 4.1. Fact table là gì?

Fact table lưu các sự kiện kinh doanh có thể đo lường được.

Ví dụ:

```text id="q2s63n"
Order placed
Payment made
Refund issued
Product viewed
Lead assigned
Call completed
Ticket created
Invoice generated
```

Fact table thường có:

```text id="c26f3b"
Business event key
Foreign keys tới dimensions
Timestamp/date
Measures
Status
Metadata
```

Ví dụ `fact_orders`:

```text id="kv9gmv"
order_id
customer_id
order_date
campaign_id
order_status
gross_amount
discount_amount
net_revenue
```

---

## 4.2. Các loại fact table phổ biến

Có 4 loại bạn nên biết.

---

## Loại 1: Transaction Fact

Đây là loại phổ biến nhất.

**Grain:** một dòng cho mỗi transaction/event.

Ví dụ:

```text id="jsskf0"
fact_orders              = 1 row per order
fact_payments            = 1 row per payment
fact_order_items         = 1 row per order item
fact_call_events         = 1 row per call
fact_lead_assignments    = 1 row per lead assignment
```

Dùng khi cần phân tích chi tiết từng sự kiện.

Ví dụ SQL:

```sql id="q5uw2g"
select
    order_date,
    count(*) as total_orders,
    sum(completed_revenue) as completed_revenue
from {{ ref('fact_orders') }}
group by order_date
```

---

## Loại 2: Periodic Snapshot Fact

**Grain:** một dòng cho một entity tại một thời điểm định kỳ.

Ví dụ:

```text id="wkf5oz"
1 row per customer per day
1 row per product per day
1 row per campaign per hour
1 row per account per month
```

Ví dụ:

```text id="e84n73"
fact_customer_daily_activity
```

| activity_date | customer_id | sessions | orders | revenue |
| ------------- | ----------: | -------: | -----: | ------: |
| 2026-07-01    |         101 |        3 |      1 |  200000 |
| 2026-07-02    |         101 |        2 |      1 |  300000 |

Dùng khi cần dashboard nhanh theo thời gian.

Ví dụ trong campaign/lead assignment:

```text id="3oj7gw"
fact_campaign_hourly_status
grain = 1 row per campaign per hour
```

---

## Loại 3: Accumulating Snapshot Fact

Dùng cho process có nhiều bước, ví dụ:

```text id="xj3ivn"
order created
payment completed
packed
shipped
delivered
returned
```

Một dòng đại diện cho một process, sau đó update các mốc thời gian.

Ví dụ:

```text id="u2dsyc"
fact_order_fulfillment
grain = 1 row per order fulfillment lifecycle
```

| order_id | created_at | paid_at    | shipped_at | delivered_at |
| -------: | ---------- | ---------- | ---------- | ------------ |
|        1 | 2026-07-01 | 2026-07-01 | 2026-07-02 | 2026-07-04   |

Dùng tốt cho:

```text id="f4d70f"
SLA tracking
Delivery lifecycle
Lead processing lifecycle
Ticket resolution lifecycle
```

---

## Loại 4: Factless Fact

Fact table không có measure số rõ ràng, chỉ ghi nhận sự kiện xảy ra.

Ví dụ:

```text id="03i6bi"
student attended class
user clicked banner
customer received campaign
doctor assigned to campaign
agent was active on shift
```

Ví dụ:

```text id="5m0kbq"
fact_campaign_exposures
grain = 1 row per customer per campaign exposure
```

Dùng để đếm:

```sql id="9zjodo"
select
    campaign_id,
    count(*) as exposed_customers
from fact_campaign_exposures
group by campaign_id
```

---

# 5. Dimension Table

## 5.1. Dimension là gì?

Dimension table chứa thông tin mô tả cho fact.

Ví dụ:

```text id="zr6kq5"
dim_customers
dim_products
dim_campaigns
dim_date
dim_agents
dim_teams
dim_locations
```

Dimension giúp người dùng slice/dice dữ liệu.

Ví dụ:

```sql id="b9c0h6"
select
    c.city,
    sum(f.completed_revenue) as revenue
from fact_orders f
join dim_customers c
    on f.customer_id = c.customer_id
group by c.city
```

---

## 5.2. Các loại dimension phổ biến

## Loại 1: Conformed Dimension

Dimension được dùng chung bởi nhiều fact.

Ví dụ:

```text id="p9w6xu"
dim_customers
```

được dùng bởi:

```text id="q2g24d"
fact_orders
fact_payments
fact_support_tickets
fact_campaign_exposures
```

Lợi ích:

```text id="hgcxgg"
Metric giữa nhiều business process có thể so sánh được
Customer definition nhất quán
Dashboard dễ join
```

---

## Loại 2: Slowly Changing Dimension Type 1

SCD Type 1 = overwrite giá trị cũ.

Ví dụ customer đổi city:

```text id="kisf61"
Old city: HCM
New city: Hanoi
```

Trong `dim_customers`, chỉ giữ Hanoi.

Dùng khi:

```text id="lsdqlw"
Không cần lịch sử
Giá trị cũ không quan trọng
Dữ liệu sai cần sửa
```

Ví dụ:

```text id="f2shdu"
customer email correction
spelling correction
current customer segment
```

---

## Loại 3: Slowly Changing Dimension Type 2

SCD Type 2 = giữ lịch sử thay đổi.

Ví dụ:

| customer_sk | customer_id | city  | valid_from | valid_to   | is_current |
| ----------: | ----------: | ----- | ---------- | ---------- | ---------- |
|           1 |         101 | HCM   | 2026-01-01 | 2026-03-31 | false      |
|           2 |         101 | Hanoi | 2026-04-01 | null       | true       |

Dùng khi:

```text id="qwul4b"
Cần biết tại thời điểm order, customer thuộc segment nào
Cần audit lịch sử
Cần phân tích thay đổi theo thời gian
```

Trong dbt, SCD Type 2 thường dùng `snapshot`.

---

## Loại 4: Degenerate Dimension

Là dimension attribute nằm luôn trong fact, không tách bảng riêng.

Ví dụ:

```text id="2du2m5"
order_number
invoice_number
ticket_number
transaction_reference
```

Vì nó không có nhiều attribute mô tả, không cần tạo `dim_order_number`.

Ví dụ:

```text id="o0zn8i"
fact_orders
- order_id
- order_number
- customer_id
- order_date
- revenue
```

---

## Loại 5: Junk Dimension

Gộp nhiều flag/status nhỏ thành một dimension.

Ví dụ các cờ:

```text id="stkp38"
is_first_order
is_discounted
is_gift
is_mobile_order
```

Thay vì để quá nhiều boolean trong fact, có thể tạo:

```text id="oyjvml"
dim_order_flags
```

| order_flag_key | is_first_order | is_discounted | is_gift | channel |
| -------------: | -------------- | ------------- | ------- | ------- |
|              1 | true           | false         | false   | web     |
|              2 | false          | true          | false   | mobile  |

Dùng khi có nhiều flag lặp lại và muốn giảm độ rộng fact table.

---

## Loại 6: Role-Playing Dimension

Cùng một dimension được dùng nhiều vai trò.

Ví dụ `dim_date` dùng cho:

```text id="zd6xo0"
order_date
payment_date
ship_date
delivery_date
refund_date
```

Trong fact:

```text id="5ncoia"
order_date_key
payment_date_key
ship_date_key
```

Tất cả đều join tới `dim_date`.

---

# 6. Star Schema

## 6.1. Star schema là gì?

Star schema là mô hình có fact ở trung tâm, dimension xung quanh.

```text id="y9e84c"
                  dim_customers
                       |
dim_products — fact_order_items — dim_date
                       |
                  dim_campaigns
                       |
                  dim_channels
```

Fact lưu sự kiện và số đo.
Dimension lưu ngữ cảnh.

---

## 6.2. Vì sao star schema phù hợp với BI?

Vì nó:

```text id="kd65v8"
Dễ hiểu cho analyst
Dễ query
Ít join phức tạp
Tối ưu cho aggregate
Dễ map vào BI tools
```

Ví dụ analyst muốn revenue by city and product:

```sql id="9za1k4"
select
    c.city,
    p.product_name,
    sum(f.item_revenue) as revenue
from fact_order_items f
join dim_customers c
    on f.customer_id = c.customer_id
join dim_products p
    on f.product_id = p.product_id
group by
    c.city,
    p.product_name
```

---

# 7. Case Study: Ecommerce Model

Giả sử raw data:

```text id="v460li"
raw_customers
raw_orders
raw_order_items
raw_products
raw_payments
```

Bạn muốn trả lời:

```text id="b5luh9"
1. Daily revenue
2. Revenue by product
3. Revenue by customer city
4. Payment success rate
5. Average order value
```

Không nên tạo một bảng khổng lồ:

```text id="sz9u8y"
orders_joined_everything
```

Vì:

```text id="i0wjg4"
order_items có grain khác orders
payments có grain khác orders
customer là dimension
product là dimension
```

Thiết kế tốt hơn:

```text id="x14l8f"
dim_customers
dim_products
fact_orders
fact_order_items
fact_payments
mart_daily_revenue
mart_product_revenue
```

---

# 8. Thiết kế grain cho từng bảng

## `fact_orders`

```text id="s2icsm"
Grain: 1 row per order
```

Cột:

```text id="azn0j1"
order_id
customer_id
order_date
order_status
gross_order_amount
discount_amount
completed_revenue
```

Dùng cho:

```text id="lxxf4n"
order count
average order value
completed revenue by day
cancelled order count
```

---

## `fact_order_items`

```text id="07n5ga"
Grain: 1 row per order item
```

Cột:

```text id="yhv8mr"
order_item_id
order_id
customer_id
product_id
order_date
quantity
item_amount
```

Dùng cho:

```text id="5rgghw"
product revenue
quantity sold
basket analysis
product category performance
```

---

## `fact_payments`

```text id="2hc8ps"
Grain: 1 row per payment transaction
```

Cột:

```text id="psmr53"
payment_id
order_id
payment_date
payment_status
payment_amount
successful_payment_amount
```

Dùng cho:

```text id="zq14a2"
payment success rate
payment amount by method
failed payment count
refund/payment reconciliation
```

---

# 9. Double Counting: lỗi phổ biến nhất

## 9.1. Ví dụ lỗi

Giả sử:

```text id="74xrtl"
Order 1 amount = 200,000
Order 1 có 2 order items
Order 1 có 2 payment attempts
```

Nếu join:

```sql id="xxpkwj"
select
    o.order_id,
    o.order_amount,
    oi.order_item_id,
    p.payment_id
from fact_orders o
left join fact_order_items oi
    on o.order_id = oi.order_id
left join fact_payments p
    on o.order_id = p.order_id
```

Kết quả:

| order_id | order_amount | order_item_id | payment_id |
| -------: | -----------: | ------------: | ---------: |
|        1 |       200000 |             1 |       9001 |
|        1 |       200000 |             1 |       9002 |
|        1 |       200000 |             2 |       9001 |
|        1 |       200000 |             2 |       9002 |

Nếu bạn sum:

```sql id="6qjx0d"
sum(order_amount)
```

thì ra:

```text id="2uh1y9"
800,000
```

Sai. Đúng là:

```text id="fthutp"
200,000
```

---

## 9.2. Nguyên nhân

Double counting xảy ra khi bạn join nhiều bảng có quan hệ:

```text id="3tkb0d"
1-to-many
many-to-many
```

mà không aggregate về cùng grain trước.

---

## 9.3. Cách phòng tránh

### Cách 1: Luôn ghi grain trong model docs

```yaml id="073b07"
models:
  - name: fact_payments
    description: >
      Payment fact table. Grain: one row per payment transaction.
```

---

### Cách 2: Aggregate trước khi join

Sai:

```sql id="nw15n3"
select
    o.order_date,
    sum(o.order_amount),
    sum(p.payment_amount)
from fact_orders o
join fact_payments p
    on o.order_id = p.order_id
group by o.order_date
```

Đúng hơn:

```sql id="k6vc9m"
with orders_daily as (

    select
        order_date,
        sum(order_amount) as gross_order_amount
    from {{ ref('fact_orders') }}
    group by order_date

),

payments_daily as (

    select
        payment_date,
        sum(payment_amount) as payment_amount
    from {{ ref('fact_payments') }}
    group by payment_date

)

select
    orders_daily.order_date,
    orders_daily.gross_order_amount,
    payments_daily.payment_amount
from orders_daily
left join payments_daily
    on orders_daily.order_date = payments_daily.payment_date
```

---

### Cách 3: Dùng đúng fact cho đúng câu hỏi

| Câu hỏi               | Dùng bảng                                             |
| --------------------- | ----------------------------------------------------- |
| Có bao nhiêu orders?  | `fact_orders`                                         |
| Product nào bán chạy? | `fact_order_items`                                    |
| Payment success rate? | `fact_payments`                                       |
| Revenue by customer?  | `fact_orders` hoặc `fact_order_items`, tùy definition |
| Quantity sold?        | `fact_order_items`                                    |

---

### Cách 4: Tạo marts đã aggregate sẵn

Ví dụ:

```text id="qefbj7"
mart_daily_revenue
mart_product_revenue
mart_customer_lifetime_value
mart_payment_success_daily
```

Dashboard nên query mart, không tự join facts phức tạp.

---

# 10. dbt Implementation: mở rộng project Bài 2

Ở Bài 2, bạn đã có:

```text id="8gqauu"
raw_customers
raw_orders
raw_payments
```

Bây giờ thêm:

```text id="b38ldj"
raw_products
raw_order_items
```

---

## 10.1. Thêm seed `raw_products.csv`

Tạo file:

```text id="p8n30d"
seeds/raw_products.csv
```

```csv id="1ck2ls"
id,product_name,category
501,Ensure Gold,Adult Nutrition
502,Glucerna,Diabetes Care
503,Pediasure,Child Nutrition
```

---

## 10.2. Thêm seed `raw_order_items.csv`

Tạo file:

```text id="d58gg0"
seeds/raw_order_items.csv
```

```csv id="bwyel1"
id,order_id,product_id,quantity,item_amount
1,1,501,2,200000
2,3,502,1,300000
3,4,503,5,500000
```

Chạy:

```bash id="2i8p7o"
dbt seed
```

---

## 10.3. Update `sources.yml`

```yaml id="jz10qs"
version: 2

sources:
  - name: raw
    schema: raw
    tables:
      - name: raw_customers
      - name: raw_orders
      - name: raw_payments
      - name: raw_products
      - name: raw_order_items
```

---

# 11. Thêm staging models

## `models/staging/stg_products.sql`

```sql id="gjgtva"
select
    cast(id as integer) as product_id,
    product_name,
    category as product_category
from {{ source('raw', 'raw_products') }}
```

---

## `models/staging/stg_order_items.sql`

```sql id="9n5i5p"
select
    cast(id as integer) as order_item_id,
    cast(order_id as integer) as order_id,
    cast(product_id as integer) as product_id,
    cast(quantity as integer) as quantity,
    cast(item_amount as decimal(18, 2)) as item_amount
from {{ source('raw', 'raw_order_items') }}
```

---

# 12. Thêm dimension product

## `models/marts/dim_products.sql`

```sql id="ka9z9s"
select
    product_id,
    product_name,
    product_category
from {{ ref('stg_products') }}
```

Grain:

```text id="eub3ac"
1 row per product
```

---

# 13. Thêm fact order items

## `models/marts/fact_order_items.sql`

```sql id="sb842m"
with order_items as (

    select *
    from {{ ref('stg_order_items') }}

),

orders as (

    select
        order_id,
        customer_id,
        order_date,
        order_status
    from {{ ref('stg_orders') }}

)

select
    order_items.order_item_id,
    order_items.order_id,
    orders.customer_id,
    order_items.product_id,
    orders.order_date,
    orders.order_status,
    order_items.quantity,
    order_items.item_amount,

    case
        when orders.order_status = 'completed'
            then order_items.item_amount
        else 0
    end as completed_item_revenue

from order_items
left join orders
    on order_items.order_id = orders.order_id
```

Grain:

```text id="gdjufj"
1 row per order item
```

Lưu ý: ở đây join với `stg_orders` để lấy `customer_id`, `order_date`, `order_status`. Vì `stg_orders` có grain 1 row per order nên không làm nhân dòng `order_items`.

---

# 14. Thêm product revenue mart

## `models/marts/mart_product_revenue.sql`

```sql id="1h8zcj"
with product_revenue as (

    select
        product_id,
        count(distinct order_id) as orders_containing_product,
        sum(quantity) as quantity_sold,
        sum(item_amount) as gross_item_amount,
        sum(completed_item_revenue) as completed_item_revenue
    from {{ ref('fact_order_items') }}
    group by product_id

)

select
    products.product_id,
    products.product_name,
    products.product_category,

    coalesce(product_revenue.orders_containing_product, 0) as orders_containing_product,
    coalesce(product_revenue.quantity_sold, 0) as quantity_sold,
    coalesce(product_revenue.gross_item_amount, 0) as gross_item_amount,
    coalesce(product_revenue.completed_item_revenue, 0) as completed_item_revenue

from {{ ref('dim_products') }} as products
left join product_revenue
    on products.product_id = product_revenue.product_id
```

Grain:

```text id="vxiz0d"
1 row per product
```

---

# 15. Update marts schema tests

Thêm vào `models/marts/schema.yml`:

```yaml id="20if3e"
  - name: dim_products
    description: Product dimension. Grain: one row per product.
    columns:
      - name: product_id
        tests:
          - not_null
          - unique

  - name: fact_order_items
    description: Order item fact table. Grain: one row per product item within an order.
    columns:
      - name: order_item_id
        tests:
          - not_null
          - unique
      - name: order_id
        tests:
          - not_null
          - relationships:
              to: ref('fact_orders')
              field: order_id
      - name: product_id
        tests:
          - not_null
          - relationships:
              to: ref('dim_products')
              field: product_id

  - name: mart_product_revenue
    description: Product revenue mart. Grain: one row per product.
    columns:
      - name: product_id
        tests:
          - not_null
          - unique
```

Chạy:

```bash id="bntzd3"
dbt build
```

---

# 16. Expected output: `mart_product_revenue`

| product_id | product_name | product_category | orders_containing_product | quantity_sold | gross_item_amount | completed_item_revenue |
| ---------: | ------------ | ---------------- | ------------------------: | ------------: | ----------------: | ---------------------: |
|        501 | Ensure Gold  | Adult Nutrition  |                         1 |             2 |            200000 |                 200000 |
|        502 | Glucerna     | Diabetes Care    |                         1 |             1 |            300000 |                 300000 |
|        503 | Pediasure    | Child Nutrition  |                         1 |             5 |            500000 |                 500000 |

---

# 17. Bài tập: cố ý tạo lỗi double counting

Đây là bài rất quan trọng.

Tạo model sai:

```text id="7xay9i"
models/marts/bad_order_payment_product_join.sql
```

```sql id="ya0idd"
select
    orders.order_id,
    orders.order_amount,
    order_items.order_item_id,
    payments.payment_id,
    payments.payment_amount
from {{ ref('fact_orders') }} as orders
left join {{ ref('fact_order_items') }} as order_items
    on orders.order_id = order_items.order_id
left join {{ ref('fact_payments') }} as payments
    on orders.order_id = payments.order_id
```

Sau đó query:

```sql id="3j7w4h"
select
    sum(order_amount) as wrong_order_amount,
    sum(payment_amount) as wrong_payment_amount
from bad_order_payment_product_join
```

Với dataset nhỏ hiện tại có thể chưa thấy sai mạnh vì mỗi order đang khá đơn giản. Hãy sửa seed để order 1 có 2 items:

```csv id="m2h1xy"
id,order_id,product_id,quantity,item_amount
1,1,501,1,100000
2,1,502,1,100000
3,3,502,1,300000
4,4,503,5,500000
```

Và thêm payment attempt thứ 2 cho order 1:

```csv id="u1w1bn"
id,order_id,payment_date,payment_status,payment_amount
9001,1,2026-07-01,Success,200000
9005,1,2026-07-01,Failed,200000
9002,2,2026-07-01,Failed,150000
9003,3,2026-07-02,Success,300000
9004,4,2026-07-02,Success,500000
```

Chạy lại:

```bash id="d9q27s"
dbt seed --full-refresh
dbt build
```

Lúc này order 1 có:

```text id="tc0pk6"
2 items
2 payments
```

Join sai sẽ tạo:

```text id="7u6ssv"
2 x 2 = 4 rows
```

Đây là cách trực quan nhất để hiểu double counting.

---

# 18. Cách fix bằng aggregate cùng grain

Thay vì join raw facts trực tiếp, hãy aggregate trước.

Ví dụ tạo model:

```text id="sd19m8"
models/marts/mart_order_reconciliation.sql
```

```sql id="r8so4t"
with order_item_amounts as (

    select
        order_id,
        sum(item_amount) as item_total_amount
    from {{ ref('fact_order_items') }}
    group by order_id

),

payment_amounts as (

    select
        order_id,
        sum(successful_payment_amount) as successful_payment_amount,
        count(*) as payment_attempts
    from {{ ref('fact_payments') }}
    group by order_id

)

select
    orders.order_id,
    orders.customer_id,
    orders.order_date,
    orders.order_status,
    orders.order_amount,

    coalesce(order_item_amounts.item_total_amount, 0) as item_total_amount,
    coalesce(payment_amounts.successful_payment_amount, 0) as successful_payment_amount,
    coalesce(payment_amounts.payment_attempts, 0) as payment_attempts,

    orders.order_amount - coalesce(order_item_amounts.item_total_amount, 0) as order_vs_item_diff,
    orders.completed_revenue - coalesce(payment_amounts.successful_payment_amount, 0) as revenue_vs_payment_diff

from {{ ref('fact_orders') }} as orders
left join order_item_amounts
    on orders.order_id = order_item_amounts.order_id
left join payment_amounts
    on orders.order_id = payment_amounts.order_id
```

Grain:

```text id="dbwo2j"
1 row per order
```

Ở đây:

```text id="cdx1wp"
fact_order_items được aggregate về order_id
fact_payments được aggregate về order_id
sau đó mới join với fact_orders
```

Đây là pattern cực kỳ quan trọng.

---

# 19. Thêm data quality test cho reconciliation

Tạo singular test:

```text id="fijyaz"
tests/assert_order_amount_matches_items.sql
```

```sql id="z1ublz"
select *
from {{ ref('mart_order_reconciliation') }}
where order_vs_item_diff != 0
```

Tạo test payment reconciliation:

```text id="q0pwnb"
tests/assert_completed_revenue_matches_successful_payment.sql
```

```sql id="m2u2db"
select *
from {{ ref('mart_order_reconciliation') }}
where revenue_vs_payment_diff != 0
  and order_status = 'completed'
```

Chạy:

```bash id="3rfaxr"
dbt test
```

Nếu test fail, đó là tín hiệu tốt: dữ liệu hoặc logic có vấn đề.

---

# 20. Checklist thiết kế fact table

Trước khi tạo fact table, luôn hỏi:

```text id="n6c6ug"
1. Một dòng trong bảng này là gì?
2. Business event là gì?
3. Primary key là gì?
4. Có thể có duplicate event không?
5. Measures nào additive?
6. Measures nào semi-additive?
7. Measures nào non-additive?
8. Dimension keys nào cần gắn vào fact?
9. Table này có join many-to-many với fact khác không?
10. Người dùng sẽ query bảng này cho câu hỏi nào?
```

---

# 21. Additive, Semi-additive, Non-additive Measures

## Additive measure

Có thể sum theo mọi dimension.

Ví dụ:

```text id="1nqucy"
revenue
quantity
payment_amount
call_duration
lead_count
```

---

## Semi-additive measure

Có thể sum theo một số dimension, nhưng không nên sum theo time.

Ví dụ:

```text id="g6h12o"
account_balance
inventory_on_hand
active_subscribers
```

Bạn có thể sum inventory theo product tại một ngày, nhưng không nên sum inventory của 30 ngày để ra “monthly inventory”.

---

## Non-additive measure

Không nên sum trực tiếp.

Ví dụ:

```text id="ytfeot"
conversion_rate
churn_rate
average_order_value
margin_percent
payment_success_rate
```

Cách tốt hơn là lưu numerator/denominator:

```text id="jr0p39"
conversion_count
total_leads
```

Sau đó tính:

```sql id="qk155p"
conversion_count * 1.0 / nullif(total_leads, 0)
```

Không nên average các rate đã tính sẵn nếu denominator khác nhau.

---

# 22. Ví dụ sai: average conversion rate

Sai:

| team | conversion_rate |
| ---- | --------------: |
| A    |             50% |
| B    |             10% |

Tính average:

```text id="tqw65p"
(50% + 10%) / 2 = 30%
```

Nhưng nếu:

```text id="09cot0"
Team A: 1 conversion / 2 leads = 50%
Team B: 10 conversions / 100 leads = 10%
```

Conversion rate đúng toàn bộ:

```text id="0l48j6"
(1 + 10) / (2 + 100) = 10.78%
```

Vì vậy fact/mart nên lưu:

```text id="z86spu"
conversion_count
lead_count
```

Không chỉ lưu mỗi:

```text id="tzzkp5"
conversion_rate
```

---

# 23. Áp dụng vào use case campaign / lead assignment

Với context data engineering thực tế như campaign assignment, bạn có thể model như sau:

## Dimensions

```text id="wmnptl"
dim_campaigns
dim_subjects
dim_teams
dim_agents
dim_date
dim_platforms
dim_brands
```

## Facts

```text id="o93tjb"
fact_lead_assignments
grain = 1 row per lead assignment event

fact_campaign_hourly_status
grain = 1 row per campaign per subject per hour

fact_agent_daily_performance
grain = 1 row per agent per day
```

## Marts

```text id="d2ot6n"
mart_campaign_assignment_summary
mart_team_assignment_fairness
mart_agent_performance_daily
```

Example `fact_lead_assignments`:

```text id="lk79bs"
assignment_id
lead_id
campaign_id
subject_id
team_id
agent_id
assigned_at
assignment_mode
frequency_mode
source_group
```

Measures:

```text id="cj4vvi"
assigned_lead_count = 1
```

Example `mart_team_assignment_fairness`:

```text id="2ieb2w"
period_key
campaign_id
subject_id
team_id
target_allocation_percent
actual_assigned_leads
expected_assigned_leads
allocation_diff
```

Đây là portfolio idea rất tốt vì nó gắn với bài toán thật: fairness, allocation, monitoring, reconciliation.

---

# 24. dbt model naming convention

Một convention dễ dùng:

```text id="ffplyt"
stg_<source_entity>
int_<business_process>
dim_<business_entity>
fact_<business_event>
mart_<business_area>_<metric>
```

Ví dụ:

```text id="42h2xf"
stg_orders
stg_order_items
int_order_payment_summary
dim_customers
dim_products
fact_orders
fact_order_items
fact_payments
mart_daily_revenue
mart_product_revenue
mart_customer_lifetime_value
```

Không nên đặt:

```text id="bsuzr5"
final_table
new_orders
orders_v2
query_for_dashboard
tmp_revenue
```

---

# 25. Bài tập cuối bài

Mở rộng project Bài 2 thành full ecommerce star schema.

## Yêu cầu

Tạo thêm:

```text id="p3c0gj"
raw_products.csv
raw_order_items.csv

stg_products
stg_order_items

dim_products
fact_order_items

mart_product_revenue
mart_order_reconciliation
```

Thêm tests:

```text id="miitwc"
dim_products.product_id unique not_null
fact_order_items.order_item_id unique not_null
fact_order_items.order_id relationships to fact_orders
fact_order_items.product_id relationships to dim_products
mart_product_revenue.product_id unique not_null
```

Thêm singular tests:

```text id="niedce"
assert_order_amount_matches_items
assert_completed_revenue_matches_successful_payment
```

---

# 26. Câu hỏi tự kiểm tra

Bạn đạt bài 3 nếu trả lời được:

```text id="z1zy25"
1. Grain là gì?
2. Vì sao grain quan trọng hơn tên bảng?
3. Transaction fact khác periodic snapshot fact như thế nào?
4. Accumulating snapshot fact dùng khi nào?
5. Factless fact là gì?
6. Conformed dimension là gì?
7. SCD Type 1 khác SCD Type 2 như thế nào?
8. Degenerate dimension là gì?
9. Vì sao join fact_orders với fact_order_items có thể gây double counting?
10. Cách fix double counting bằng aggregate trước khi join là gì?
11. Vì sao không nên average conversion_rate trực tiếp?
12. Khi nào nên tạo mart thay vì để dashboard tự join?
```

---

# 27. Ghi nhớ quan trọng

```text id="78bdbd"
Dimensional modeling không phải là normalize database.
Nó là thiết kế dữ liệu để phân tích dễ, đúng và nhanh.

Fact table phải có grain rõ ràng.

Dimension table mô tả context cho fact.

Không join nhiều fact table khác grain rồi sum trực tiếp.

Metric dạng rate nên tính từ numerator và denominator.

Marts nên phục vụ câu hỏi business cụ thể.

dbt giúp bạn biến các nguyên tắc này thành code có version control, tests, docs và lineage.
```