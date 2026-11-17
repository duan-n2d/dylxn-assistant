---
title: "Data Modeling & dbt - Bài 6: ETL, ELT và Analytics Engineering"
type: tutorial
domain: data-engineering
level: beginner
series: data-modeling-dbt
order: 6
tags:
  - data-engineering
  - etl
  - elt
  - etl-vs-elt
  - etlt
  - analytics-engineering
  - dbt
  - modern-data-stack
---

# Data Modeling & dbt

## Bài 6 — ETL, ELT và vai trò Analytics Engineering

Ở Bài 1 có sơ đồ: source → ingestion → warehouse → dbt → marts. Bài này giải thích vì sao luồng đó có thứ tự **Load trước, Transform sau**, và nghề **analytics engineering** ra đời từ đâu.

---

# 1. ETL

## ETL (Extract, Transform, Load) là gì?

**ETL** là pattern tích hợp dữ liệu gồm 3 pha, theo đúng thứ tự:

```text
Extract   → lấy dữ liệu từ nguồn (DB vận hành, file SFTP, API)
Transform → làm sạch, join, tính toán trên một engine riêng (ETL server, Spark, script Python)
Load      → ghi kết quả đã chuẩn hoá vào warehouse
```

**Cách hoạt động.** Transform xảy ra **ngoài** warehouse. Warehouse chỉ nhận dữ liệu đã đúng schema đích — gọi là **schema-on-write**: schema được định nghĩa trước, dữ liệu không khớp sẽ bị reject trước khi vào kho. Công cụ điển hình: Informatica PowerCenter, SSIS, Talend, DataStage, hoặc job Spark/pandas tự viết.

Ví dụ ETL bằng Python cho project mẫu:

```python
import pandas as pd
import duckdb

orders = pd.read_csv("raw_orders.csv")                               # Extract
orders = orders.rename(columns={"id": "order_id", "user_id": "customer_id"})
orders["order_status"] = orders["status"].str.lower()                # Transform
orders = orders[orders["order_status"] == "completed"]

con = duckdb.connect("warehouse.duckdb")
con.execute("create or replace table fact_orders as select * from orders")  # Load
```

Chú ý: các đơn `cancelled` **không bao giờ vào warehouse** — nếu sau này business muốn tính cancel rate, phải sửa pipeline và extract lại.

**Khi nào ETL hợp lý:**

```text
- Warehouse on-prem đắt, compute hạn chế → không muốn transform trong kho
- Cần lọc/mask dữ liệu nhạy cảm (PII) TRƯỚC khi rời hệ thống nguồn vì lý do compliance
- Transform phức tạp không biểu diễn tốt bằng SQL (parse file nhị phân, ML feature, xử lý ảnh)
- Streaming: biến đổi event trước khi ghi
```

**Pitfalls:** raw data bị mất sau transform nên khó backfill; logic nằm trong tool GUI hoặc code riêng, khó review/test; mỗi thay đổi nhỏ cần data engineer sửa pipeline.

---

# 2. ELT

## ELT (Extract, Load, Transform) là gì?

**ELT** đảo thứ tự hai bước cuối: **load raw data vào warehouse/lakehouse trước**, rồi transform **ngay bên trong** bằng SQL, tận dụng compute của warehouse.

```text
Extract + Load  → Fivetran / Airbyte / dlt / script copy nguyên trạng vào schema raw
Transform       → dbt chạy SQL trong DuckDB / Snowflake / BigQuery / Databricks
```

Đây chính là luồng của project dbt + DuckDB ở Bài 2:

```text
dbt seed (load CSV nguyên trạng)  → raw_orders
dbt run  (transform bằng SQL)     → stg_orders → fact_orders → mart_daily_revenue
```

**Vì sao ELT phổ biến:** cloud data warehouse tách storage và compute, scale compute theo nhu cầu, lưu trữ rẻ. Do đó giữ toàn bộ raw data trong kho trở nên khả thi, và SQL trở thành ngôn ngữ transform chung. Gần với **schema-on-read**: raw được giữ gần như nguyên trạng, schema nghiệp vụ được áp ở lớp staging/marts.

**Ưu điểm:**

```text
- Raw data luôn còn → rebuild / backfill model bất kỳ lúc nào (dbt run --full-refresh)
- Transform là SQL trong git → code review, test, docs, lineage (đúng thế mạnh của dbt)
- Analyst biết SQL tự đóng góp được model
- Ingestion đơn giản, dùng connector có sẵn
```

**Pitfalls:**

```text
- Chi phí compute warehouse tăng nếu model không incremental, query lặp lại toàn bảng
- Raw chứa PII được load vào kho → cần phân quyền, masking, retention policy
- "Load mọi thứ" dễ thành data swamp nếu không có staging chuẩn và ownership rõ
```

---

# 3. ETL vs ELT

## ETL vs ELT — so sánh và khi nào dùng cái nào

Khác biệt cốt lõi giữa **ETL vs ELT** là **transform ở đâu** và **raw data có được giữ lại trong kho không**.

| Tiêu chí | ETL | ELT |
| -------- | --- | --- |
| Thứ tự | Extract → Transform → Load | Extract → Load → Transform |
| Nơi transform | Engine riêng ngoài warehouse | Bên trong warehouse/lakehouse |
| Raw data trong kho | Thường không | Có (schema raw) |
| Schema | Schema-on-write | Gần schema-on-read |
| Ngôn ngữ | Tool GUI, Java, Python, Spark | Chủ yếu SQL (dbt) |
| Backfill | Phải extract lại | Rebuild từ raw |
| Thời kỳ | Warehouse on-prem (Teradata, Oracle) | Cloud warehouse / lakehouse |
| Người viết transform | Data engineer | Data/analytics engineer, analyst |

