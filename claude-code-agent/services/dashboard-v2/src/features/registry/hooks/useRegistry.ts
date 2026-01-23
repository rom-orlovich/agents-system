import { useQuery, useQueryClient } from "@tanstack/react-query";

export interface RegistryAsset {
  name: string;
  description: string;
  is_builtin: boolean;
  type: "skill" | "agent";
  version?: string;
}

export function useRegistry() {
  const queryClient = useQueryClient();
  const { data: skills, isLoading: isSkillsLoading } = useQuery<RegistryAsset[]>({
    queryKey: ["registry", "skills"],
    queryFn: async () => {
      const res = await fetch("/api/registry/skills");
      const data = await res.json();
      return data.map((s: any) => ({
        name: s.name,
        description: s.description,
        is_builtin: s.is_builtin,
        type: "skill",
        version: "1.0.0", // Mocked as backend doesn't seem to provide version yet
      }));
    },
  });

  const { data: agents, isLoading: isAgentsLoading } = useQuery<RegistryAsset[]>({
    queryKey: ["registry", "agents"],
    queryFn: async () => {
      const res = await fetch("/api/registry/agents");
      const data = await res.json();
      return data.map((a: any) => ({
        name: a.name,
        description: a.description,
        is_builtin: a.is_builtin,
        type: "agent",
        version: "1.0.0",
      }));
    },
  });

  return {
    skills: skills || [],
    agents: agents || [],
    isLoading: isSkillsLoading || isAgentsLoading,
    refresh: () => {
      queryClient.invalidateQueries({ queryKey: ["registry"] });
    },
  };
}
