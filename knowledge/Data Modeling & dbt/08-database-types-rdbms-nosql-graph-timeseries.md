---
title: "Data Modeling & dbt - Bài 8: Các loại database nguồn — Relational, NoSQL, Graph, Time-Series"
type: tutorial
domain: data-engineering
level: beginner
series: data-modeling-dbt
order: 8
tags:
  - data-engineering
  - relational-database
  - rdbms
  - nosql
  - graph-database
  - time-series-database
  - oltp
  - cdc
  - lakehouse
---

# Data Modeling & dbt

## Bài 8 — Các loại database: Relational, NoSQL, Graph, Time-Series và cách chúng đổ về warehouse/lakehouse

Warehouse không tự sinh dữ liệu — dữ liệu đến từ các database vận hành. Hiểu đặc điểm từng loại database giúp bạn biết cách ingest, cách viết staging, và khi nào **không** nên kéo mọi thứ vào warehouse.

```text
RDBMS (Postgres, MySQL)      ┐
NoSQL (MongoDB, DynamoDB)    ├─→ ingestion / CDC ─→ raw ─→ dbt staging ─→ marts
Graph DB (Neo4j)             │
Time-series DB (InfluxDB)    ┘
```

---

# 1. Relational Database (RDBMS)

## Relational Database (RDBMS) — và cách RDBMS feed vào warehouse/lakehouse

**Relational database là gì?** RDBMS lưu dữ liệu trong **bảng gồm row và column**, các bảng liên kết bằng **primary key / foreign key**, truy vấn bằng SQL, và mọi thay đổi chạy trong **ACID transaction** (Atomicity, Consistency, Isolation, Durability). Ví dụ: PostgreSQL, MySQL, SQL Server, Oracle.

Backend của công ty sữa online ở Bài 1 nhiều khả năng là một RDBMS với schema 3NF:

```sql
create table customers (
    customer_id  bigint primary key,
    email        varchar unique not null,
    city         varchar
);

create table orders (
    order_id     bigint primary key,
    customer_id  bigint not null references customers(customer_id),
    status       varchar check (status in ('pending','completed','cancelled')),
    amount       numeric(18,2),
    updated_at   timestamp
);
```

**Đặc điểm:** lưu theo row (row-oriented), tối ưu cho đọc/ghi từng record qua index — đúng nhu cầu OLTP. Constraint (PK, FK, CHECK) được **enforce** nên dữ liệu nhất quán.

**So với bảng trong warehouse / Iceberg:**

```text
RDBMS                               Warehouse / Iceberg table
Row-oriented, index B-tree          Columnar (Parquet), scan lớn
Enforce PK/FK/unique                Thường KHÔNG enforce → dùng dbt test
Update từng row rẻ                  Update tạo file/snapshot mới, nên batch
Scale dọc (1 máy mạnh)              Scale ngang, tách storage/compute
```

**Cách đưa RDBMS vào warehouse:**

```text
1. Full snapshot extract: copy cả bảng mỗi ngày — đơn giản, tốn với bảng lớn
2. Incremental theo updated_at: chỉ lấy row thay đổi — miss row bị hard delete
3. CDC (Change Data Capture): đọc WAL/binlog (Debezium, Fivetran, Airbyte) → bắt cả insert/update/delete
```

**Pitfalls:** chạy query phân tích nặng thẳng lên DB production (làm chậm app) — dùng read replica hoặc ingest ra warehouse; giả định warehouse sẽ giữ được constraint như source; bỏ qua hard delete khi incremental.

---

# 2. NoSQL Database

## NoSQL Database — các loại, trade-off và phân tích dữ liệu NoSQL

**NoSQL** là nhóm database **không dùng mô hình bảng quan hệ** làm trung tâm, thiết kế để scale ngang, schema linh hoạt và tối ưu cho một kiểu truy cập cụ thể. Bốn nhóm chính:

| Loại | Mô hình | Ví dụ | Dùng cho |
| ---- | ------- | ----- | -------- |
| Document | JSON/BSON document | MongoDB, Couchbase, Firestore | Catalog sản phẩm, user profile |
| Key-value | key → value | Redis, DynamoDB | Session, cache, giỏ hàng |
| Wide-column | Row key + column family | Cassandra, HBase, Bigtable | Event log ghi khối lượng lớn |
| Graph | Node + edge | Neo4j | Quan hệ (xem phần 3) |

**Trade-off:** đổi tính nhất quán chặt và join linh hoạt lấy khả năng scale và latency thấp. Nhiều hệ chọn **eventual consistency** (theo định lý CAP, khi có network partition phải chọn giữa consistency và availability). Data model được thiết kế **theo query** (query-first), thường denormalize và lồng dữ liệu.

**Phân tích dữ liệu NoSQL trong warehouse/lakehouse.** Không nên chạy analytics trên MongoDB production. Cách làm: ingest document vào cột JSON/VARIANT ở raw, rồi **flatten ở staging** bằng dbt:

```sql
-- raw.mongo_orders có cột doc kiểu JSON:
-- {"_id": "1", "customer": {"id": 101, "city": "HCM"}, "items": [{"sku": "P1", "qty": 2}]}

-- models/staging/stg_mongo_order_items.sql (DuckDB)
select
    doc ->> '$._id'                        as order_id,
    cast(doc ->> '$.customer.id' as int)   as customer_id,
    item ->> '$.sku'                       as product_id,
    cast(item ->> '$.qty' as int)          as quantity
from {{ source('raw', 'mongo_orders') }},
     unnest(cast(json_extract(doc, '$.items') as json[])) as t(item)
```

Trên Snowflake dùng `VARIANT` + `LATERAL FLATTEN`, trên BigQuery dùng `JSON`/`ARRAY` + `UNNEST`.

**Pitfalls:**

```text
- Schema drift: field mới/đổi kiểu không báo trước → staging phải chịu được null, test accepted_values
- Mảng lồng nhau → explode sai grain → double counting (Bài 3)
- Document chứa bản sao denormalized (tên customer trong order) đã cũ → lấy dimension từ nguồn chuẩn
- Dùng NoSQL chỉ vì "scale" khi dữ liệu nhỏ, quan hệ phức tạp → RDBMS thường tốt hơn
```

---

# 3. Graph Database

## Graph Database — node, edge và graph query trên lakehouse

**Graph database** lưu dữ liệu dưới dạng **node** (entity: customer, product, device) và **edge / relationship** (quan hệ có hướng, có thuộc tính: `PURCHASED`, `REFERRED`, `USED_DEVICE`). Mô hình phổ biến là **property graph** (Neo4j, Amazon Neptune, TigerGraph, Memgraph); ngôn ngữ truy vấn: Cypher, Gremlin, và chuẩn ISO **GQL**.

**Cách hoạt động.** Điểm mạnh là **index-free adjacency**: mỗi node trỏ trực tiếp tới các node kề, nên duyệt quan hệ nhiều bước (multi-hop) có chi phí theo số node được duyệt, thay vì phải join các bảng lớn nhiều lần như SQL.

Ví dụ: tìm khách hàng được giới thiệu gián tiếp tối đa 3 cấp bởi customer 101:

```cypher
MATCH (c:Customer {id: 101})-[:REFERRED*1..3]->(r:Customer)
RETURN DISTINCT r.id
```

Cùng câu hỏi bằng SQL cần recursive CTE:

```sql
with recursive referral_chain as (
    select referred_customer_id as customer_id, 1 as depth
    from referrals where referrer_customer_id = 101
    union all
    select r.referred_customer_id, rc.depth + 1
    from referrals r
    join referral_chain rc on r.referrer_customer_id = rc.customer_id
    where rc.depth < 3
)
select distinct customer_id from referral_chain;
```

