---
title: AI Agents và Tool Calling - Agentic AI, Autonomous Agents, Function Calling, ReAct, Reasoning Engine
type: concept
domain: ai-engineering
tags:
  - ai-engineering
  - ai-agents
  - agentic-ai
  - autonomous-agents
  - tool-calling
  - function-calling
  - react
  - reasoning-engine
  - mcp
---
# AI Engineering — LLM, RAG & Agents

## Bài 6 — AI Agents và Tool Calling: từ "trả lời" sang "hành động"

RAG cho LLM khả năng **đọc** tài liệu. Agent cho LLM khả năng **hành động**: gọi tool, chạy SQL, đọc kết quả, quyết định bước tiếp theo. Bài này đi từ khái niệm Agentic AI, AI agent, autonomous agent tới cơ chế kỹ thuật bên dưới: tool calling, ReAct và reasoning engine.

---

## Agentic AI

**Agentic AI** là cách gọi chung cho các hệ thống dùng LLM không chỉ để sinh văn bản một lượt, mà để **lập kế hoạch, suy luận và hành động** qua nhiều bước nhằm đạt một mục tiêu — có tool, có memory, có vòng phản hồi.

**Phổ "mức độ agentic":**

```text
1. LLM call đơn         : prompt → text
2. RAG                  : retrieve → prompt → text (luồng cố định)
3. Workflow có LLM      : các bước do lập trình viên định sẵn, LLM làm từng bước
4. Agent                : LLM tự chọn tool và số bước trong một vòng lặp
5. Multi-agent          : nhiều agent phối hợp
```

**Thành phần điển hình:**

- **Reasoning engine** (LLM): lập kế hoạch, chọn hành động.
- **Tools**: API, SQL, search, code execution — qua **function calling** hoặc giao thức chuẩn như **MCP (Model Context Protocol)**. Repo này có `mcp/server.py` để expose knowledge base như một tool cho agent khác.
- **Memory**: ngắn hạn (context hội thoại), dài hạn (vector store, file ghi chú).
- **Guardrails & oversight**: phân quyền, giới hạn bước, human-in-the-loop.

**Vấn đề khi triển khai:**

- **Độ tin cậy cộng dồn**: mỗi bước có xác suất lỗi; 10 bước liên tiếp thì lỗi tích luỹ đáng kể.
- **Chi phí & latency** không đoán trước được (số vòng lặp thay đổi theo câu hỏi).
- **An toàn**: agent có quyền ghi/xoá; prompt injection qua dữ liệu tool trả về.
- **Observability**: cần trace từng bước (prompt, tool call, kết quả) để debug.

**Lời khuyên thực tế:** bắt đầu bằng mức thấp nhất giải quyết được vấn đề. Nhiều bài toán "agent" thực ra chỉ cần workflow cố định + LLM ở một vài bước — dễ test và rẻ hơn.

---

## AI Agents

**AI agent** là chương trình dùng LLM làm "bộ não" để theo đuổi một mục tiêu bằng cách **lặp**: quan sát trạng thái → suy luận → gọi tool → đọc kết quả → quyết định tiếp tục hay dừng.

**Vòng lặp agent tối giản:**

```python
messages = [system_prompt, user_question]
for step in range(MAX_STEPS):                    # luôn có giới hạn bước
    reply = llm.chat(messages, tools=TOOL_SCHEMAS)
    if not reply.tool_calls:
        return reply.content                     # agent quyết định đã đủ để trả lời
    for call in reply.tool_calls:
        result = TOOL_REGISTRY[call.name](**call.arguments)   # app thực thi, không phải LLM
        messages.append(tool_result(call.id, truncate(result)))
raise RuntimeError("Vượt số bước tối đa")
```

**Thành phần:**

- **Tool registry**: danh sách tool với tên, mô tả, JSON schema tham số và hàm thực thi tương ứng. Mô tả tool tốt quan trọng ngang prompt.
- **Planning**: ReAct (suy luận xen kẽ hành động), plan-and-execute (lập kế hoạch trước rồi làm), reflection (tự đánh giá kết quả).
- **Memory & state**: lịch sử message, scratchpad, kết quả trung gian.
- **Human oversight**: xác nhận trước hành động rủi ro (ghi DB, gửi email, deploy).

