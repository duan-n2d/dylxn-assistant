---
title: Prompting, Reasoning và Context - Prompt Engineering, Chain of Thought, DSPy, Context Management, Semantic Caching, LLM Routing
type: tutorial
domain: ai-engineering
tags:
  - ai-engineering
  - prompt-engineering
  - chain-of-thought
  - dspy
  - context-window-management
  - semantic-caching
  - llm-routing
---
# AI Engineering — LLM, RAG & Agents

## Bài 2 — Prompting, Reasoning và Context: điều khiển LLM trong hệ thống thật

Bài 1 giải thích LLM là gì. Bài này nói về cách **điều khiển** LLM: viết prompt, khuyến khích suy luận từng bước, tối ưu prompt bằng code (DSPy), quản lý context window, và hai kỹ thuật tối ưu chi phí ở tầng hệ thống: semantic caching và LLM routing.

---

## Prompt Engineering

**Prompt engineering** là việc thiết kế input cho LLM (chỉ dẫn, ví dụ, context, định dạng output) để nhận được kết quả chính xác, đúng format và ổn định.

**Các thành phần của một prompt tốt:**

- **System prompt**: vai trò, quy tắc, giới hạn ("Bạn là trợ lý Data Engineering, chỉ trả lời từ context").
- **Task**: yêu cầu cụ thể, đo được.
- **Context**: dữ liệu liên quan (chunk từ RAG, schema bảng, kết quả tool).
- **Output format**: JSON schema, Markdown, SQL thuần…
- **Examples**: few-shot.

**Kỹ thuật phổ biến:**

- **Zero-shot**: chỉ mô tả task.
- **Few-shot**: kèm vài cặp input → output mẫu; rất hiệu quả cho format và phong cách.
- **Chain of Thought**: yêu cầu suy luận từng bước (xem phần sau).
- **Delimiters**: bao context bằng tag/khối rõ ràng để model phân biệt chỉ dẫn và dữ liệu.
- **Structured output**: yêu cầu JSON, hoặc dùng tính năng JSON mode / schema của runtime (Ollama hỗ trợ tham số `format`).

**Ví dụ Text-to-SQL:**

```text
System: Bạn sinh SQL DuckDB. Chỉ dùng bảng/cột trong SCHEMA. Chỉ SELECT.
SCHEMA:
  fct_orders(order_id, customer_id, order_date, amount)
  dim_customers(customer_id, segment)
Ví dụ:
  Q: Tổng doanh thu theo segment
  SQL: SELECT c.segment, SUM(o.amount) FROM fct_orders o JOIN dim_customers c USING (customer_id) GROUP BY 1;
Q: Số đơn hàng theo tháng năm 2025
SQL:
```

**Pitfall:**

- Prompt "dài và chung chung" kém hơn prompt ngắn và cụ thể.
- Nhét dữ liệu không tin cậy (nội dung web, tài liệu do user upload) vào prompt mà không phân tách → **prompt injection**.
- Tối ưu prompt cho một model rồi đổi model: hành vi có thể thay đổi, cần chạy lại bộ eval.
- Không version prompt — hãy lưu prompt như code (repo này để trong `llm/prompts.py`).

---

## Chain of Thought (CoT)

**Chain of Thought (CoT)** là kỹ thuật prompting khiến LLM viết ra các bước suy luận trung gian trước khi đưa ra đáp án cuối. Ý tưởng được phổ biến qua nghiên cứu của Google (Wei et al., 2022) với few-shot CoT; biến thể **zero-shot CoT** chỉ cần thêm câu kiểu "Let's think step by step".

**Vì sao hiệu quả:** LLM sinh từng token; khi viết ra bước trung gian, mỗi bước trở thành context cho bước sau — model có thêm "không gian tính toán" thay vì phải nhảy thẳng tới đáp án. Hiệu quả rõ với bài toán nhiều bước: số học, logic, lập kế hoạch truy vấn.

**Biến thể và quan hệ:**

- **Self-consistency**: sinh nhiều chuỗi CoT (temperature > 0), lấy đáp án đa số.
- **ReAct**: xen kẽ suy luận (Thought) với hành động gọi tool (Action) và quan sát kết quả (Observation) — CoT mở rộng ra thế giới bên ngoài.
- **Reasoning models**: nhiều model hiện đại (kể cả dòng Qwen3 có "thinking mode") được huấn luyện để tự suy luận nội bộ trước khi trả lời, nên không cần prompt CoT thủ công.

**Ví dụ:**

