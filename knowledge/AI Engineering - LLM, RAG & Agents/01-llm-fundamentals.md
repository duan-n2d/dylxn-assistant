---
title: LLM Fundamentals - Generative AI, Tokenization, Context Window, Temperature, Hallucination
type: concept
domain: ai-engineering
tags:
  - ai-engineering
  - generative-ai
  - llm
  - tokenization
  - context-window
  - temperature
  - hallucination
---
# AI Engineering — LLM, RAG & Agents

## Bài 1 — LLM Fundamentals: Generative AI, LLM, Tokenization, Context Window, Temperature và Hallucination

Bài này là nền tảng cho toàn bộ series AI Engineering. Trước khi làm RAG hay agent, bạn cần hiểu LLM "nhìn" dữ liệu như thế nào (token), nó nhớ được bao nhiêu (context window), nó chọn chữ tiếp theo ra sao (temperature) và vì sao nó có thể bịa (hallucination).

```text
Lộ trình series:
01 LLM fundamentals
02 Prompting, reasoning, context management, caching, routing
03 Embeddings & vector search
04 Vector databases
05 RAG pipeline: chunking, hybrid search, re-ranking
06 Agents & tool calling
07 Multi-agent & frameworks
08 Knowledge graph, ontology, taxonomy, GraphRAG
09 Agentic analytics & lakehouse
10 GEO & AEO
```

---

## Generative AI (AI tạo sinh)

**Generative AI** là nhóm model học phân phối xác suất của dữ liệu huấn luyện rồi **sinh ra dữ liệu mới** có cùng "dáng dấp": văn bản, code, ảnh, audio, video. Điểm khác với AI "truyền thống" (discriminative/predictive) là: model phân loại trả lời "email này có phải spam không?", còn model generative trả lời "hãy viết một email".

**Các họ kiến trúc chính:**

- **Transformer (autoregressive)**: sinh từng token một, mỗi token dựa trên các token trước đó. Đây là nền của LLM như GPT, Llama, Qwen, Claude.
- **Diffusion model**: bắt đầu từ nhiễu ngẫu nhiên rồi khử nhiễu dần thành ảnh/audio (Stable Diffusion…).
- Các họ cũ hơn: GAN, VAE.

**Khi nào dùng trong data engineering:**

- Sinh SQL/dbt model từ mô tả (Text-to-SQL), viết docs cho cột, sinh test case.
- Tóm tắt incident, giải thích lineage, trả lời câu hỏi trên tài liệu nội bộ (RAG — chính là repo Dylxn Assistant này).
- Trích xuất dữ liệu có cấu trúc từ văn bản tự do (hoá đơn, ticket) để nạp vào bảng.

**Trade-off và pitfall:**

- Output là **xác suất**, không phải tra cứu: cùng prompt có thể ra kết quả khác nhau, và có thể sai một cách tự tin (xem Hallucination).
- Chi phí tính theo token và latency cao hơn nhiều so với một câu SQL.
- Dữ liệu nhạy cảm gửi lên API bên ngoài là rủi ro governance — lý do repo này chạy LLM local qua **Ollama**.

**Ví dụ:** "Viết dbt model `fct_orders` từ `stg_orders` với grain một dòng một order" → generative AI sinh SQL; con người vẫn phải review grain và test.

---

## Large Language Models (LLMs)

**Large Language Model (LLM)** là mạng neural kiến trúc **Transformer** được huấn luyện trên lượng văn bản rất lớn với mục tiêu đơn giản: **dự đoán token tiếp theo**. Từ mục tiêu đơn giản này, ở quy mô đủ lớn, model học được ngữ pháp, kiến thức thế giới, cách viết code và một mức độ suy luận.

**Cách hoạt động (rút gọn):**

1. Văn bản → **tokenization** → dãy token ID.
2. Mỗi token ID → vector (embedding) + thông tin vị trí.
3. Nhiều tầng **self-attention** cho phép mỗi token "nhìn" các token khác trong context để cập nhật biểu diễn.
4. Tầng cuối cho ra **logits** — điểm cho mọi token trong vocabulary → softmax → xác suất → sampling (theo **temperature**) → token tiếp theo.
5. Lặp lại (autoregressive) cho tới khi gặp token kết thúc hoặc chạm giới hạn độ dài.

**Các khái niệm đi kèm:**

- **Parameters**: số trọng số (vd 4B, 8B, 70B). Nhiều tham số thường giỏi hơn nhưng tốn RAM/VRAM hơn. Repo này mặc định dùng `qwen3:4b` qua Ollama — đủ nhỏ để chạy trên laptop.
- **Pre-training → instruction tuning / RLHF**: base model chỉ "viết tiếp văn bản"; bản instruct/chat được tinh chỉnh để làm theo chỉ dẫn.
- **Context window**: số token tối đa xử lý trong một lần gọi.
- **Knowledge cutoff**: model không biết gì sau thời điểm dữ liệu huấn luyện, và không biết gì về tài liệu nội bộ của bạn → cần **RAG**.

