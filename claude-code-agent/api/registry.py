"""Skills and agents registry API endpoints."""

import shutil
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from core.config import settings
from shared import APIResponse
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/registry", tags=["registry"])


class SkillInfo(BaseModel):
    """Skill information."""
    name: str
    description: str
    is_builtin: bool
    has_scripts: bool
    path: str


class AgentInfo(BaseModel):
    """Agent information."""
    name: str
    agent_type: str
    description: str
    is_builtin: bool
    path: str


@router.get("/skills")
async def list_skills() -> List[SkillInfo]:
    """List all available skills (builtin + user)."""
    skills = []
    
    # Builtin skills
    builtin_skills_dir = settings.skills_dir
    if builtin_skills_dir.exists():
        for skill_dir in builtin_skills_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                skill_md = skill_dir / "SKILL.md"
                description = _extract_description(skill_md)
                skills.append(SkillInfo(
                    name=skill_dir.name,
                    description=description,
                    is_builtin=True,
                    has_scripts=(skill_dir / "scripts").exists(),
                    path=str(skill_dir),
                ))
    
    # User skills
    user_skills_dir = settings.user_skills_dir
    if user_skills_dir.exists():
        for skill_dir in user_skills_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                skill_md = skill_dir / "SKILL.md"
                description = _extract_description(skill_md)
                skills.append(SkillInfo(
                    name=skill_dir.name,
                    description=description,
                    is_builtin=False,
                    has_scripts=(skill_dir / "scripts").exists(),
                    path=str(skill_dir),
                ))
    
    return skills


@router.post("/skills/upload")
async def upload_skill(
    name: str = Form(..., description="Skill folder name"),
    files: List[UploadFile] = File(..., description="Skill files (SKILL.md required)")
) -> APIResponse:
    """Upload a new skill folder."""
    
    # Validate skill name
    if not name or "/" in name or ".." in name:
        raise HTTPException(400, "Invalid skill name")
    
    # Check if SKILL.md is included
    has_skill_md = any(f.filename == "SKILL.md" for f in files)
    if not has_skill_md:
        raise HTTPException(400, "SKILL.md is required")
    
    # Create skill directory
    skill_dir = settings.user_skills_dir / name
    if skill_dir.exists():
        raise HTTPException(400, f"Skill '{name}' already exists")
    
    skill_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Save all files
        for file in files:
            # Determine target path
            if "/" in file.filename:
                # Handle subdirectories (e.g., scripts/run.py)
                file_path = skill_dir / file.filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                file_path = skill_dir / file.filename
            
            # Write file
            content = await file.read()
            file_path.write_bytes(content)
        
        logger.info("skill_uploaded", name=name, files_count=len(files))
        
        return APIResponse(
            success=True,
            message=f"Skill '{name}' uploaded successfully",
            data={"path": str(skill_dir)}
        )
    except Exception as e:
        # Cleanup on error
        if skill_dir.exists():
            shutil.rmtree(skill_dir)
        raise HTTPException(500, f"Failed to upload skill: {str(e)}")


@router.delete("/skills/{skill_name}")
async def delete_skill(skill_name: str) -> APIResponse:
    """Delete a user skill (builtin skills cannot be deleted)."""
    
    # Only allow deleting user skills
    skill_dir = settings.user_skills_dir / skill_name
    
    if not skill_dir.exists():
        raise HTTPException(404, f"Skill '{skill_name}' not found")
    
    if not skill_dir.is_relative_to(settings.user_skills_dir):
        raise HTTPException(403, "Cannot delete builtin skills")
    
    shutil.rmtree(skill_dir)
    
    logger.info("skill_deleted", name=skill_name)
    
    return APIResponse(
        success=True,
        message=f"Skill '{skill_name}' deleted successfully"
    )


@router.post("/agents/upload")
async def upload_agent(
    name: str = Form(..., description="Agent folder name"),
    files: List[UploadFile] = File(..., description="Agent files (.claude/CLAUDE.md required)")
) -> APIResponse:
    """Upload a new agent folder."""
    
    # Validate agent name
    if not name or "/" in name or ".." in name:
        raise HTTPException(400, "Invalid agent name")
    
    # Check if .claude/CLAUDE.md is included
    has_claude_md = any(f.filename == ".claude/CLAUDE.md" or f.filename == "CLAUDE.md" for f in files)
    if not has_claude_md:
        raise HTTPException(400, ".claude/CLAUDE.md is required")
    
    # Create agent directory
    agent_dir = settings.user_agents_dir / name
    if agent_dir.exists():
        raise HTTPException(400, f"Agent '{name}' already exists")
    
    agent_dir.mkdir(parents=True, exist_ok=True)
    claude_dir = agent_dir / ".claude"
    claude_dir.mkdir(exist_ok=True)
    
    try:
        # Save all files
        for file in files:
            # Determine target path
            if file.filename == "CLAUDE.md":
                # If user uploaded CLAUDE.md directly, put it in .claude/
                file_path = claude_dir / "CLAUDE.md"
            elif file.filename.startswith(".claude/"):
                # Already has .claude/ prefix
                file_path = agent_dir / file.filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
            elif "/" in file.filename:
                # Handle subdirectories
                file_path = agent_dir / file.filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                file_path = agent_dir / file.filename
            
            # Write file
            content = await file.read()
            file_path.write_bytes(content)
        
        logger.info("agent_uploaded", name=name, files_count=len(files))
        
        return APIResponse(
            success=True,
            message=f"Agent '{name}' uploaded successfully",
            data={"path": str(agent_dir)}
        )
    except Exception as e:
        # Cleanup on error
        if agent_dir.exists():
            shutil.rmtree(agent_dir)
        raise HTTPException(500, f"Failed to upload agent: {str(e)}")


