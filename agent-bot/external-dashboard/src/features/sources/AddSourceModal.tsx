import { useState } from "react";
import { X, GitBranch, TicketIcon, FileText, AlertTriangle, Link2, CheckCircle } from "lucide-react";
import { Link } from "react-router-dom";
import type { CreateSourceRequest, SourceTypeInfo } from "./hooks/useSources";
import { useSourceTypes } from "./hooks/useSources";

interface AddSourceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (request: CreateSourceRequest) => void;
  isSubmitting: boolean;
}

type SourceType = "github" | "jira" | "confluence";

const SOURCE_ICONS: Record<string, typeof GitBranch> = {
  github: GitBranch,
  jira: TicketIcon,
  confluence: FileText,
};

interface GitHubConfig {
  include_patterns: string;
  exclude_patterns: string;
  branches: string;
  file_patterns: string;
}

interface JiraConfig {
  jql: string;
  issue_types: string;
  include_labels: string;
  max_results: number;
}

interface ConfluenceConfig {
  spaces: string;
  include_labels: string;
  content_types: string;
}

export function AddSourceModal({
  isOpen,
  onClose,
  onSubmit,
  isSubmitting,
}: AddSourceModalProps) {
  const [step, setStep] = useState<"select" | "configure">("select");
  const [selectedType, setSelectedType] = useState<SourceType | null>(null);
  const [selectedTypeInfo, setSelectedTypeInfo] = useState<SourceTypeInfo | null>(null);
  const [name, setName] = useState("");

  const { data: sourceTypes, isLoading: isLoadingTypes } = useSourceTypes();

  const [githubConfig, setGithubConfig] = useState<GitHubConfig>({
    include_patterns: "",
    exclude_patterns: "",
    branches: "main, master",
    file_patterns: "**/*.py, **/*.ts, **/*.js, **/*.go",
  });

  const [jiraConfig, setJiraConfig] = useState<JiraConfig>({
    jql: "",
    issue_types: "Bug, Story, Task",
    include_labels: "",
    max_results: 1000,
  });

  const [confluenceConfig, setConfluenceConfig] = useState<ConfluenceConfig>({
    spaces: "",
    include_labels: "",
    content_types: "page, blogpost",
  });

  const handleTypeSelect = (typeInfo: SourceTypeInfo) => {
    setSelectedType(typeInfo.source_type as SourceType);
    setSelectedTypeInfo(typeInfo);
    setName(`${typeInfo.name} Source`);
    setStep("configure");
  };

  const handleSubmit = () => {
    if (!selectedType || !name) return;

    let config: Record<string, unknown> = {};

    if (selectedType === "github") {
      config = {
        include_patterns: githubConfig.include_patterns
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        exclude_patterns: githubConfig.exclude_patterns
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        branches: githubConfig.branches
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        file_patterns: githubConfig.file_patterns
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      };
    } else if (selectedType === "jira") {
      config = {
        jql: jiraConfig.jql,
        issue_types: jiraConfig.issue_types
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        include_labels: jiraConfig.include_labels
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        max_results: jiraConfig.max_results,
      };
    } else if (selectedType === "confluence") {
      config = {
        spaces: confluenceConfig.spaces
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        include_labels: confluenceConfig.include_labels
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        content_types: confluenceConfig.content_types
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      };
    }

    onSubmit({
      name,
      source_type: selectedType,
      config,
      enabled: true,
    });
  };

  const handleClose = () => {
    setStep("select");
    setSelectedType(null);
    setSelectedTypeInfo(null);
    setName("");
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white border border-gray-200 w-full max-w-lg mx-4">
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <h2 className="font-heading text-sm">
            {step === "select" ? "ADD_DATA_SOURCE" : "CONFIGURE_SOURCE"}
          </h2>
          <button
            type="button"
            onClick={handleClose}
            className="p-1 hover:bg-gray-100"
          >
            <X size={16} />
          </button>
        </div>

        <div className="p-4">
          {step === "select" && (
            <div className="grid gap-3">
              <p className="text-[10px] text-gray-500 mb-2">
                Select the type of data source you want to add. Each source will
                be indexed and made searchable for the AI agent.
              </p>
              {isLoadingTypes ? (
                <div className="text-center py-4 text-[10px] text-gray-500">
                  Loading source types...
                </div>
              ) : (
                sourceTypes?.map((typeInfo) => {
                  const Icon = SOURCE_ICONS[typeInfo.source_type] || FileText;
                  return (
                    <button
                      type="button"
                      key={typeInfo.source_type}
                      onClick={() => handleTypeSelect(typeInfo)}
                      className={`flex items-center gap-3 p-3 border text-left transition-colors ${
                        typeInfo.oauth_connected
                          ? "border-gray-200 hover:border-gray-400 hover:bg-gray-50"
                          : "border-amber-200 bg-amber-50/50"
                      }`}
                    >
                      <div className="p-2 border border-gray-200">
                        <Icon size={20} />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-heading text-sm">{typeInfo.name}</span>
                          {typeInfo.oauth_connected ? (
                            <CheckCircle size={12} className="text-green-500" />
                          ) : (
                            <AlertTriangle size={12} className="text-amber-500" />
                          )}
                        </div>
                        <div className="text-[10px] text-gray-500">
                          {typeInfo.description}
                        </div>
                        {!typeInfo.oauth_connected && (
                          <div className="text-[10px] text-amber-600 mt-1">
                            OAuth not connected -
                            <Link
                              to="/integrations"
                              className="inline-flex items-center gap-1 ml-1 hover:text-amber-800"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <Link2 size={10} />
                              Connect
                            </Link>
                          </div>
                        )}
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          )}

          {step === "configure" && selectedType && (
            <div className="space-y-4">
              {selectedTypeInfo && !selectedTypeInfo.oauth_connected && (
                <div className="p-3 bg-amber-50 border border-amber-200 text-[10px]">
                  <div className="flex items-center gap-1 text-amber-700 mb-1">
                    <AlertTriangle size={12} />
                    <span className="font-heading">OAUTH_NOT_CONNECTED</span>
                  </div>
                  <p className="text-amber-600 mb-2">
                    You can configure this source, but it will be created as disabled.
                    Connect {selectedTypeInfo.oauth_platform} OAuth to enable syncing.
                  </p>
                  <Link
                    to="/integrations"
                    className="inline-flex items-center gap-1 text-amber-700 hover:text-amber-900 font-heading"
                  >
                    <Link2 size={10} />
                    GO_TO_INTEGRATIONS
                  </Link>
                </div>
              )}

              <div>
                <label className="block text-[10px] font-heading text-gray-500 mb-1">
                  SOURCE_NAME
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-200 text-sm focus:outline-none focus:border-gray-400"
                  placeholder="Enter source name"
                />
              </div>

              {selectedType === "github" && (
                <>
                  <div>
                    <label className="block text-[10px] font-heading text-gray-500 mb-1">
                      INCLUDE_PATTERNS (comma-separated)
                    </label>
                    <input
                      type="text"
                      value={githubConfig.include_patterns}
                      onChange={(e) =>
                        setGithubConfig({
                          ...githubConfig,
                          include_patterns: e.target.value,
                        })
                      }
                      className="w-full px-3 py-2 border border-gray-200 text-sm font-mono focus:outline-none focus:border-gray-400"
                      placeholder="owner/repo, owner/repo-*"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-heading text-gray-500 mb-1">
                      BRANCHES (comma-separated)
                    </label>
                    <input
                      type="text"
                      value={githubConfig.branches}
                      onChange={(e) =>
                        setGithubConfig({
                          ...githubConfig,
                          branches: e.target.value,
                        })
                      }
                      className="w-full px-3 py-2 border border-gray-200 text-sm font-mono focus:outline-none focus:border-gray-400"
                      placeholder="main, master, develop"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-heading text-gray-500 mb-1">
                      FILE_PATTERNS (comma-separated)
                    </label>
                    <input
                      type="text"
                      value={githubConfig.file_patterns}
                      onChange={(e) =>
                        setGithubConfig({
                          ...githubConfig,
                          file_patterns: e.target.value,
                        })
                      }
                      className="w-full px-3 py-2 border border-gray-200 text-sm font-mono focus:outline-none focus:border-gray-400"
                      placeholder="**/*.py, **/*.ts"
                    />
                  </div>
                </>
              )}

              {selectedType === "jira" && (
                <>
                  <div>
                    <label className="block text-[10px] font-heading text-gray-500 mb-1">
                      JQL_FILTER (optional)
                    </label>
                    <input
                      type="text"
                      value={jiraConfig.jql}
                      onChange={(e) =>
                        setJiraConfig({ ...jiraConfig, jql: e.target.value })
                      }
                      className="w-full px-3 py-2 border border-gray-200 text-sm font-mono focus:outline-none focus:border-gray-400"
                      placeholder="project = PROJ AND status != Done"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-heading text-gray-500 mb-1">
                      ISSUE_TYPES (comma-separated)
                    </label>
                    <input
                      type="text"
                      value={jiraConfig.issue_types}
                      onChange={(e) =>
                        setJiraConfig({
                          ...jiraConfig,
                          issue_types: e.target.value,
                        })
                      }
                      className="w-full px-3 py-2 border border-gray-200 text-sm font-mono focus:outline-none focus:border-gray-400"
                      placeholder="Bug, Story, Task"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-heading text-gray-500 mb-1">
                      MAX_RESULTS
                    </label>
                    <input
                      type="number"
                      value={jiraConfig.max_results}
                      onChange={(e) =>
                        setJiraConfig({
                          ...jiraConfig,
                          max_results: parseInt(e.target.value) || 1000,
                        })
                      }
                      className="w-full px-3 py-2 border border-gray-200 text-sm font-mono focus:outline-none focus:border-gray-400"
                    />
                  </div>
                </>
              )}

              {selectedType === "confluence" && (
                <>
                  <div>
                    <label className="block text-[10px] font-heading text-gray-500 mb-1">
                      SPACES (comma-separated, leave empty for all)
                    </label>
                    <input
                      type="text"
                      value={confluenceConfig.spaces}
                      onChange={(e) =>
                        setConfluenceConfig({
                          ...confluenceConfig,
                          spaces: e.target.value,
                        })
                      }
                      className="w-full px-3 py-2 border border-gray-200 text-sm font-mono focus:outline-none focus:border-gray-400"
                      placeholder="ENG, DOCS, WIKI"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-heading text-gray-500 mb-1">
                      CONTENT_TYPES (comma-separated)
                    </label>
                    <input
                      type="text"
                      value={confluenceConfig.content_types}
                      onChange={(e) =>
                        setConfluenceConfig({
                          ...confluenceConfig,
                          content_types: e.target.value,
                        })
                      }
                      className="w-full px-3 py-2 border border-gray-200 text-sm font-mono focus:outline-none focus:border-gray-400"
                      placeholder="page, blogpost"
                    />
                  </div>
                </>
              )}

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setStep("select")}
                  className="flex-1 px-4 py-2 border border-gray-200 hover:bg-gray-50 text-[10px] font-heading"
                >
                  BACK
                </button>
                <button
                  type="button"
                  onClick={handleSubmit}
                  disabled={isSubmitting || !name}
                  className="flex-1 px-4 py-2 bg-black text-white hover:bg-gray-800 text-[10px] font-heading disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? "CREATING..." : "CREATE_SOURCE"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
