---
title: Embeddings và Vector Search - Embeddings, Vector Embeddings, Similarity Metrics, Semantic Search, Vector Indexes
type: concept
domain: ai-engineering
tags:
  - ai-engineering
  - embeddings
  - vector-embeddings
  - similarity-metrics
  - cosine-similarity
  - semantic-search
  - vector-index
  - hnsw
  - ivf
---
# AI Engineering — LLM, RAG & Agents

## Bài 3 — Embeddings và Vector Search: biến "ý nghĩa" thành con số có thể tìm kiếm

Retrieval trong RAG dựa trên một ý tưởng: biểu diễn văn bản thành vector sao cho **văn bản cùng nghĩa có vector gần nhau**, rồi tìm láng giềng gần nhất. Bài này đi qua embeddings, cách đo khoảng cách, semantic search và các index giúp tìm kiếm nhanh trên hàng triệu vector.

---

## Embeddings

**Embeddings** là cách biểu diễn một đối tượng (câu, đoạn văn, ảnh, sản phẩm, user…) bằng một **vector số thực có số chiều cố định**, sinh ra bởi một model đã học sao cho khoảng cách giữa các vector phản ánh mức độ tương đồng về nghĩa.

**Cách tạo:** một **embedding model** (thường là Transformer encoder) đọc input và xuất vector. Model được huấn luyện bằng **contrastive learning**: kéo các cặp liên quan (câu hỏi ↔ đoạn trả lời) lại gần nhau, đẩy cặp không liên quan ra xa.

**Embedding trong repo này:** dùng `intfloat/multilingual-e5-small`:

- Đa ngôn ngữ (hỗ trợ tiếng Việt), vector **384 chiều** (khớp `DEFAULT_VECTOR_SIZE = 384` trong `vector_store.py`).
- Họ E5 yêu cầu **prefix**: tài liệu nhúng dạng `"passage: ..."`, câu hỏi dạng `"query: ..."`. Quên prefix làm chất lượng retrieval giảm rõ rệt.
- Input tối đa 512 token.

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("intfloat/multilingual-e5-small")
docs = model.encode(["passage: Grain là mức chi tiết của một dòng fact."],
                    normalize_embeddings=True)
q = model.encode(["query: grain trong fact table là gì?"],
                 normalize_embeddings=True)
print(docs.shape)          # (1, 384)
print(float(q @ docs.T))   # cosine similarity (vì đã normalize)
```

**Ứng dụng:** semantic search, RAG, clustering, dedup, recommendation, phân loại, semantic caching, LLM routing.

**Trade-off khi chọn model:** số chiều lớn hơn → thường chính xác hơn nhưng tốn storage/RAM hơn; model đa ngôn ngữ vs model chuyên tiếng Anh; giới hạn token; chạy local hay gọi API.

**Pitfall:**

- **Không trộn** vector từ hai model khác nhau trong cùng một collection — không gian vector không tương thích. Đổi model ⇒ **re-embed toàn bộ**.
- Embedding không hiểu tốt mã định danh, số, tên riêng hiếm (`SKU-88412`) → cần **hybrid search** với keyword.
- Lưu kèm tên + phiên bản model trong metadata để biết khi nào cần re-index.

---

## Vector Embeddings (vector embeddings và data lakehouse)

**Vector embeddings** nhấn mạnh khía cạnh *dữ liệu* của embeddings: mỗi embedding là một mảng số (ví dụ `float32[384]`) gắn với một bản ghi nguồn, và cần được **lưu trữ, version, cập nhật** như bất kỳ dataset nào trong data platform.

**Đa phương thức:** không chỉ text — ảnh (CLIP), audio, code, thậm chí hàng dữ liệu bảng đều có thể embed. Model đa phương thức đưa text và ảnh vào **cùng một không gian**, cho phép tìm ảnh bằng câu mô tả.

**Kích thước lưu trữ (tính nhanh):**

```text
1 vector 384 chiều float32 = 384 × 4 byte ≈ 1.5 KB
1 triệu chunk               ≈ 1.5 GB (chưa tính index HNSW và payload)
Quantization int8           ≈ giảm ~4 lần
```

**Embeddings trong lakehouse — pattern phổ biến:**

```text
documents (bronze)  →  chunks (silver)  →  chunk_embeddings (gold)
                                              chunk_id, embedding ARRAY<FLOAT>,
                                              model_name, model_version, embedded_at
                                                   │
                                                   ▼
                                     sync sang vector DB (Qdrant/Milvus) để serve ANN
