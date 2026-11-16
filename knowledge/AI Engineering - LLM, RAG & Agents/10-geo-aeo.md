---
title: GEO và AEO - Generative Engine Optimization, Answer Engine Optimization
type: concept
domain: ai-engineering
tags:
  - ai-engineering
  - geo
  - aeo
  - seo
  - generative-engine-optimization
  - answer-engine-optimization
  - content-strategy
---
# AI Engineering — LLM, RAG & Agents

## Bài 10 — GEO và AEO: tối ưu nội dung cho AI assistant và answer engine

Người dùng ngày càng hỏi trực tiếp AI assistant và nhận một câu trả lời tổng hợp thay vì danh sách link. Bài này giải thích GEO và AEO — và điều thú vị: các nguyên tắc này cũng chính là nguyên tắc viết **knowledge note tốt cho RAG nội bộ** như Dylxn Assistant.

---

## Generative Engine Optimization (GEO)

**Generative Engine Optimization (GEO)** là việc tổ chức và viết nội dung để các **generative engine** — AI assistant và công cụ tìm kiếm có LLM tổng hợp câu trả lời — có thể **tìm thấy, hiểu đúng, trích dẫn và tóm tắt chính xác** nội dung đó trong câu trả lời. Thuật ngữ được phổ biến qua bài nghiên cứu "GEO: Generative Engine Optimization" (Aggarwal và cộng sự, 2023).

**Cơ chế bên dưới:** nhiều generative engine hoạt động như một hệ **RAG trên web**: tìm kiếm → lấy các trang/đoạn liên quan → LLM tổng hợp → gắn citation. Vì vậy GEO thực chất là tối ưu cho **retrieval + chunking + generation** của người khác.

**Kỹ thuật thường được khuyến nghị:**

- **Câu trả lời tự đứng được**: mỗi section mở đầu bằng định nghĩa rõ ràng, có thể trích riêng mà vẫn đúng nghĩa (tốt cho chunking).
- **Cấu trúc rõ**: heading mô tả đúng nội dung, danh sách, bước, ví dụ.
- **Bằng chứng cụ thể**: số liệu có nguồn, trích dẫn, ví dụ — nghiên cứu GEO ghi nhận việc bổ sung thống kê, trích dẫn và nguồn đáng tin có xu hướng tăng khả năng được hiển thị trong câu trả lời.
- **Nhất quán thuật ngữ** và nêu cả từ đồng nghĩa/viết tắt ("Retrieval-Augmented Generation (RAG)").
- **Khả năng truy cập kỹ thuật**: nội dung render được không cần JavaScript nặng, không chặn crawler mong muốn, cập nhật ngày sửa đổi. Một số site thử nghiệm file `llms.txt` (một đề xuất cộng đồng, chưa phải chuẩn chính thức) để hướng dẫn LLM đọc nội dung.

**Ví dụ — áp dụng cho chính knowledge base này:** mỗi thuật ngữ có heading riêng chứa đúng tên + viết tắt, mở đầu bằng định nghĩa in đậm → retriever của Dylxn match chính xác và LLM trích dẫn đúng section.

**Pitfall:** nhồi từ khoá (keyword stuffing) — không giúp và có thể phản tác dụng; tối ưu cho một engine cụ thể trong khi hành vi engine thay đổi liên tục; khó đo lường (không có "thứ hạng" ổn định như SEO) — nên theo dõi tần suất được trích dẫn trên tập câu hỏi mẫu theo thời gian.

---

## Answer Engine Optimization (AEO) vs SEO và GEO

**Answer Engine Optimization (AEO)** là việc cấu trúc nội dung để **answer engine** — featured snippet, hộp trả lời của search engine, voice assistant, AI assistant — có thể lấy nội dung của bạn làm **câu trả lời trực tiếp** cho một câu hỏi.

**So sánh SEO, AEO, GEO:**

```text
SEO  : mục tiêu = xếp hạng cao trong danh sách link → người dùng click vào site
       đo bằng ranking, traffic, CTR
AEO  : mục tiêu = được chọn làm CÂU TRẢ LỜI trực tiếp (snippet, voice, AI answer)
       nội dung dạng hỏi–đáp ngắn, định nghĩa 40–60 từ, FAQ, structured data
GEO  : mục tiêu = được LLM tổng hợp và TRÍCH DẪN trong câu trả lời sinh ra
       nội dung đáng tin, nhiều bằng chứng, dễ chunk, nhất quán thực thể
```

Ba khái niệm chồng lấn nhiều; nền tảng chung vẫn là nội dung chất lượng, dễ crawl và có cấu trúc. AEO nhấn mạnh **định dạng câu hỏi–câu trả lời** và **structured data** (schema.org như `FAQPage`, `HowTo`, `Article`, `Dataset`).

**Data team dùng AEO/GEO thế nào:**

- **Data catalog & business glossary nội bộ**: viết định nghĩa metric theo dạng "Câu hỏi → câu trả lời ngắn → chi tiết" để chatbot nội bộ (RAG/agentic analytics) trả lời đúng "Active user được tính thế nào?".
- **Tài liệu dataset/API công khai**: thêm mô tả rõ ràng và structured data (vd schema.org `Dataset`) để công cụ tìm kiếm và AI assistant hiểu dataset.
- **Đo lường**: dùng dữ liệu analytics (traffic từ AI assistant, truy vấn tìm kiếm) và bộ câu hỏi mẫu để theo dõi nội dung có được trích dẫn hay không — một bài toán data pipeline quen thuộc.

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [{
    "@type": "Question",
    "name": "Hybrid search là gì?",
    "acceptedAnswer": {
      "@type": "Answer",
      "text": "Hybrid search kết hợp vector search và keyword search (BM25) rồi trộn thứ hạng, để vừa hiểu nghĩa vừa khớp chính xác thuật ngữ."
    }
  }]
}
```

**Pitfall:** viết câu trả lời quá ngắn, mất sắc thái quan trọng (điều kiện, ngoại lệ); structured data không khớp nội dung hiển thị; coi AEO/GEO thay thế SEO — thực tế answer engine vẫn dựa nhiều vào chỉ mục tìm kiếm truyền thống.
