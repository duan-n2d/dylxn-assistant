---
title: RAG Pipeline - Retrieval-Augmented Generation, Chunking, Hybrid Search, Re-ranking
type: tutorial
domain: ai-engineering
tags:
  - ai-engineering
  - rag
  - retrieval-augmented-generation
  - chunking
  - hybrid-search
  - bm25
  - rrf
  - re-ranking
  - cross-encoder
  - lakehouse
---
# AI Engineering — LLM, RAG & Agents

## Bài 5 — RAG Pipeline: Chunking, Hybrid Search và Re-ranking

Đây là bài trung tâm của series, vì chính Dylxn Assistant là một hệ RAG. Bài này mô tả pipeline RAG đầu-cuối, các chiến lược chunking, cách lưu chunk trong bảng lakehouse, hybrid search và re-ranking.

---

## Retrieval-Augmented Generation (RAG)

**Retrieval-Augmented Generation (RAG)** là kiến trúc trong đó, tại thời điểm hỏi, hệ thống **truy xuất** tài liệu liên quan từ một kho tri thức rồi đưa chúng vào prompt để LLM **sinh câu trả lời dựa trên tài liệu đó** (grounding), thay vì chỉ dựa vào kiến thức trong trọng số.

**Vì sao cần RAG:** LLM không biết tài liệu nội bộ, có knowledge cutoff, và có thể hallucinate. Fine-tuning tốn kém, khó cập nhật và không cho trích dẫn nguồn. RAG cập nhật tri thức chỉ bằng cách sửa tài liệu và re-index.

**Pipeline của Dylxn Assistant:**

```text
INDEXING (offline)
Markdown (knowledge/) → parser: YAML frontmatter + tách theo heading
  → chunker: tối đa 1800 ký tự, overlap 200
  → embed "passage: ..." bằng multilingual-e5-small (384 chiều)
  → Qdrant (vector) + SQLite FTS5 (keyword)

QUERY (online)
câu hỏi → embed "query: ..." → Qdrant top-k  ┐
        → FTS5 BM25 top-k                    ┴→ fusion (0.7 vector + 0.3 keyword)
  → top 5 chunk → build context có đánh số [1]..[n] (≤ 12000 ký tự)
  → prompt + context → LLM (Ollama qwen3:4b) → câu trả lời kèm citation
```

**Các biến thể nâng cao:** query rewriting / multi-query, HyDE (embed một câu trả lời giả định), re-ranking, parent-child retrieval, GraphRAG, **agentic RAG** (agent tự quyết định khi nào và tìm gì).

**Đánh giá RAG — tách hai tầng:**

- **Retrieval**: recall@k, MRR, hit rate — chunk đúng có nằm trong top-k không?
- **Generation**: faithfulness (có bám context không), answer relevance, citation đúng nguồn.

**Pitfall:**

- Sửa prompt khi lỗi thật ra nằm ở retrieval (chunk đúng không được lấy) — luôn kiểm tra retrieval trước.
- Không có cơ chế "không biết" khi context không liên quan.
- Knowledge base thiếu nội dung — đây chính là lý do series này được viết: trước đó Dylxn chỉ có tài liệu Data Modeling & dbt nên không thể trả lời câu hỏi về AI/RAG.

---

## Chunking Strategies for RAG (Chiến lược chunking)

**Chunking** là bước chia tài liệu dài thành các đoạn nhỏ trước khi embed. Chunk là **đơn vị retrieval**: quá lớn → vector bị loãng nhiều chủ đề, tốn context; quá nhỏ → mất ngữ cảnh, câu trả lời bị cắt rời.

**Các chiến lược:**

- **Fixed-size**: cắt theo N ký tự/token với **overlap** (vd 200) để không mất ý ở ranh giới. Đơn giản, nhưng có thể cắt giữa câu/giữa code block.
- **Sentence / paragraph-based**: gom câu hoặc đoạn văn đến khi đạt kích thước tối đa. Tôn trọng ranh giới tự nhiên.
- **Recursive**: thử tách theo dấu phân cách lớn trước (`\n\n`), quá dài mới tách tiếp bằng dấu nhỏ hơn (`\n`, `. `, khoảng trắng).
- **Structural / document-aware**: tách theo cấu trúc tài liệu — heading Markdown, section HTML, hàm trong code, trang PDF. **Repo này dùng cách này**: parser tách theo heading, chunker chỉ cắt thêm khi một section vượt 1800 ký tự (ưu tiên ranh giới đoạn văn, overlap 200).
- **Semantic chunking**: embed từng câu, cắt khi độ tương đồng giữa câu liền kề giảm mạnh.
- **Parent-child (small-to-big)**: index chunk nhỏ để tìm chính xác, nhưng trả về chunk cha (cả section) cho LLM để đủ ngữ cảnh.
- **Contextual enrichment**: thêm title/heading/tóm tắt tài liệu vào đầu mỗi chunk trước khi embed, để chunk "tự đứng được".

