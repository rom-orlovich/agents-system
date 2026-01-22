import { clsx } from "clsx";
import { Package, Settings, Shield } from "lucide-react";
import { useState } from "react";
import { useRegistry } from "./hooks/useRegistry";

export function RegistryFeature() {
  const { skills, agents, isLoading } = useRegistry();
  const [activeTab, setActiveTab] = useState<"skills" | "agents">("skills");

  const assets = activeTab === "skills" ? skills : agents;

  if (isLoading) return <div className="p-8 text-center font-heading">SYNCHRONIZING_REGISTRY...</div>;

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="flex justify-between items-center bg-white p-4 border border-gray-200">
        <div className="flex gap-4">
          <button
            type="button"
            onClick={() => setActiveTab("skills")}
            className={clsx(
              "px-4 py-2 font-heading text-[11px] font-bold tracking-widest uppercase transition-colors",
              activeTab === "skills" ? "bg-primary text-white" : "border border-gray-200 text-gray-400 hover:bg-gray-50"
            )}
          >
            SKILLS_REGISTRY
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("agents")}
            className={clsx(
              "px-4 py-2 font-heading text-[11px] font-bold tracking-widest uppercase transition-colors",
              activeTab === "agents" ? "bg-primary text-white" : "border border-gray-200 text-gray-400 hover:bg-gray-50"
            )}
          >
            AGENTS_REGISTRY
          </button>
        </div>
        <button
          type="button"
          className="px-4 py-2 border border-gray-200 text-[10px] font-heading font-bold hover:bg-gray-50"
        >
          REGISTER_NEW_ASSET
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {assets.map((asset) => (
          <AssetCard 
            key={asset.name} 
            name={asset.name} 
            type={asset.type} 
            version={asset.version || "1.0.0"} 
          />
        ))}
      </div>
    </div>
  );
}

function AssetCard({ name, type, version }: { name: string; type: string; version: string }) {
  return (
    <div
      className="panel group hover:border-primary transition-colors"
      data-label={type.toUpperCase()}
    >
      <div className="flex items-start justify-between">
        <div className="p-2 bg-gray-50 text-gray-400 group-hover:text-primary transition-colors">
          {type === "skill" ? <Package size={20} /> : <Shield size={20} />}
        </div>
        <div className="text-[10px] font-mono text-gray-300">v{version}</div>
      </div>
      <div className="mt-4">
        <div className="text-xs font-heading font-black truncate">{name}</div>
        <div className="mt-4 flex gap-2">
          <button
            type="button"
            className="flex-1 py-1.5 text-[10px] font-heading font-bold tracking-wider border border-gray-200 hover:bg-gray-50 uppercase shadow-sm"
          >
            CONFIG
          </button>
          <button
            type="button"
            className="p-1.5 border border-gray-200 hover:bg-red-50 hover:text-red-500 transition-colors"
          >
            <Settings size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
