import { clsx } from "clsx";
import { Package, RefreshCw, Settings, Shield, X, Plus } from "lucide-react";
import { useState } from "react";
import { useRegistry, type RegistryAsset } from "./hooks/useRegistry";

export function RegistryFeature() {
  const { skills, agents, isLoading, refresh } = useRegistry();
  const [activeTab, setActiveTab] = useState<"skills" | "agents">("skills");
  const [selectedAsset, setSelectedAsset] = useState<RegistryAsset | null>(null);
  const [isAdding, setIsAdding] = useState(false);

  const assets = activeTab === "skills" ? skills : agents;

  if (isLoading) return <div className="p-8 text-center font-heading animate-pulse">SYNCHRONIZING_REGISTRY...</div>;

  return (
    <div className="space-y-8 animate-in fade-in duration-500 relative">
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
        <div className="flex gap-4 items-center">
          <button
            type="button"
            onClick={refresh}
            className="p-2 border border-gray-200 text-gray-400 hover:text-primary hover:bg-gray-50 transition-colors"
            title="REFRESH_REGISTRY"
          >
            <RefreshCw size={14} className={isLoading ? "animate-spin" : ""} />
          </button>
          <button
            type="button"
            onClick={() => setIsAdding(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-white text-[10px] font-heading font-bold hover:opacity-90 transition-all uppercase tracking-widest shadow-sm active:scale-95"
          >
            <Plus size={14} />
            REGISTER_NEW_ASSET
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {assets.map((asset) => (
          <AssetCard 
            key={asset.name} 
            asset={asset}
            onConfig={() => setSelectedAsset(asset)}
          />
        ))}
      </div>

      {(selectedAsset || isAdding) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-[2px] animate-in fade-in duration-200">
          <div className="bg-white border border-gray-200 shadow-2xl w-full max-w-lg mx-4 animate-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between p-4 border-b border-gray-100 bg-gray-50/80">
              <h3 className="font-heading font-bold text-xs uppercase tracking-widest">
                {isAdding ? "REGISTER_NEW_ASSET" : `CONFIGURE_${selectedAsset?.type.toUpperCase()}`}
              </h3>
              <button
                type="button"
                onClick={() => {
                  setSelectedAsset(null);
                  setIsAdding(false);
                }}
                className="p-1 hover:bg-gray-200 rounded text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X size={16} />
              </button>
            </div>
            
            <div className="p-6 space-y-6">
              <div className="space-y-1">
                <div className="text-[10px] text-gray-400 font-heading">ASSET_NAME</div>
                <input 
                  type="text" 
                  defaultValue={selectedAsset?.name || ""} 
                  readOnly={!!selectedAsset}
                  className="w-full bg-gray-50 border border-gray-200 px-3 py-2 text-xs font-mono outline-none focus:border-primary transition-colors"
                />
              </div>

              <div className="space-y-1">
                <div className="text-[10px] text-gray-400 font-heading">DESCRIPTION</div>
                <textarea 
                  defaultValue={selectedAsset?.description || ""}
                  rows={3}
                  className="w-full bg-gray-50 border border-gray-200 px-3 py-2 text-xs font-mono outline-none focus:border-primary transition-colors resize-none"
                />
              </div>

              {!isAdding && (
                <div className="space-y-1">
                  <div className="text-[10px] text-gray-400 font-heading">RAW_CONFIGURATION (.json)</div>
                  <div className="bg-gray-950 p-4 font-mono text-[10px] text-green-400 border border-gray-800 shadow-inner overflow-x-auto">
                    {JSON.stringify({
                      version: selectedAsset?.version || "1.0.0",
                      is_builtin: selectedAsset?.is_builtin,
                      type: selectedAsset?.type,
                      last_sync: new Date().toISOString()
                    }, null, 2)}
                  </div>
                </div>
              )}
            </div>

            <div className="p-4 bg-gray-50 border-t border-gray-100 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => {
                  setSelectedAsset(null);
                  setIsAdding(false);
                }}
                className="px-4 py-2 text-[10px] font-heading font-bold text-gray-400 hover:text-gray-600 uppercase tracking-widest"
              >
                CANCEL
              </button>
              <button
                type="button"
                onClick={() => {
                  alert("INTEGRATION_PENDING: Backend commit required for registry modification");
                  setSelectedAsset(null);
                  setIsAdding(false);
                }}
                className="px-6 py-2 bg-primary text-white text-[10px] font-heading font-bold hover:opacity-90 uppercase tracking-widest shadow-sm"
              >
                {isAdding ? "PUBLISH_ASSET" : "SAVE_CHANGES"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function AssetCard({ asset, onConfig }: { asset: RegistryAsset; onConfig: () => void }) {
  const { name, type, version } = asset;
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
            onClick={onConfig}
            className="flex-1 py-1.5 text-[10px] font-heading font-bold tracking-wider border border-gray-200 hover:bg-gray-50 uppercase shadow-sm active:bg-gray-100 transition-colors"
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