**Gợi ý chọn kích thước:** bắt đầu khoảng 200–500 token, đo recall trên bộ câu hỏi thật rồi điều chỉnh; luôn ≤ giới hạn input của embedding model (E5: 512 token).

**Ví dụ — vì sao knowledge note nên có heading riêng cho từng khái niệm:**

```markdown
## Hybrid Search          ← chunk này chỉ nói về Hybrid Search
...
## Re-ranking Models      ← chunk riêng; câu hỏi "re-ranking là gì" match chính xác
```

**Pitfall:** chunk mất ngữ cảnh ("Nó giúp giảm chi phí" — "nó" là gì?); bảng/code bị cắt đôi; overlap quá lớn tạo nhiều chunk trùng chiếm hết top-k; đổi chiến lược chunking mà không re-index toàn bộ.

---

## Chunking for RAG: Storing Chunks in Lakehouse Tables (lưu chunk trong bảng Iceberg)

Khi RAG chạy ở quy mô doanh nghiệp (hàng triệu tài liệu, nhiều nguồn), chunking nên được coi là **một bước data pipeline** với bảng đầu ra có schema, version và lineage — thay vì chỉ là script tạm. Lakehouse (Apache Iceberg, Delta Lake) là nơi tự nhiên để lưu.

**Mô hình bảng gợi ý:**

```sql
-- silver: một dòng một chunk
CREATE TABLE rag.chunks (
  chunk_id        STRING,      -- hash(doc_id, chunk_index, strategy_version)
  doc_id          STRING,
  source_uri      STRING,
  heading_path    STRING,      -- "Bài 5 > Hybrid Search"
  chunk_index     INT,
  content         STRING,
  content_hash    STRING,      -- phát hiện thay đổi để embed incremental
  token_count     INT,
  chunk_strategy  STRING,      -- 'heading-aware-1800-200'
  acl_groups      ARRAY<STRING>,
  ingested_at     TIMESTAMP
) PARTITIONED BY (days(ingested_at));

-- gold: embedding tách bảng riêng vì gắn với model
CREATE TABLE rag.chunk_embeddings (
  chunk_id STRING, model_name STRING, model_version STRING,
  embedding ARRAY<FLOAT>, embedded_at TIMESTAMP
);
```

**Lợi ích:**

- **Reproducibility**: Iceberg snapshot / time travel cho biết chatbot đã trả lời dựa trên phiên bản chunk nào.
- **Thử nghiệm A/B chiến lược chunking**: lưu nhiều `chunk_strategy` song song, so sánh recall.
- **Incremental**: chỉ embed chunk có `content_hash` mới (MERGE INTO), giảm chi phí.
- **Governance**: `acl_groups` đi theo chunk, áp dụng khi retrieve; xoá tài liệu ở nguồn → xoá chunk → sync xoá trong vector DB.
- Dùng được dbt/Spark/SQL quen thuộc để kiểm thử: chunk rỗng, `token_count` > 512, chunk trùng lặp.

**Pitfall:** `chunk_id` không deterministic khiến mỗi lần chạy sinh ID mới và vector DB phình to; quên partition/compaction làm bảng có quá nhiều file nhỏ; lưu embedding và content cùng bảng khiến đổi model phải ghi lại toàn bộ.

---

## Hybrid Search

**Hybrid search** kết hợp **dense retrieval** (vector/semantic) với **sparse/keyword retrieval** (BM25, full-text) rồi trộn hai danh sách kết quả thành một thứ hạng. Mục tiêu: vừa hiểu nghĩa (paraphrase, đa ngôn ngữ) vừa bắt chính xác thuật ngữ, mã, tên riêng (`FTS5`, `SCD Type 2`, `ERR-4012`).

**Các cách fusion:**

**1. Reciprocal Rank Fusion (RRF)** — chỉ dùng thứ hạng, không cần chuẩn hoá điểm:

