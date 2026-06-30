---
tags:
  - mcp
  - ia
  - agentes
created: 2026-06-28
---

# MCP Server — Interface para Agentes de IA

## Visao Geral

Servidor MCP (Model Context Protocol) que expõe as operacoes de NF-e como ferramentas consumiveis por agentes de IA (Claude Code, Cline, Copilot, etc.).

## Ferramentas (Tools)

| Ferramenta | Descricao | Input |
|-----------|-----------|-------|
| `gerar_nfe` | Gerar e enviar NFe | `registro: int` ou dados completos |
| `consultar_nfe` | Consultar situacao | `chave: str` |
| `cancelar_nfe` | Cancelar NFe | `chave: str`, `justificativa: str` |
| `inutilizar_nfe` | Inutilizar numeracao | `cnpj, modelo, serie, nIni, nFim, just` |
| `cce_nfe` | Carta de Correcao | `chave: str`, `correcao: str` |
| `status_sefaz` | Status SEFAZ | - |
| `validar_dados_nfe` | Validar dados sem enviar | dados JSON |
| `explicar_regra` | Explicar regra fiscal | `regra: str` (ex: "difal", "cst 20") |

## Recursos (Resources)

| URI | Descricao |
|-----|-----------|
| `nfe://regras/icms` | Tabela de CST/CSOSN ICMS |
| `nfe://regras/pis-cofins` | Tabela de CST PIS/COFINS |
| `nfe://regras/finalidade` | Finalidades da NFe |
| `nfe://regras/tpag` | Meios de pagamento |
| `nfe://templates/ini` | Template de INI |
| `nfe://status` | Status do servidor |

## Exemplo de Uso (com Claude Code / Cline)

O agente pode ser instruido a usar as ferramentas MCP:

```
"Use a ferramenta consultar_nfe para verificar a chave 352006... e
depois, se estiver pendente, cancele com justificativa adequada."
```

## Implementacao

```python
from mcp.server import Server
from mcp.types import Tool, TextContent

server = Server("nfe-hub")

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="gerar_nfe",
            description="Gera e envia uma NF-e para a SEFAZ",
            inputSchema={...}
        ),
        ...
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "gerar_nfe":
        return await gerar_nfe(arguments)
    ...
```

## Estrutura do Projeto

```
mcp/
├── __init__.py
├── server.py            ← Servidor MCP principal
├── tools/               ← Implementacao das ferramentas
│   ├── __init__.py
│   ├── gerar.py
│   ├── consultar.py
│   └── cancelar.py
└── resources/           ← Recursos disponiveis
    ├── __init__.py
    └── regras.py
```

## Dependencias

```
mcp
httpx
```

## Como Conectar

### Claude Code
```json
{
  "mcpServers": {
    "nfe-hub": {
      "command": "python",
      "args": ["/opt/nfelazarus/mcp/server.py"]
    }
  }
}
```

### Cline (VS Code)
Adicionar no `cline_mcp_settings.json`:
```json
{
  "nfe-hub": {
    "command": "python",
    "args": ["/opt/nfelazarus/mcp/server.py"]
  }
}
```

## Skills / Instrucoes para Agentes

Arquivo de skill para agentes que interagem com o sistema:

```markdown
# Skill: NF-e Hub

## Ferramentas Disponiveis
- `gerar_nfe(dados)` - Gera e envia NF-e
- `consultar_nfe(chave)` - Consulta situacao
- `cancelar_nfe(chave, justificativa)` - Cancela NF-e

## Fluxo Tipico
1. Validar dados antes de gerar
2. Gerar → Aguardar processamento
3. Se rejeitada, corrigir e regerar
4. Se autorizada, informar chave e DANFE

## Regras Importantes
- homologacao: ambiente=2, serie=800
- Producao: ambiente=1, serie do cadastro
- Cancelamento: justificativa minima 15 caracteres
```
