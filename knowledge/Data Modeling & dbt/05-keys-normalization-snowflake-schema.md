---
title: "Data Modeling & dbt - Bài 5: Natural Key, Surrogate Key, 3NF và Snowflake Schema"
type: tutorial
domain: data-engineering
level: intermediate
series: data-modeling-dbt
order: 5
tags:
  - data-modeling
  - natural-key
  - surrogate-key
  - dbt-utils
  - normalization
  - 3nf
  - snowflake-schema
  - star-schema
  - data-vault
---

# Data Modeling & dbt

## Bài 5 — Keys và Normalization: Natural Key, Surrogate Key, 3NF, Snowflake Schema

Bài 4 dùng `customer_sk` cho dimension Type 2 nhưng chưa giải thích nó đến từ đâu. Bài này trả lời hai câu hỏi thiết kế nền tảng:

```text
1. Row trong dimension được định danh bằng key nào? (natural vs surrogate)
2. Dữ liệu nên normalized tới mức nào? (3NF vs star vs snowflake schema)
```

---

# 1. Natural Key vs Surrogate Key

## Natural Key (khoá tự nhiên) — natural keys vs surrogate keys

**Natural key là gì?** Natural key (còn gọi business key) là cột hoặc tổ hợp cột **có ý nghĩa nghiệp vụ** và đã tồn tại trong thế giới thật hoặc hệ thống nguồn, đủ để phân biệt một entity. Ví dụ: email khách hàng, số CCCD, mã SKU, số VIN của xe, `order_id` do backend sinh ra, hoặc tổ hợp `(source_system, customer_id)`.

Trong project mẫu, `customer_id` trong `raw_customers.csv` là natural key nhìn từ phía warehouse: nó do hệ thống nguồn cấp, không phải do dbt sinh.

**Ưu điểm:**

```text
- Dễ hiểu, dễ debug: nhìn là biết row nào
- Join trực tiếp với source, không cần lookup
- Không phải duy trì cơ chế sinh key
```

**Nhược điểm / pitfall:**

```text
- Có thể thay đổi: khách đổi email, SKU bị đánh lại mã
- Có thể trùng giữa nhiều hệ thống: customer_id=101 ở CRM khác customer_id=101 ở app
- Có thể null hoặc đến muộn (late-arriving)
- Không đủ để định danh row khi dimension là SCD Type 2 (1 customer → nhiều version)
- Composite natural key dài làm join chậm và dễ viết sai
```

**Khi nào dùng natural key làm key chính?** Staging model và fact grain (ví dụ `fact_orders` unique theo `order_id`), dimension Type 1 đơn giản với một nguồn duy nhất và key ổn định. Ngay cả khi dùng surrogate key, **luôn giữ natural key như một cột** trong dimension để trace về source và test uniqueness:

```yaml
# models/marts/schema.yml
models:
  - name: dim_customers
    columns:
      - name: customer_id        # natural key
        tests:
          - not_null
          - unique               # chỉ đúng nếu dim là Type 1
```

**So sánh nhanh:**

| | Natural key | Surrogate key |
| - | - | - |
| Nguồn gốc | Từ nghiệp vụ / source | Do warehouse sinh |
| Ý nghĩa | Có | Không |
| Ổn định | Có thể đổi | Ổn định theo quy ước |
| Dùng cho SCD Type 2 | Không đủ | Có (mỗi version 1 key) |

---

## Surrogate Key — cách generate surrogate key (dbt, DuckDB, Iceberg)

**Surrogate key là gì?** Surrogate key là identifier **do hệ thống sinh ra, không mang ý nghĩa nghiệp vụ**, dùng làm primary key của dimension và foreign key trong fact (`customer_sk`, `product_sk`). Nó tách warehouse khỏi sự thay đổi của source.

**Vì sao cần:**

