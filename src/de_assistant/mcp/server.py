from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MCPTool:
    name: str
    description: str
    handler: object


@dataclass
class MCPServer:
    tools: list[MCPTool] = field(default_factory=list)

    def register(self, tool: MCPTool) -> None:
        self.tools.append(tool)

    def list_tools(self) -> list[str]:
        return [tool.name for tool in self.tools]


def create_server() -> MCPServer:
    return MCPServer()