@router.delete("/agents/{agent_name}")
async def delete_agent(agent_name: str) -> APIResponse:
    """Delete a user agent (builtin agents cannot be deleted)."""
    
    # Only allow deleting user agents
    agent_dir = settings.user_agents_dir / agent_name
    
    if not agent_dir.exists():
        raise HTTPException(404, f"Agent '{agent_name}' not found")
    
    if not agent_dir.is_relative_to(settings.user_agents_dir):
        raise HTTPException(403, "Cannot delete builtin agents")
    
    shutil.rmtree(agent_dir)
    
    logger.info("agent_deleted", name=agent_name)
    
    return APIResponse(
        success=True,
        message=f"Agent '{agent_name}' deleted successfully"
    )


@router.get("/agents")
async def list_agents() -> List[AgentInfo]:
    """List all available agents (builtin + user)."""
    agents = []
    
    # Builtin sub-agents from .claude/agents/*.md
    builtin_agents_dir = settings.agents_dir
    if builtin_agents_dir.exists():
        for agent_file in builtin_agents_dir.glob("*.md"):
            # Extract description from frontmatter
            try:
                content = agent_file.read_text()
                description = ""
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        frontmatter = parts[1]
                        for line in frontmatter.split("\n"):
                            if line.startswith("description:"):
                                description = line.split(":", 1)[1].strip()
                                break
                
                agents.append(AgentInfo(
                    name=agent_file.stem,
                    agent_type=agent_file.stem,
                    description=description or f"{agent_file.stem} sub-agent",
                    is_builtin=True,
                    path=str(agent_file),
                ))
            except Exception:
                pass
    
    # User agents
    user_agents_dir = settings.user_agents_dir
    if user_agents_dir.exists():
        for agent_dir in user_agents_dir.iterdir():
            if agent_dir.is_dir() and (agent_dir / ".claude").exists():
                claude_dir = agent_dir / ".claude"
                description = _extract_agent_description(claude_dir)
                agents.append(AgentInfo(
                    name=agent_dir.name,
                    agent_type=agent_dir.name,
                    description=description,
                    is_builtin=False,
                    path=str(agent_dir),
                ))
    
    return agents


class AssetContent(BaseModel):
    """Content of a registry asset."""
    name: str
    type: str
    content: str


@router.get("/{asset_type}/{name}/content")
async def get_asset_content(asset_type: str, name: str) -> AssetContent:
    """Get the markdown content of an agent or skill."""
    if asset_type == "agents":
        # Check builtin
        path = settings.agents_dir / f"{name}.md"
        if not path.exists():
            # Check user
            path = settings.user_agents_dir / name / ".claude" / "CLAUDE.md"
            if not path.exists():
                # Try .md in user agents dir
                path = settings.user_agents_dir / f"{name}.md"
    elif asset_type == "skills":
        # Check builtin
        path = settings.skills_dir / name / "SKILL.md"
        if not path.exists():
            # Check user
            path = settings.user_skills_dir / name / "SKILL.md"
    else:
        raise HTTPException(400, "Invalid asset type")

    if not path or not path.exists():
        raise HTTPException(404, f"{asset_type[:-1].capitalize()} '{name}' not found")

    try:
        content = path.read_text()
        return AssetContent(name=name, type=asset_type[:-1], content=content)
    except Exception as e:
        raise HTTPException(500, f"Failed to read asset content: {str(e)}")


@router.put("/{asset_type}/{name}/content")
async def update_asset_content(asset_type: str, name: str, data: AssetContent) -> APIResponse:
    """Update the markdown content of an agent or skill."""
    if asset_type == "agents":
        # Check builtin
        path = settings.agents_dir / f"{name}.md"
        if not path.exists():
            # Check user
            path = settings.user_agents_dir / name / ".claude" / "CLAUDE.md"
            if not path.exists():
                 path = settings.user_agents_dir / f"{name}.md"
    elif asset_type == "skills":
        # Check builtin
        path = settings.skills_dir / name / "SKILL.md"
        if not path.exists():
            # Check user
            path = settings.user_skills_dir / name / "SKILL.md"
    else:
        raise HTTPException(400, "Invalid asset type")

    if not path or not path.exists():
        # If it doesn't exist, we might want to create it, but for now let's just 404
        raise HTTPException(404, f"{asset_type[:-1].capitalize()} '{name}' not found")

    try:
        path.write_text(data.content)
        return APIResponse(success=True, message=f"{asset_type[:-1].capitalize()} '{name}' updated successfully")
    except Exception as e:
        raise HTTPException(500, f"Failed to update asset content: {str(e)}")


def _extract_description(skill_md: Path) -> str:
    """Extract description from SKILL.md."""
    try:
        content = skill_md.read_text()
        lines = content.split('\n')
        # Find first non-empty line after title
        for i, line in enumerate(lines):
            if line.strip().startswith('#'):
                # Look for description in next few lines
                for j in range(i + 1, min(i + 5, len(lines))):
                    desc = lines[j].strip()
                    if desc and not desc.startswith('#'):
                        return desc[:200]
        return "No description available"
    except Exception:
        return "No description available"


def _extract_agent_description(claude_dir: Path) -> str:
    """Extract description from agent .claude directory."""
    claude_md = claude_dir / "CLAUDE.md"
    if claude_md.exists():
        return _extract_description(claude_md)
    return "No description available"