```text
RRF(d) = Σ_{mỗi retriever r} 1 / (k + rank_r(d))     (k thường = 60)
```

Ổn định, ít phải tinh chỉnh; được nhiều vector DB hỗ trợ sẵn (Qdrant Query API, Weaviate, Elasticsearch…).

**2. Weighted score fusion** — `score = α·semantic + (1−α)·keyword`. Cần **chuẩn hoá** hai loại điểm về cùng thang (min-max, z-score) vì cosine nằm trong [-1, 1] còn BM25 không có cận trên.

**Hybrid trong Dylxn Assistant:** vector search trên Qdrant + keyword search trên **SQLite FTS5** (`tokenize='porter unicode61'`, xếp hạng bằng hàm `bm25()`), rồi trộn theo trọng số `hybrid_weight = 0.7` (semantic) và `keyword_weight = 0.3`. Chunk chỉ xuất hiện ở một phía vẫn được giữ.

**Lưu ý kỹ thuật về FTS5:** hàm `bm25()` của SQLite FTS5 trả về giá trị **âm**, càng âm càng liên quan (vì vậy `ORDER BY bm25(...)` tăng dần). Khi trộn với cosine phải đổi dấu/chuẩn hoá trước; nếu chỉ kẹp `max(score, 0)` thì mọi điểm keyword sẽ thành 0.

```sql
SELECT chunk_id, -bm25(chunks_fts) AS kw_score   -- đổi dấu: lớn hơn = tốt hơn
FROM chunks_fts
WHERE chunks_fts MATCH '"hybrid" "search"'
ORDER BY kw_score DESC LIMIT 15;
```

**Pitfall:** tokenizer keyword không hợp ngôn ngữ (stemmer `porter` dành cho tiếng Anh, không giúp gì cho tiếng Việt); trộn điểm thô không chuẩn hoá; đặt trọng số theo cảm tính thay vì đo trên bộ câu hỏi chuẩn.

---

## Re-ranking Models (Reranker, Cross-encoder)

**Re-ranking model** là model thứ hai trong pipeline retrieval, nhận câu hỏi và một tập ứng viên (vd top 50 từ hybrid search) rồi **chấm lại điểm liên quan** cho từng cặp (query, document) để sắp xếp lại, chỉ giữ top vài kết quả tốt nhất cho LLM. Đây là **two-stage retrieval**: stage 1 nhanh, recall cao; stage 2 chậm hơn nhưng chính xác.

**Bi-encoder vs cross-encoder:**

```text
Bi-encoder (embedding model, vd E5)        Cross-encoder (reranker)
- embed query và doc RIÊNG RẼ              - đưa query + doc VÀO CÙNG model
- doc embed trước, lưu index               - không pre-compute được, chạy mỗi query
- nhanh, scale hàng triệu doc              - chậm, chỉ dùng cho vài chục ứng viên
- độ chính xác vừa                         - chính xác cao hơn vì attention chéo
```

**Các lựa chọn:** cross-encoder mã nguồn mở (họ `bge-reranker`, `ms-marco` cross-encoder, có bản đa ngôn ngữ), reranker dạng API, **late-interaction** (ColBERT) ở giữa hai cách, hoặc **LLM-as-reranker** (hỏi LLM chấm điểm — đắt nhất).

```python
from sentence_transformers import CrossEncoder

reranker = CrossEncoder("BAAI/bge-reranker-v2-m3")        # đa ngôn ngữ
candidates = retriever.retrieve(q)                       # vd 20 chunk
scores = reranker.predict([(q, c.content) for c in candidates])
top = [c for _, c in sorted(zip(scores, candidates), key=lambda x: -x[0])][:5]
```

**Khi nào dùng:** khi top-k hiện tại chứa chunk đúng nhưng xếp hạng thấp, khi muốn giảm số chunk đưa vào context (rẻ hơn, ít nhiễu), hoặc khi hybrid fusion khó tinh chỉnh.

**Trade-off / pitfall:** tăng latency (chạy model trên từng cặp — với CPU laptop, 20–50 cặp là hợp lý); reranker chỉ sắp xếp lại, **không cứu được** nếu stage 1 không lấy được chunk đúng (tăng candidate pool trước); chọn reranker chỉ hỗ trợ tiếng Anh cho nội dung tiếng Việt; chunk dài bị cắt theo giới hạn token của reranker.
