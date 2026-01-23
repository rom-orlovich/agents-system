import { clsx } from "clsx";
import { Bot, Clock, MessageSquare, Plus, Trash2, User, X, Check } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useChat } from "./hooks/useChat";
import { useCLIStatus } from "../../hooks/useCLIStatus";

export function ChatFeature() {
  const { conversations, messages, selectedConversation, setSelectedConversation, sendMessage, createConversation, deleteConversation } =
    useChat();
  const { active: cliActive } = useCLIStatus();
  const [input, setInput] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const titleInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    if (isCreating && titleInputRef.current) {
      titleInputRef.current.focus();
    }
  }, [isCreating]);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || cliActive === false) return;
    sendMessage(input);
    setInput("");
  };

  const handleCreate = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!newTitle.trim()) return;
    createConversation(newTitle);
    setNewTitle("");
    setIsCreating(false);
  };
  
  const isDisabled = cliActive === false;

  return (
    <div className="flex h-full border border-gray-200 bg-[#fbfcfd] animate-in fade-in duration-500 overflow-hidden rounded-xl shadow-xl shadow-gray-200/20">
      {/* Sidebar */}
      <aside className="w-64 border-r border-gray-200 flex flex-col bg-gray-50/50 min-h-0">
        <div className="p-4 border-b border-gray-200 bg-white flex justify-between items-center">
          <span className="font-heading text-[10px] font-bold text-gray-400 tracking-widest">COMMS_CHANNELS</span>
          <button 
            type="button"
            onClick={() => setIsCreating(true)}
            className="p-1 hover:bg-gray-100 text-gray-400 hover:text-primary rounded transition-colors"
          >
            <Plus size={14} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {isCreating && (
            <div className="p-2 m-2 bg-white border border-primary/20 rounded shadow-sm">
              <form onSubmit={handleCreate}>
                 <input
                  ref={titleInputRef}
                  type="text"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="CHANNEL_NAME..."
                  className="w-full text-[11px] font-heading font-bold mb-2 outline-none placeholder:text-gray-300"
                  onKeyDown={(e) => {
                    if (e.key === "Escape") {
                      setIsCreating(false);
                      setNewTitle("");
                    }
                  }}
                />
                <div className="flex justify-end gap-1">
                  <button
                    type="button"
                    onClick={() => {
                      setIsCreating(false);
                      setNewTitle("");
                    }}
                    className="p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded transition-colors"
                  >
                    <X size={12} />
                  </button>
                  <button
                    type="submit"
                    className="p-1 text-primary hover:bg-primary/10 rounded transition-colors"
                  >
                    <Check size={12} />
                  </button>
                </div>
              </form>
            </div>
          )}
          
          {conversations?.map((conv) => (
            <button
              type="button"
              key={conv.id}
              onClick={() => setSelectedConversation(conv)}
              className={clsx(
                "w-full text-left p-4 transition-all border-b border-gray-100 hover:bg-white group relative",
                selectedConversation?.id === conv.id ? "bg-white" : "",
              )}
            >
              {selectedConversation?.id === conv.id && (
                <div className="absolute left-0 top-0 bottom-0 w-1 bg-primary animate-in slide-in-from-left duration-300" />
              )}
              
              <div className="flex justify-between items-start mb-1">
                <div className={clsx(
                  "text-[11px] font-heading font-black truncate transition-colors tracking-tight",
                  selectedConversation?.id === conv.id ? "text-primary" : "text-gray-900 group-hover:text-primary"
                )}>
                  {conv.title}
                </div>
                <div className="flex items-center gap-1.5 shrink-0 ml-2">
                  <div className="w-1 h-1 rounded-full bg-green-500 animate-pulse" />
                  <span className="text-[8px] font-heading font-bold text-green-500 tracking-tighter uppercase opacity-80">LIVE</span>
                </div>
              </div>

              <div className="text-[10px] text-gray-400 truncate mt-1 font-mono opacity-60">
                {conv.lastMessage || "AWAITING_TRANSMISSION..."}
              </div>

              <div className="flex items-center justify-between mt-4">
                <div className="flex items-center gap-1.5 text-[10px] font-mono text-gray-400">
                  <Clock size={10} className="shrink-0 opacity-40" />
                  <span>{new Date(conv.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                </div>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm(`TERMINATE_STREAM: ${conv.title}?`)) {
                      deleteConversation(conv.id);
                    }
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-500 transition-all text-gray-300"
                  title="DELETE_CONVERSATION"
                >
                  <Trash2 size={12} />
                </button>
              </div>
            </button>
          ))}
        </div>
      </aside>

      {/* Main Chat Area */}
      <section className="flex-1 flex flex-col bg-white overflow-hidden relative">
        {selectedConversation ? (
          <>
            <div className="p-4 border-b border-gray-200 flex justify-between items-center bg-white/90 backdrop-blur-sm z-10 sticky top-0">
              <h2 className="text-xs font-heading font-black">{selectedConversation.title}</h2>
              <div className="text-[10px] font-heading text-green-500 font-bold border border-green-100 px-2 py-0.5 rounded">
                ENCRYPTED_STREAM
              </div>
            </div>

            <div 
              ref={scrollRef}
              className="flex-1 overflow-y-auto p-4 space-y-6 scroll-smooth bg-gray-50/20"
            >
              <div className="max-w-3xl mx-auto w-full">
                {messages?.map((msg) => (
                  <div
                    key={msg.id}
                    className={clsx(
                      "group flex gap-4 mb-8 items-start animate-in fade-in slide-in-from-bottom-2 duration-300",
                      msg.role === "user" ? "flex-row-reverse" : "",
                    )}
                  >
                    <div
                      className={clsx(
                        "w-8 h-8 flex items-center justify-center flex-shrink-0 border shadow-sm transition-all duration-300",
                        msg.role === "user"
                          ? "border-gray-200 bg-white rounded-full group-hover:border-primary/30"
                          : "border-primary/20 bg-primary/5 text-primary rounded-none group-hover:bg-primary group-hover:text-white",
                      )}
                    >
                      {msg.role === "user" ? <User size={14} /> : <Bot size={14} />}
                    </div>
                    <div
                      className={clsx(
                        "p-4 text-[11px] leading-relaxed border shadow-sm max-w-[80%] transition-all",
                        msg.role === "user"
                          ? "bg-slate-50 border-slate-200 rounded-2xl rounded-tr-none text-slate-600"
                          : "bg-white border-gray-100 rounded-2xl rounded-tl-none text-gray-800",
                      )}
                    >
                      <div className="font-mono whitespace-pre-wrap selection:bg-primary/20 leading-relaxed text-[11px]">
                        {msg.content}
                      </div>
                      <div className="mt-3 flex items-center justify-between gap-4 opacity-0 group-hover:opacity-40 transition-opacity">
                        <span className="text-[9px] font-mono tracking-tighter uppercase font-bold">{msg.role}</span>
                        <span className="text-[9px] font-mono">{new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="p-4 border-t border-gray-200 bg-white z-10">
              <form onSubmit={handleSend} className="max-w-3xl mx-auto flex gap-2">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={isDisabled ? "CLI INACTIVE - Cannot send messages" : "ENTER_COMMAND..."}
                  disabled={isDisabled}
                  className={clsx(
                    "flex-1 bg-gray-50 border border-gray-200 px-4 py-2 text-xs font-mono focus:border-primary focus:bg-white transition-all outline-none rounded-sm",
                    isDisabled && "opacity-50 cursor-not-allowed"
                  )}
                />
                <button
                  type="submit"
                  disabled={isDisabled}
                  className={clsx(
                    "px-4 py-2 transition-all active:scale-95 font-heading text-[10px] font-bold tracking-widest uppercase",
                    isDisabled
                      ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                      : "bg-primary text-white hover:opacity-90"
                  )}
                >
                  SEND
                </button>
              </form>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center bg-gray-50/10">
            <div className="text-center group max-w-sm px-8 animate-in zoom-in-95 duration-500">
              <div className="w-20 h-20 border border-gray-100 rounded-3xl flex items-center justify-center mx-auto mb-8 text-gray-200 group-hover:text-primary transition-all duration-500 group-hover:scale-110 group-hover:rotate-12 bg-white shadow-sm">
                <MessageSquare size={36} strokeWidth={1.5} />
              </div>
              <div className="font-heading text-[11px] font-black text-gray-400 tracking-[0.2em] uppercase mb-3">
                NO_ACTIVE_TRANSMISSION
              </div>
              <p className="font-mono text-[10px] text-gray-400/60 leading-relaxed mb-8">
                Select a frequency from correctly established channels or initialize a new secure uplink
              </p>
              <button
                type="button"
                onClick={() => setIsCreating(true)}
                className="inline-flex items-center gap-2 px-6 py-2.5 bg-white border border-gray-100 text-[10px] font-heading font-black text-gray-400 hover:text-primary hover:border-primary/20 transition-all uppercase tracking-widest rounded-lg shadow-sm hover:shadow-md active:scale-95"
              >
                <Plus size={14} />
                INITIALIZE_CHANNEL
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
