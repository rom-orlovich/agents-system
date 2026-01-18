"""
Discovery Agent Implementation
==============================
Finds relevant repositories and files for Jira tickets.
Mirrors the distributed system's discovery_agent/main.py
"""

import json
from pathlib import Path
from typing import List, Dict, Any

import structlog
from langchain_aws import ChatBedrock

from config import settings

logger = structlog.get_logger(__name__)


class DiscoveryAgent:
    """Agent for discovering relevant repositories."""
    
    def __init__(self, mcp_gateway):
        """Initialize the discovery agent.
        
        Args:
            mcp_gateway: Gateway for accessing MCP tools.
        """
        self.llm = ChatBedrock(
            model_id=settings.bedrock.discovery_model,
            region_name=settings.aws.region,
            model_kwargs={
                "max_tokens": settings.bedrock.max_tokens,
                "temperature": settings.bedrock.temperature
            }
        )
        self.github_mcp = mcp_gateway.get_tool("github-mcp")
        
        self._load_prompts()
        logger.info("discovery_agent_initialized", model=settings.bedrock.discovery_model)
    
    def _load_prompts(self):
        """Load prompts from prompts directory."""
        prompts_dir = Path(__file__).parent.parent / "prompts" / "discovery"
        
        system_prompt_path = prompts_dir / "system.md"
        if system_prompt_path.exists():
            self.system_prompt = system_prompt_path.read_text()
        else:
            self.system_prompt = self._get_default_prompt()
    
    def _get_default_prompt(self) -> str:
        """Default system prompt if file doesn't exist."""
        return """You are the Discovery Agent for an enterprise software organization.
Your mission is to find ALL repositories and code files relevant to the given Jira ticket."""
    
    def _call_llm(self, prompt: str, max_tokens: int = 2048) -> str:
        """Call the Bedrock LLM."""
        from langchain_core.messages import SystemMessage, HumanMessage
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=prompt)
        ]
        response = self.llm.invoke(messages)
        return response.content
    
    def _parse_json(self, response: str) -> Any:
        """Parse JSON from LLM response."""
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            response = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            response = response[start:end].strip()
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return []
    
    def extract_keywords(self, ticket: Dict[str, Any]) -> List[str]:
        """Extract technical keywords from ticket."""
        prompt = f"""Analyze this Jira ticket and extract key technical terms:

Title: {ticket.get('summary', '')}
Description: {ticket.get('description', '')}

Extract:
1. Technologies mentioned (e.g., React, PostgreSQL, OAuth)
2. Features/services (e.g., authentication, payment, dashboard)
3. Error terms (e.g., NullPointerException, 404)

Return as JSON array of strings."""

        response = self._call_llm(prompt, max_tokens=500)
        keywords = self._parse_json(response)
        
        if isinstance(keywords, list):
            return keywords[:10]
        return []
    
    def search_repositories(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """Search for relevant repositories."""
        candidate_repos = []
        
        for keyword in keywords[:5]:
            results = self.github_mcp.search_code(keyword)
            
            for result in results[:10]:
                repo_name = result["repository"]["name"]
                if not any(r["name"] == repo_name for r in candidate_repos):
                    candidate_repos.append({
                        "name": repo_name,
                        "url": result["repository"]["url"],
                        "initial_score": result.get("score", 0.5)
                    })
        
        return candidate_repos
    
    def analyze_repositories(self, candidate_repos: List[Dict], keywords: List[str]) -> List[Dict]:
        """Analyze each candidate repository."""
        analyzed = []
        
        for repo in candidate_repos[:20]:
            tree = self.github_mcp.get_repo_tree(repo["name"])
            relevant_files = self._find_relevant_files(tree, keywords)
            
            if relevant_files:
                analyzed.append({
                    "name": repo["name"],
                    "files": relevant_files,
                    "languages": self._detect_languages(tree),
                    "relevance": len(relevant_files) * 0.1
                })
        
        return analyzed
    
    def _find_relevant_files(self, tree: Dict, keywords: List[str]) -> List[Dict]:
        """Find relevant files in repo tree."""
        relevant = []
        for item in tree.get("tree", []):
            if item.get("type") == "blob":
                path = item["path"]
                for keyword in keywords:
                    if keyword.lower() in path.lower():
                        file_type = "test" if "test" in path.lower() else "source"
                        if "config" in path.lower():
                            file_type = "config"
                        relevant.append({
                            "path": path,
                            "type": file_type,
                            "relevance": 0.8
                        })
                        break
        return relevant[:10]
    
    def _detect_languages(self, tree: Dict) -> List[str]:
        """Detect programming languages in repo."""
        extensions = {}
        for item in tree.get("tree", []):
            if "." in item.get("path", ""):
                ext = item["path"].rsplit(".", 1)[-1]
                extensions[ext] = extensions.get(ext, 0) + 1
        
        ext_to_lang = {
            "py": "Python", "js": "JavaScript", "ts": "TypeScript",
            "go": "Go", "java": "Java", "rb": "Ruby", "rs": "Rust"
        }
        
        return [ext_to_lang.get(ext, ext) for ext in list(extensions.keys())[:3]]
    
    def find_dependencies(self, analyzed_repos: List[Dict]) -> List[Dict]:
        """Find cross-repository dependencies."""
        dependencies = []
        
        for repo in analyzed_repos:
            for file in repo.get("files", [])[:3]:
                try:
                    content = self.github_mcp.get_file_content(repo["name"], file["path"])
                    if content:
                        deps = self._identify_api_calls(content, analyzed_repos)
                        dependencies.extend(deps)
                except Exception:
                    pass
        
        return dependencies
    
    def _identify_api_calls(self, content: str, repos: List[Dict]) -> List[Dict]:
        """Identify API calls to other repos."""
        deps = []
        for repo in repos:
            if repo["name"] in content:
                deps.append({
                    "to": repo["name"],
                    "type": "API",
                    "description": f"References {repo['name']}"
                })
        return deps
    
    def rank_and_filter(self, analyzed_repos: List[Dict], ticket: Dict, keywords: List[str]) -> List[Dict]:
        """Rank repos and filter low relevance."""
        ranked = []
        
        for repo in analyzed_repos:
            score = self._calculate_relevance(repo, ticket, keywords)
            
            if score >= 0.3:
                reason = f"Repository contains {len(repo.get('files', []))} relevant files"
                ranked.append({
                    "name": repo["name"],
                    "relevance": score,
                    "reason": reason,
                    "files": repo.get("files", [])
                })
        
        ranked.sort(key=lambda x: x["relevance"], reverse=True)
        return ranked[:5]
    
    def _calculate_relevance(self, repo: Dict, ticket: Dict, keywords: List[str]) -> float:
        """Calculate relevance score for a repository."""
        score = 0.0
        
        matches = sum(1 for kw in keywords if kw.lower() in str(repo).lower())
        score += min(matches * 0.2, 0.6)
        score += len(repo.get("files", [])) * 0.05
        
        return min(score, 1.0)
    
    def _estimate_complexity(self, repos: List[Dict]) -> str:
        """Estimate implementation complexity."""
        total_files = sum(len(r.get("files", [])) for r in repos)
        
        if len(repos) <= 1 and total_files <= 5:
            return "Low"
        elif len(repos) <= 2 and total_files <= 15:
            return "Medium"
        else:
            return "High"
    
    def generate_approach(self, ticket: Dict, repos: List[Dict]) -> str:
        """Generate recommended approach."""
        prompt = f"""Based on the ticket and discovered repositories, provide a one-sentence
recommended approach for implementation.

Ticket: {ticket.get('summary', '')}
Repos: {[r['name'] for r in repos[:3]]}

Return only the recommendation as plain text."""

        return self._call_llm(prompt, max_tokens=200).strip()
    
    def run(self, ticket: Dict[str, Any]) -> Dict[str, Any]:
        """Run discovery for a ticket.
        
        Args:
            ticket: Ticket data with summary, description, etc.
            
        Returns:
            DiscoveryResult dict
        """
        logger.info("discovery_started", ticket_id=ticket.get("id", "unknown"))
        
        # Step 1: Extract keywords
        keywords = self.extract_keywords(ticket)
        logger.info("keywords_extracted", count=len(keywords))
        
        # Step 2: Search repositories
        candidates = self.search_repositories(keywords)
        logger.info("candidates_found", count=len(candidates))
        
        # Step 3: Analyze repositories
        analyzed = self.analyze_repositories(candidates, keywords)
        logger.info("repos_analyzed", count=len(analyzed))
        
        # Step 4: Find dependencies
        dependencies = self.find_dependencies(analyzed)
        
        # Step 5: Rank and filter
        ranked = self.rank_and_filter(analyzed, ticket, keywords)
        
        # Generate approach
        approach = self.generate_approach(ticket, ranked)
        
        result = {
            "relevantRepos": ranked,
            "crossRepoDependencies": dependencies,
            "estimatedComplexity": self._estimate_complexity(ranked),
            "recommendedApproach": approach,
            "keywords": keywords
        }
        
        logger.info("discovery_complete", repos=len(ranked), complexity=result["estimatedComplexity"])
        return result