```

- Bảng lakehouse (Iceberg/Delta/Parquet) là **source of truth**: rẻ, version được (time travel), có lineage.
- Vector DB là **serving layer**: index ANN cho truy vấn nhanh.
- Pipeline **incremental**: chỉ embed chunk mới/thay đổi (so sánh content hash) — đúng như repo này tạo point ID deterministic từ `chunk_id` bằng SHA-256 để upsert idempotent.

**Pitfall:** re-embed toàn bộ mỗi lần chạy (tốn kém); không lưu `model_version` nên không biết vector nào cũ; để lakehouse và vector DB lệch nhau (chunk đã xoá ở nguồn nhưng còn trong index).

---

## Vector Similarity Metrics (Cosine, Dot Product, Euclidean)

**Vector similarity metrics** là các hàm đo mức độ gần nhau của hai embedding. Ba metric phổ biến:

**Cosine similarity** — đo góc giữa hai vector, bỏ qua độ dài:

```text
cos(a, b) = (a · b) / (‖a‖ ‖b‖)      ∈ [-1, 1], càng lớn càng giống
```

**Dot product (inner product)** — `a · b = Σ aᵢbᵢ`; nhạy với cả hướng lẫn độ dài vector. Một số model được huấn luyện để độ dài vector mang tín hiệu (ví dụ độ "phổ biến").

**Euclidean distance (L2)** — `‖a − b‖`, khoảng cách hình học; càng nhỏ càng giống.

**Mối quan hệ quan trọng:** khi vector đã **normalize về độ dài 1**:

```text
cosine(a, b) = a · b
‖a − b‖² = 2 − 2·cos(a, b)
```

→ cả ba metric cho **cùng thứ hạng** kết quả. Đó là lý do nhiều hệ thống normalize vector rồi dùng dot product (tính nhanh nhất).

**Chọn metric thế nào:** dùng **metric mà embedding model được huấn luyện với** (ghi trong model card). Với E5, khuyến nghị normalize và dùng cosine — repo này tạo collection Qdrant với `Distance.COSINE`.

**Ngoài ra:** **Manhattan (L1)**; **Hamming** cho binary vector (binary quantization); **Jaccard** cho tập hợp/sparse.

**Pitfall:**

- Đặt collection là Euclid nhưng model huấn luyện cho cosine và không normalize → thứ hạng sai.
- So sánh điểm tuyệt đối giữa hai model khác nhau: E5 có xu hướng cho cosine khá cao ngay cả với cặp không liên quan (thường quanh 0.7–0.8), nên `score_threshold` phải hiệu chỉnh theo từng model, không dùng một ngưỡng "0.5" chung chung.
- Trộn điểm cosine với điểm BM25 (thang đo khác nhau) mà không chuẩn hoá — xem Hybrid Search.

---

## Semantic Search

**Semantic search** là tìm kiếm theo **ý nghĩa** thay vì khớp từ khoá. Câu hỏi "làm sao tránh đếm trùng doanh thu khi join" có thể tìm ra đoạn viết về "double counting" và "fan-out join" dù không chung từ nào.

**Pipeline:**

1. **Indexing (offline)**: chunk tài liệu → embed (`passage: ...`) → lưu vector + payload vào vector DB.
2. **Query (online)**: embed câu hỏi (`query: ...`) → tìm **k nearest neighbors** theo similarity metric → trả về chunk kèm score.
3. (Tuỳ chọn) lọc theo metadata, re-rank, rồi đưa vào LLM.

```python
hits = client.query_points(
    collection_name="knowledge",
    query=embed_query("tránh double counting khi join"),
    limit=5,
).points
for h in hits:
    print(round(h.score, 3), h.payload["heading"])
