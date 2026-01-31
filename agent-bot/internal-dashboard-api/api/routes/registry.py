from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/registry", tags=["registry"])


class SkillInfo(BaseModel):
    name: str
    description: str
    is_builtin: bool
    has_scripts: bool
    path: str


class AgentInfo(BaseModel):
    name: str
    agent_type: str
    description: str
    is_builtin: bool
    path: str


class AssetContent(BaseModel):
    name: str
    type: str
    content: str


SKILLS_DIR = Path("/app/.claude/skills")
AGENTS_DIR = Path("/app/.claude/agents")
USER_SKILLS_DIR = Path("/data/config/skills")
USER_AGENTS_DIR = Path("/data/config/agents")


@router.get("/skills")
async def list_skills() -> list[SkillInfo]:
    skills = []

    if SKILLS_DIR.exists():
        for skill_dir in SKILLS_DIR.iterdir():
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

    if USER_SKILLS_DIR.exists():
        for skill_dir in USER_SKILLS_DIR.iterdir():
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


@router.get("/agents")
async def list_agents() -> list[AgentInfo]:
    agents = []

    if AGENTS_DIR.exists():
        for agent_file in AGENTS_DIR.glob("*.md"):
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
                    description=description or f"{agent_file.stem} agent",
                    is_builtin=True,
                    path=str(agent_file),
                ))
            except Exception:
                pass

    if USER_AGENTS_DIR.exists():
        for agent_dir in USER_AGENTS_DIR.iterdir():
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


@router.get("/{asset_type}/{name}/content")
async def get_asset_content(asset_type: str, name: str) -> AssetContent:
    if asset_type == "agents":
        path = AGENTS_DIR / f"{name}.md"
        if not path.exists():
            path = USER_AGENTS_DIR / name / ".claude" / "CLAUDE.md"
    elif asset_type == "skills":
        path = SKILLS_DIR / name / "SKILL.md"
        if not path.exists():
            path = USER_SKILLS_DIR / name / "SKILL.md"
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
async def update_asset_content(asset_type: str, name: str, data: AssetContent):
    if asset_type == "agents":
        path = AGENTS_DIR / f"{name}.md"
        if not path.exists():
            path = USER_AGENTS_DIR / name / ".claude" / "CLAUDE.md"
    elif asset_type == "skills":
        path = SKILLS_DIR / name / "SKILL.md"
        if not path.exists():
            path = USER_SKILLS_DIR / name / "SKILL.md"
    else:
        raise HTTPException(400, "Invalid asset type")

    if not path or not path.exists():
        raise HTTPException(404, f"{asset_type[:-1].capitalize()} '{name}' not found")

    try:
        path.write_text(data.content)
        return {"success": True, "message": f"{asset_type[:-1].capitalize()} updated"}
    except Exception as e:
        raise HTTPException(500, f"Failed to update: {str(e)}")


def _extract_description(skill_md: Path) -> str:
    try:
        content = skill_md.read_text()
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith('#'):
                for j in range(i + 1, min(i + 5, len(lines))):
                    desc = lines[j].strip()
                    if desc and not desc.startswith('#'):
                        return desc[:200]
        return "No description available"
    except Exception:
        return "No description available"


def _extract_agent_description(claude_dir: Path) -> str:
    claude_md = claude_dir / "CLAUDE.md"
    if claude_md.exists():
        return _extract_description(claude_md)
    return "No description available"
