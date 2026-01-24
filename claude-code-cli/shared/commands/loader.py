"""Load command definitions from YAML files.

This module loads and parses command definitions from YAML files,
converting them to typed CommandDefinition objects.

Usage:
    from shared.commands import get_loader
    
    loader = get_loader()
    commands = loader.load_all()
    
    # Get specific command
    approve_cmd = loader.get_command("approve")
    # Also works with aliases
    approve_cmd = loader.get_command("lgtm")
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional
import yaml
import logging

from ..models import CommandDefinition, CommandParameter
from ..enums import Platform

logger = logging.getLogger("command_loader")


class CommandLoader:
    """Load command definitions from YAML files.
    
    Attributes:
        commands_dir: Directory containing YAML command files
    
    Example:
        loader = CommandLoader()
        
        # Load all commands
        commands = loader.load_all()
        
        # Get specific command
        cmd = loader.get_command("approve")
        print(cmd.description)
        
        # Get command by alias
        cmd = loader.get_command("lgtm")  # Returns 'approve' command
    """
    
    def __init__(self, commands_dir: Optional[Path] = None):
        """Initialize loader.
        
        Args:
            commands_dir: Directory containing YAML files.
                         Defaults to the commands directory.
        """
        if commands_dir is None:
            commands_dir = Path(__file__).parent
        
        self.commands_dir = commands_dir
        self._cache: Optional[Dict[str, CommandDefinition]] = None
        self._alias_map: Optional[Dict[str, str]] = None
    
    def load_all(self) -> Dict[str, CommandDefinition]:
        """Load all command definitions.
        
        Returns:
            Dict mapping command names to definitions.
        """
        if self._cache is not None:
            return self._cache
        
        commands: Dict[str, CommandDefinition] = {}
        
        # Load main definitions file
        main_file = self.commands_dir / "definitions.yaml"
        if main_file.exists():
            commands.update(self._load_file(main_file))
        
        # Load any additional YAML files (for organization)
        for yaml_file in self.commands_dir.glob("*.yaml"):
            if yaml_file.name != "definitions.yaml":
                try:
                    commands.update(self._load_file(yaml_file))
                except Exception as e:
                    logger.warning(f"Failed to load {yaml_file}: {e}")
        
        self._cache = commands
        
        # Build alias map
        self._build_alias_map()
        
        logger.info(f"Loaded {len(commands)} commands")
        return commands
    
    def _load_file(self, path: Path) -> Dict[str, CommandDefinition]:
        """Load commands from a single YAML file.
        
        Args:
            path: Path to YAML file.
            
        Returns:
            Dict mapping command names to definitions.
        """
        with open(path, "r") as f:
            raw_data = yaml.safe_load(f) or {}
        
        commands: Dict[str, CommandDefinition] = {}
        
        for name, raw_cmd in raw_data.items():
            if not isinstance(raw_cmd, dict):
                continue
            
            try:
                # Parse parameters
                parameters: List[CommandParameter] = []
                for raw_param in raw_cmd.get("parameters", []):
                    parameters.append(CommandParameter(
                        name=raw_param.get("name", ""),
                        param_type=raw_param.get("type", "string"),
                        required=raw_param.get("required", False),
                        description=raw_param.get("description", ""),
                        default=raw_param.get("default"),
                    ))
                
                # Parse platforms
                platforms: List[Platform] = []
                raw_platforms = raw_cmd.get("platforms", ["all"])
                
                for p in raw_platforms:
                    if p == "all":
                        platforms = list(Platform)
                        break
                    try:
                        platforms.append(Platform(p))
                    except ValueError:
                        logger.warning(f"Unknown platform: {p}")
                
                commands[name] = CommandDefinition(
                    name=name,
                    aliases=raw_cmd.get("aliases", []),
                    description=raw_cmd.get("description", "").strip(),
                    usage=raw_cmd.get("usage", f"@agent {name}"),
                    examples=raw_cmd.get("examples", []),
                    parameters=parameters,
                    handler=raw_cmd.get("handler", f"handle_{name.replace('-', '_')}"),
                    platforms=platforms,
                    response_template=raw_cmd.get("response_template"),
                )
            except Exception as e:
                logger.error(f"Failed to parse command '{name}': {e}")
        
        return commands
    
    def _build_alias_map(self) -> None:
        """Build mapping from aliases to command names."""
        if self._cache is None:
            self.load_all()
        
        self._alias_map = {}
        
        for name, cmd in self._cache.items():
            # Primary name
            self._alias_map[name.lower()] = name
            
            # Handle hyphenated names (ci-status -> ci_status)
            normalized = name.replace("-", "_").lower()
            self._alias_map[normalized] = name
            
            # Aliases
            for alias in cmd.aliases:
                alias_lower = str(alias).lower()
                self._alias_map[alias_lower] = name
    
    def get_command(self, name: str) -> Optional[CommandDefinition]:
        """Get a specific command by name or alias.
        
        Args:
            name: Command name or alias.
            
        Returns:
            CommandDefinition if found, None otherwise.
        """
        if self._cache is None:
            self.load_all()
        
        name_lower = name.lower().strip()
        
        # Direct lookup
        if name_lower in self._alias_map:
            cmd_name = self._alias_map[name_lower]
            return self._cache.get(cmd_name)
        
        return None
    
    def get_alias_map(self) -> Dict[str, str]:
        """Get mapping from aliases to command names.
        
        Returns:
            Dict mapping aliases to command names.
        """
        if self._alias_map is None:
            self._build_alias_map()
        
        return self._alias_map.copy()
    
    def get_commands_for_platform(self, platform: Platform) -> List[CommandDefinition]:
        """Get commands available on a specific platform.
        
        Args:
            platform: Platform to filter by.
            
        Returns:
            List of commands available on the platform.
        """
        if self._cache is None:
            self.load_all()
        
        return [
            cmd for cmd in self._cache.values()
            if platform in cmd.platforms
        ]
    
    def invalidate_cache(self) -> None:
        """Clear the cache to force reload."""
        self._cache = None
        self._alias_map = None


# =============================================================================
# Global Loader Instance
# =============================================================================

_loader: Optional[CommandLoader] = None


def get_loader() -> CommandLoader:
    """Get global command loader instance.
    
    Returns:
        CommandLoader singleton.
    """
    global _loader
    if _loader is None:
        _loader = CommandLoader()
    return _loader
