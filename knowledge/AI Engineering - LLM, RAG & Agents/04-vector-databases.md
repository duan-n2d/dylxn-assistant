---
title: Vector Databases - Qdrant, Chroma, Pinecone, Weaviate, Milvus và Lakehouse
type: concept
domain: ai-engineering
tags:
  - ai-engineering
  - vector-database
  - qdrant
  - chroma
  - pinecone
  - weaviate
  - milvus
  - lakehouse
  - iceberg
---
# AI Engineering — LLM, RAG & Agents

## Bài 4 — Vector Databases: lưu và truy vấn embeddings ở quy mô production

Bài 3 giải thích embeddings và ANN index. Bài này nói về **hệ thống** lưu trữ chúng: vector database là gì, so sánh các lựa chọn phổ biến (Qdrant — thứ repo này đang dùng, Chroma, Pinecone, Weaviate, Milvus) và khi nào lakehouse cần một vector DB riêng.

---

## Vector Database

**Vector database** là hệ quản trị dữ liệu chuyên lưu **vector embeddings kèm metadata** và trả lời truy vấn **similarity search** (k láng giềng gần nhất) nhanh nhờ ANN index.

**Một vector DB đầy đủ thường cung cấp:**

- **CRUD trên vector**: upsert, delete, update payload — không chỉ build index một lần.
- **ANN index**: HNSW, IVF, PQ, DiskANN…
- **Metadata filtering**: "tìm chunk gần nhất *trong domain = data-engineering và type = tutorial*".
- **Hybrid search**: kết hợp dense vector với sparse/keyword (BM25).
- **Multi-tenancy, phân quyền, replication, sharding, backup/snapshot.**
- Quantization để giảm RAM.

**Vector DB vs các lựa chọn khác:**

```text
Thư viện ANN (FAISS, hnswlib)   → chỉ là index trong process; tự lo lưu trữ, update, filter
Extension DB (pgvector cho Postgres) → tiện nếu đã có Postgres, join với dữ liệu quan hệ
Search engine (Elasticsearch/OpenSearch) → mạnh keyword, có thêm kNN vector
Vector DB chuyên dụng (Qdrant, Milvus, Weaviate, Pinecone, Chroma)
                                 → tối ưu riêng cho vector + filter ở quy mô lớn
```

**Khi nào cần:** số vector lớn (hàng triệu+), cần latency thấp, update liên tục, filter phức tạp, nhiều tenant. Với vài nghìn chunk như knowledge base cá nhân, bản embedded/local là đủ — repo này dùng `QdrantClient(path="data/qdrant")`, chạy local không cần server.

**Pitfall:** coi vector DB là source of truth duy nhất (khó audit, khó re-embed) — nên giữ dữ liệu gốc + chunk ở nơi khác (Markdown, lakehouse). Không tạo index cho field lọc → filter chậm.

---

## Qdrant

**Qdrant** là vector database và similarity search engine mã nguồn mở viết bằng **Rust**, đây là vector store của Dylxn Assistant.

**Mô hình dữ liệu:**

- **Collection**: tập vector cùng cấu hình (kích thước, distance metric). Repo dùng collection `knowledge`, 384 chiều, `Distance.COSINE`.
- **Point**: một bản ghi gồm `id` (số nguyên hoặc UUID), `vector`, và **payload** (JSON tuỳ ý: content, source, heading, tags…).
- **Named vectors**: một point có thể có nhiều vector (vd `dense` + `sparse`, hoặc vector cho title và cho body).

**Tính năng nổi bật:**

- Index **HNSW** với filter tích hợp lúc duyệt đồ thị; tạo **payload index** cho field hay lọc.
- **Sparse vectors** (cho BM25/SPLADE-style) + **Query API** với prefetch và fusion (RRF) để làm hybrid search ngay trong DB.
- Quantization: scalar, product, binary.
- Chế độ triển khai: **local/embedded** qua Python client (`path=` hoặc `:memory:`), Docker server (REST cổng 6333, gRPC 6334), cluster phân tán, hoặc managed cloud.

```python
from qdrant_client import QdrantClient, models

client = QdrantClient(path="data/qdrant")
client.create_payload_index("knowledge", field_name="metadata.domain",
                            field_schema=models.PayloadSchemaType.KEYWORD)

hits = client.query_points(
    collection_name="knowledge",
    query=embed_query("Qdrant là gì"),
    query_filter=models.Filter(must=[models.FieldCondition(
        key="metadata.domain", match=models.MatchValue(value="ai-engineering"))]),
    limit=5,
).points
```

