import { clsx } from "clsx";
import { Bot, Clock, MessageSquare, Plus, Trash2, User, X, Check } from "lucide-react";
import React, { useEffect, useRef, useState } from "react";
import { useChat } from "./hooks/useChat";
import { useCLIStatus } from "../../hooks/useCLIStatus";
import { useTaskModal } from "../../hooks/useTaskModal";

export function ChatFeature() {
  const { conversations, messages, selectedId, selectedConversation, setSelectedConversation, sendMessage, createConversation, deleteConversation } =
    useChat();
  const { active: cliActive } = useCLIStatus();
  const { openTask } = useTaskModal();
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

  const renderMessageContent = (content: string) => {
    // Regex to match task- followed by alphanumeric characters
    const taskRegex = /task-[a-zA-Z0-9]+/g;
    const parts = content.split(taskRegex);
    const matches = content.match(taskRegex);

    if (!matches) return content;

    return parts.reduce((acc: (React.ReactNode)[], part, i) => {
      acc.push(part);
      if (matches[i]) {
        acc.push(
          <button
            key={`${i}-task`}
            type="button"
            onClick={() => openTask(matches[i])}
            className="text-primary hover:underline font-bold cursor-pointer bg-primary/10 px-1 rounded-sm transition-colors hover:bg-primary/20"
          >
            {matches[i]}
          </button>
        );
      }
      return acc;
    }, []);
  };

  const [mobileView, setMobileView] = useState<"list" | "chat">("list");

  useEffect(() => {
    if (selectedId && window.innerWidth < 768) {
      setMobileView("chat");
    }
  }, [selectedId]);

  return (
    <div className="flex h-full border border-panel-border bg-background-app animate-in fade-in duration-500 overflow-hidden rounded-xl shadow-xl dark:shadow-slate-950/50 relative">
      {/* Sidebar / Thread List */}
      <aside className={clsx(
        "w-full md:w-64 border-r border-panel-border flex flex-col bg-sidebar-bg min-h-0 transition-all duration-300",
        mobileView === "chat" ? "hidden md:flex" : "flex"
      )}>
        <div className="p-4 border-b border-panel-border bg-panel-bg flex justify-between items-center">
          <span className="font-heading text-[10px] font-bold text-app-muted tracking-widest">COMMS_CHANNELS</span>
          <button 
            type="button"
            onClick={() => setIsCreating(true)}
            className="p-1 hover:bg-background-app text-app-muted hover:text-primary rounded transition-colors"
          >
            <Plus size={14} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {isCreating && (
            <div className="p-2 m-2 bg-panel-bg border border-primary/20 rounded shadow-sm">
              <form onSubmit={handleCreate}>
                 <input
                  ref={titleInputRef}
                  type="text"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="CHANNEL_NAME..."
                  className="w-full text-[11px] font-heading font-bold mb-2 outline-none placeholder:text-gray-300 bg-transparent text-app-main"
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
                    className="p-1 text-app-muted hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/10 rounded transition-colors"
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
            <div
              role="button"
              tabIndex={0}
              key={conv.id}
              onClick={() => {
                setSelectedConversation(conv);
                if (window.innerWidth < 768) setMobileView("chat");
              }}
              onKeyDown={(e) => e.key === "Enter" && setSelectedConversation(conv)}
              className={clsx(
                "w-full text-left p-4 transition-all border-b border-panel-border hover:bg-panel-bg group relative cursor-pointer outline-none",
                selectedConversation?.id === conv.id ? "bg-panel-bg shadow-inner" : "",
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
                  className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-500 transition-all text-app-muted"
                  title="DELETE_CONVERSATION"
                >
                  <Trash2 size={12} />
                </button>
              </div>
            </div>
          ))}
        </div>
      </aside>

      {/* Main Chat Area */}
      <section className={clsx(
        "flex-1 flex flex-col bg-panel-bg overflow-hidden relative",
        mobileView === "list" ? "hidden md:flex" : "flex"
      )}>
        {selectedId ? (
          <>
            <div className="p-4 border-b border-panel-border flex justify-between items-center bg-panel-bg/90 backdrop-blur-sm z-10 sticky top-0">
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setMobileView("list")}
                  className="p-1 md:hidden hover:bg-background-app rounded text-app-muted transition-colors"
                >
                  <X size={18} />
                </button>
                <h2 className="text-xs font-heading font-black text-app-main">
                  {selectedConversation?.title || "Establishment in progress..."}
                </h2>
              </div>
              <div className="text-[10px] font-heading text-green-500 font-bold border border-green-500/20 px-2 py-0.5 rounded uppercase">
                ENCRYPTED_STREAM
              </div>
            </div>

            <div 
              ref={scrollRef}
              className="flex-1 overflow-y-auto p-4 space-y-6 scroll-smooth bg-background-app/20"
            >
              <div className="max-w-3xl mx-auto w-full">
                {messages?.map((msg) => (
                  <div
                    key={msg.id}
                    className={clsx(
                      "group flex gap-2 md:gap-4 mb-8 items-start animate-in fade-in slide-in-from-bottom-2 duration-300",
                      msg.role === "user" ? "flex-row-reverse" : "",
                    )}
                  >
                    <div
                      className={clsx(
                        "w-6 h-6 md:w-8 md:h-8 flex items-center justify-center flex-shrink-0 border shadow-sm transition-all duration-300",
                        msg.role === "user"
                          ? "border-input-border bg-panel-bg rounded-full group-hover:border-primary/30"
                          : "border-primary/20 bg-primary/5 text-primary rounded-none group-hover:bg-primary group-hover:text-white",
                      )}
                    >
                      {msg.role === "user" ? <User size={12} className="md:w-3.5 md:h-3.5 text-app-main" /> : <Bot size={12} className="md:w-3.5 md:h-3.5" />}
                    </div>
                    <div
                      className={clsx(
                        "p-3 md:p-4 text-[10px] md:text-[11px] leading-relaxed border shadow-sm max-w-[85%] md:max-w-[80%] transition-all",
                        msg.role === "user"
                          ? "bg-background-app border-panel-border rounded-2xl rounded-tr-none text-app-main/80"
                          : "bg-panel-bg border-panel-border rounded-2xl rounded-tl-none text-app-main",
                      )}
                    >
                      <div className="font-mono whitespace-pre-wrap selection:bg-primary/20 leading-relaxed">
                        {renderMessageContent(msg.content)}
                      </div>
                      <div className="mt-2 md:mt-3 flex items-center justify-between gap-4 opacity-0 group-hover:opacity-40 transition-opacity">
                        <span className="text-[8px] md:text-[9px] font-mono tracking-tighter uppercase font-bold text-app-muted">{msg.role}</span>
                        <span className="text-[8px] md:text-[9px] font-mono text-app-muted">{new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center bg-background-app/10">
            <div className="text-center group max-w-sm px-8 animate-in zoom-in-95 duration-500">
              <div className="w-16 h-16 md:w-20 md:h-20 border border-panel-border rounded-3xl flex items-center justify-center mx-auto mb-8 text-app-muted/30 group-hover:text-primary transition-all duration-500 group-hover:scale-110 group-hover:rotate-12 bg-panel-bg shadow-sm">
                <MessageSquare size={32} className="md:w-9 md:h-9" strokeWidth={1.5} />
              </div>
              <div className="font-heading text-[10px] md:text-[11px] font-black text-app-muted tracking-[0.2em] uppercase mb-3">
                NO_ACTIVE_TRANSMISSION
              </div>
              <p className="font-mono text-[9px] md:text-[10px] text-app-muted/60 leading-relaxed mb-8">
                Select a frequency from correctly established channels or initialize a new secure uplink
              </p>
              <button
                type="button"
                onClick={() => setIsCreating(true)}
                className="inline-flex items-center gap-2 px-6 py-2.5 bg-panel-bg border border-input-border text-[10px] font-heading font-black text-app-muted hover:text-primary hover:border-primary/20 transition-all uppercase tracking-widest rounded-lg shadow-sm hover:shadow-md active:scale-95"
              >
                <Plus size={14} />
                INITIALIZE_CHANNEL
              </button>
            </div>
          </div>
        )}
        
        {/* Input form always visible at bottom */}
        <div className="p-4 border-t border-panel-border bg-panel-bg z-10 w-full">
          <form onSubmit={handleSend} className="max-w-3xl mx-auto flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={isDisabled ? "CLI INACTIVE" : selectedId ? "ENTER_COMMAND..." : "ENTER_COMMAND..."}
              disabled={isDisabled}
              className={clsx(
                "flex-1 bg-background-app border border-input-border px-3 md:px-4 py-2 text-[10px] md:text-xs font-mono focus:border-primary focus:bg-panel-bg transition-all outline-none rounded-sm text-input-text",
                isDisabled && "opacity-50 cursor-not-allowed"
              )}
            />
            <button
              type="submit"
              disabled={isDisabled}
              className={clsx(
                "px-3 md:px-4 py-2 transition-all active:scale-95 font-heading text-[10px] font-bold tracking-widest uppercase",
                isDisabled
                  ? "bg-slate-200 text-slate-400 cursor-not-allowed"
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