**Ví dụ data engineering — agent điều tra "vì sao doanh thu hôm qua giảm 30%":**

```text
1. search_docs("định nghĩa metric revenue")     → biết metric dùng fct_orders, loại đơn huỷ
2. run_sql("SELECT order_date, SUM(amount) ...") → xác nhận giảm
3. run_sql("... GROUP BY channel")               → giảm tập trung ở channel 'app'
4. check_pipeline_status("stg_app_orders")       → job ingest lỗi từ 02:00
5. Trả lời: dữ liệu app bị thiếu do pipeline lỗi, không phải doanh thu thật giảm.
```

**Pitfall:** cho agent tool quá mạnh (SQL có quyền ghi); không giới hạn số bước → vòng lặp vô hạn, cháy chi phí; tool trả về quá nhiều dữ liệu làm tràn context; mô tả tool mơ hồ khiến agent gọi sai tool.

---

## Autonomous Agents

**Autonomous agent** là agent hoạt động với **mức tự chủ cao**: nhận một mục tiêu cấp cao, tự **phân rã** thành các bước, tự thực hiện qua tool, tự **phát hiện lỗi và sửa** dựa trên phản hồi, và có thể chạy dài (phút, giờ) mà không cần con người can thiệp từng bước.

**Khác gì agent thông thường:** agent "hỏi-đáp" thường làm vài bước trong một request; autonomous agent có vòng đời dài hơn, tự quản lý task list, có memory bền, có thể tự kích hoạt (theo lịch hoặc sự kiện).

**Cơ chế tự sửa lỗi (self-correction):**

- Chạy SQL lỗi → đọc thông báo lỗi → sửa tên cột → chạy lại.
- Chạy test (dbt test, pytest) → thấy fail → sửa code → chạy lại cho đến khi pass.
- **Reflection**: sau mỗi giai đoạn, tự đánh giá "đã đạt mục tiêu chưa, còn thiếu gì".

**Ví dụ:** "Mỗi sáng, kiểm tra freshness các model dbt; nếu source trễ, tìm nguyên nhân trong log, tạo ticket kèm tóm tắt và đề xuất fix" — agent tự chạy, chỉ báo con người khi cần quyết định.

**Giới hạn an toàn bắt buộc:**

- **Least privilege**: credential chỉ đủ cho việc cần làm (read-only warehouse, chỉ ghi vào nhánh git riêng).
- **Sandbox** cho code execution.
- **Budget**: giới hạn số bước, thời gian, token, chi phí.
- **Approval gates**: hành động không đảo ngược được (drop table, gửi tin cho khách hàng, merge vào main) cần người duyệt.
- **Audit log** đầy đủ mọi hành động.

**Pitfall:** tự chủ càng cao thì lỗi nhỏ ở đầu càng lan xa; agent "tự tin" báo đã xong trong khi chưa kiểm chứng — luôn yêu cầu bằng chứng (kết quả test, output query) trong báo cáo; dữ liệu từ nguồn ngoài có thể chứa chỉ dẫn độc hại (prompt injection) điều khiển agent.

---

## Tool Calling

**Tool calling** là khả năng của LLM **yêu cầu** ứng dụng gọi một hàm/API bên ngoài và sử dụng kết quả để tiếp tục. Điểm cốt lõi: **LLM không tự thực thi gì cả** — nó chỉ sinh ra một cấu trúc (tên tool + tham số JSON); ứng dụng của bạn quyết định có chạy hay không, chạy và trả kết quả lại cho LLM.

**Luồng chuẩn:**

```text
1. App gửi: messages + danh sách tool (name, description, JSON Schema tham số)
2. LLM trả về: tool_call {name: "run_sql", arguments: {"query": "SELECT ..."}}
3. App: validate tham số → kiểm tra quyền → thực thi → nhận kết quả
4. App gửi lại kết quả dưới dạng message role "tool"
5. LLM: gọi thêm tool hoặc trả lời cuối cùng
```