**Cách chọn:**

```text
Chọn ELT khi:
- Có cloud warehouse hoặc lakehouse đủ mạnh
- Transform chủ yếu là join/aggregate/làm sạch biểu diễn được bằng SQL
- Muốn team analytics tự phát triển model với dbt

Chọn ETL (hoặc bước T trước load) khi:
- Phải loại bỏ/mask PII trước khi dữ liệu rời nguồn
- Dữ liệu cần xử lý phi-SQL (file nhị phân, NLP, ảnh)
- Warehouse đích đắt hoặc yếu về compute
```

Thực tế hầu hết hệ thống là **hybrid**: một chút "T" nhẹ khi ingest (parse JSON, mask PII, dedupe event) rồi ELT với dbt cho toàn bộ business logic. Đừng tranh luận tên gọi — điều quan trọng là raw data có được giữ lại, logic có được version control và test hay không.

**Pitfall khi chuyển từ ETL sang ELT:** bê nguyên stored procedure khổng lồ vào một dbt model. Hãy tách lại theo staging → intermediate → marts như Bài 1.

## EtLT (ETLT) — tên gọi chính thức cho pattern hybrid

Pattern hybrid vừa nhắc ở trên có một tên riêng: **EtLT** (cũng viết **ETLT**), viết chữ "t" thường ở giữa để nhấn mạnh đây là một bước transform **nhỏ, nhẹ** — khác với chữ "T" hoa, đầy đủ, nằm sau "L":

```text
E   → Extract: lấy dữ liệu từ nguồn
t   → transform nhẹ ngay lúc ingest: parse JSON/Avro, mask PII, dedupe, chuẩn hoá encoding, flatten field lồng cơ bản
L   → Load: ghi vào warehouse/lakehouse (thường vào schema raw)
T   → Transform đầy đủ bằng SQL trong warehouse: join, aggregate, dimensional model (đây là phần dbt đảm nhiệm)
```

EtLT xuất hiện vì ELT thuần tuý ("load nguyên trạng rồi transform hết trong SQL") đôi khi không khả thi: một số việc buộc phải làm trước khi data rời khỏi pipeline ingest — ví dụ mask số thẻ tín dụng vì lý do compliance, hoặc parse một blob JSON lồng sâu thành column phẳng để dbt có thể `select` được. Những việc này do connector ingest (Fivetran, Airbyte, dlt, custom script) đảm nhiệm ở bước `t` nhỏ, còn toàn bộ business logic (grain, fact/dimension, metric) vẫn nằm ở bước `T` lớn trong dbt.

Nói cách khác: project Bài 2–5 của bạn, nếu nhìn kỹ, đã luôn là EtLT chứ không phải ELT thuần — `dbt seed` cast kiểu dữ liệu cơ bản trước khi vào `raw_*` cũng có thể xem là một chút `t` nhẹ, trước khi `dbt run` làm phần `T` đầy đủ.

---

# 4. Analytics Engineering

## Analytics Engineering là gì?

**Analytics engineering** là công việc biến raw data đã được load vào warehouse thành **các model sạch, có test, có tài liệu, sẵn sàng cho phân tích** — áp dụng kỹ thuật software engineering (version control, code review, CI, testing, modular code) vào lớp transformation. Người làm vai trò này gọi là **analytics engineer**; dbt là công cụ gắn liền với nghề này.

**Vị trí trong team data:**

```text
Data Engineer       → ingestion, hạ tầng, pipeline, platform, streaming
Analytics Engineer  → staging, dimensional model, marts, metrics, tests, docs (lớp T của ELT)
Data Analyst        → trả lời câu hỏi business, dashboard, phân tích ad-hoc
```

Ranh giới mềm: ở công ty nhỏ, một người làm cả ba.

**Công việc hằng ngày của analytics engineer — chính là những gì Bài 1–5 đã làm:**

```text
- Khai báo source, viết stg_* để chuẩn hoá tên cột, kiểu dữ liệu
- Thiết kế grain, fact/dimension, xử lý SCD, surrogate key
- Viết test: unique, not_null, relationships, reconciliation
- Viết docs + mô tả grain cho từng model, publish dbt docs
- Định nghĩa metric dùng chung (semantic layer: dbt Semantic Layer / MetricFlow, Cube, LookML)
- Review PR, chạy CI (dbt build trên PR), theo dõi chi phí và freshness
```

Ví dụ một PR điển hình của analytics engineer — thêm metric và test cho mart:

```yaml
# models/marts/schema.yml
models:
  - name: mart_daily_revenue
    description: "1 row per order_date. Nguồn chính thức cho doanh thu hằng ngày."
    columns:
      - name: order_date
        tests: [unique, not_null]
      - name: completed_revenue
        description: "Tổng order_amount của đơn completed"
        tests:
          - dbt_utils.expression_is_true:
              expression: ">= 0"
```

**Giá trị mang lại:** một định nghĩa "doanh thu" duy nhất (tránh 3 analyst 3 con số như Bài 1), lineage rõ ràng, phát hiện lỗi dữ liệu trước khi lên dashboard.

**Pitfalls:**

```text
- Chỉ viết SQL mà bỏ qua test/docs → chỉ là "analyst viết view", không phải engineering
- Model sprawl: hàng trăm mart trùng logic, không owner
- Đưa business logic vào BI tool thay vì vào model → mất single source of truth
- Bỏ qua chi phí compute của full refresh trên bảng lớn
```

---

# 5. Câu hỏi tự kiểm tra

```text
1. Project Bài 2 là ETL hay ELT? Chỉ ra từng bước.
2. Schema-on-write khác schema-on-read thế nào?
3. Nêu 2 tình huống vẫn nên transform trước khi load.
4. Analytics engineer khác data engineer ở trách nhiệm nào?
```