```text
- Gộp nhiều nguồn: (crm, 101) và (app, 101) thành 2 key khác nhau
- SCD Type 2: mỗi version của customer 101 có một customer_sk riêng
- Cô lập khỏi việc source đổi format key
- Có thể tạo row "unknown" (ví dụ sk = -1 hoặc hash của 'unknown') cho fact thiếu dimension
```

**Cách generate — 3 kiểu phổ biến:**

1. **Sequence / identity / autoincrement** (truyền thống trong RDBMS). Nhanh, gọn, nhưng phụ thuộc thứ tự load, khó dùng khi rebuild bảng (dbt `table` sẽ sinh số khác mỗi lần) và khó song song hoá trên engine phân tán.

2. **`row_number()`** trong SQL: dễ, nhưng **không ổn định** giữa các lần chạy — thêm 1 customer là key của các row khác có thể đổi, làm hỏng fact đã build.

3. **Hash key** (cách khuyến nghị trong dbt và lakehouse): hash natural key (+ cột phân biệt version) thành chuỗi. Deterministic: cùng input → cùng key, bất kể chạy lại bao nhiêu lần, chạy trên engine nào.

```sql
-- models/marts/dim_customers.sql (dùng dbt_utils)
select
    {{ dbt_utils.generate_surrogate_key(['customer_id', 'dbt_valid_from']) }} as customer_sk,
    customer_id,                      -- giữ natural key
    city,
    dbt_valid_from as valid_from,
    dbt_valid_to   as valid_to
from {{ ref('customers_snapshot') }}
```

Macro này về cơ bản là `md5(cast(coalesce(cast(customer_id as varchar), '_dbt_utils_surrogate_key_null_') || '-' || ...))`. Viết tay trên DuckDB:

```sql
select md5(concat_ws('|', 'crm', cast(customer_id as varchar))) as customer_sk, *
from stg_customers;
```

**Trên Apache Iceberg / lakehouse:** Iceberg không có sequence hay autoincrement tập trung như RDBMS, và job Spark/Trino ghi song song nên khó sinh số tăng dần an toàn. Vì vậy hash key (MD5/SHA-256, hoặc `xxhash64` nếu cần kiểu số) là lựa chọn phổ biến. Iceberg cũng không enforce primary key/unique (identifier fields chỉ là metadata), nên uniqueness phải kiểm tra bằng dbt test.

**Pitfalls:**

```text
- Quên chuẩn hoá input trước khi hash ('HCM ' vs 'HCM', kiểu int vs string) → key khác nhau
- Không đưa source_system vào hash khi gộp nhiều nguồn → collision nghiệp vụ
- Hash string dài (32 ký tự) tốn storage hơn bigint; chấp nhận được với columnar storage
- Fact phải lookup đúng version (Type 2) khi lấy customer_sk, không join chỉ bằng customer_id
```

---

# 2. Normalization và Third Normal Form (3NF)

## Third Normal Form (3NF) — normalization và vị trí của 3NF trong warehouse/lakehouse

**3NF là gì?** Third normal form là mức chuẩn hoá schema trong đó: bảng đạt 2NF, và **mọi cột không phải key chỉ phụ thuộc vào key, không phụ thuộc bắc cầu qua cột non-key khác**. Câu nhớ kinh điển: "the key, the whole key, and nothing but the key".

Đi từng bước với một bảng order "phẳng":

```text
order_id | customer_id | customer_city | product_ids     | product_names
1        | 101         | HCM           | P1,P2           | Sữa A,Sữa B
```

- **1NF**: mỗi ô là giá trị nguyên tử, không có list → tách thành 1 row / (order, product).
- **2NF**: với key ghép `(order_id, product_id)`, `product_name` chỉ phụ thuộc `product_id` (một phần key) → tách `products`.
- **3NF**: `customer_city` phụ thuộc `customer_id`, mà `customer_id` phụ thuộc `order_id` → phụ thuộc bắc cầu → tách `customers`.

