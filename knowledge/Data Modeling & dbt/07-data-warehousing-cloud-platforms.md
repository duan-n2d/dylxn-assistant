---
title: "Data Modeling & dbt - Bài 7: Data Warehousing, Cloud Data Warehouse, Snowflake, BigQuery và Open Lakehouse"
type: tutorial
domain: data-engineering
level: intermediate
series: data-modeling-dbt
order: 7
tags:
  - data-engineering
  - data-warehouse
  - data-warehousing
  - cloud-data-warehouse
  - lakehouse
  - apache-iceberg
  - snowflake
  - bigquery
  - dbt-adapter
---

# Data Modeling & dbt

## Bài 7 — Data Warehousing và các nền tảng: Cloud Data Warehouse, Snowflake, BigQuery, Open Lakehouse

Từ Bài 2 tới giờ, "warehouse" của mình là một file DuckDB local. Ở công ty thật, cùng project dbt đó sẽ chạy trên một **cloud data warehouse** hoặc **lakehouse**. Bài này giải thích data warehousing là gì và so sánh các nền tảng phổ biến.

---

# 1. Data Warehousing

## Data Warehousing là gì?

**Data warehousing** là thực hành gom dữ liệu từ nhiều hệ thống vận hành về **một kho tập trung, tối ưu cho phân tích**, nơi dữ liệu được làm sạch, tích hợp, giữ lịch sử và mô hình hoá để trả lời câu hỏi business một cách nhất quán. **Data warehouse** là hệ thống lưu trữ đó.

Bối cảnh điển hình: công ty sữa online ở Bài 1 có đơn hàng trong PostgreSQL của backend, payment từ cổng thanh toán, lead trong CRM, ticket trong hệ thống CSKH. Không hệ thống nào trả lời được "khách từ campaign nào có tỉ lệ hoàn tiền cao nhất" — vì dữ liệu nằm rải rác. Warehouse giải quyết bằng cách đưa tất cả về một chỗ và nối bằng dimension chung (conformed dimension).

**Đặc tính kinh điển (theo Bill Inmon):**

```text
Subject-oriented  → tổ chức theo chủ đề (customer, order), không theo ứng dụng
Integrated        → chuẩn hoá mã, đơn vị, định dạng giữa các nguồn
Time-variant      → giữ lịch sử, phân tích theo thời gian
Non-volatile      → dữ liệu đã nạp ít bị sửa/xoá, chủ yếu append
```

**Kiến trúc phân lớp thường gặp:**

```text
Sources → Raw / Landing → Staging → Integration (3NF hoặc Data Vault, tuỳ chọn) → Marts (star schema) → BI / semantic layer
```

Hai trường phái thiết kế: **Kimball** (bottom-up, build dimensional marts theo business process, nối bằng conformed dimension — cách series này đang làm) và **Inmon** (top-down, enterprise model 3NF trước rồi mới tách data mart).

**Khác OLTP:** warehouse là hệ thống OLAP — đọc nhiều, scan lớn, lưu dạng columnar, không phục vụ transaction của app.

**Pitfalls:**

```text
- Biến warehouse thành "bãi chứa" raw không có model → không ai tin số liệu
- Không có owner cho định nghĩa metric
- Load dữ liệu nhưng không giữ lịch sử dimension (thiếu snapshot) → không trả lời được câu hỏi quá khứ
```

---

# 2. Cloud Data Warehouse vs Open Lakehouse

## Cloud Data Warehouse vs Open Lakehouse — storage, format và lock-in

**Cloud data warehouse** là warehouse dạng dịch vụ managed trên cloud (Snowflake, Google BigQuery, Amazon Redshift, Azure Synapse/Fabric Warehouse). Bạn chỉ cần SQL; vendor lo storage, compute, tối ưu, backup, scale. Dữ liệu thường lưu trong **định dạng nội bộ độc quyền** mà chỉ engine của vendor đọc trực tiếp được.