**Khi nào dùng graph DB:** fraud detection (nhiều tài khoản dùng chung thiết bị/thẻ), recommendation, mạng lưới giới thiệu, knowledge graph, phân tích supply chain, quyền truy cập phức tạp — tức là câu hỏi xoay quanh **đường đi và mức độ kết nối**.

**Khi nào KHÔNG cần:** aggregate kiểu doanh thu theo tháng — star schema làm tốt hơn nhiều. Nếu chỉ cần 1–2 hop thỉnh thoảng, recursive CTE trên warehouse hoặc Iceberg tables (Spark GraphFrames, DuckDB) là đủ, tránh phải vận hành và đồng bộ thêm một hệ thống. Pattern phổ biến: lưu edge list (`referrals`, `customer_devices`) dạng bảng trong lakehouse làm nguồn sự thật, rồi load vào graph engine khi cần duyệt sâu.

**Pitfalls:** supernode (một node có hàng triệu edge) làm query chậm; dữ liệu graph lệch so với warehouse nếu đồng bộ kém; dùng graph cho bài toán thực chất là bảng.

---

# 4. Time-Series Database

## Time-Series Database (TSDB) vs Apache Iceberg cho dữ liệu time-series

**Time-series database** là database chuyên lưu và truy vấn **dữ liệu gắn timestamp**, ghi liên tục với tần suất cao: metric hệ thống, dữ liệu cảm biến IoT, giá chứng khoán, event ứng dụng. Ví dụ: InfluxDB, TimescaleDB (extension của PostgreSQL), Prometheus, QuestDB, kdb+.

**Cách hoạt động / tối ưu đặc thù:**

```text
- Ghi append-only rất nhanh, dữ liệu sắp xếp theo thời gian
- Partition theo time chunk; nén delta / delta-of-delta cho timestamp và giá trị
- Hàm chuyên biệt: time_bucket, downsampling, gap filling, interpolation
- Retention policy: tự xoá dữ liệu raw cũ, giữ bản rollup
- Tag/label để lọc theo series (device_id, host)
```

Ví dụ TimescaleDB:

```sql
select time_bucket('5 minutes', ts) as bucket, device_id, avg(temperature) as avg_temp
from sensor_readings
where ts > now() - interval '1 day'
group by bucket, device_id;
```

**TSDB vs Iceberg tables:**

| Nhu cầu | TSDB | Iceberg / lakehouse |
| ------- | ---- | ------------------- |
| Dashboard realtime, alert theo giây | Rất tốt | Không phù hợp (latency cao hơn) |
| Lưu lịch sử nhiều năm, rẻ | Tốn kém | Rất tốt (object storage) |
| Join với dim_customers, dim_devices | Hạn chế | Tự nhiên với SQL/dbt |
| Ghi tần suất cao, điểm nhỏ | Tối ưu | Cần batch/micro-batch + compaction |

Pattern hay gặp: TSDB giữ dữ liệu "nóng" vài ngày–vài tuần cho monitoring; dữ liệu được đẩy định kỳ ra Iceberg (partition theo `day(ts)`) để phân tích dài hạn và join với dimension trong dbt. Trong warehouse, bảng time-series chính là một **transaction fact** hoặc **periodic snapshot fact** (Bài 3) với grain như "1 row per device per minute".

**Pitfalls:**

```text
- High cardinality tag (vd. user_id làm tag) → số series bùng nổ, TSDB chậm
- Lẫn lộn timezone và event time vs ingestion time
- Late-arriving data làm rollup đã tính bị sai
- Ghi từng điểm nhỏ trực tiếp vào Iceberg → small-file problem
```

---

# 5. Câu hỏi tự kiểm tra

```text
1. Vì sao warehouse thường không enforce foreign key như RDBMS?
2. Incremental theo updated_at bỏ sót loại thay đổi nào? CDC xử lý ra sao?
3. Flatten mảng items từ MongoDB ảnh hưởng tới grain thế nào?
4. Khi nào nên dùng graph DB thay vì recursive CTE?
5. Vì sao thường kết hợp TSDB (dữ liệu nóng) và Iceberg (lịch sử)?
```
