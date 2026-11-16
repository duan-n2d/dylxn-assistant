---
title: Multi-Agent và Frameworks - Multi-Agent System, Orchestration, Agentic Frameworks, LangChain, LlamaIndex, Autonomous Workflows
type: concept
domain: ai-engineering
tags:
  - ai-engineering
  - multi-agent-system
  - multi-agent-orchestration
  - agentic-frameworks
  - langchain
  - langgraph
  - llamaindex
  - autonomous-workflows
  - orchestration
---
# AI Engineering — LLM, RAG & Agents

## Bài 7 — Multi-Agent và Frameworks: phối hợp nhiều agent và chọn công cụ xây dựng

Bài 6 nói về một agent đơn lẻ. Bài này mở rộng sang hệ nhiều agent, cách điều phối chúng, các framework phổ biến (LangChain, LlamaIndex…) và autonomous workflow — nơi agent gặp lại những khái niệm quen thuộc của data engineer: DAG, scheduler, retry, alert.

---

## Multi-Agent System (MAS)

**Multi-agent system** là kiến trúc trong đó **nhiều agent tự chủ**, mỗi agent có vai trò, prompt, tool và đôi khi model riêng, **tương tác** với nhau để giải quyết một nhiệm vụ quá rộng hoặc quá phức tạp cho một agent duy nhất. Khái niệm MAS có từ lâu trong AI cổ điển; phiên bản hiện nay dùng LLM làm agent.

**Vì sao tách thành nhiều agent:**

- **Chuyên môn hoá**: mỗi agent có prompt ngắn, tập tool nhỏ → chọn tool chính xác hơn.
- **Context riêng**: mỗi agent giữ context của mình, tránh một context khổng lồ chứa mọi thứ.
- **Song song hoá**: nhiều agent nghiên cứu các nhánh cùng lúc.
- **Kiểm tra chéo**: một agent làm, một agent review.

**Ví dụ cho data team:**

```text
Planner agent      : hiểu câu hỏi, chia việc
Catalog agent      : tìm bảng/metric phù hợp trong data catalog, semantic layer
SQL agent          : viết và chạy SQL read-only
Validator agent    : kiểm tra kết quả (tổng khớp, không double counting)
Writer agent       : viết báo cáo cuối cho business user
```

**Trade-off:**

- Chi phí token tăng nhiều lần (mỗi agent gọi LLM riêng, trao đổi message).
- Khó debug hơn: lỗi có thể nằm ở bước chuyển giao giữa agent.
- Thông tin bị "rơi" khi agent này tóm tắt cho agent kia.

**Pitfall:** chia agent theo "chức danh" cho đẹp thay vì theo ranh giới thật của dữ liệu/tool; nhiều agent cùng ghi vào một tài nguyên mà không có cơ chế khoá. Nguyên tắc: **một agent tốt trước, nhiều agent khi đo được lợi ích**.

---

## Multi-Agent Orchestration

**Multi-agent orchestration** là tầng điều phối quyết định **agent nào làm gì, khi nào, theo thứ tự nào**, dữ liệu/kết quả được truyền giữa các agent ra sao, và khi nào toàn bộ hệ thống coi là hoàn thành.

**Các pattern điều phối:**

- **Sequential (pipeline)**: A → B → C, output agent trước là input agent sau. Dễ hiểu, dễ debug.
- **Supervisor / orchestrator–worker**: một agent điều phối giao việc cho các worker, tổng hợp kết quả, quyết định bước kế.
- **Hierarchical**: supervisor của supervisor — cho bài toán rất lớn.
- **Parallel fan-out / fan-in**: nhiều agent chạy song song (vd mỗi agent phân tích một region), một bước gộp kết quả.
- **Handoff**: agent chuyển quyền điều khiển hội thoại cho agent khác phù hợp hơn (vd từ "support" sang "billing").
- **Debate / reviewer**: agent sinh kết quả, agent khác phản biện, lặp tới khi đạt chuẩn.

**Shared state — trái tim của orchestration:** định nghĩa rõ một state object (câu hỏi, kế hoạch, kết quả từng bước, lỗi) mà mọi agent đọc/ghi theo hợp đồng, thay vì truyền văn bản tự do.

```python
# LangGraph-style: graph có state, node = agent, edge = điều kiện chuyển
from typing import TypedDict

class AnalysisState(TypedDict):
    question: str
    plan: list[str]
    sql: str | None
    result: list[dict] | None
    issues: list[str]

# planner → sql_agent → validator → (issues? quay lại sql_agent : writer)
```