**Open lakehouse** lưu dữ liệu dạng file mở (Parquet) trên object storage của chính bạn (S3, GCS, ADLS), quản lý bởi một **open table format** — phổ biến nhất là **Apache Iceberg** (ngoài ra Delta Lake, Apache Hudi). Table format thêm vào data lake những gì trước đây chỉ warehouse có: ACID transaction, schema evolution, time travel, partition evolution. Một **catalog** (Iceberg REST catalog, AWS Glue, Apache Polaris, Unity Catalog, Nessie) cho biết bảng nào nằm ở đâu, và **nhiều engine** (Spark, Trino, Flink, DuckDB, Snowflake, BigQuery) cùng đọc/ghi một bản dữ liệu.

| Tiêu chí | Cloud data warehouse | Open lakehouse (Iceberg) |
| -------- | -------------------- | ------------------------ |
| Storage | Do vendor quản lý | Object storage của bạn |
| Format | Độc quyền | Parquet + Iceberg metadata (mở) |
| Compute | Engine của vendor | Nhiều engine tuỳ chọn |
| Vận hành | Gần như zero-ops | Phải lo catalog, compaction, expire snapshot |
| Lock-in | Cao: đổi vendor = migrate dữ liệu | Thấp: đổi engine, giữ nguyên dữ liệu |
| Trải nghiệm SQL / governance | Rất hoàn thiện | Đang trưởng thành, phụ thuộc engine |

**Xu hướng hội tụ:** ranh giới đang mờ dần — Snowflake và BigQuery đều hỗ trợ đọc/ghi Iceberg tables nằm trên storage của khách hàng. Nhiều công ty chọn mô hình: dữ liệu lớn lưu Iceberg trên S3/GCS, warehouse dùng như một trong các engine.

**Ví dụ với DuckDB (đọc Iceberg local để học):**

```sql
install iceberg;
load iceberg;
select count(*) from iceberg_scan('data/lakehouse/orders');
```

**dbt hoạt động trên cả hai:** đổi adapter (`dbt-snowflake`, `dbt-bigquery`, `dbt-spark`, `dbt-trino`, `dbt-duckdb`), model SQL gần như giữ nguyên — đây là lý do học dbt trên DuckDB vẫn chuyển giao được.

**Chọn thế nào:**

```text
Team nhỏ, muốn nhanh, ít người vận hành             → cloud data warehouse
Dữ liệu rất lớn, nhiều engine (ML, streaming, SQL), → open lakehouse
  quan tâm chi phí storage và tránh lock-in
```

**Pitfalls lakehouse:** quên compaction → hàng nghìn file nhỏ, query chậm; không expire snapshot → storage phình; nhiều catalog không đồng bộ.

---

# 3. Snowflake

## Snowflake (nền tảng data cloud) và Apache Iceberg

**Snowflake** là cloud data platform managed, chạy trên AWS, Azure và GCP. Đừng nhầm với **snowflake schema** (Bài 5) — hai khái niệm không liên quan.

**Kiến trúc tách storage và compute — 3 lớp:**

```text
Storage        → dữ liệu lưu dạng micro-partition columnar, nén, trên object storage của cloud
Compute        → virtual warehouse: cluster compute độc lập, size XS → 6XL, tự suspend/resume
Cloud services → metadata, optimizer, bảo mật, transaction
```

Vì compute tách khỏi storage, team BI và job dbt có thể dùng **hai virtual warehouse khác nhau** trên cùng dữ liệu mà không tranh tài nguyên. Tính phí theo credit (thời gian warehouse chạy) + storage.

**Tính năng hay dùng:** Time Travel (query dữ liệu ở thời điểm trước), zero-copy clone (clone database để test PR dbt mà không nhân đôi storage), Streams & Tasks (CDC và lịch chạy), Snowpark (Python), data sharing giữa account.

