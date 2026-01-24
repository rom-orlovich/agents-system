import { clsx } from "clsx";
import { Bot, Clock, MessageSquare, Plus, Trash2, User, X, Check } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useChat } from "./hooks/useChat";
import { useCLIStatus } from "../../hooks/useCLIStatus";

export function ChatFeature() {
  const { conversations, messages, selectedId, selectedConversation, setSelectedConversation, sendMessage, createConversation, deleteConversation } =
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
    <div className="flex h-full border border-app bg-panel-app animate-in fade-in duration-500 overflow-hidden rounded-xl shadow-xl dark:shadow-slate-950/50">
      {/* Sidebar */}
      <aside className="w-64 border-r border-app flex flex-col bg-chat-sidebar min-h-0">
        <div className="p-4 border-b border-app bg-white dark:bg-slate-900/50 flex justify-between items-center">
          <span className="font-heading text-[10px] font-bold text-slate-400 dark:text-slate-500 tracking-widest">COMMS_CHANNELS</span>
          <button 
            type="button"
            onClick={() => setIsCreating(true)}
            className="p-1 hover:bg-gray-100 dark:hover:bg-slate-800 text-gray-400 hover:text-primary rounded transition-colors"
          >
            <Plus size={14} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {isCreating && (
            <div className="p-2 m-2 bg-white dark:bg-slate-800 border border-primary/20 rounded shadow-sm">
              <form onSubmit={handleCreate}>
                 <input
                  ref={titleInputRef}
                  type="text"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="CHANNEL_NAME..."
                  className="w-full text-[11px] font-heading font-bold mb-2 outline-none placeholder:text-gray-300 dark:bg-transparent dark:text-white"
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
                    className="p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 rounded transition-colors"
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
                "w-full text-left p-4 transition-all border-b border-app hover:bg-white dark:hover:bg-slate-900 group relative",
                selectedConversation?.id === conv.id ? "bg-white dark:bg-slate-800/50" : "",
              )}
            >
              {selectedConversation?.id === conv.id && (
                <div className="absolute left-0 top-0 bottom-0 w-1 bg-primary animate-in slide-in-from-left duration-300" />
              )}
              
              <div className="flex justify-between items-start mb-1">
                <div className={clsx(
                  "text-[11px] font-heading font-black truncate transition-colors tracking-tight",
                  selectedConversation?.id === conv.id ? "text-primary" : "text-app-main group-hover:text-primary"
                )}>
                  {conv.title}
                </div>
                <div className="flex items-center gap-1.5 shrink-0 ml-2">
                  <div className="w-1 h-1 rounded-full bg-green-500 animate-pulse" />
                  <span className="text-[8px] font-heading font-bold text-green-500 tracking-tighter uppercase opacity-80">LIVE</span>
                </div>
              </div>

              <div className="text-[10px] text-app-muted truncate mt-1 font-mono opacity-60">
                {conv.lastMessage || "AWAITING_TRANSMISSION..."}
              </div>

              <div className="flex items-center justify-between mt-4">
                <div className="flex items-center gap-1.5 text-[10px] font-mono text-app-muted">
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
                  className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-500 transition-all text-slate-400 dark:text-slate-600"
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
      <section className="flex-1 flex flex-col bg-white dark:bg-slate-900 overflow-hidden relative">
        {selectedId ? (
          <>
            <div className="p-4 border-b border-app flex justify-between items-center bg-white/90 dark:bg-slate-900/90 backdrop-blur-sm z-10 sticky top-0">
              <h2 className="text-xs font-heading font-black dark:text-white">
                {selectedConversation?.title || "Establishment in progress..."}
              </h2>
              <div className="text-[10px] font-heading text-green-500 font-bold border border-green-100 dark:border-green-900/30 px-2 py-0.5 rounded uppercase">
                ENCRYPTED_STREAM
              </div>
            </div>

            <div 
              ref={scrollRef}
              className="flex-1 overflow-y-auto p-4 space-y-6 scroll-smooth bg-gray-50/20 dark:bg-slate-950/20"
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
                          ? "border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 rounded-full group-hover:border-primary/30"
                          : "border-primary/20 bg-primary/5 text-primary rounded-none group-hover:bg-primary group-hover:text-white",
                      )}
                    >
                      {msg.role === "user" ? <User size={14} className="dark:text-slate-300" /> : <Bot size={14} />}
                    </div>
                    <div
                      className={clsx(
                        "p-4 text-[11px] leading-relaxed border shadow-sm max-w-[80%] transition-all",
                        msg.role === "user"
                          ? "bg-slate-50 dark:bg-slate-800/50 border-slate-200 dark:border-slate-700 rounded-2xl rounded-tr-none text-slate-600 dark:text-slate-300"
                          : "bg-white dark:bg-slate-800 border-gray-100 dark:border-slate-700 rounded-2xl rounded-tl-none text-gray-800 dark:text-slate-200",
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
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center bg-gray-50/10 dark:bg-slate-950/10">
            <div className="text-center group max-w-sm px-8 animate-in zoom-in-95 duration-500">
              <div className="w-20 h-20 border border-gray-100 dark:border-slate-800 rounded-3xl flex items-center justify-center mx-auto mb-8 text-gray-200 dark:text-slate-800 group-hover:text-primary transition-all duration-500 group-hover:scale-110 group-hover:rotate-12 bg-white dark:bg-slate-900 shadow-sm shadow-gray-200/50 dark:shadow-black">
                <MessageSquare size={36} strokeWidth={1.5} />
              </div>
              <div className="font-heading text-[11px] font-black text-gray-400 dark:text-gray-600 tracking-[0.2em] uppercase mb-3">
                NO_ACTIVE_TRANSMISSION
              </div>
              <p className="font-mono text-[10px] text-gray-400/60 dark:text-gray-500 leading-relaxed mb-8">
                Select a frequency from correctly established channels or initialize a new secure uplink
              </p>
              <button
                type="button"
                onClick={() => setIsCreating(true)}
                className="inline-flex items-center gap-2 px-6 py-2.5 bg-white dark:bg-slate-800 border border-gray-100 dark:border-slate-700 text-[10px] font-heading font-black text-gray-400 dark:text-gray-500 hover:text-primary hover:border-primary/20 transition-all uppercase tracking-widest rounded-lg shadow-sm hover:shadow-md active:scale-95"
              >
                <Plus size={14} />
                INITIALIZE_CHANNEL
              </button>
            </div>
          </div>
        )}
        
        {/* Input form always visible at bottom */}
        <div className="p-4 border-t border-app bg-white dark:bg-slate-900 z-10">
          <form onSubmit={handleSend} className="max-w-3xl mx-auto flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={isDisabled ? "CLI INACTIVE - Cannot send messages" : selectedId ? "ENTER_COMMAND..." : "ENTER_COMMAND... (will create new conversation)"}
              disabled={isDisabled}
              className={clsx(
                "flex-1 bg-gray-50 dark:bg-slate-950 border border-app px-4 py-2 text-xs font-mono focus:border-primary focus:bg-white dark:focus:bg-slate-900 transition-all outline-none rounded-sm dark:text-white",
                isDisabled && "opacity-50 cursor-not-allowed"
              )}
            />
            <button
              type="submit"
              disabled={isDisabled}
              className={clsx(
                "px-4 py-2 transition-all active:scale-95 font-heading text-[10px] font-bold tracking-widest uppercase",
                isDisabled
                  ? "bg-gray-300 dark:bg-slate-800 text-gray-500 dark:text-slate-600 cursor-not-allowed"
                  : "bg-primary text-white hover:opacity-90"
              )}
            >
              EXECUTE
            </button>
          </form>
        </div>
      </section>
    </div>
  );
}