**Pitfall:** coi LLM như database. LLM không lưu "bản ghi" có thể truy vấn chính xác; nó nén kiến thức vào trọng số và có thể **hallucinate**. Với số liệu kinh doanh, hãy để LLM sinh SQL chạy trên warehouse thay vì hỏi LLM con số trực tiếp.

```text
Hỏi: "Doanh thu tháng 10 là bao nhiêu?"
Sai:  hỏi thẳng LLM → con số bịa
Đúng: LLM sinh SQL → chạy trên semantic layer/lakehouse → LLM diễn giải kết quả
```

---

## Tokenization in LLMs (Tokenization trong LLM)

**Tokenization** là bước cắt văn bản thành các đơn vị **token** và ánh xạ mỗi token thành một **integer ID** trong vocabulary của model. LLM không đọc ký tự hay từ — nó chỉ thấy dãy số ID.

**Các cách tokenize:**

- **Word-level**: mỗi từ là một token → vocabulary khổng lồ, không xử lý được từ mới (out-of-vocabulary).
- **Character-level**: vocabulary nhỏ nhưng chuỗi rất dài, model khó học.
- **Subword** (phổ biến nhất hiện nay): **BPE (Byte-Pair Encoding)**, **WordPiece**, **Unigram/SentencePiece**. Từ phổ biến là một token, từ hiếm bị tách thành nhiều mảnh. Byte-level BPE đảm bảo mọi chuỗi UTF-8 đều tokenize được.

**BPE hoạt động thế nào:** bắt đầu từ các byte/ký tự, đếm cặp liền kề xuất hiện nhiều nhất trong corpus, gộp thành token mới, lặp lại đến khi đạt kích thước vocabulary mong muốn.

**Vì sao data engineer cần quan tâm:**

- **Chi phí và giới hạn** đều tính bằng token, không phải ký tự. Tiếng Việt có dấu thường tốn nhiều token hơn tiếng Anh cho cùng một ý, vì tokenizer được huấn luyện chủ yếu trên tiếng Anh.
- **Chunk size** trong RAG phải khớp giới hạn token của embedding model. Ví dụ `multilingual-e5-small` nhận tối đa 512 token; repo này chunk theo **1800 ký tự**, cần đảm bảo không vượt 512 token sau khi tokenize, nếu không phần đuôi bị cắt (truncation) và mất nghĩa.
- Mỗi model có tokenizer riêng: đếm token bằng tokenizer của GPT không đúng cho Qwen hay E5.

```python
from transformers import AutoTokenizer

tok = AutoTokenizer.from_pretrained("intfloat/multilingual-e5-small")
text = "passage: Grain là mức chi tiết của một dòng trong fact table."
ids = tok(text)["input_ids"]
print(len(ids))  # số token thực tế, dùng để kiểm tra chunk có vượt 512 không
```

**Pitfall:** ước lượng "1 token ≈ 4 ký tự" chỉ đúng tương đối cho tiếng Anh; với tiếng Việt, code, JSON hoặc số liệu, hãy đo bằng tokenizer thật.

---

## AI Context Window (Context Window là gì)

**Context window** là số token tối đa mà một LLM xử lý được trong một lần gọi, gồm **cả input** (system prompt, lịch sử hội thoại, tài liệu đính kèm, kết quả tool) **lẫn output** model sinh ra. Vượt giới hạn → request bị lỗi hoặc phần đầu bị cắt bỏ.

**Vì sao có giới hạn:** self-attention so sánh mọi token với mọi token khác nên chi phí tính toán và bộ nhớ (KV cache) tăng nhanh theo độ dài. Model cũng chỉ hoạt động tốt ở độ dài nó được huấn luyện.

**Context window và RAG:** context window có hạn (và tốn tiền theo token) nên không thể nhét toàn bộ knowledge base vào prompt. Đó là lý do ra đời **Retrieval-Augmented Generation**: chỉ lấy vài chunk liên quan nhất (repo này mặc định `retrieval_limit = 5`, giới hạn context `context_max_chars = 12000`) rồi đưa vào prompt.

**Context dài có thay thế RAG không?** Không hoàn toàn:

- Chi phí và latency tăng theo số token mỗi lần hỏi.
- Hiện tượng **"lost in the middle"**: model thường tận dụng thông tin ở đầu và cuối context tốt hơn ở giữa.
- Dữ liệu thay đổi liên tục, cần phân quyền theo user → retrieval vẫn cần thiết.