Kết quả 3NF:

```sql
create table customers   (customer_id int primary key, city varchar);
create table products    (product_id varchar primary key, product_name varchar);
create table orders      (order_id int primary key, customer_id int references customers);
create table order_items (order_id int references orders, product_id varchar references products,
                          quantity int, primary key (order_id, product_id));
```

**Vì sao OLTP dùng 3NF:** mỗi fact được lưu đúng 1 chỗ → update một nơi, tránh update/insert/delete anomaly, ghi nhanh và nhất quán.

**Vì sao marts thường KHÔNG dùng 3NF:** query phân tích phải join nhiều bảng, khó cho analyst. Dimensional model (star schema) cố ý denormalize để đọc nhanh, dễ hiểu.

**3NF còn hợp ở đâu trong warehouse/lakehouse:**

```text
- Hệ thống nguồn (OLTP) và raw/staging layer: giữ cấu trúc như source
- Lớp integration kiểu Inmon (Corporate Information Factory): enterprise model 3NF, rồi build data mart
- Data Vault: hub/link/satellite là một dạng normalize cao, tối ưu cho tích hợp nhiều nguồn và lưu lịch sử
- Master/reference data cần một nguồn sự thật duy nhất
```

**Pitfall:** áp 3NF cho marts phục vụ BI → dashboard 8–10 join, chậm và dễ double counting; ngược lại, denormalize ở staging làm mất khả năng trace về source.

---

# 3. Snowflake Schema

## Snowflake Schema — so sánh snowflake schema với star schema

**Snowflake schema là gì?** Là một biến thể của dimensional model, trong đó **dimension table được normalize** thành nhiều bảng con theo hierarchy. Sơ đồ toả nhánh như bông tuyết, nên có tên này (không liên quan tới nền tảng Snowflake).

Star schema (Bài 3):

```text
fact_order_items → dim_products (product_id, product_name, category_name, category_group)
```

Snowflake schema:

```text
fact_order_items → dim_products (product_id, product_name, category_id)
                        → dim_categories (category_id, category_name, category_group_id)
                              → dim_category_groups (category_group_id, category_group_name)
```

Query doanh thu theo category group trên snowflake schema:

```sql
select g.category_group_name, sum(f.revenue) as revenue
from fact_order_items f
join dim_products p        on f.product_id = p.product_id
join dim_categories c      on p.category_id = c.category_id
join dim_category_groups g on c.category_group_id = g.category_group_id
group by 1;
```

Trên star schema chỉ cần 1 join tới `dim_products`.

**Ưu điểm:**

```text
- Ít lặp dữ liệu trong dimension (tên category không lặp trên mỗi product)
- Update hierarchy ở một chỗ
- Phù hợp dimension rất lớn có hierarchy sâu, hoặc khi nhiều dimension dùng chung một sub-dimension (ví dụ dim_geography)
```

**Nhược điểm:**

```text
- Nhiều join hơn → query khó viết, BI tool khó model
- Với columnar warehouse hiện đại, tiết kiệm storage gần như không đáng kể
- Dễ join sai khi hierarchy có nhánh null
```

**Khi nào dùng:** mặc định dùng star schema cho marts. Chọn snowflake khi có sub-dimension dùng chung thật sự, hierarchy thay đổi thường xuyên cần quản lý tập trung, hoặc tool OLAP yêu cầu. Trong dbt, một cách cân bằng là giữ các bảng normalized ở lớp intermediate (`int_categories`) rồi **flatten** vào `dim_products` ở lớp marts.

---

# 4. Câu hỏi tự kiểm tra

```text
1. Vì sao customer_id không đủ làm primary key cho dim_customers Type 2?
2. Vì sao row_number() không phải cách tốt để tạo surrogate key?
3. Cho ví dụ phụ thuộc bắc cầu vi phạm 3NF.
4. Khi nào snowflake schema đáng để thêm join?
```