**Snowflake với Iceberg:** Snowflake hỗ trợ **Iceberg tables** mà file Parquet + metadata nằm trên bucket của khách hàng. Có hai kiểu: Snowflake làm catalog (Snowflake ghi được, engine khác đọc qua catalog), hoặc dùng catalog ngoài (Glue, REST catalog, Snowflake Open Catalog dựa trên Apache Polaris) để Spark/Trino cùng truy cập. Nhờ vậy Snowflake có thể là một engine trong lakehouse đa engine thay vì nơi giữ dữ liệu độc quyền.

**Chạy project dbt trên Snowflake** — chỉ cần đổi profile:

```yaml
# ~/.dbt/profiles.yml
ecommerce_analytics:
  target: dev
  outputs:
    dev:
      type: snowflake
      account: xy12345.ap-southeast-1
      user: dbt_user
      authenticator: externalbrowser
      role: TRANSFORMER
      warehouse: TRANSFORM_WH
      database: ANALYTICS
      schema: dbt_dev
      threads: 4
```

**Pitfalls:** để warehouse size lớn chạy liên tục (quên auto-suspend) → hoá đơn cao; full refresh bảng lớn mỗi giờ; cấp role quá rộng. Dùng resource monitor và incremental model.

---

# 4. Google BigQuery

## Google BigQuery — kiến trúc, Iceberg tables và vị trí trong lakehouse

**Google BigQuery** là cloud data warehouse **serverless** của Google Cloud: không có cluster hay warehouse để bật/tắt — bạn gửi SQL, Google tự cấp tài nguyên.

**Kiến trúc:**

```text
Dremel     → engine query phân tán, chia query thành cây execution, cấp tài nguyên theo "slot"
Colossus   → distributed file system lưu dữ liệu dạng columnar (format Capacitor)
Jupiter    → network tốc độ cao nối storage và compute
Borg       → hệ thống điều phối tài nguyên
```

Storage và compute tách hoàn toàn. Có hai mô hình giá: **on-demand** (trả theo số bytes mà query scan) và **capacity** (mua slot theo editions).

**Hệ quả với data modeling:** vì on-demand tính theo bytes scan, thiết kế bảng ảnh hưởng trực tiếp chi phí:

```sql
-- dbt model trên BigQuery: partition + cluster fact_orders
{{
    config(
        materialized='incremental',
        partition_by={'field': 'order_date', 'data_type': 'date'},
        cluster_by=['customer_id'],
        unique_key='order_id'
    )
}}
select * from {{ ref('stg_orders') }}
```

Query có `where order_date = '2026-07-01'` chỉ scan 1 partition thay vì cả bảng. BigQuery cũng hỗ trợ tốt nested/repeated field (`STRUCT`, `ARRAY`), nên đôi khi denormalize `order_items` thành array trong `fact_orders` là hợp lý.

**BigQuery và Iceberg / lakehouse:** qua **BigLake**, BigQuery có thể query Iceberg tables nằm trên Cloud Storage với governance thống nhất, và có loại bảng Iceberg do BigQuery quản lý (BigQuery ghi Parquet + Iceberg metadata vào bucket của bạn, hỗ trợ DML). Engine khác như Spark có thể đọc cùng dữ liệu qua catalog. Điều này cho phép dùng BigQuery làm engine SQL chính mà vẫn giữ dữ liệu ở format mở.

**Pitfalls:**

```text
- SELECT * trên bảng lớn → trả tiền scan mọi cột; luôn chọn cột cần dùng
- LIMIT không giảm bytes scan với on-demand pricing
- Quên require_partition_filter cho bảng lớn
- Nhiều DML nhỏ, liên tục → quota và chi phí; ưu tiên batch/merge
```

---

# 5. Câu hỏi tự kiểm tra

```text
1. Bốn đặc tính của data warehouse theo Inmon là gì?
2. Iceberg giải quyết vấn đề gì cho data lake?
3. Vì sao tách storage/compute giúp team BI và dbt không tranh tài nguyên trên Snowflake?
4. Vì sao partition và cluster quan trọng về chi phí trên BigQuery?
```
