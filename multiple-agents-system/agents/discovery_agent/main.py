"""
Discovery Agent Implementation
==============================
Finds relevant repositories and files for Jira tickets.
"""

import json
import os
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_aws import ChatBedrock

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import settings


class DiscoveryState(TypedDict):
    """State for the discovery workflow."""
    ticket: dict
    keywords: List[str]
    candidate_repos: List[dict]
    analyzed_repos: List[dict]
    dependencies: List[dict]
    final_result: dict


class DiscoveryAgent:
    """Agent for discovering relevant repositories."""
    
    def __init__(self, agentcore_gateway):
        """Initialize the discovery agent.
        
        Args:
            agentcore_gateway: Gateway for accessing MCP tools.
        """
        self.llm = ChatBedrock(
            model_id=settings.models.discovery_model,
            region_name=settings.aws.region
        )
        self.github_mcp = agentcore_gateway.get_tool("github-mcp")
        self.knowledge_base = agentcore_gateway.get_tool("knowledge-base")
        
        self._load_prompts()
        self.graph = self._build_graph()
    
    def _load_prompts(self):
        """Load prompts from prompts directory."""
        prompts_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "prompts", "discovery"
        )
        
        with open(os.path.join(prompts_dir, "system.md")) as f:
            self.system_prompt = f.read()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(DiscoveryState)
        
        workflow.add_node("extract_keywords", self.extract_keywords)
        workflow.add_node("search_repos", self.search_repositories)
        workflow.add_node("analyze_repos", self.analyze_repositories)
        workflow.add_node("find_dependencies", self.find_dependencies)
        workflow.add_node("rank_and_filter", self.rank_and_filter)
        
        workflow.set_entry_point("extract_keywords")
        workflow.add_edge("extract_keywords", "search_repos")
        workflow.add_edge("search_repos", "analyze_repos")
        workflow.add_edge("analyze_repos", "find_dependencies")
        workflow.add_edge("find_dependencies", "rank_and_filter")
        workflow.add_edge("rank_and_filter", END)
        
        return workflow.compile()
    
    async def extract_keywords(self, state: DiscoveryState) -> DiscoveryState:
        """Extract technical keywords from ticket."""
        prompt = f"""
        Analyze this Jira ticket and extract key technical terms:
        
        Title: {state['ticket']['summary']}
        Description: {state['ticket']['description']}
        
        Extract:
        1. Technologies mentioned (e.g., React, PostgreSQL, OAuth)
        2. Features/services (e.g., authentication, payment, dashboard)
        3. Error terms (e.g., NullPointerException, 404)
        
        Return as JSON array of strings.
        """
        
        response = await self.llm.ainvoke(prompt)
        keywords = json.loads(response.content)
        
        return {**state, "keywords": keywords}
    
    async def search_repositories(self, state: DiscoveryState) -> DiscoveryState:
        """Search for relevant repositories."""
        candidate_repos = []
        
        for keyword in state["keywords"][:5]:
            results = await self.github_mcp.search_code(
                org=settings.github.org,
                query=keyword
            )
            
            for result in results[:10]:
                repo_name = result["repository"]["name"]
                if not any(r["name"] == repo_name for r in candidate_repos):
                    candidate_repos.append({
                        "name": repo_name,
                        "url": result["repository"]["url"],
                        "initial_score": result.get("score", 0.5)
                    })
        
        return {**state, "candidate_repos": candidate_repos}
    
    async def analyze_repositories(self, state: DiscoveryState) -> DiscoveryState:
        """Analyze each candidate repository."""
        analyzed = []
        
        for repo in state["candidate_repos"][:20]:
            tree = await self.github_mcp.get_repo_tree(repo=repo["name"])
            
            relevant_files = await self._find_relevant_files(
                tree=tree,
                keywords=state["keywords"]
            )
            
            if len(relevant_files) > 0:
                analyzed.append({
                    "name": repo["name"],
                    "files": relevant_files,
                    "languages": self._detect_languages(tree)
                })
        
        return {**state, "analyzed_repos": analyzed}
    
    async def find_dependencies(self, state: DiscoveryState) -> DiscoveryState:
        """Find cross-repository dependencies."""
        dependencies = []
        
        for repo in state["analyzed_repos"]:
            for file in repo["files"][:3]:
                content = await self.github_mcp.get_file(
                    repo=repo["name"],
                    path=file["path"]
                )
                
                deps = await self._identify_api_calls(content, state["analyzed_repos"])
                dependencies.extend(deps)
        
        return {**state, "dependencies": dependencies}
    
    async def rank_and_filter(self, state: DiscoveryState) -> DiscoveryState:
        """Rank repos and create final output."""
        ranked_repos = []
        
        for repo in state["analyzed_repos"]:
            score = await self._calculate_relevance_score(
                repo=repo,
                ticket=state["ticket"],
                keywords=state["keywords"]
            )
            
            if score >= 0.3:
                reason = await self._generate_reason(repo, state["ticket"])
                ranked_repos.append({
                    "name": repo["name"],
                    "relevance": score,
                    "reason": reason,
                    "files": repo["files"]
                })
        
        ranked_repos.sort(key=lambda x: x["relevance"], reverse=True)
        
        final_result = {
            "relevantRepos": ranked_repos[:5],
            "crossRepoDependencies": state["dependencies"],
            "estimatedComplexity": self._estimate_complexity(ranked_repos),
            "recommendedApproach": await self._generate_approach(state)
        }
        
        return {**state, "final_result": final_result}
    
    async def _find_relevant_files(self, tree: dict, keywords: List[str]) -> List[dict]:
        """Find relevant files in repo tree."""
        relevant = []
        for item in tree.get("tree", []):
            if item["type"] == "blob":
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
    
    def _detect_languages(self, tree: dict) -> List[str]:
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
    
    async def _identify_api_calls(self, content: str, repos: List[dict]) -> List[dict]:
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
    
    async def _calculate_relevance_score(self, repo: dict, ticket: dict, keywords: List[str]) -> float:
        """Calculate relevance score for a repository."""
        score = 0.0
        
        matches = sum(1 for kw in keywords if kw.lower() in str(repo).lower())
        score += min(matches * 0.2, 0.6)
        
        score += len(repo.get("files", [])) * 0.05
        
        return min(score, 1.0)
    
    async def _generate_reason(self, repo: dict, ticket: dict) -> str:
        """Generate reason for repo relevance."""
        return f"Repository contains {len(repo.get('files', []))} relevant files"
    
    def _estimate_complexity(self, repos: List[dict]) -> str:
        """Estimate implementation complexity."""
        total_files = sum(len(r.get("files", [])) for r in repos)
        
        if len(repos) <= 1 and total_files <= 5:
            return "Low"
        elif len(repos) <= 2 and total_files <= 15:
            return "Medium"
        else:
            return "High"
    
    async def _generate_approach(self, state: DiscoveryState) -> str:
        """Generate recommended approach."""
        prompt = f"""
        Based on the ticket and discovered repositories, provide a one-sentence
        recommended approach for implementation.
        
        Ticket: {state['ticket']['summary']}
        Repos: {[r['name'] for r in state['analyzed_repos'][:3]]}
        """
        
        response = await self.llm.ainvoke(prompt)
        return response.content.strip()
    
    async def run(self, ticket: dict) -> dict:
        """Run discovery for a ticket."""
        initial_state = {
            "ticket": ticket,
            "keywords": [],
            "candidate_repos": [],
            "analyzed_repos": [],
            "dependencies": [],
            "final_result": {}
        }
        
        final_state = await self.graph.ainvoke(initial_state)
        return final_state["final_result"]


async def handler(event, context):
    """Lambda handler for discovery agent."""
    from agents.shared.gateway import AgentCoreGateway
    
    gateway = AgentCoreGateway()
    agent = DiscoveryAgent(gateway)
    
    ticket = {
        "ticketId": event.get("ticketId"),
        "summary": event.get("summary"),
        "description": event.get("description", ""),
        "labels": event.get("labels", []),
        "priority": event.get("priority", "Medium")
    }
    
    result = await agent.run(ticket)
    
    return {
        "statusCode": 200,
        "body": json.dumps(result)
    }
