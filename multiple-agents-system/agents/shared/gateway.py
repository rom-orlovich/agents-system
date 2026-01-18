"""
AgentCore Gateway
=================
Provides access to MCP tools and AgentCore services.
"""

import os
import json
import boto3
from typing import Any, Dict


class AgentCoreGateway:
    """Gateway for accessing AgentCore services and MCP tools."""
    
    def __init__(self):
        """Initialize the gateway."""
        self.bedrock_agent = boto3.client('bedrock-agent-runtime')
        self.secrets_manager = boto3.client('secretsmanager')
        
        self._tools: Dict[str, Any] = {}
        self._services: Dict[str, Any] = {}
    
    def get_tool(self, tool_name: str) -> 'MCPToolProxy':
        """Get an MCP tool proxy.
        
        Args:
            tool_name: Name of the MCP tool (e.g., 'github-mcp', 'jira-mcp')
            
        Returns:
            MCPToolProxy for invoking tool methods.
        """
        if tool_name not in self._tools:
            self._tools[tool_name] = MCPToolProxy(tool_name, self)
        return self._tools[tool_name]
    
    def get_service(self, service_name: str) -> 'AgentCoreService':
        """Get an AgentCore service.
        
        Args:
            service_name: Name of the service (e.g., 'code-interpreter')
            
        Returns:
            AgentCoreService for invoking service methods.
        """
        if service_name not in self._services:
            if service_name == 'code-interpreter':
                self._services[service_name] = CodeInterpreterService(self)
            else:
                self._services[service_name] = AgentCoreService(service_name, self)
        return self._services[service_name]
    
    def get_secret(self, secret_name: str) -> str:
        """Get a secret from Secrets Manager."""
        response = self.secrets_manager.get_secret_value(SecretId=secret_name)
        return response['SecretString']


class MCPToolProxy:
    """Proxy for invoking MCP tools."""
    
    def __init__(self, tool_name: str, gateway: AgentCoreGateway):
        """Initialize the tool proxy."""
        self.tool_name = tool_name
        self.gateway = gateway
        self.bedrock_agent = gateway.bedrock_agent
    
    def __getattr__(self, method_name: str):
        """Return async method wrapper for any attribute access."""
        async def method_wrapper(**kwargs):
            return await self._invoke_tool(method_name, kwargs)
        return method_wrapper
    
    async def _invoke_tool(self, method: str, params: dict) -> Any:
        """Invoke an MCP tool method."""
        response = self.bedrock_agent.invoke_agent(
            agentId=os.environ.get(f'{self.tool_name.upper().replace("-", "_")}_GATEWAY_ID'),
            sessionId='default',
            inputText=json.dumps({
                'tool': method,
                'parameters': params
            })
        )
        
        completion = response.get('completion', [])
        if completion:
            return json.loads(completion[0].get('text', '{}'))
        return {}


class AgentCoreService:
    """Base class for AgentCore services."""
    
    def __init__(self, service_name: str, gateway: AgentCoreGateway):
        """Initialize the service."""
        self.service_name = service_name
        self.gateway = gateway


class CodeInterpreterService(AgentCoreService):
    """Code interpreter service for running code safely."""
    
    def __init__(self, gateway: AgentCoreGateway):
        """Initialize the code interpreter."""
        super().__init__('code-interpreter', gateway)
        self.bedrock_agent = gateway.bedrock_agent
    
    async def execute(
        self,
        language: str,
        code: str,
        timeout_seconds: int = 300
    ) -> 'ExecutionResult':
        """Execute code in the sandbox.
        
        Args:
            language: Programming language (python, bash, javascript)
            code: Code to execute
            timeout_seconds: Maximum execution time
            
        Returns:
            ExecutionResult with stdout, stderr, and return_code
        """
        response = self.bedrock_agent.invoke_code_interpreter(
            codeInterpreterInput={
                'language': language,
                'code': code
            },
            timeoutSeconds=timeout_seconds
        )
        
        output = response.get('output', {})
        
        return ExecutionResult(
            stdout=output.get('stdout', ''),
            stderr=output.get('stderr', ''),
            return_code=output.get('returnCode', 0)
        )


class ExecutionResult:
    """Result of code execution."""
    
    def __init__(self, stdout: str, stderr: str, return_code: int):
        """Initialize the result."""
        self.stdout = stdout
        self.stderr = stderr
        self.return_code = return_code
    
    def __repr__(self):
        return f"ExecutionResult(return_code={self.return_code})"
