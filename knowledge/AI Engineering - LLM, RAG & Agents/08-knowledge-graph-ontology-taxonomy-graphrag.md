---
title: Knowledge Graph, Ontology, Taxonomy và GraphRAG
type: concept
domain: ai-engineering
tags:
  - ai-engineering
  - knowledge-graph
  - ontology
  - taxonomy
  - graphrag
  - rdf
  - data-catalog
  - data-governance
---
# AI Engineering — LLM, RAG & Agents

## Bài 8 — Knowledge Graph, Ontology, Taxonomy và GraphRAG: tri thức có cấu trúc cho AI

Vector search giỏi tìm đoạn văn "na ná" câu hỏi, nhưng yếu khi câu hỏi cần **đi theo quan hệ** ("bảng nào bị ảnh hưởng nếu source X lỗi?") hoặc cần **tổng hợp toàn cục** ("các chủ đề chính trong toàn bộ tài liệu là gì?"). Bài này giới thiệu ba cách cấu trúc tri thức — taxonomy, ontology, knowledge graph — và GraphRAG.

---

## Taxonomy

**Taxonomy** (hệ phân loại) là cấu trúc **phân cấp** các thuật ngữ/danh mục theo quan hệ cha–con ("is-a" / "thuộc về"), dùng để **phân loại và gắn nhãn** tài sản dữ liệu, tài liệu, sản phẩm một cách nhất quán.

**Ví dụ — taxonomy cho data catalog:**

```text
Data Domain
├── Sales
│   ├── Orders
│   └── Payments
├── Customer
│   ├── Profile
│   └── Behavior
└── Finance
Sensitivity
├── Public
├── Internal
├── Confidential
└── Restricted (PII, PCI)
```

**Data steward dùng taxonomy để:**

- **Tag** bảng/cột trong catalog (`domain=Sales/Orders`, `sensitivity=Restricted`).
- **Điều khiển truy cập**: policy kiểu "role analyst không được đọc cột tag `Restricted`" (tag-based access control / masking).
- **Tìm kiếm & khám phá**: lọc catalog theo domain.
- **Lọc retrieval trong RAG**: metadata `domain`, `tags` trong frontmatter của knowledge note (như các file trong repo này) là một taxonomy đơn giản, có thể dùng làm filter trong Qdrant.

**Taxonomy vs ontology:** taxonomy chủ yếu chỉ có **một loại quan hệ** (cha–con); ontology mô tả **nhiều loại quan hệ** và thuộc tính, ràng buộc. Taxonomy là bước đầu dễ làm, ontology là bước mở rộng.

**Pitfall:** cây quá sâu/quá chi tiết không ai dùng đúng; một mục thuộc nhiều nhánh (cần poly-hierarchy hoặc tag nhiều chiều); không có owner nên taxonomy mục nát; tag tự do (free-text) thay vì danh sách kiểm soát dẫn tới `sales`, `Sales`, `sale` cùng tồn tại.

---

## Ontology

**Ontology** là **mô hình hình thức, máy đọc được** của một domain: định nghĩa các **khái niệm (class)**, **thuộc tính (property)**, **quan hệ** giữa chúng và các **ràng buộc/luật**. Ontology là "schema ngữ nghĩa" để dữ liệu từ nhiều nguồn được hiểu thống nhất và cho phép máy **suy luận**.

**Thành phần:**

- **Class**: `Customer`, `Order`, `Product`, `Metric`, `Table`.
- **Object property** (quan hệ): `Order placedBy Customer`, `Metric computedFrom Table`.
- **Data property**: `Order.amount: decimal`.
- **Hierarchy & ràng buộc**: `EnterpriseCustomer subClassOf Customer`; mỗi `Order` có đúng một `Customer`.
- **Luật suy luận**: nếu `A dependsOn B` và `B dependsOn C` thì `A dependsOn C` (transitive).

**Chuẩn W3C phổ biến:** **RDF** (dữ liệu dạng triple subject–predicate–object), **RDFS** và **OWL** (định nghĩa ontology), **SKOS** (cho taxonomy/thesaurus), **SPARQL** (truy vấn), **SHACL** (kiểm tra ràng buộc).

```turtle
@prefix ex: <https://example.org/de#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ex:Metric      a rdfs:Class .
ex:Table       a rdfs:Class .
ex:computedFrom rdfs:domain ex:Metric ; rdfs:range ex:Table .

ex:revenue     a ex:Metric ; ex:computedFrom ex:fct_orders .
ex:fct_orders  a ex:Table ;  ex:dependsOn ex:stg_orders .
```

**Ontology trên lakehouse:** ontology làm lớp ngữ nghĩa phía trên bảng vật lý — ánh xạ "Customer" tới `dim_customers`, "Revenue" tới công thức cụ thể. Nó gần với **semantic layer** (định nghĩa metric/dimension) nhưng biểu đạt quan hệ phong phú hơn, và là xương sống để xây **knowledge graph**. Agent Text-to-SQL được lợi vì hiểu thực thể và quan hệ thay vì đoán từ tên cột.

