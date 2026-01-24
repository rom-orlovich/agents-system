"""Container management API endpoints."""

import os
import psutil
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from core.database.redis_client import redis_client

router = APIRouter(prefix="/api/v2/container", tags=["container"])

# Allowlist of commands that can be executed
ALLOWED_COMMANDS = [
    "ls",
    "pwd",
    "whoami",
    "cat",
    "head",
    "tail",
    "grep",
    "find",
    "ps",
    "df",
    "du",
    "free",
    "uptime",
    "echo",
    "date",
    "which",
    "env",
]

# Allowlist of process names that can be killed
ALLOWED_KILL_PROCESSES = [
    "claude",
    "python",
    "node",
]


class ExecRequest(BaseModel):
    """Request to execute a command."""
    command: str = Field(..., description="Command to execute")
    timeout: int = Field(default=30, description="Timeout in seconds")


class ProcessInfo(BaseModel):
    """Process information."""
    pid: int
    name: str
    cpu_percent: float
    memory_mb: float
    status: str


class ResourceUsage(BaseModel):
    """Container resource usage."""
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    disk_percent: float


@router.get("/status", response_model=dict)
async def get_container_status():
    """Get container health status."""
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        
        healthy = cpu < 90 and memory.percent < 90 and disk.percent < 90
        
        return {
            "healthy": healthy,
            "status": "healthy" if healthy else "degraded",
            "cpu_percent": cpu,
            "memory_percent": memory.percent,
            "memory_mb": memory.used / (1024 * 1024),
            "disk_percent": disk.percent
        }
    except Exception as e:
        return {
            "healthy": False,
            "status": "error",
            "error": str(e)
        }


@router.get("/processes", response_model=dict)
async def list_processes():
    """List all running processes in the container."""
    processes = []
    
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'status']):
            try:
                info = proc.info
                processes.append({
                    "pid": info['pid'],
                    "name": info['name'],
                    "cpu_percent": info['cpu_percent'] or 0.0,
                    "memory_mb": (info['memory_info'].rss / (1024 * 1024)) if info['memory_info'] else 0.0,
                    "status": info['status']
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list processes: {str(e)}"
        )
    
    return {"processes": processes}


@router.get("/resources", response_model=dict)
async def get_resources():
    """Get container resource usage."""
    # Try to get from Redis cache first
    cached = await redis_client.get_container_resources()
    if cached:
        return {
            "cpu_percent": float(cached.get("cpu_percent", 0)),
            "memory_mb": float(cached.get("memory_mb", 0)),
            "memory_percent": float(cached.get("memory_percent", 0)),
            "disk_percent": float(cached.get("disk_percent", 0))
        }
    
    # Calculate fresh values
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        
        resources = {
            "cpu_percent": cpu,
            "memory_mb": memory.used / (1024 * 1024),
            "memory_percent": memory.percent,
            "disk_percent": disk.percent
        }
        
        # Cache in Redis
        await redis_client.set_container_resources(resources)
        
        return resources
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get resources: {str(e)}"
        )


@router.post("/processes/{pid}/kill", response_model=dict)
async def kill_process(pid: int):
    """Kill a process by PID. Only allowed for specific processes."""
    try:
        proc = psutil.Process(pid)
        proc_name = proc.name()
        
        # Check if process is in allowlist
        if not any(allowed in proc_name.lower() for allowed in ALLOWED_KILL_PROCESSES):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Process '{proc_name}' is not allowed to be killed. Only these processes can be killed: {ALLOWED_KILL_PROCESSES}"
            )
        
        proc.terminate()
        return {"success": True, "pid": pid, "action": "terminated"}
        
    except psutil.NoSuchProcess:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Process {pid} not found"
        )
    except psutil.AccessDenied:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied to kill process {pid}"
        )


@router.post("/exec", response_model=dict)
async def execute_command(request: ExecRequest):
    """Execute a command in the container. Only allowed commands."""
    import asyncio
    import shlex
    
    # Parse command to get base command
    try:
        parts = shlex.split(request.command)
        base_command = parts[0] if parts else ""
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid command format"
        )
    
    # Check if command is in allowlist
    if base_command not in ALLOWED_COMMANDS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Command '{base_command}' is not in allowlist. Allowed commands: {ALLOWED_COMMANDS}"
        )
    
    try:
        proc = await asyncio.create_subprocess_shell(
            request.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=request.timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail=f"Command timed out after {request.timeout} seconds"
            )
        
        return {
            "success": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": stdout.decode() if stdout else "",
            "stderr": stderr.decode() if stderr else ""
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute command: {str(e)}"
        )
