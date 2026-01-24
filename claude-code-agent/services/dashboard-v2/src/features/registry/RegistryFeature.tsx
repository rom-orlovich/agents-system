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
      <div className="flex flex-col sm:flex-row justify-between items-stretch sm:items-center bg-panel-bg p-4 border border-panel-border rounded-lg shadow-sm gap-4">
        <div className="flex flex-col xs:flex-row gap-2 sm:gap-4">
          <button
            type="button"
            onClick={() => setActiveTab("skills")}
            className={clsx(
              "px-4 py-2 font-heading text-[10px] sm:text-[11px] font-bold tracking-widest uppercase transition-all rounded-sm flex-1 sm:flex-none",
              activeTab === "skills" ? "bg-primary text-white shadow-lg shadow-primary/20" : "border border-panel-border text-app-muted hover:bg-background-app hover:text-text-main"
            )}
          >
            SKILLS
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("agents")}
            className={clsx(
              "px-4 py-2 font-heading text-[10px] sm:text-[11px] font-bold tracking-widest uppercase transition-all rounded-sm flex-1 sm:flex-none",
              activeTab === "agents" ? "bg-primary text-white shadow-lg shadow-primary/20" : "border border-panel-border text-app-muted hover:bg-background-app hover:text-text-main"
            )}
          >
            AGENTS
          </button>
        </div>
        <div className="flex gap-2 sm:gap-4 items-center justify-between sm:justify-end">
          <button
            type="button"
            onClick={refresh}
            className="p-2 border border-panel-border text-app-muted hover:text-primary hover:bg-background-app transition-colors rounded-sm"
            title="REFRESH_REGISTRY"
          >
            <RefreshCw size={14} className={isLoading ? "animate-spin" : ""} />
          </button>
          <button
            type="button"
            onClick={() => setIsAdding(true)}
            className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-4 py-2 bg-primary text-white text-[10px] font-heading font-bold hover:opacity-90 transition-all uppercase tracking-widest shadow-sm active:scale-95"
          >
            <Plus size={14} />
            <span className="xs:inline">REGISTER</span>
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
          className="fixed inset-0 z-[100] flex justify-end bg-black/60 backdrop-blur-sm animate-in fade-in duration-300"
          onClick={() => setEditingAsset(null)}
        >
          <div 
            className="w-full max-w-3xl bg-modal-bg shadow-2xl flex flex-col animate-in slide-in-from-right duration-500 border-l border-modal-border"
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
            
            <div className="flex-1 p-0 overflow-hidden relative bg-input-bg">
              <div className="absolute top-3 right-6 text-[9px] font-mono text-app-muted pointer-events-none uppercase tracking-widest">
                Markdown Editor // RAW_CONTENT
              </div>
              <textarea 
                value={assetContent}
                onChange={(e) => setAssetContent(e.target.value)}
                className="w-full h-full bg-transparent text-input-text p-8 font-mono text-sm leading-relaxed outline-none resize-none selection:bg-primary/20"
                spellCheck={false}
              />
            </div>

            <div className="p-4 border-t border-modal-border flex justify-between items-center bg-modal-bg">
              <div className="text-[10px] font-mono text-app-muted uppercase tracking-widest px-2">
                {assetContent.length} Characters • UTF-8
              </div>
              <div className="flex gap-4">
                <button
                  type="button"
                  onClick={() => setEditingAsset(null)}
                  className="px-6 py-2 text-[10px] font-heading font-black text-app-muted hover:text-text-main transition-colors uppercase tracking-[0.1em]"
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-[4px] animate-in fade-in duration-200">
          <div className="bg-modal-bg border border-modal-border shadow-2xl w-full max-w-lg mx-4 animate-in zoom-in-95 duration-200 rounded-none">
            <div className="flex items-center justify-between p-4 border-b border-modal-border bg-panel-bg">
              <h3 className="font-heading font-bold text-xs uppercase tracking-widest text-text-main">
                {isAdding ? "REGISTER_NEW_ASSET" : `CONFIGURE_${selectedAsset?.type.toUpperCase()}`}
              </h3>
              <button
                type="button"
                onClick={() => {
                  setSelectedAsset(null);
                  setIsAdding(false);
                }}
                className="p-1 hover:bg-background-app rounded text-app-muted hover:text-text-main transition-colors"
              >
                <X size={16} />
              </button>
            </div>
            
            <div className="p-6 space-y-6">
              <div className="space-y-1">
                <div className="text-[10px] text-app-muted font-heading">ASSET_NAME</div>
                <input 
                  type="text" 
                  defaultValue={selectedAsset?.name || ""} 
                  readOnly={!!selectedAsset}
                  className="w-full bg-input-bg border border-input-border px-3 py-2 text-xs font-mono outline-none focus:border-primary transition-colors text-input-text"
                />
              </div>

              <div className="space-y-1">
                <div className="text-[10px] text-app-muted font-heading">DESCRIPTION</div>
                <textarea 
                  defaultValue={selectedAsset?.description || ""}
                  rows={3}
                  className="w-full bg-input-bg border border-input-border px-3 py-2 text-xs font-mono outline-none focus:border-primary transition-colors resize-none text-input-text"
                />
              </div>

              {!isAdding && (
                <div className="space-y-1">
                  <div className="text-[10px] text-app-muted font-heading">RAW_CONFIGURATION (.json)</div>
                  <div className="bg-slate-950 p-4 font-mono text-[10px] text-green-400 border border-slate-800 shadow-inner overflow-x-auto">
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

            <div className="p-4 bg-panel-bg border-t border-modal-border flex justify-end gap-3">
              <button
                type="button"
                onClick={() => {
                  setSelectedAsset(null);
                  setIsAdding(false);
                }}
                className="px-4 py-2 text-[10px] font-heading font-bold text-app-muted hover:text-text-main uppercase tracking-widest"
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
      className="panel group hover:border-primary transition-all duration-300 bg-panel-bg"
      data-label={type.toUpperCase()}
    >
      <div className="flex items-start justify-between">
        <div className="p-2 bg-background-app text-app-muted group-hover:text-white group-hover:bg-primary transition-all rounded-lg">
          {type === "skill" ? <Package size={20} /> : <Shield size={20} />}
        </div>
        <div className="text-[10px] font-mono text-app-muted opacity-40">v{version || "1.0.0"}</div>
      </div>
      <div className="mt-4">
        <div className="text-xs font-heading font-black truncate text-text-main">{name}</div>
        <div className="mt-4 flex gap-2">
          <button
            type="button"
            onClick={onConfig}
            className="flex-1 py-1.5 text-[10px] font-heading font-bold tracking-wider border border-panel-border text-app-muted hover:bg-background-app hover:text-primary uppercase shadow-sm active:bg-background-app transition-all rounded-sm"
          >
            CONFIG
          </button>
          <button
            type="button"
            onClick={onEdit}
            className="p-1.5 border border-panel-border text-app-muted hover:bg-background-app hover:text-primary hover:border-primary transition-all active:scale-90 rounded-sm"
            title="EDIT_CONTENT"
          >
            <Settings size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