**Với Ollama:** context mặc định của model chạy local thường nhỏ hơn mức tối đa model hỗ trợ; có thể chỉnh bằng option `num_ctx`. `num_predict` (repo đặt 256) giới hạn số token output.

```json
{ "model": "qwen3:4b", "prompt": "...", "options": { "num_ctx": 8192, "num_predict": 256 } }
```

**Pitfall:** quên rằng output cũng chiếm chỗ trong context; nhồi context sát giới hạn khiến câu trả lời bị cụt. Xem thêm **Context Window Management** ở Bài 2.

---

## Temperature in Generative AI (Temperature)

**Temperature** là tham số sampling điều khiển mức độ ngẫu nhiên khi LLM chọn token tiếp theo. Model tạo ra logits cho mọi token; trước khi softmax, logits được **chia cho temperature T**:

```text
p_i = exp(z_i / T) / Σ_j exp(z_j / T)
```

- **T → 0**: phân phối "nhọn", gần như luôn chọn token xác suất cao nhất (greedy) → ổn định, lặp lại được.
- **T = 1**: giữ nguyên phân phối model học.
- **T > 1**: phân phối "phẳng" hơn, token ít khả năng cũng được chọn → đa dạng, sáng tạo nhưng dễ lạc đề và sai.

**Tham số đi kèm:** **top-k** (chỉ xét k token tốt nhất), **top-p / nucleus sampling** (xét nhóm token nhỏ nhất có tổng xác suất ≥ p). Thường chỉ nên chỉnh một trong temperature hoặc top-p, không chỉnh mạnh cả hai.

**Chọn temperature theo task:**

```text
Text-to-SQL, trích xuất JSON, phân loại   → 0 – 0.2
RAG trả lời theo tài liệu                  → 0 – 0.3
Tóm tắt, viết docs                         → 0.3 – 0.7
Brainstorm tên metric, ý tưởng             → 0.7 – 1.0
```

**Ví dụ Ollama:**

```json
{ "model": "qwen3:4b", "prompt": "Viết SQL ...", "options": { "temperature": 0.1 } }
```

**Pitfall:**

- Temperature = 0 **không** đảm bảo tuyệt đối deterministic (batching, floating point trên GPU, phiên bản model có thể khác).
- Temperature thấp không chữa hallucination: model vẫn có thể tự tin trả lời sai — chỉ là sai nhất quán hơn. Grounding (RAG) mới là giải pháp chính.
- Một số reasoning model khuyến nghị dùng temperature mặc định của nhà cung cấp; đọc model card trước khi chỉnh.

---

## AI Hallucination (Hallucination trong LLM)

**Hallucination** là khi LLM sinh ra nội dung trôi chảy, nghe hợp lý nhưng **sai hoặc không có căn cứ**: bịa tên hàm, bịa cột không tồn tại, bịa trích dẫn, bịa số liệu.

**Vì sao xảy ra:**

- LLM được huấn luyện để sinh văn bản **có xác suất cao**, không phải để kiểm chứng sự thật. Khi thiếu kiến thức, nó vẫn sinh câu "giống" câu trả lời.
- Kiến thức trong trọng số bị nén, mơ hồ, có thể lỗi thời (knowledge cutoff).
- Prompt mơ hồ hoặc ép model phải trả lời ("hãy cho tôi con số").
- Context nhiễu: retrieval trả về chunk sai, model tổng hợp sai.

**Các loại thường gặp trong data work:**

- Text-to-SQL bịa tên bảng/cột (`customer_ltv` không tồn tại).
- Giải thích sai logic dbt macro.
- Trả lời câu hỏi nằm ngoài knowledge base như thể biết.

**Cách giảm thiểu:**

1. **RAG / grounding**: chỉ trả lời dựa trên context được retrieve, kèm **citation** — repo này đánh số nguồn cho từng chunk trong context.
2. Prompt cho phép từ chối: "Nếu context không chứa câu trả lời, nói rằng không biết."
3. **Validation có cấu trúc**: với SQL — parse, kiểm tra tên bảng/cột với catalog, chạy `EXPLAIN`, giới hạn read-only. Với JSON — validate schema.
4. Temperature thấp cho task cần chính xác.
5. Evaluation: bộ câu hỏi chuẩn (golden set) đo tỉ lệ trả lời đúng/đúng nguồn.

```text
System: Chỉ trả lời dựa trên CONTEXT. Trích dẫn [1], [2]...
        Nếu CONTEXT không đủ, trả lời: "Knowledge base chưa có thông tin này."
```

**Pitfall:** tin rằng RAG loại bỏ hoàn toàn hallucination. Model vẫn có thể diễn giải sai chunk đúng, hoặc retrieval trả về chunk sai. Cần đo cả **retrieval quality** lẫn **faithfulness** của câu trả lời.