```text
Q: Bảng fct_order_items grain là một dòng một item. Join với fct_payments
   grain một dòng một payment, theo order_id. SUM(amount) có đúng không?
Hãy suy luận từng bước rồi kết luận.

A: 1) Một order có n item và m payment.
   2) Join theo order_id tạo n × m dòng.
   3) SUM(payment.amount) bị nhân n lần → double counting.
   Kết luận: sai; cần aggregate từng bảng về grain order trước khi join.
```

**Trade-off / pitfall:**

- Tốn thêm token output → chậm và đắt hơn; không cần cho task đơn giản (phân loại, trích xuất).
- Chuỗi suy luận viết ra **không đảm bảo** phản ánh đúng quá trình nội bộ, và có thể sai dù trông hợp lý.
- Khi cần output máy đọc (JSON/SQL), tách phần suy luận khỏi phần đáp án, hoặc parse riêng phần cuối.

---

## DSPy

**DSPy** là framework mã nguồn mở xuất phát từ Stanford NLP, theo triết lý **"programming, not prompting"**: thay vì tay viết và chỉnh từng prompt, bạn khai báo pipeline LLM bằng code, định nghĩa metric, rồi để **optimizer** tự tìm prompt/few-shot example (và có thể cả fine-tune trọng số) tốt nhất.

**Khái niệm chính:**

- **Signature**: khai báo input/output của một bước, ví dụ `"question, schema -> sql"`.
- **Module**: khối xử lý dùng signature, ví dụ `dspy.Predict`, `dspy.ChainOfThought`, `dspy.ReAct`. Module có thể lồng nhau thành pipeline (giống layer trong PyTorch).
- **Metric**: hàm Python chấm điểm output (SQL chạy được và trả kết quả đúng?).
- **Optimizer** (trước gọi là teleprompter): ví dụ `BootstrapFewShot`, `MIPROv2` — chạy pipeline trên tập train, chọn ví dụ/chỉ dẫn tối đa hoá metric.

```python
import dspy

lm = dspy.LM("ollama_chat/qwen3:4b", api_base="http://localhost:11434")
dspy.configure(lm=lm)

class TextToSQL(dspy.Signature):
    """Sinh SQL DuckDB chỉ dùng bảng trong schema."""
    question: str = dspy.InputField()
    schema: str = dspy.InputField()
    sql: str = dspy.OutputField()

gen = dspy.ChainOfThought(TextToSQL)

def exec_match(example, pred, trace=None):
    return run(pred.sql) == run(example.sql)   # so kết quả thực thi

optimized = dspy.BootstrapFewShot(metric=exec_match).compile(gen, trainset=train)
```

**Khi nào dùng:** pipeline nhiều bước có tập ví dụ có nhãn và metric rõ ràng (Text-to-SQL, extraction, RAG QA), hoặc cần chuyển đổi giữa nhiều model mà không viết lại prompt.

**Pitfall:** cần dữ liệu đánh giá chất lượng; metric sai thì optimizer tối ưu sai. Quá trình compile gọi LLM rất nhiều lần (chi phí). API của DSPy thay đổi khá nhanh giữa các phiên bản — kiểm tra docs phiên bản bạn dùng.

---

## Context Window Management

**Context window management** là kỷ luật quyết định **cái gì được đưa vào** context window giới hạn của LLM, theo thứ tự nào, ở dạng nào — để tối đa chất lượng trong giới hạn token và chi phí. Với agent gọi tool nhiều vòng, đây là vấn đề sống còn vì lịch sử hội thoại và output tool tăng rất nhanh.

**Các kỹ thuật:**

- **Retrieval có chọn lọc**: chỉ lấy top-k chunk liên quan (RAG), dùng **re-ranking** để chọn chunk tốt nhất.
- **Budget theo token/ký tự**: repo này cắt context ở `context_max_chars = 12000`; mỗi chunk tối đa 1800 ký tự.
- **Ordering**: đặt thông tin quan trọng nhất ở đầu hoặc cuối (giảm hiệu ứng "lost in the middle").
- **Dedup**: loại chunk trùng/na ná (overlap giữa các chunk liền nhau).
- **Compression / summarization**: tóm tắt lịch sử hội thoại cũ, chỉ giữ quyết định quan trọng.
- **Trim tool output**: thay vì đưa 10.000 dòng kết quả SQL, đưa schema + 20 dòng mẫu + thống kê tổng hợp.
- **Memory ngoài**: lưu ghi chú, kết quả trung gian ra file/DB, chỉ nạp lại khi cần.
- **Tool selection**: nếu có hàng trăm tool, chỉ đưa mô tả các tool liên quan vào prompt.

**Ví dụ cho agent phân tích dữ liệu:**

