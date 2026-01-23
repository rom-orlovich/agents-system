import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

export interface Conversation {
  id: string;
  title: string;
  lastMessage: string;
  timestamp: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export function useChat() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data: conversations, isLoading: isConvLoading } = useQuery<Conversation[]>({
    queryKey: ["conversations"],
    queryFn: async () => {
      const res = await fetch("/api/conversations");
      const data = await res.json();
      return data.map((conv: any) => ({
        id: conv.conversation_id,
        title: conv.title,
        lastMessage: "", // Backend doesn't provide lastMessage directly in list
        timestamp: conv.updated_at || conv.created_at,
      }));
    },
  });

  const { data: messages, isLoading: isMsgLoading } = useQuery<Message[]>({
    queryKey: ["messages", selectedId],
    queryFn: async () => {
      if (!selectedId) return [];
      const res = await fetch(`/api/conversations/${selectedId}/messages`);
      const data = await res.json();
      return data.map((msg: any) => ({
        id: msg.message_id,
        role: msg.role,
        content: msg.content,
        timestamp: msg.created_at,
      }));
    },
    enabled: !!selectedId,
  });

  const sendMutation = useMutation({
    mutationFn: async (content: string) => {
      const res = await fetch(`/api/conversations/${selectedId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role: "user", content }),
      });
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["messages", selectedId] });
    },
  });

  const createMutation = useMutation({
    mutationFn: async (title: string) => {
      const res = await fetch("/api/conversations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title }),
      });
      return res.json();
    },
    onSuccess: (newConv) => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      setSelectedId(newConv.conversation_id);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await fetch(`/api/conversations/${id}`, {
        method: "DELETE",
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      if (selectedId) setSelectedId(null);
    },
  });

  return {
    conversations,
    messages,
    isLoading: isConvLoading || isMsgLoading,
    selectedConversation: conversations?.find((c) => c.id === selectedId),
    setSelectedConversation: (conv: Conversation) => setSelectedId(conv.id),
    sendMessage: (content: string) => sendMutation.mutate(content),
    createConversation: (title: string) => createMutation.mutate(title),
    deleteConversation: (id: string) => deleteMutation.mutate(id),
  };
}