**Liên hệ data engineering:** orchestration agent giống orchestration pipeline (Airflow, Dagster): định nghĩa phụ thuộc, truyền artifact, retry, timeout, quan sát. Khác biệt là đồ thị có thể **động** — đường đi do LLM quyết định lúc chạy.

**Pitfall:** vòng lặp giữa các agent không có điều kiện dừng; supervisor trở thành nút cổ chai và tốn token; không có trace xuyên suốt (cần trace ID cho toàn bộ cuộc chạy).

---

## Agentic Frameworks

**Agentic frameworks** là các thư viện cung cấp sẵn "khung xương" để xây agent: trừu tượng hoá việc gọi LLM, **tool binding**, **memory**, vòng lặp agent, **multi-agent orchestration**, tracing và tích hợp với vector store/nguồn dữ liệu.

**Các framework tiêu biểu (theo định hướng):**

```text
LangChain / LangGraph    : hệ sinh thái tích hợp rộng; LangGraph cho agent dạng graph có state
LlamaIndex               : mạnh về data ingestion, indexing, RAG; có agent và workflow
AutoGen (Microsoft)      : multi-agent dạng hội thoại giữa các agent
CrewAI                   : multi-agent theo "role" và "task", cấu hình ngắn gọn
DSPy                     : lập trình pipeline và tối ưu prompt tự động
Semantic Kernel          : SDK của Microsoft cho .NET/Python/Java
SDK của nhà cung cấp     : agent SDK của các hãng model, thường gắn với MCP
```

**Framework cung cấp gì:** abstraction cho nhiều LLM provider, định nghĩa tool từ hàm Python (tự sinh JSON Schema), quản lý message history, retry/parse output, checkpoint state, human-in-the-loop, tích hợp tracing/eval.

**Có nên dùng framework?**

- **Nên** khi cần nhiều tích hợp có sẵn, multi-agent có state phức tạp, muốn đi nhanh.
- **Cân nhắc tự viết** khi luồng đơn giản: vòng lặp agent cốt lõi chỉ vài chục dòng code (xem Bài 6). Dylxn Assistant tự viết pipeline RAG (`rag.py`, `retriever.py`, `llm/ollama.py`) — dễ hiểu từng dòng, ít phụ thuộc.

**Pitfall:** abstraction nhiều tầng làm khó debug ("prompt thực sự gửi đi là gì?"); API thay đổi nhanh giữa các phiên bản; khoá chặt vào framework khiến khó thay thế. Luôn bật tracing để thấy prompt thật, và giữ logic nghiệp vụ (định nghĩa metric, quyền truy cập) ngoài framework.

---

## LangChain

**LangChain** là framework mã nguồn mở (Python và JavaScript/TypeScript) để xây ứng dụng LLM bằng cách ghép các thành phần chuẩn hoá: model, prompt template, output parser, retriever, tool, memory, agent.

**Các phần chính của hệ sinh thái:**

- **langchain-core**: các interface cơ bản (Runnable, ChatModel, Retriever, Tool…) và **LCEL** — cú pháp nối các bước bằng toán tử `|`.
- **Integrations** (các package như `langchain-ollama`, `langchain-qdrant`): hàng trăm kết nối tới LLM, embedding, vector store, document loader.
- **LangGraph**: thư viện xây agent/workflow dưới dạng **đồ thị có state**, hỗ trợ vòng lặp, checkpoint, human-in-the-loop — là hướng khuyến nghị cho agent mới trong hệ LangChain.
- **LangSmith**: nền tảng (thương mại) cho tracing, evaluation, monitoring.

**Ví dụ RAG với Ollama + Qdrant (minh hoạ, tên lớp có thể khác theo phiên bản):**

```python
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

prompt = ChatPromptTemplate.from_messages([
    ("system", "Chỉ trả lời từ CONTEXT, trích dẫn [n].\nCONTEXT:\n{context}"),
    ("human", "{question}"),
])
llm = ChatOllama(model="qwen3:4b", temperature=0.1)
chain = prompt | llm | StrOutputParser()

answer = chain.invoke({"context": build_context(retriever.retrieve(q)), "question": q})
```

**Với dữ liệu lakehouse:** LangChain có `SQLDatabase` utility và SQL agent/toolkit để LLM xem schema và chạy truy vấn qua SQLAlchemy — tiện cho prototype Text-to-SQL; ở production nên thay bằng tool hẹp đi qua semantic layer và tài khoản read-only.

**Pitfall:** dùng các class "legacy chain/agent" cũ trong tutorial lỗi thời; nhiều tầng wrapper che mất prompt thật; nâng cấp phiên bản gây breaking change. Embedding E5 qua wrapper chung có thể **không tự thêm** prefix `query:`/`passage:` — kiểm tra kỹ.

