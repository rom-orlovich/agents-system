import { useState } from "react";
import { X, GitBranch, TicketIcon, FileText } from "lucide-react";
import type { CreateSourceRequest } from "./hooks/useSources";

interface AddSourceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (request: CreateSourceRequest) => void;
  isSubmitting: boolean;
}

type SourceType = "github" | "jira" | "confluence";

const SOURCE_OPTIONS: {
  type: SourceType;
  name: string;
  icon: typeof GitBranch;
  description: string;
}[] = [
  {
    type: "github",
    name: "GitHub",
    icon: GitBranch,
    description: "Index code repositories",
  },
  {
    type: "jira",
    name: "Jira",
    icon: TicketIcon,
    description: "Index tickets and issues",
  },
  {
    type: "confluence",
    name: "Confluence",
    icon: FileText,
    description: "Index documentation pages",
  },
];

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
  const [name, setName] = useState("");

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

  const handleTypeSelect = (type: SourceType) => {
    setSelectedType(type);
    setName(`${type.charAt(0).toUpperCase() + type.slice(1)} Source`);
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
              {SOURCE_OPTIONS.map((option) => (
                <button
                  type="button"
                  key={option.type}
                  onClick={() => handleTypeSelect(option.type)}
                  className="flex items-center gap-3 p-3 border border-gray-200 hover:border-gray-400 hover:bg-gray-50 text-left transition-colors"
                >
                  <div className="p-2 border border-gray-200">
                    <option.icon size={20} />
                  </div>
                  <div>
                    <div className="font-heading text-sm">{option.name}</div>
                    <div className="text-[10px] text-gray-500">
                      {option.description}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}

          {step === "configure" && selectedType && (
            <div className="space-y-4">
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
