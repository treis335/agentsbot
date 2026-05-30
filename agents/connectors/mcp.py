"""
agents/connectors/mcp.py — Model Context Protocol Support

Implementa um servidor MCP leve para comunicação entre agentes.
Baseado nos padrões do DeepSeek-TUI e LobeHub.
"""
import json
import os
import asyncio
from datetime import datetime
from typing import Optional, Callable, Any

class MCPServer:
    """Servidor MCP leve para comunicação entre agentes do ecossistema."""
    
    def __init__(self, name: str = "correoto-mcp"):
        self.name = name
        self.tools = {}
        self.resources = {}
        self._running = False
        
    def register_tool(self, name: str, handler: Callable, description: str = ""):
        """Regista uma ferramenta MCP."""
        self.tools[name] = {
            "handler": handler,
            "description": description,
            "registered_at": datetime.now().isoformat()
        }
        
    def register_resource(self, uri: str, handler: Callable, description: str = ""):
        """Regista um recurso MCP."""
        self.resources[uri] = {
            "handler": handler,
            "description": description,
            "registered_at": datetime.now().isoformat()
        }
        
    async def call_tool(self, name: str, params: dict = None) -> dict:
        """Chama uma ferramenta registada."""
        if name not in self.tools:
            return {"error": f"Tool '{name}' not found", "status": "error"}
        try:
            tool = self.tools[name]
            if asyncio.iscoroutinefunction(tool["handler"]):
                result = await tool["handler"](**(params or {}))
            else:
                result = tool["handler"](**(params or {}))
            return {"result": result, "status": "success", "tool": name}
        except Exception as e:
            return {"error": str(e), "status": "error", "tool": name}
    
    async def get_resource(self, uri: str) -> dict:
        """Obtém um recurso registado."""
        if uri not in self.resources:
            return {"error": f"Resource '{uri}' not found", "status": "error"}
        try:
            resource = self.resources[uri]
            if asyncio.iscoroutinefunction(resource["handler"]):
                result = await resource["handler"]()
            else:
                result = resource["handler"]()
            return {"result": result, "status": "success", "uri": uri}
        except Exception as e:
            return {"error": str(e), "status": "error", "uri": uri}
    
    def list_tools(self) -> list:
        """Lista todas as ferramentas registadas."""
        return [{"name": k, "description": v["description"]} for k, v in self.tools.items()]
    
    def list_resources(self) -> list:
        """Lista todos os recursos registados."""
        return [{"uri": k, "description": v["description"]} for k, v in self.resources.items()]


class MCPClient:
    """Cliente MCP para agentes se comunicarem com o servidor."""
    
    def __init__(self, server: MCPServer):
        self.server = server
        
    async def call(self, tool: str, params: dict = None) -> dict:
        """Chama uma ferramenta no servidor MCP."""
        return await self.server.call_tool(tool, params)
    
    async def get(self, uri: str) -> dict:
        """Obtém um recurso do servidor MCP."""
        return await self.server.get_resource(uri)


# Instância global do servidor MCP
_mcp_server = None

def get_mcp_server() -> MCPServer:
    """Obtém a instância global do servidor MCP."""
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = MCPServer()
    return _mcp_server