---

## LlamaIndex

**LlamaIndex** là **data framework** mã nguồn mở (Python, TypeScript) chuyên kết nối dữ liệu riêng của bạn với LLM: ingest, parse, chunk, index, truy vấn — tức là tập trung vào chữ **R** trong RAG — và mở rộng sang agent và workflow.

**Khái niệm chính:**

- **Document / Node**: tài liệu gốc và các chunk (node) có metadata, quan hệ parent-child.
- **Readers / connectors** (nhiều connector qua LlamaHub): file, Notion, database, API…; **LlamaParse** (dịch vụ) cho PDF phức tạp.
- **Node parsers / text splitters**: chunking theo câu, theo Markdown heading, semantic splitter, hierarchical (parent-child).
- **Index**: `VectorStoreIndex` (phổ biến nhất), summary index, property graph index (cho GraphRAG)…
- **Retriever → Query engine / Chat engine**: retriever lấy node, node postprocessor (re-rank, lọc), synthesizer tạo câu trả lời.
- **Agents & Workflows**: agent gọi tool (có thể là query engine), workflow hướng sự kiện cho luồng nhiều bước.

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.llms.ollama import Ollama

Settings.llm = Ollama(model="qwen3:4b", request_timeout=600)
docs = SimpleDirectoryReader("knowledge", recursive=True, required_exts=[".md"]).load_data()
nodes = MarkdownNodeParser().get_nodes_from_documents(docs)   # chunk theo heading
index = VectorStoreIndex(nodes)   # cấu hình embed model / Qdrant vector store riêng
print(index.as_query_engine(similarity_top_k=5).query("Hybrid search là gì?"))
```

**LangChain vs LlamaIndex (khái quát):** LlamaIndex mạnh và "có chính kiến" về pipeline dữ liệu cho RAG; LangChain/LangGraph rộng hơn về tích hợp và điều phối agent. Hai thứ có thể dùng cùng nhau.

**Pitfall:** embedding model mặc định có thể là API trả phí — phải cấu hình rõ embed model local nếu muốn chạy offline; abstraction cao khiến khó kiểm soát chunk thực tế (hãy in node ra kiểm tra); API thay đổi theo phiên bản.

---

## Autonomous Workflows

**Autonomous workflow** là quy trình **tự vận hành** hướng tới mục tiêu định sẵn: được kích hoạt theo lịch hoặc sự kiện, chạy qua nhiều bước (có thể có bước dùng LLM/agent), tự xử lý lỗi thông thường bằng retry/fallback, và chỉ cần con người khi gặp ngoại lệ. Về mặt vận hành, chúng được quản lý giống pipeline dữ liệu: **DAG**, orchestrator, retry, timeout, alert, SLA.

**Workflow vs agent:**

```text
Workflow : đường đi do LẬP TRÌNH VIÊN định sẵn (DAG); dự đoán được, dễ test
Agent    : đường đi do LLM quyết định lúc chạy; linh hoạt, khó dự đoán
Thực tế  : workflow làm khung xương, agent được nhúng vào một vài node cần linh hoạt
```

**Ví dụ — xử lý dbt test fail tự động (Airflow/Dagster/Prefect):**

```text
[schedule 06:00] dbt build
   └─ on failure ─► collect_logs
                    └─► llm_triage (agent: đọc log, query dữ liệu lỗi, phân loại)
                         ├─ "source chưa về"  → chờ 30 phút, retry (tối đa 3 lần)
                         ├─ "dữ liệu bẩn"     → quarantine dòng lỗi, tạo ticket kèm tóm tắt
                         └─ "lỗi logic model" → mở draft PR đề xuất fix, cần người review
                    └─► alert Slack nếu vẫn fail sau retry
```

**Các yêu cầu thiết kế:**

- **Idempotency**: chạy lại một bước không gây trùng lặp/ghi đè sai.
- **Checkpoint / state**: workflow dài có thể tiếp tục từ bước lỗi thay vì chạy lại từ đầu.
- **Guardrails** cho bước LLM: output phải qua validate (schema, test) trước khi tác động hệ thống.
- **Observability**: log, metric (tỉ lệ tự xử lý thành công, số lần escalate), chi phí LLM mỗi lần chạy.
- **Human-in-the-loop** ở các điểm quyết định không đảo ngược được.

**Pitfall:** để agent tự "sửa" dữ liệu production mà không review; retry vô hạn khi lỗi không phải tạm thời; không có kill switch để tắt nhánh tự động khi nó hành xử sai.