**Hỗ trợ trong runtime:** các API LLM lớn và Ollama (endpoint `/api/chat` với tham số `tools`, cho model hỗ trợ tool như dòng Qwen3, Llama 3.1+) đều hỗ trợ. **MCP (Model Context Protocol)** chuẩn hoá cách một server expose tool/resource cho nhiều client agent khác nhau.

**Governance — vì tool calling là "cửa" để LLM tác động thế giới thật:**

- Validate arguments theo schema; không tin tưởng tham số LLM sinh ra.
- Allowlist tool theo user/role; với SQL: read-only role, timeout, `LIMIT`, chặn DDL/DML.
- Log mọi tool call (ai, khi nào, tham số, kết quả).
- Xác nhận của con người cho tool có side effect.

**Pitfall:**

- Tool trả lỗi dạng exception làm vỡ vòng lặp — nên trả lỗi về LLM dưới dạng text để nó tự sửa.
- Quá nhiều tool (hàng chục, trăm) làm model chọn sai và tốn token mô tả — gom nhóm hoặc chọn tool động.
- Model nhỏ chạy local có thể sinh JSON không hợp lệ hoặc gọi tool không tồn tại — cần parse chặt và retry.

---

## AI Agent Tool Use (Function Calling)

**Function calling** là tên gọi (phổ biến từ API của OpenAI, 2023) cho cơ chế tool use ở mức API: bạn mô tả các **function** bằng **JSON Schema**, model được fine-tune để khi cần sẽ xuất ra lời gọi function có cấu trúc thay vì văn bản tự do. "Tool use", "tool calling" và "function calling" thực chất chỉ cùng một cơ chế; phần này tập trung vào **cách định nghĩa function tốt** cho agent dữ liệu.

**Định nghĩa tool — ví dụ cho Ollama `/api/chat`:**

```json
{
  "type": "function",
  "function": {
    "name": "search_knowledge",
    "description": "Tìm trong knowledge base Data Engineering/AI của Dylxn. Dùng khi cần định nghĩa, best practice, ví dụ. Không dùng cho số liệu kinh doanh.",
    "parameters": {
      "type": "object",
      "properties": {
        "query": {"type": "string", "description": "Câu hỏi bằng ngôn ngữ tự nhiên"},
        "domain": {"type": "string", "enum": ["data-engineering", "ai-engineering"]}
      },
      "required": ["query"]
    }
  }
}
```

**Nguyên tắc thiết kế function:**

- **Tên và description rõ ràng**, nói cả *khi nào dùng* và *khi nào không dùng*.
- Tham số có kiểu chặt chẽ, dùng `enum` khi được — giảm lỗi của model.
- **Ít tool, mỗi tool mạnh vừa đủ**: `get_metric(metric, grain, filters)` an toàn hơn `run_any_sql(query)`.
- Kết quả trả về **gọn và có cấu trúc**: tóm tắt + vài dòng mẫu, kèm thông báo lỗi dễ hiểu ("cột `revenue` không tồn tại; các cột có: amount, order_date…").
- **Idempotent** cho tool đọc; tool ghi cần xác nhận.

**Parallel function calling:** nhiều model có thể yêu cầu nhiều function trong một lượt (vd lấy 3 metric song song) — app có thể thực thi đồng thời.

**Pitfall:** để function nhận SQL tự do với quyền admin; description quá ngắn khiến model không biết dùng; trả về toàn bộ bảng 100.000 dòng; không xử lý trường hợp model trả lời bằng text thay vì gọi function.

---

## ReAct Framework (Reason + Act)

**ReAct** (Reasoning + Acting, Yao et al., 2022) là pattern prompting trong đó agent **xen kẽ** các bước suy luận bằng ngôn ngữ (**Thought**) với hành động gọi tool (**Action**) và đọc kết quả (**Observation**), lặp cho tới khi đủ thông tin để trả lời. Nó kết hợp ưu điểm của Chain of Thought (suy luận) với khả năng lấy thông tin thật từ môi trường (giảm hallucination).

**Định dạng kinh điển:**