**Pattern trong repo:** point ID được tạo **deterministic** từ `chunk_id` (SHA-256 → UUID) nên re-ingest là upsert idempotent, không sinh bản trùng.

**Pitfall:** chế độ local `path=` chỉ cho **một process** truy cập tại một thời điểm (file lock) — chạy API và script ingest song song sẽ lỗi; khi cần nhiều process hãy chạy Qdrant server. Đổi embedding model phải tạo collection mới (khác kích thước vector).

---

## Chroma

**Chroma** (ChromaDB) là embedding database mã nguồn mở, hướng tới **trải nghiệm developer** đơn giản cho ứng dụng LLM: vài dòng code là có vector store chạy được.

**Đặc điểm:**

- API Python và JavaScript/TypeScript; khái niệm chính là **collection** chứa `ids`, `documents`, `embeddings`, `metadatas`.
- Chế độ: **in-memory**, **persistent** (lưu xuống đĩa, nền SQLite cho metadata) và **client-server** (HTTP), cùng dịch vụ cloud.
- Index vector dựa trên **HNSW**; distance cấu hình được (`l2` mặc định, `cosine`, `ip`).
- Có **embedding function** mặc định (model sentence-transformers nhỏ chạy local), nên có thể `add(documents=...)` mà không tự embed. Cũng có thể truyền embedding tự tính.
- Filter bằng `where` (metadata) và `where_document` (chứa chuỗi).

```python
import chromadb

client = chromadb.PersistentClient(path="data/chroma")
col = client.get_or_create_collection("knowledge", metadata={"hnsw:space": "cosine"})
col.add(ids=["c1"], documents=["Grain là mức chi tiết của một dòng fact"],
        embeddings=[embed_passage("Grain là ...")],
        metadatas=[{"domain": "data-engineering"}])
res = col.query(query_embeddings=[embed_query("grain là gì")], n_results=3,
                where={"domain": "data-engineering"})
```

**Khi nào dùng:** prototype, notebook, ứng dụng nhỏ–vừa, demo RAG; tích hợp sẵn với LangChain/LlamaIndex.

**Trade-off / pitfall:**

- Embedding function mặc định chủ yếu cho tiếng Anh — với tiếng Việt nên truyền embedding từ model đa ngôn ngữ (vd multilingual-e5-small) và nhớ prefix `query:`/`passage:`.
- Distance mặc định là L2; nếu model huấn luyện cho cosine, khai báo `hnsw:space` khi **tạo** collection (không đổi được sau đó).
- Ở quy mô rất lớn, nhu cầu phân tán/HA phức tạp thì Qdrant, Milvus hoặc dịch vụ managed thường phù hợp hơn.

---

## Pinecone

**Pinecone** là vector database **fully managed** (SaaS, mã nguồn đóng): bạn không vận hành server, chỉ gọi API. Kiến trúc **serverless** tách storage (object storage) và compute, tính phí theo lượng lưu trữ và số lần đọc/ghi.

**Khái niệm chính:**

- **Index**: khai báo `dimension` và `metric` (cosine, dotproduct, euclidean).
- **Namespace**: phân vùng dữ liệu trong index — hay dùng cho **multi-tenancy** (mỗi khách hàng/team một namespace).
- **Record**: `id`, `values` (dense vector), tuỳ chọn `sparse_values`, `metadata`.
- **Metadata filtering** với cú pháp kiểu MongoDB (`$eq`, `$in`, `$gte`…).
- **Hybrid search**: kết hợp dense + sparse vector; hệ sinh thái có cả embedding và reranking model được host sẵn (tính năng thay đổi theo thời gian — kiểm tra docs hiện hành).

```python
from pinecone import Pinecone

pc = Pinecone(api_key="...")
index = pc.Index("knowledge")
index.upsert(vectors=[{"id": "c1", "values": vec,
                       "metadata": {"domain": "ai-engineering"}}],
             namespace="team-data")
res = index.query(vector=qvec, top_k=5, include_metadata=True,
                  filter={"domain": {"$eq": "ai-engineering"}},
                  namespace="team-data")
```

**Khi nào dùng:** team không muốn vận hành hạ tầng, cần scale nhanh, chấp nhận dữ liệu nằm ở cloud của nhà cung cấp.

**Trade-off / pitfall:**

- **Vendor lock-in** và chi phí tăng theo lượng dữ liệu/truy vấn; không chạy offline/local — trái với triết lý local-first của Dylxn Assistant.
- Dữ liệu (kể cả text trong metadata) rời khỏi hạ tầng của bạn → cân nhắc governance/PII.
- Giới hạn kích thước metadata mỗi record — đừng nhét cả chunk dài vào metadata; lưu content ở store khác và giữ ID.

