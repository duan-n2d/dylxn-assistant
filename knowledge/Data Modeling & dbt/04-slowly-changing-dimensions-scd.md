---
title: "Data Modeling & dbt - Bài 4: Slowly Changing Dimensions (SCD Type 1, Type 2, Type 3) với dbt"
type: tutorial
domain: data-engineering
level: intermediate
series: data-modeling-dbt
order: 4
tags:
  - data-modeling
  - dimensional-modeling
  - slowly-changing-dimension
  - scd-type-1
  - scd-type-2
  - scd-type-3
  - dbt-snapshot
  - merge
  - iceberg
---

# Data Modeling & dbt

## Bài 4 — Slowly Changing Dimensions: Type 1, Type 2, Type 3

Ở Bài 3, bạn đã gặp khái niệm **Slowly Changing Dimension (SCD)** ở mức định nghĩa. Bài này đi sâu vào cách **implement** từng loại trên project dbt + DuckDB đang có:

```text
seeds/raw_customers.csv
  ↓
stg_customers
  ↓
dim_customers   ← bài này: xử lý khi thuộc tính customer thay đổi
  ↓
fact_orders
```

Câu hỏi trung tâm của SCD:

> **Khi một thuộc tính của dimension thay đổi (customer chuyển city, đổi segment), mình xử lý giá trị cũ như thế nào?**

Ba lựa chọn phổ biến:

| Loại | Cách xử lý | Lịch sử giữ lại |
| ---- | ---------- | --------------- |
| Type 1 | Ghi đè giá trị cũ | Không có |
| Type 2 | Thêm row mới, đóng row cũ | Toàn bộ |
| Type 3 | Thêm cột `previous_*` | Chỉ 1 bước trước |

---

# 1. Type 1 SCD

## Type 1 SCD — overwrite giá trị cũ (dbt, MERGE INTO, Iceberg)

**Type 1 SCD là gì?** Đây là cách xử lý thay đổi đơn giản nhất: khi source báo thuộc tính mới, mình **cập nhật đè (overwrite)** lên row hiện có trong dimension. Dimension luôn có đúng 1 row cho mỗi business key và chỉ phản ánh **trạng thái hiện tại**.

Ví dụ customer 101 chuyển từ `HCM` sang `Hanoi`:

```text
Trước:  customer_id=101 | city=HCM
Sau:    customer_id=101 | city=Hanoi     (giá trị HCM biến mất khỏi dim)
```

**Cách làm trong dbt.** Thực tế, `dim_customers` ở Bài 2 (materialized `table`) đã là Type 1: mỗi lần `dbt run`, bảng được rebuild từ `stg_customers` nên luôn mang giá trị mới nhất. Khi bảng lớn và muốn chỉ update phần thay đổi, dùng incremental model với `unique_key`:

```sql
-- models/marts/dim_customers_type1.sql
{{
    config(
        materialized='incremental',
        unique_key='customer_id',
        incremental_strategy='merge'   -- hoặc 'delete+insert' tùy adapter
    )
}}

select
    customer_id,
    customer_name,
    city,
    customer_updated_at
from {{ ref('stg_customers') }}

{% if is_incremental() %}
where customer_updated_at > (select max(customer_updated_at) from {{ this }})
{% endif %}
```

Ở mức SQL thuần, câu lệnh tương ứng là `MERGE INTO` (hỗ trợ trên Snowflake, BigQuery, Databricks, Spark/Iceberg, và các bản DuckDB mới):

```sql
merge into analytics.dim_customers as t
using staging.stg_customers as s
    on t.customer_id = s.customer_id
when matched and (t.city <> s.city or t.customer_name <> s.customer_name) then
    update set city = s.city, customer_name = s.customer_name
when not matched then
    insert (customer_id, customer_name, city)
    values (s.customer_id, s.customer_name, s.city);
```

**Lưu ý với Apache Iceberg / Delta.** Trên table format có snapshot, `MERGE INTO` tạo một snapshot mới; snapshot cũ **vẫn chứa giá trị HCM** cho tới khi bị expire. Time travel (`FOR VERSION AS OF ...`) có thể đọc lại giá trị cũ, nhưng đó là cơ chế vận hành/khôi phục, **không phải** thay thế cho Type 2 — snapshot sẽ bị dọn theo retention policy và không gắn với business time.

**Khi nào dùng:** sửa lỗi dữ liệu (typo tên, email sai), thuộc tính mà business chỉ quan tâm giá trị hiện tại (số điện thoại, current segment), dimension nhỏ và đơn giản.

**Trade-off / pitfall:**

