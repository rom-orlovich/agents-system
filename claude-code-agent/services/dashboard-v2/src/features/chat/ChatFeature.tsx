import { clsx } from "clsx";
import { Bot, Clock, MessageSquare, Send, User } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useChat } from "./hooks/useChat";

export function ChatFeature() {
  const { conversations, messages, selectedConversation, setSelectedConversation, sendMessage } =
    useChat();
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    sendMessage(input);
    setInput("");
  };

  return (
    <div className="flex h-full border border-gray-200 bg-white animate-in fade-in duration-500 overflow-hidden rounded-lg shadow-sm">
      {/* Sidebar */}
      <aside className="w-64 border-r border-gray-200 flex flex-col bg-gray-50/50 min-h-0">
        <div className="p-4 border-b border-gray-200 bg-white font-heading text-[10px] font-bold text-gray-400 tracking-widest">
          COMMS_CHANNELS
        </div>
        <div className="flex-1 overflow-y-auto">
          {conversations?.map((conv) => (
            <button
              type="button"
              key={conv.id}
              onClick={() => setSelectedConversation(conv)}
              className={clsx(
                "w-full text-left p-4 transition-colors border-b border-gray-100 hover:bg-white group",
                selectedConversation?.id === conv.id ? "bg-white border-r-2 border-r-primary" : "",
              )}
            >
              <div className="text-xs font-heading font-black truncate group-hover:text-primary transition-colors">
                {conv.title}
              </div>
              <div className="text-[10px] text-gray-400 truncate mt-1">{conv.lastMessage}</div>
              <div className="text-[10px] text-gray-300 mt-3 flex items-center justify-between font-mono">
                <span className="flex items-center gap-1.5">
                  <Clock size={10} /> {new Date(conv.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
                <span className="text-[8px] opacity-70">LIVE</span>
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
                      "flex gap-4 mb-6",
                      msg.role === "user" ? "ml-auto flex-row-reverse" : "",
                    )}
                  >
                    <div
                      className={clsx(
                        "w-8 h-8 rounded-none flex items-center justify-center flex-shrink-0 border shadow-sm",
                        msg.role === "user"
                          ? "border-gray-200 bg-white"
                          : "border-primary/20 bg-primary/5 text-primary",
                      )}
                    >
                      {msg.role === "user" ? <User size={16} /> : <Bot size={16} />}
                    </div>
                    <div
                      className={clsx(
                        "p-4 text-xs leading-relaxed border shadow-sm max-w-[85%]",
                        msg.role === "user"
                          ? "bg-gray-50 border-gray-200 italic"
                          : "bg-white border-primary/10",
                      )}
                    >
                      <div className="font-mono whitespace-pre-wrap selection:bg-primary/20">{msg.content}</div>
                      <div className="mt-2 text-[9px] text-gray-300 font-mono">
                        {new Date(msg.timestamp).toLocaleTimeString()}
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
                  placeholder="ENTER_COMMAND..."
                  className="flex-1 bg-gray-50 border border-gray-200 px-4 py-2 text-xs font-mono focus:border-primary focus:bg-white transition-all outline-none rounded-sm"
                />
                <button
                  type="submit"
                  className="bg-primary text-white px-4 py-2 hover:opacity-90 transition-all active:scale-95 font-heading text-[10px] font-bold tracking-widest uppercase"
                >
                  SEND
                </button>
              </form>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center bg-gray-50/30">
            <div className="text-center">
              <div className="w-16 h-16 border-2 border-dashed border-gray-200 rounded-full flex items-center justify-center mx-auto mb-6 text-gray-300 animate-pulse">
                <MessageSquare size={32} />
              </div>
              <div className="font-heading text-xs font-bold text-gray-300 tracking-widest uppercase mb-2">
                NO_ACTIVE_TRANSMISSION
              </div>
              <div className="font-mono text-[10px] text-gray-400/80">
                Select a frequency from correctly established channels
              </div>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
