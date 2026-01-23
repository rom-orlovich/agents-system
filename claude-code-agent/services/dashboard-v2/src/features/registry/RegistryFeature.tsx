import { clsx } from "clsx";
import { Package, RefreshCw, Settings, Shield, X, Plus } from "lucide-react";
import { useState } from "react";
import { useRegistry, type RegistryAsset } from "./hooks/useRegistry";

export function RegistryFeature() {
  const { skills, agents, isLoading, refresh, getAssetContent, updateAssetContent } = useRegistry();
  const [activeTab, setActiveTab] = useState<"skills" | "agents">("skills");
  const [selectedAsset, setSelectedAsset] = useState<RegistryAsset | null>(null);
  const [isAdding, setIsAdding] = useState(false);
  const [editingAsset, setEditingAsset] = useState<RegistryAsset | null>(null);
  const [assetContent, setAssetContent] = useState<string>("");
  const [isSaving, setIsSaving] = useState(false);

  const handleEditContent = async (asset: RegistryAsset) => {
    try {
      const data = await getAssetContent(asset.type, asset.name);
      setAssetContent(data.content);
      setEditingAsset(asset);
    } catch (error) {
      console.error("Failed to load content:", error);
      alert("CRITICAL_FAILURE: UNABLE_TO_READ_ASSET_CONTENT");
    }
  };

  const handleSaveContent = async () => {
    if (!editingAsset) return;
    setIsSaving(true);
    try {
      await updateAssetContent(editingAsset.type, editingAsset.name, assetContent);
      setEditingAsset(null);
      refresh();
    } catch (error) {
      console.error("Failed to save content:", error);
      alert("CRITICAL_FAILURE: UNABLE_TO_PERSIST_CHANGES");
    } finally {
      setIsSaving(false);
    }
  };

  const assets = activeTab === "skills" ? skills : agents;

  if (isLoading) return (
    <div className="p-8 text-center font-heading animate-pulse flex flex-col items-center gap-4">
      <div className="w-12 h-12 border-2 border-primary border-t-transparent animate-spin" />
      <div className="tracking-[0.2em] text-[10px] font-black">SYNCHRONIZING_SYSTEM_REGISTRY...</div>
    </div>
  );

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
            onEdit={() => handleEditContent(asset)}
          />
        ))}
      </div>

      {/* Content Editor Drawer */}
      {editingAsset && (
        <div 
          className="fixed inset-0 z-[100] flex justify-end bg-black/50 backdrop-blur-sm animate-in fade-in duration-300"
          onClick={() => setEditingAsset(null)}
        >
          <div 
            className="w-full max-w-3xl bg-white shadow-2xl flex flex-col animate-in slide-in-from-right duration-500 border-l border-gray-200"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-4 bg-primary text-white shadow-md">
              <div className="flex items-center gap-3">
                <Settings size={18} className="animate-spin-slow" />
                <h3 className="font-heading font-black text-xs uppercase tracking-[0.15em]">
                  {editingAsset.type.toUpperCase()}_EDITOR: {editingAsset.name}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setEditingAsset(null)}
                className="p-1 hover:bg-white/20 transition-colors rounded"
              >
                <X size={20} />
              </button>
            </div>
            
            <div className="flex-1 p-0 overflow-hidden relative bg-slate-50">
              <div className="absolute top-3 right-6 text-[9px] font-mono text-slate-400 pointer-events-none uppercase tracking-widest">
                Markdown Editor // RAW_CONTENT
              </div>
              <textarea 
                value={assetContent}
                onChange={(e) => setAssetContent(e.target.value)}
                className="w-full h-full bg-transparent text-slate-800 p-8 font-mono text-sm leading-relaxed outline-none resize-none selection:bg-primary/20"
                spellCheck={false}
              />
            </div>

            <div className="p-4 border-t border-gray-100 flex justify-between items-center bg-white">
              <div className="text-[10px] font-mono text-slate-400 uppercase tracking-widest px-2">
                {assetContent.length} Characters • UTF-8
              </div>
              <div className="flex gap-4">
                <button
                  type="button"
                  onClick={() => setEditingAsset(null)}
                  className="px-6 py-2 text-[10px] font-heading font-black text-slate-400 hover:text-slate-600 transition-colors uppercase tracking-[0.1em]"
                >
                  DISCARD_CHANGES
                </button>
                <button
                  type="button"
                  onClick={handleSaveContent}
                  disabled={isSaving}
                  className="px-10 py-2.5 bg-primary text-white text-[10px] font-heading font-black hover:opacity-90 active:scale-95 transition-all disabled:opacity-50 uppercase tracking-[0.15em] shadow-lg shadow-primary/20"
                >
                  {isSaving ? "SAVING..." : "SAVE_ALL_CHANGES"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

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

function AssetCard({ asset, onConfig, onEdit }: { asset: RegistryAsset; onConfig: () => void; onEdit: () => void }) {
  const { name, type, version } = asset;
  return (
    <div
      className="panel group hover:border-primary transition-all duration-300 border-gray-200 bg-white"
      data-label={type.toUpperCase()}
    >
      <div className="flex items-start justify-between">
        <div className="p-2 bg-gray-50 text-gray-400 group-hover:text-white group-hover:bg-primary transition-all">
          {type === "skill" ? <Package size={20} /> : <Shield size={20} />}
        </div>
        <div className="text-[10px] font-mono text-gray-300">v{version || "1.0.0"}</div>
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
            onClick={onEdit}
            className="p-1.5 border border-gray-200 hover:bg-slate-50 hover:text-primary hover:border-primary transition-all active:scale-90"
            title="EDIT_CONTENT"
          >
            <Settings size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
