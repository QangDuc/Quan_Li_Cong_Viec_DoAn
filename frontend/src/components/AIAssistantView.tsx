import React, { useState, useRef, useEffect } from "react";
import {
  Bot,
  Send,
  Sparkles,
  RefreshCw,
  Trash2,
  CheckCircle2,
} from "lucide-react";
import { API_BASE } from "../types";

interface Props {
  token: string;
  currentUser: any;
  tasks: any[];
}

/** Hiển thị văn bản có in đậm **...** sạch đẹp, không lộ dấu sao thô */
function renderFormattedText(text: string) {
  return text.split("\n").map((line, lineIdx) => {
    const trimmed = line.trim();
    const isQuote = trimmed.startsWith(">");
    const cleanLine = isQuote ? trimmed.replace(/^>\s*/, "") : line;

    const parts = cleanLine.split(/(\*\*.*?\*\*)/g);
    const renderedParts = parts.map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
        return (
          <strong key={i} className="font-bold text-slate-900">
            {part.slice(2, -2)}
          </strong>
        );
      }
      return <React.Fragment key={i}>{part}</React.Fragment>;
    });

    if (isQuote) {
      return (
        <div
          key={lineIdx}
          className="pl-3 border-l-3 border-indigo-400 bg-indigo-50/50 py-1 my-1 rounded-r-lg text-slate-700"
        >
          {renderedParts}
        </div>
      );
    }

    return (
      <div key={lineIdx} className={trimmed === "" ? "h-2" : "leading-relaxed"}>
        {renderedParts}
      </div>
    );
  });
}