```text
[System + quy tắc]                  ~800 token  (cố định, đặt đầu → dễ prompt-cache)
[Semantic layer: metric liên quan]  ~1500 token (retrieve theo câu hỏi)
[Tóm tắt các bước đã làm]           ~500 token
[Kết quả SQL gần nhất: 20 dòng]     ~700 token
[Câu hỏi hiện tại]
```

**Pitfall:** đưa "càng nhiều càng tốt" — context nhiễu làm model trả lời kém hơn và đắt hơn. Cắt chunk giữa chừng khiến mất câu kết luận. Quên tính token cho output và cho mô tả tool.

---

## Semantic Caching

**Semantic caching** là lớp cache cho ứng dụng LLM: lưu cặp (prompt, response), và khi có request mới **cùng nghĩa** (không cần trùng từng chữ) với một request cũ thì trả lại response đã lưu, bỏ qua lời gọi LLM.

**Cách hoạt động:**

1. Request mới → tạo **embedding** của câu hỏi.
2. Tìm trong vector store (có thể là một collection Qdrant riêng) câu hỏi cũ gần nhất.
3. Nếu **similarity ≥ threshold** (ví dụ cosine ≥ 0.95) và entry còn hạn (TTL) → **cache hit**, trả response cũ.
4. Nếu không → gọi LLM, lưu (embedding, câu hỏi, response, metadata) vào cache.

```python
def answer(q: str) -> str:
    v = embed_query(q)
    hit = qdrant.search("llm_cache", v, limit=1, score_threshold=0.95)
    if hit:
        return hit[0].payload["response"]
    resp = rag.ask(q)
    qdrant.upsert("llm_cache", [point(v, {"q": q, "response": resp, "kb_version": KB_VERSION})])
    return resp
```

**So với exact cache:** exact cache (hash của prompt) an toàn tuyệt đối nhưng hit rate thấp; semantic cache hit rate cao hơn nhưng có rủi ro trả sai.

**Khi nào dùng:** FAQ lặp lại nhiều (chatbot nội bộ, "định nghĩa metric X là gì?"), LLM đắt/chậm.

**Pitfall:**

- **False hit**: "doanh thu tháng 10" và "doanh thu tháng 11" có embedding rất gần nhau nhưng đáp án khác. Cần threshold cao, hoặc tách các tham số (ngày, ID) ra khỏi key và so khớp chính xác.
- **Stale data**: knowledge base hoặc dữ liệu thay đổi → phải invalidate (gắn `kb_version`, TTL).
- **Phân quyền**: không chia sẻ cache giữa user có quyền khác nhau.
- Không cache câu trả lời phụ thuộc thời gian thực hoặc phụ thuộc lịch sử hội thoại.

---

## LLM Routing

**LLM routing** là việc đặt một lớp điều phối trước nhiều model, quyết định **mỗi request nên gửi tới model nào** để cân bằng chất lượng, latency và chi phí. Câu hỏi đơn giản đi tới model nhỏ/rẻ/local; câu hỏi khó đi tới model lớn.

**Các chiến lược:**

- **Rule-based**: theo loại task, độ dài input, ngôn ngữ, độ nhạy cảm dữ liệu. Ví dụ dữ liệu PII bắt buộc dùng model local (Ollama).
- **Classifier-based**: một model nhỏ (hoặc embedding + classifier) dự đoán độ khó/loại câu hỏi.
- **Semantic routing**: so embedding câu hỏi với các "route" mẫu (vd route `sql`, route `docs`, route `chitchat`).
- **Cascade / fallback**: thử model rẻ trước; nếu output không qua kiểm tra (SQL không parse được, confidence thấp) thì leo thang lên model mạnh. Fallback khi provider lỗi hoặc timeout.

```python
def route(q: str, has_pii: bool) -> str:
    if has_pii:
        return "ollama/qwen3:4b"            # dữ liệu không rời máy
    if classify(q) == "definition":
        return "ollama/qwen3:4b"            # tra cứu RAG đơn giản
    return "large-hosted-model"              # suy luận nhiều bước, Text-to-SQL phức tạp
```

**Liên hệ repo:** `llm/factory.py` hiện chọn provider (`mock` / `ollama`) theo cấu hình — đây là dạng routing tĩnh đơn giản nhất; có thể mở rộng thành routing theo request.

**Trade-off / pitfall:**

- Router cũng tốn latency và có thể chọn sai; cần log quyết định route và đo chất lượng từng nhánh.
- Các model khác nhau phản ứng khác nhau với cùng prompt → cần prompt và eval riêng cho từng model.
- Hành vi không nhất quán giữa các lần hỏi (lúc model A, lúc model B) có thể gây khó hiểu cho người dùng.