```

**Keyword search vs semantic search:**

```text
Keyword (BM25, SQLite FTS5)       Semantic (vector)
- khớp chính xác từ/mã/tên        - hiểu đồng nghĩa, diễn đạt khác, đa ngôn ngữ
- giải thích được vì sao match    - khó giải thích
- yếu với paraphrase              - yếu với ID, mã lỗi, tên hiếm
```

→ Thực tế thường dùng **hybrid search** kết hợp cả hai — đúng như repo này kết hợp Qdrant với SQLite FTS5.

**Pitfall:** semantic search **luôn trả về kết quả** (k láng giềng gần nhất) kể cả khi không có gì liên quan — cần ngưỡng score hoặc bước kiểm tra relevance để LLM không trả lời dựa trên chunk lạc đề. Chunk quá dài làm vector bị "trung bình hoá" nhiều chủ đề, giảm độ chính xác.

---

## Vector Search Indexes (ANN Index: HNSW, IVF, PQ)

**Vector search index** là cấu trúc dữ liệu giúp tìm láng giềng gần nhất nhanh mà không phải so sánh câu hỏi với **mọi** vector. Tìm chính xác (brute-force/flat) có độ phức tạp O(N) mỗi query — ổn với vài chục nghìn vector, quá chậm với hàng chục triệu. Index đánh đổi một chút độ chính xác lấy tốc độ: **Approximate Nearest Neighbor (ANN)**.

**HNSW (Hierarchical Navigable Small World):**

- Xây đồ thị nhiều tầng: tầng trên thưa (bước nhảy xa), tầng dưới dày (chi tiết). Tìm kiếm đi tham lam từ tầng trên xuống.
- Tham số: `M` (số cạnh mỗi node), `ef_construct` (chất lượng khi build), `ef` / `ef_search` (độ rộng tìm kiếm lúc query — tăng thì recall cao hơn, chậm hơn).
- Recall cao, latency thấp; tốn RAM; là index mặc định của Qdrant, Weaviate, Chroma.

**IVF (Inverted File Index):**

- Phân cụm vector bằng k-means thành `nlist` cụm (centroid). Query chỉ quét `nprobe` cụm gần nhất.
- Build nhanh, ít RAM hơn HNSW; recall phụ thuộc `nprobe`; cần dữ liệu huấn luyện để tạo centroid.

**PQ (Product Quantization) và quantization nói chung:** nén vector (chia thành sub-vector, mã hoá bằng codebook) → giảm RAM nhiều lần, đổi lại sai số. Thường kết hợp: `IVF_PQ`. Ngoài ra có scalar quantization (int8), binary quantization.

**Disk-based (DiskANN và tương tự):** giữ phần lớn index trên SSD cho tập dữ liệu rất lớn.

```text
Quy mô                     Gợi ý
< ~100K vector             flat/brute-force cũng đủ (recall 100%)
100K – vài chục triệu      HNSW (+ scalar quantization nếu thiếu RAM)
rất lớn, RAM hạn chế       IVF_PQ, DiskANN
```

**Pitfall:**

- Đo latency mà không đo **recall@k** (so với brute-force) → không biết index đang bỏ sót bao nhiêu.
- **Filter + ANN**: lọc metadata quá chặt sau khi tìm ANN có thể trả về ít hơn k kết quả; vector DB tốt (Qdrant) lọc trong lúc duyệt đồ thị và cần **payload index** cho field lọc.
- HNSW update/xoá nhiều làm index phân mảnh; cần optimize/rebuild định kỳ.