**Pitfall:** thiết kế ontology "hoàn hảo" mất nhiều tháng trước khi có giá trị — bắt đầu nhỏ từ các câu hỏi thật; ontology không gắn với dữ liệu thật thì thành tài liệu chết; trùng lặp với semantic layer mà không đồng bộ.

---

## Knowledge Graph

**Knowledge graph** là cách lưu tri thức dưới dạng **đồ thị**: **node** là thực thể (khách hàng, bảng, metric, khái niệm), **edge** là quan hệ có tên (`PLACED`, `DEPENDS_ON`, `OWNED_BY`), cả node và edge có thể có thuộc tính. Truy vấn có thể **đi theo quan hệ** trực tiếp qua nhiều bước (multi-hop) — việc mà SQL phải viết nhiều self-join hoặc recursive CTE.

**Hai mô hình phổ biến:**

- **RDF triple store** (subject–predicate–object), truy vấn bằng SPARQL, gắn với ontology OWL.
- **Labeled Property Graph** (Neo4j, Memgraph, Amazon Neptune…), truy vấn bằng Cypher/openCypher hoặc Gremlin. ISO **GQL** là chuẩn truy vấn đồ thị mới.

**Ví dụ — lineage dữ liệu như knowledge graph (Cypher):**

```cypher
// Dashboard nào bị ảnh hưởng nếu source raw.app_orders lỗi?
MATCH (s:Source {name: "raw.app_orders"})<-[:DEPENDS_ON*1..6]-(m)
      <-[:USES]-(d:Dashboard)
RETURN DISTINCT d.name, d.owner
```

**Ứng dụng trong data/AI:** data lineage và impact analysis, data catalog (bảng–cột–owner–glossary), fraud detection (vòng giao dịch), recommendation, **GraphRAG** cho LLM.

**Liên hệ repo:** Dylxn Assistant có module `knowledge_graph.py` — một knowledge graph tối giản in-memory (entity có `kind`, relation có tên, hàm `related_nodes`). Đây là nền để liên kết các khái niệm giữa các note (vd "Grain" liên quan "Fact table", "Double counting") và bổ sung cho vector search.

**Xây knowledge graph từ văn bản:** dùng LLM trích xuất (entity, relation, entity) từ chunk, rồi **entity resolution** (gộp "LLM", "Large Language Model", "mô hình ngôn ngữ lớn" thành một node).

**Pitfall:** entity resolution kém tạo node trùng; trích xuất bằng LLM có thể bịa quan hệ — cần ngưỡng tin cậy và giữ link về chunk nguồn; graph lớn nhưng không có câu hỏi nghiệp vụ rõ ràng thì tốn công vô ích.

---

## GraphRAG

**GraphRAG** là họ kỹ thuật RAG dùng **knowledge graph** (thay vì, hoặc kết hợp với, vector search thuần) để lấy context cho LLM — cung cấp các **sự kiện có cấu trúc và liên kết** thay vì chỉ các đoạn văn rời rạc. Tên này được phổ biến đặc biệt qua dự án mã nguồn mở **Microsoft GraphRAG** (2024).

**Hai hướng chính:**

**1. Graph-enhanced retrieval (local, multi-hop):** tìm entity trong câu hỏi → truy vấn graph lấy hàng xóm/đường đi → kèm các chunk gốc liên kết với entity đó → đưa vào prompt.

```text
Q: "Nếu đổi grain của fct_orders thì metric nào bị ảnh hưởng?"
Vector search: tìm được đoạn nói về grain, nhưng không biết metric nào dùng fct_orders
Graph:  (fct_orders)<-[:COMPUTED_FROM]-(revenue), (aov), (order_count)
→ context = định nghĩa grain + danh sách metric phụ thuộc + chunk mô tả từng metric
```

**2. Community summaries (global, kiểu Microsoft GraphRAG):** khi indexing, LLM trích xuất entity/quan hệ từ toàn bộ corpus → xây graph → chia **community** bằng thuật toán phát hiện cộng đồng (Leiden) theo nhiều cấp → LLM viết **tóm tắt cho từng community**. Truy vấn **global search** dùng các tóm tắt này để trả lời câu hỏi bao quát ("chủ đề chính trong 5.000 ticket hỗ trợ là gì?") — loại câu hỏi mà top-k vector search làm rất kém. **Local search** kết hợp entity, quan hệ và chunk liên quan.

**Khi nào dùng:**

- Câu hỏi multi-hop, cần quan hệ (lineage, tổ chức, phụ thuộc).
- Câu hỏi tổng hợp toàn cục trên corpus lớn.
- Domain đã có graph sẵn (data catalog, lineage từ dbt `manifest.json`).

**Trade-off / pitfall:**

- Indexing kiểu community summaries **rất tốn LLM call** (trích xuất + tóm tắt toàn corpus) và phải chạy lại khi dữ liệu đổi nhiều.
- Chất lượng phụ thuộc chất lượng trích xuất entity/relation.
- Với câu hỏi tra cứu đơn giản ("Hybrid search là gì?"), RAG vector/hybrid thường đủ tốt, rẻ hơn.
- Cách thực tế: **hybrid** — vector + keyword cho tra cứu, graph cho câu hỏi quan hệ, router chọn chiến lược theo loại câu hỏi.
