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
      console.log(`FETCH_MESSAGES: /api/conversations/${selectedId}/messages`);
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
      // Use /api/chat endpoint which creates tasks and conversations
      // If no conversation is selected, conversation_id will be undefined and a new one will be created
      const sessionId = "default-session";
      const params = new URLSearchParams({ session_id: sessionId });
      if (selectedId) params.append("conversation_id", selectedId);
      
      const res = await fetch(`/api/chat?${params.toString()}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: content }),
      });
      const data = await res.json();
      return data;
    },
    onSuccess: (data) => {
      // If a new conversation was created, select it
      if (data.data?.conversation_id) {
        if (!selectedId) {
          setSelectedId(data.data.conversation_id);
        }
        // Invalidate conversations list to show new conversation
        queryClient.invalidateQueries({ queryKey: ["conversations"] });
        // Invalidate messages for the conversation (new or existing)
        queryClient.invalidateQueries({ queryKey: ["messages", data.data.conversation_id] });
      }
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
      const res = await fetch(`/api/conversations/${id}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Failed to delete conversation");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      if (selectedId) setSelectedId(null);
    },
    onError: (error) => {
      console.error("Delete conversation error:", error);
      alert("Failed to delete conversation. Please try again.");
    }
  });

  return {
    conversations,
    messages,
    isLoading: isConvLoading || isMsgLoading,
    selectedId,
    selectedConversation: conversations?.find((c) => c.id === selectedId),
    setSelectedConversation: (conv: Conversation) => setSelectedId(conv.id),
    sendMessage: (content: string) => sendMutation.mutate(content),
    createConversation: (title: string) => createMutation.mutate(title),
    deleteConversation: (id: string) => deleteMutation.mutate(id),
  };
}