---

## Weaviate

**Weaviate** là vector database mã nguồn mở viết bằng **Go**, lưu **object** (dữ liệu có schema) cùng vector của chúng, với điểm mạnh là hybrid search và hệ thống **module** tích hợp model.

**Đặc điểm:**

- **Collection** (trước đây gọi là class) có **properties** kiểu dữ liệu rõ ràng; có thể khai báo **cross-reference** giữa các object (gần giống quan hệ đồ thị).
- Index vector **HNSW** (ngoài ra có flat và dynamic), hỗ trợ quantization.
- **Hybrid search** tích hợp: chạy BM25 + vector rồi fusion, tham số **`alpha`** điều chỉnh trọng số (`alpha=1` thuần vector, `alpha=0` thuần keyword).
- **Vectorizer modules**: Weaviate có thể tự gọi embedding model (local hoặc API) khi import dữ liệu và khi query bằng text; có module generative (RAG ngay trong query) và reranker.
- API: GraphQL, REST, gRPC; client Python/TS/Go/Java.
- **Multi-tenancy** native cho SaaS.

```python
import weaviate
from weaviate.classes.query import Filter

client = weaviate.connect_to_local()
kb = client.collections.get("Knowledge")
res = kb.query.hybrid(
    query="double counting khi join",
    vector=embed_query("double counting khi join"),   # nếu tự embed
    alpha=0.7,
    limit=5,
    filters=Filter.by_property("domain").equal("data-engineering"),
)
```

**Khi nào dùng:** cần hybrid search "out-of-the-box", dữ liệu có schema/quan hệ, muốn DB tự lo vectorize.

**Pitfall:** tokenizer BM25 mặc định của nhiều search engine không tối ưu cho tiếng Việt — kiểm tra cấu hình tokenization của property. Vectorizer tự động tiện nhưng khó kiểm soát model version; đổi module = re-index. Tiêu tốn RAM của HNSW cần được tính trước khi scale.

---

## Milvus and the Lakehouse (Vector Database vs Vector Search trên Iceberg)

**Milvus** là vector database **phân tán** mã nguồn mở (dự án thuộc LF AI & Data Foundation, công ty Zilliz phát triển chính và cung cấp bản managed Zilliz Cloud). Milvus nhắm tới quy mô rất lớn — hàng trăm triệu đến tỉ vector.

**Kiến trúc (cloud-native, tách storage/compute):**

- Lớp truy cập (proxy), coordinator, worker node (query/data/index node — chi tiết thay đổi theo phiên bản).
- Metadata lưu ở etcd; log/stream qua message queue; segment dữ liệu và index lưu trên **object storage** (S3/MinIO).
- Nhiều loại index: FLAT, IVF_FLAT, IVF_PQ, HNSW, DiskANN, GPU index; hỗ trợ sparse vector và hybrid search.
- Có **Milvus Lite** (nhúng trong Python) cho dev, standalone (Docker) và cluster (Kubernetes).

**Vector DB riêng hay vector search ngay trên lakehouse (Iceberg)?**

Lakehouse có thể lưu embedding như một cột (`ARRAY<FLOAT>` / `list<float>` trong Parquet) trong bảng Iceberg. Một số engine hỗ trợ hàm khoảng cách (cosine/L2) để quét bảng. Lựa chọn:

```text
Vector search trên bảng lakehouse            Vector DB (Milvus, Qdrant...)
+ một source of truth, governance, time travel  + ANN index → latency mili-giây
+ join trực tiếp với dữ liệu kinh doanh         + QPS cao, update realtime
+ rẻ, không thêm hệ thống                        + filter + hybrid search tối ưu
- thường là brute-force scan → chậm khi lớn      - thêm hệ thống phải vận hành & đồng bộ
- không phù hợp truy vấn online QPS cao          - dữ liệu bị nhân bản
```

**Quy tắc thực tế:**

- **Batch/analytics** (dedup sản phẩm hàng đêm, clustering, đánh giá chất lượng embedding) → làm trên lakehouse.
- **Online serving** (RAG chatbot, search cho user, agent cần trả lời < 1 giây) ở quy mô lớn → vector DB như Milvus.
- Pattern kết hợp: Iceberg giữ `chunk_embeddings` (source of truth, có `model_version`) → job sync incremental sang Milvus/Qdrant.

**Pitfall:** vận hành Milvus cluster khá nặng (nhiều thành phần phụ thuộc) — đừng dùng cho knowledge base vài nghìn chunk; không có cơ chế đồng bộ xoá giữa lakehouse và vector DB dẫn tới "chunk ma".