```text
- Report lịch sử bị "viết lại": doanh thu tháng 1 của customer 101 giờ sẽ hiện ở Hanoi
- Aggregate đã cache (mart_revenue_by_city) không khớp nếu không rebuild lại
- Không audit được "trước đây giá trị là gì"
- Nếu nghi ngờ sau này cần lịch sử → làm Type 2 ngay từ đầu, vì lịch sử đã mất thì không lấy lại được
```

---

# 2. Type 2 SCD (nhắc lại ngắn)

## Type 2 SCD với dbt snapshot

Type 2 giữ **toàn bộ lịch sử** bằng cách thêm row mới mỗi lần thay đổi, kèm `valid_from` / `valid_to`. Trong dbt, công cụ chuẩn là `snapshot`:

```sql
-- snapshots/customers_snapshot.sql
{% snapshot customers_snapshot %}
{{
    config(
        target_schema='snapshots',
        unique_key='customer_id',
        strategy='check',
        check_cols=['city', 'customer_segment']
    )
}}
select * from {{ ref('stg_customers') }}
{% endsnapshot %}
```

Chạy `dbt snapshot` định kỳ; dbt tự thêm `dbt_valid_from`, `dbt_valid_to`, `dbt_scd_id`. Sau đó `dim_customers` đọc từ snapshot, tạo surrogate key (xem Bài 5) và fact join theo `order_date between valid_from and coalesce(valid_to, '9999-12-31')`. Nếu source có cột `updated_at` tin cậy, dùng `strategy='timestamp'` thay vì `check`.

---

# 3. Type 3 SCD

## Type 3 SCD — giữ giá trị trước đó trong cột riêng

**Type 3 SCD là gì?** Thay vì thêm row (Type 2) hay ghi đè (Type 1), Type 3 **thêm cột** để lưu giá trị trước đó ngay trên cùng row. Dimension vẫn 1 row / business key, nhưng có thêm `previous_<attribute>` (và thường là ngày thay đổi).

| customer_id | city  | previous_city | city_changed_at |
| ----------: | ----- | ------------- | --------------- |
| 101 | Hanoi | HCM | 2026-04-01 |
| 102 | Hanoi | null | null |

**Cách hoạt động.** Khi thuộc tính đổi: copy giá trị hiện tại sang `previous_city`, ghi giá trị mới vào `city`. Lần đổi tiếp theo, giá trị `previous_city` cũ sẽ bị mất — vì vậy Type 3 chỉ giữ **lịch sử giới hạn** (thường 1 bước).

**Cách làm trong dbt.** Cách gọn nhất là derive Type 3 từ snapshot Type 2 (nguồn sự thật đầy đủ), dùng window function:

```sql
-- models/marts/dim_customers_type3.sql
with history as (
    select
        customer_id,
        city,
        dbt_valid_from,
        dbt_valid_to,
        lag(city) over (
            partition by customer_id order by dbt_valid_from
        ) as previous_city
    from {{ ref('customers_snapshot') }}
)

select
    customer_id,
    city,
    previous_city,
    case when previous_city is not null then dbt_valid_from end as city_changed_at
from history
where dbt_valid_to is null      -- chỉ lấy row hiện tại
```

**Khi nào dùng:** business muốn so sánh "trước vs sau" cho một thay đổi có kế hoạch — ví dụ tái cơ cấu vùng bán hàng (`current_region` vs `previous_region`), đổi tên category sản phẩm, chuyển agent sang team mới. Report có thể hiển thị doanh thu theo cả cách phân vùng cũ và mới song song.

**Trade-off / pitfall:**

```text
- Chỉ giữ được 1 (hoặc N cố định) giá trị cũ → không thay được Type 2 cho audit
- Mỗi thuộc tính cần theo dõi lại thêm cột → schema phình nhanh
- Không biết giá trị cũ có hiệu lực TỪ khi nào nếu không lưu thêm ngày
- Fact không thể join "đúng thời điểm" như Type 2
```

---

# 4. Chọn loại SCD nào?

```text
Chỉ cần giá trị hiện tại / sửa lỗi          → Type 1
Cần biết giá trị tại thời điểm xảy ra fact  → Type 2 (dbt snapshot)
Cần so sánh trước/sau một lần thay đổi      → Type 3
```

Thực tế hay kết hợp: một dimension có cột Type 1 (email), cột Type 2 (segment), và lưu snapshot để có thể derive Type 3 khi cần. Nguyên tắc an toàn: **luôn snapshot raw dimension sớm**, vì từ Type 2 có thể suy ra Type 1 và Type 3, còn chiều ngược lại thì không.

---

# 5. Câu hỏi tự kiểm tra

```text
1. Vì sao dim_customers materialized table ở Bài 2 là SCD Type 1?
2. Time travel trên Iceberg có thay được SCD Type 2 không? Vì sao?
3. Type 3 khác Type 2 ở điểm nào về số row và số cột?
4. Làm sao derive Type 3 từ dbt snapshot?
```
