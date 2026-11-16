---
title: Agentic Analytics và Lakehouse - Text-to-SQL, Dremio Text-to-SQL, Agentic Lakehouse
type: tutorial
domain: ai-engineering
tags:
  - ai-engineering
  - agentic-analytics
  - text-to-sql
  - semantic-layer
  - lakehouse
  - iceberg
  - dremio
  - agentic-lakehouse
  - mcp
---
# AI Engineering — LLM, RAG & Agents

## Bài 9 — Agentic Analytics và Lakehouse: để AI agent hỏi dữ liệu một cách an toàn

Đây là bài giao thoa giữa Data Engineering và AI Engineering. Một agent chỉ trả lời đúng câu hỏi dữ liệu khi nền tảng dữ liệu bên dưới được mô hình hoá tốt (grain, fact, dimension — xem series Data Modeling & dbt) và có **semantic layer** định nghĩa metric rõ ràng.

---

## Agentic Analytics

**Agentic analytics** là cách làm phân tích dữ liệu trong đó **AI agent** nhận câu hỏi bằng ngôn ngữ tự nhiên, tự tìm dữ liệu phù hợp, sinh và chạy SQL trên warehouse/lakehouse, kiểm tra kết quả, lặp lại khi cần, rồi diễn giải bằng lời — thay vì người dùng phải tự viết SQL hoặc chờ data team làm dashboard.

**Khác gì "Text-to-SQL một lượt":** Text-to-SQL cơ bản là một lần LLM call → một câu SQL. Agentic analytics là **vòng lặp ReAct**: khám phá schema, thử truy vấn, đọc lỗi, sửa, truy vấn thêm để giải thích ("vì sao giảm?"), kiểm chứng.

**Kiến trúc tham chiếu:**

```text
User question
   │
   ▼
Agent (reasoning engine)  ◄── RAG: glossary, định nghĩa metric, docs (vd Dylxn knowledge base)
   │  tools:
   ├── list_metrics / get_metric_definition   (semantic layer)
   ├── describe_table / search_catalog        (catalog, taxonomy, tag)
   ├── run_sql (READ-ONLY, timeout, LIMIT)     (lakehouse engine: Trino/Dremio/Spark/DuckDB)
   └── plot / summarize
   ▼
Answer + SQL đã chạy + nguồn (để người dùng kiểm chứng)
```

**Ba trụ cột để đáng tin:**

1. **Semantic layer**: metric như `revenue`, `active_users` được định nghĩa một lần (công thức, filter, grain hợp lệ). Agent gọi metric thay vì tự sáng tác công thức → tránh mỗi lần hỏi ra một con số khác.
2. **Data model sạch**: grain rõ ràng, khoá join đúng, tránh fan-out gây **double counting**.
3. **Guardrails**: tài khoản **read-only**, row/column-level security theo người hỏi, giới hạn chi phí truy vấn, hiển thị SQL để audit.

**Pitfall:**

- Cho agent truy cập thẳng hàng trăm bảng raw — nó sẽ chọn nhầm bảng (`orders_v2_backup`).
- Không có golden question set để đánh giá độ chính xác (so kết quả thực thi với đáp án chuẩn).
- Câu trả lời "trôi chảy nhưng sai" nguy hiểm hơn dashboard lỗi vì khó nhận ra — luôn trả kèm SQL và định nghĩa metric đã dùng.

---

## Text-to-SQL trên Lakehouse và Dremio Text-to-SQL

**Text-to-SQL** là việc dùng LLM chuyển câu hỏi ngôn ngữ tự nhiên thành câu SQL chạy được. **Dremio Text-to-SQL** là tính năng generative AI tích hợp trong nền tảng lakehouse **Dremio**, cho phép người dùng nhập câu hỏi bằng ngôn ngữ tự nhiên trong giao diện SQL và nhận lại câu SQL đề xuất trên các dataset/view của Dremio, để người dùng business khai thác dữ liệu mà không cần viết code. (Chi tiết giao diện và model bên dưới thay đổi theo phiên bản Dremio — kiểm tra tài liệu hiện hành.)

**Vì sao nền tảng lakehouse làm Text-to-SQL tốt hơn LLM "trần":** độ chính xác Text-to-SQL phụ thuộc chủ yếu vào **context về dữ liệu**, và engine lakehouse đã nắm sẵn context đó:

- Schema, kiểu dữ liệu của bảng Iceberg/view.
- **Semantic layer**: view nghiệp vụ, mô tả (wiki), nhãn/tag, quan hệ.
- Quyền truy cập của chính người dùng — SQL sinh ra chạy dưới quyền đó.

**Pipeline Text-to-SQL tốt (áp dụng cho mọi engine):**

```text
1. Schema linking  : retrieve bảng/cột/metric liên quan (vector + keyword trên catalog)
2. Prompt          : schema rút gọn + mô tả cột + vài ví dụ (few-shot) + dialect SQL
3. Generate        : temperature thấp
4. Validate        : parse SQL, kiểm tra bảng/cột tồn tại, chỉ SELECT, EXPLAIN
5. Execute         : read-only, LIMIT, timeout
6. Self-correct    : nếu lỗi → đưa thông báo lỗi lại cho LLM sửa (tối đa n lần)
7. Present         : kết quả + SQL + giải thích
```

**Ví dụ:**

```text
Q: "Doanh thu theo tháng của khách Enterprise năm 2025"
SQL:
SELECT DATE_TRUNC('month', o.order_date) AS month, SUM(o.amount) AS revenue
FROM marts.fct_orders o
JOIN marts.dim_customers c ON o.customer_id = c.customer_id
WHERE c.segment = 'Enterprise' AND o.order_date >= DATE '2025-01-01'
  AND o.order_date < DATE '2026-01-01' AND o.status <> 'cancelled'
GROUP BY 1 ORDER BY 1;
```

**Pitfall:** câu hỏi mơ hồ ("doanh thu" gồm thuế không? tính theo ngày đặt hay ngày thanh toán?) — hệ thống tốt nên hỏi lại hoặc nêu giả định; SQL chạy được **không có nghĩa là đúng** (join sai grain vẫn chạy); dialect khác nhau giữa engine (hàm ngày tháng).

---

## Agentic Lakehouse

**Agentic lakehouse** là thuật ngữ do **Dremio** đưa ra để chỉ một lakehouse được thiết kế cho việc **AI agent là người dùng chính** (bên cạnh con người): agent có thể khám phá, hiểu và truy vấn dữ liệu nhanh và an toàn. Ý tưởng chung (không phụ thuộc vendor) gồm:

- **Open table format** (Apache Iceberg) trên object storage — một bản dữ liệu, nhiều engine đọc được.
- **Semantic layer giàu ngữ nghĩa**: view nghiệp vụ, mô tả, tag, định nghĩa metric — chính là "context" agent cần để sinh SQL đúng.
- **Truy cập dữ liệu hiệu năng cao theo cột**: Dremio xây dựng trên **Apache Arrow** (định dạng in-memory dạng cột) và hỗ trợ **Arrow Flight** để trả kết quả lớn cho client/agent nhanh, ít chi phí serialize.
- **Giao diện cho agent**: ví dụ **MCP server** để agent (Claude, các agent framework) gọi tool như liệt kê dataset, đọc schema, chạy SQL.
- **Tăng tốc tự động** (vd materialization/caching mà Dremio gọi là reflections) vì agent sinh ra rất nhiều truy vấn khám phá.
- **Governance** thống nhất: phân quyền theo người dùng/agent, audit.
- Khả năng kết hợp tìm kiếm ngữ nghĩa/vector cho dữ liệu phi cấu trúc cạnh dữ liệu bảng (mức hỗ trợ tuỳ phiên bản sản phẩm).

**Hiện thực hoá bằng stack mở (ví dụ):**

```text
Iceberg tables (S3/MinIO)
  └── dbt marts + semantic layer (metric definitions, docs)
       └── Query engine (Dremio / Trino / Spark / DuckDB)
            └── MCP server: list_datasets, describe, get_metric, run_readonly_sql
                 └── Agent (ReAct) + RAG trên docs/glossary (Qdrant + FTS5 như Dylxn)
```

**Trade-off / pitfall:** "agentic" không thay thế được data modeling — agent trên dữ liệu lộn xộn chỉ sinh câu trả lời sai nhanh hơn; agent sinh nhiều truy vấn tốn compute (cần quota, cache); đây là thuật ngữ marketing — khi đánh giá sản phẩm, hãy kiểm tra năng lực cụ thể (semantic layer, quyền theo user, audit, API cho agent) thay vì nhãn.
