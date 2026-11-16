---
title: "Data Modeling & dbt - Bài 9: Master Data Management (MDM) và golden record"
type: tutorial
domain: data-engineering
level: intermediate
series: data-modeling-dbt
order: 9
tags:
  - data-modeling
  - master-data-management
  - mdm
  - golden-record
  - entity-resolution
  - data-governance
  - conformed-dimension
  - lakehouse
---

# Data Modeling & dbt

## Bài 9 — Master Data Management (MDM): xây golden record cho customer và product

Bài 5 nói về surrogate key khi gộp nhiều nguồn, Bài 8 nói về các database nguồn khác nhau. Câu hỏi tiếp theo: **cùng một khách hàng xuất hiện ở CRM, app và hệ thống CSKH với ID khác nhau — làm sao biết đó là một người?** Đó là bài toán của MDM.

---

# 1. Master Data Management

## Master Data Management (MDM) là gì?

**Master data** là dữ liệu mô tả các entity cốt lõi, dùng chung giữa nhiều hệ thống và ít thay đổi so với transaction: customer, product, supplier, employee, location. **Master Data Management (MDM)** là tập hợp quy trình, quy tắc và công cụ để tạo và duy trì **một bản ghi đáng tin cậy duy nhất — golden record** — cho mỗi entity, kèm ánh xạ (cross-reference) về ID ở từng hệ thống nguồn.

Ví dụ customer "Nguyễn An" trong 3 nguồn:

| source | source_id | name | email | phone | city |
| ------ | --------- | ---- | ----- | ----- | ---- |
| crm | C-88 | Nguyen An | an@mail.com | null | HCM |
| app | 101 | An Nguyen | AN@mail.com | 0901234567 | Ho Chi Minh |
| support | T-5 | An | null | 0901 234 567 | null |

Golden record mong muốn:

| master_customer_id | name | email | phone | city |
| ------------------ | ---- | ----- | ----- | ---- |
| MC-0001 | Nguyen An | an@mail.com | 0901234567 | HCM |

**Quy trình MDM gồm các bước:**

```text
1. Standardize   → chuẩn hoá: lowercase email, bỏ khoảng trắng phone, map 'Ho Chi Minh' → 'HCM'
2. Match         → entity resolution: deterministic (email trùng) hoặc probabilistic/fuzzy (tên + phone gần giống)
3. Merge         → survivorship rules: chọn giá trị "thắng" cho từng thuộc tính
4. Cross-reference → bảng map (source, source_id) → master_id
5. Steward       → data steward xử lý case không chắc chắn, sửa match sai
```

**Các kiểu triển khai MDM (implementation styles):**

```text
Registry       → chỉ lưu cross-reference + match, không sửa nguồn; nhẹ nhất, hợp cho analytics
Consolidation  → gom về hub để tạo golden record phục vụ báo cáo; nguồn không nhận lại dữ liệu
Coexistence    → golden record được đồng bộ ngược về các nguồn
Centralized    → MDM hub là nơi tạo/sửa master data duy nhất; nguồn chỉ đọc
```

Với team analytics trên warehouse/lakehouse, **registry hoặc consolidation** là điểm khởi đầu thực tế: có thể làm bằng dbt.

**Ví dụ MDM kiểu consolidation bằng dbt (match deterministic theo email/phone):**

```sql
-- models/intermediate/int_customer_identities.sql
with unioned as (
    select 'crm' as source, source_id, lower(trim(email)) as email,
           regexp_replace(phone, '[^0-9]', '', 'g') as phone, name, city, updated_at
    from {{ ref('stg_crm_customers') }}
    union all
    select 'app', cast(customer_id as varchar), lower(trim(email)),
           regexp_replace(phone, '[^0-9]', '', 'g'), customer_name, city, customer_updated_at
    from {{ ref('stg_customers') }}
)
select
    *,
    {{ dbt_utils.generate_surrogate_key(['coalesce(email, phone)']) }} as master_customer_id
from unioned
```

```sql
-- models/marts/dim_customers_master.sql — survivorship: giá trị non-null mới nhất thắng
select
    master_customer_id,
    arg_max(name, updated_at)  filter (where name is not null)  as name,
    arg_max(email, updated_at) filter (where email is not null) as email,
    arg_max(phone, updated_at) filter (where phone is not null) as phone,
    arg_max(city, updated_at)  filter (where city is not null)  as city,
    count(*) as source_record_count
from {{ ref('int_customer_identities') }}
group by master_customer_id
```

(Match key `coalesce(email, phone)` ở đây chỉ để minh hoạ; thực tế cần xử lý transitive match — A trùng email với B, B trùng phone với C — bằng thuật toán connected components hoặc công cụ chuyên dụng như Splink, Zingg, hay MDM suite như Informatica MDM, Reltio, Profisee.)

**MDM trên lakehouse (Iceberg):** lưu bảng `customer_xref` và `customer_golden` dạng Iceberg tables; `MERGE INTO` cập nhật golden record mỗi lần chạy, snapshot giúp audit "golden record trước lần merge trông thế nào". Dimension `dim_customers` dùng `master_customer_id` làm conformed dimension cho mọi fact.

**Liên hệ với dimensional modeling:** golden record chính là nền cho **conformed dimension** (Bài 3). Không có MDM, mỗi fact join với một kiểu customer ID khác nhau → không đếm đúng số khách thật.

**Pitfalls:**

```text
- Over-matching: gộp nhầm 2 người khác nhau (dùng chung email công ty, số điện thoại gia đình) — khó gỡ hơn under-matching
- master_customer_id không ổn định giữa các lần chạy → fact lịch sử trỏ sai; cần lưu và tái sử dụng mapping
- Thiếu data steward và quy trình sửa match → mất niềm tin
- Coi MDM là dự án công cụ thay vì quy trình governance có owner
- Xử lý PII khi so khớp: cần phân quyền và masking
```

---

# 2. Câu hỏi tự kiểm tra

```text
1. Master data khác transaction data thế nào?
2. Golden record là gì? Survivorship rule dùng để làm gì?
3. Registry style khác centralized style ở điểm nào?
4. Vì sao over-matching nguy hiểm hơn under-matching?
5. MDM liên quan gì tới conformed dimension?
```