```text
Question: Top 3 khách hàng theo doanh thu quý 3 thuộc segment nào?
Thought: Cần biết metric doanh thu được định nghĩa thế nào trong semantic layer.
Action: get_metric_definition[revenue]
Observation: revenue = SUM(fct_orders.amount) WHERE status != 'cancelled'
Thought: Giờ tính doanh thu theo customer trong Q3 và lấy top 3, join dim_customers.
Action: run_sql[SELECT c.customer_id, c.segment, SUM(o.amount) AS rev
               FROM fct_orders o JOIN dim_customers c USING (customer_id)
               WHERE o.status <> 'cancelled' AND o.order_date BETWEEN '2025-07-01' AND '2025-09-30'
               GROUP BY 1,2 ORDER BY rev DESC LIMIT 3]
Observation: (C17, Enterprise, 920M), (C03, Enterprise, 610M), (C88, SMB, 450M)
Thought: Đã đủ dữ liệu.
Final Answer: 2 khách Enterprise (C17, C03) và 1 khách SMB (C88).
```

**Ngày nay:** thay vì parse text "Action: …" bằng regex, hầu hết hệ thống dùng **native tool calling** của model; phần "Thought" là nội dung text hoặc reasoning nội bộ của model. Tư tưởng vòng lặp ReAct vẫn giữ nguyên — đây là nền của phần lớn agent framework (LangGraph `create_react_agent`, `dspy.ReAct`…).

**Khi nào dùng:** câu hỏi cần nhiều bước mà bước sau phụ thuộc kết quả bước trước (phân tích dữ liệu, điều tra sự cố).

**Pitfall:** vòng lặp lặp lại cùng một action (cần phát hiện và dừng); observation quá dài; với task có luồng cố định, workflow tường minh rẻ và đáng tin hơn ReAct.

---

## Reasoning Engine

**Reasoning engine** là thành phần trong hệ agent chịu trách nhiệm **ra quyết định**: hiểu mục tiêu, lập kế hoạch các bước, chọn tool và tham số, đánh giá kết quả trả về và quyết định bước tiếp theo hoặc dừng. Trong hầu hết hệ thống hiện nay, reasoning engine chính là **LLM** cộng với prompt/logic điều khiển bao quanh nó.

**Phân biệt vai trò:**

```text
Reasoning engine   → "nghĩ gì, làm gì tiếp"     (LLM + planning prompt)
Tools              → "làm"                       (SQL engine, API, search)
Memory             → "nhớ"                       (context, vector store)
Orchestrator       → "chạy vòng lặp, áp luật"    (code của bạn / framework)
```

**Các kiểu lập luận reasoning engine thường áp dụng:**

- **Decomposition**: chia câu hỏi "so sánh retention cohort tháng 1 và tháng 6 theo channel" thành các truy vấn con.
- **Plan-and-execute**: viết kế hoạch đầy đủ trước, rồi thực thi; tái lập kế hoạch khi kết quả bất ngờ.
- **Verification**: kiểm tra kết quả có hợp lý không (tổng theo channel có bằng tổng toàn bộ không? có giá trị NULL bất thường không?).
- **Reflection**: tự phê bình câu trả lời trước khi gửi.

**Chọn model cho reasoning engine:** suy luận nhiều bước, chọn tool chính xác đòi hỏi model đủ mạnh; model local nhỏ (vd 4B tham số) phù hợp cho tác vụ hẹp, có cấu trúc rõ. Có thể kết hợp **LLM routing**: model mạnh để lập kế hoạch, model nhỏ cho bước đơn giản.

**Ngoài LLM:** trước thời LLM, "reasoning engine" còn chỉ rule engine hoặc **reasoner** trên ontology (suy diễn logic từ OWL/RDF) — vẫn hữu ích khi cần suy luận xác định, giải thích được (xem Bài 8).

**Pitfall:** tin rằng reasoning engine "hiểu" dữ liệu — nó chỉ thấy những gì có trong context; thiếu semantic layer/định nghĩa metric thì kế hoạch dù logic vẫn cho kết quả sai. Đặt toàn bộ luật nghiệp vụ trong prompt thay vì trong code/guardrail có thể kiểm thử.
