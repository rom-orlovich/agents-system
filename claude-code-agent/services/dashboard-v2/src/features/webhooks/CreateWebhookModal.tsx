import { useState } from "react";
import { X } from "lucide-react";

interface CreateWebhookModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: { name: string; provider: string }) => Promise<void>;
}

export function CreateWebhookModal({ isOpen, onClose, onSubmit }: CreateWebhookModalProps) {
  const [name, setName] = useState("");
  const [provider, setProvider] = useState("jira");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      await onSubmit({ name, provider });
      onClose();
      setName("");
      setProvider("jira");
    } catch (err) {
      setError("Failed to create webhook");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="w-full max-w-md bg-white border border-gray-200 shadow-xl p-6 relative animate-in fade-in zoom-in duration-200">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition-colors"
        >
          <X size={18} />
        </button>
        
        <h2 className="text-lg font-heading font-bold mb-6">NEW_LISTENER</h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-heading font-bold text-gray-500 mb-1">NAME</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 text-sm focus:outline-none focus:border-primary transition-colors font-mono"
              placeholder="my-webhook"
              required
            />
          </div>
          
          <div>
            <label className="block text-xs font-heading font-bold text-gray-500 mb-1">PROVIDER</label>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 text-sm focus:outline-none focus:border-primary transition-colors font-mono bg-white"
            >
              <option value="jira">Jira</option>
              <option value="github">GitHub</option>
              <option value="slack">Slack</option>
              <option value="custom">Custom</option>
            </select>
          </div>
          


          {error && <div className="text-red-500 text-xs font-mono">{error}</div>}
          
          <div className="flex justify-end gap-2 mt-6">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-heading border border-gray-200 hover:bg-gray-50 transition-colors"
            >
              CANCEL
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 text-xs font-heading bg-black text-white hover:bg-gray-800 transition-colors disabled:opacity-50"
            >
              {isSubmitting ? "CREATING..." : "CREATE_LISTENER"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