export const AIAssistantView: React.FC<Props> = ({ token, currentUser, tasks }) => {
  const initialGreeting = {
    role: "assistant" as const,
    engine: "Gemini AI — Trợ lý Điều phối Khoa CNTT (HUIT)",
    text:
      `Xin chào **${currentUser?.full_name || "Thầy/Cô"}**! Tôi là Trợ lý AI được tích hợp sẵn của Khoa Công nghệ Thông tin — Trường ĐH Công Thương TP.HCM (HUIT).\n\n` +
      `Tôi kết nối trực tiếp với dữ liệu công việc thực tế của Khoa để hỗ trợ Thầy/Cô:\n` +
      `• Phân tích tiến độ, rà soát các công việc nhóm và kiểm tra trạng thái nộp minh chứng.\n` +
      `• Đề xuất **Người phụ trách chính (Trưởng nhóm)** và các giảng viên có **độ trễ dự báo thấp nhất** theo từng nhóm chuyên môn.\n` +
      `• Thống kê định mức giờ chuẩn quy đổi và soạn thảo nhanh thông báo nhắc việc.\n\n` +
      `Thầy/Cô có thể nhấn vào các gợi ý bên dưới hoặc nhập câu hỏi bất kỳ để bắt đầu ngay!`,
  };

  const [messages, setMessages] = useState<
    { role: "user" | "assistant"; text: string; engine?: string }[]
  >([initialGreeting]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [selectedTaskId, setSelectedTaskId] = useState<number | "">("");
  const chatEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  const handleSend = async (customPrompt?: string) => {
    const promptText = (customPrompt ?? input).trim();
    if (!promptText || sending) return;

    const historyPayload = messages.slice(-6).map((m) => ({
      role: m.role,
      content: m.text,
    }));

    setMessages((prev) => [...prev, { role: "user", text: promptText }]);
    if (!customPrompt) setInput("");
    setSending(true);

    try {
      const res = await fetch(`${API_BASE}/ai/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          message: promptText,
          task_id: selectedTaskId === "" ? null : Number(selectedTaskId),
          history: historyPayload,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            text: data.reply || "Không có phản hồi.",
            engine: data.engine || "Gemini AI — Trợ lý Điều phối Khoa CNTT",
          },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            text: `⚠️ Không thể xử lý yêu cầu: ${data.detail || "Vui lòng thử lại."}`,
            engine: "Hệ thống",
          },
        ]);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: "⚠️ Không thể kết nối tới máy chủ Trợ lý AI. Vui lòng kiểm tra lại kết nối Backend.",
          engine: "Hệ thống",
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  const quickPrompts = [
    "Tổng hợp nhanh tiến độ công việc và các nhóm việc đang mở",
    "Liệt kê các công việc đang quá hạn hoặc có nguy cơ trễ hạn cao",
    "Gợi ý chọn Người phụ trách chính (Trưởng nhóm) và giảng viên độ trễ thấp nhất",
    "Thống kê định mức giờ chuẩn quy đổi của các giảng viên trong Khoa",
    "Soạn nội dung nhắc nhở thành viên nhóm bổ sung thiếu sót minh chứng",
  ];

  return (
    <div className="max-w-5xl mx-auto">
      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm flex flex-col h-[740px] overflow-hidden">
        {/* HEADER TRỢ LÝ AI TÍCH HỢP SẴN */}
        <div className="px-6 py-4 bg-gradient-to-r from-blue-900 via-indigo-900 to-slate-900 text-white flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3.5">
            <img
              src="/huit-logo.png"
              alt="HUIT Logo"
              className="w-11 h-11 rounded-full object-cover shadow-md shrink-0"
            />
            <div>
              <h3 className="font-extrabold text-sm sm:text-base flex items-center gap-2">
                Trợ lý AI Điều phối & Phân tích Công việc Khoa CNTT
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-[11px] rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-400/30 font-semibold">
                  <CheckCircle2 className="w-3 h-3" /> Đã tích hợp sẵn
                </span>
              </h3>
              <p className="text-xs text-blue-200 mt-0.5">
                Phân tích trực tiếp dữ liệu tiến độ, minh chứng nhóm, độ trễ giảng viên & định mức giờ chuẩn
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <select
              value={selectedTaskId}
              onChange={(e) =>
                setSelectedTaskId(e.target.value === "" ? "" : Number(e.target.value))
              }
              aria-label="Chọn ngữ cảnh công việc để phân tích"
              className="px-3 py-1.5 rounded-xl bg-white/10 hover:bg-white/15 border border-white/20 text-xs text-white font-medium max-w-[240px] truncate outline-none cursor-pointer"
              title="Chọn công việc cụ thể để AI phân tích sâu"
            >
              <option value="" className="text-slate-900">
                Ngữ cảnh: Toàn bộ Khoa CNTT
              </option>
              {tasks.slice(0, 25).map((t) => (
                <option key={t.id} value={t.id} className="text-slate-900">
                  [{t.code}] {t.title}
                </option>
              ))}
            </select>

            <button
              type="button"
              onClick={() => setMessages([initialGreeting])}
              className="p-2 rounded-xl bg-white/10 hover:bg-white/20 text-blue-100 border border-white/15 cursor-pointer transition"
              title="Làm mới cuộc trò chuyện"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* THANH CÂU HỎI GỢI Ý NHANH */}
        <div className="px-5 py-3 bg-slate-50 border-b border-slate-200 flex flex-wrap gap-2">
          {quickPrompts.map((qp, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleSend(qp)}
              disabled={sending}
              className="px-3 py-1.5 rounded-xl bg-white hover:bg-indigo-50 text-slate-700 hover:text-indigo-700 border border-slate-200/90 hover:border-indigo-300 text-xs font-semibold transition cursor-pointer flex items-center gap-1.5 shadow-2xs disabled:opacity-50"
            >
              <Sparkles className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
              {qp}
            </button>
          ))}
        </div>

        {/* KHUNG HỘI THOẠI */}
        <div className="flex-1 p-6 overflow-y-auto space-y-4 bg-slate-50/40">
          {messages.map((m, i) => (
            <div
              key={i}
              className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[82%] rounded-2xl px-4 py-3.5 text-xs sm:text-sm shadow-2xs ${
                  m.role === "user"
                    ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-br-xs font-medium"
                    : "bg-white border border-slate-200/90 text-slate-800 rounded-bl-xs"
                }`}
              >
                {m.engine && m.role === "assistant" && (
                  <div className="text-[11px] font-bold text-indigo-600 mb-1.5 flex items-center gap-1.5 pb-1.5 border-b border-slate-100">
                    <Bot className="w-3.5 h-3.5" /> {m.engine}
                  </div>
                )}
                {m.role === "user" ? (
                  <div className="whitespace-pre-line">{m.text}</div>
                ) : (
                  <div className="space-y-0.5">{renderFormattedText(m.text)}</div>
                )}
              </div>
            </div>
          ))}

          {sending && (
            <div className="flex justify-start">
              <div className="bg-white border border-slate-200 rounded-2xl px-4 py-3 text-xs text-slate-600 flex items-center gap-2.5 shadow-2xs">
                <RefreshCw className="w-4 h-4 animate-spin text-indigo-600" />
                <span>Trợ lý AI đang phân tích dữ liệu và tổng hợp câu trả lời...</span>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Ô NHẬP TIN NHẮN */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="p-4 bg-white border-t border-slate-200 flex items-center gap-3"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Nhập yêu cầu hoặc câu hỏi bất kỳ cho Trợ lý AI (VD: Phân tích công việc nhóm CV-2610-NHOM01, ai phù hợp làm Trưởng nhóm?)..."
            className="flex-1 px-4 py-3 bg-slate-50 focus:bg-white border border-slate-300 rounded-2xl text-xs sm:text-sm outline-none focus:ring-2 focus:ring-indigo-500 transition"
          />
          <button
            type="submit"
            disabled={sending || !input.trim()}
            className="px-5 py-3 rounded-2xl bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-700 hover:to-blue-700 disabled:opacity-50 text-white text-xs sm:text-sm font-bold flex items-center gap-2 cursor-pointer transition shadow-sm"
          >
            <Send className="w-4 h-4" />
            <span>Gửi AI</span>
          </button>
        </form>
      </div>
    </div>
  );
};

export default AIAssistantView;
