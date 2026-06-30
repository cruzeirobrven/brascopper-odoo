import sys
from pathlib import Path
from datetime import datetime

_parent = Path(__file__).resolve().parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent

import subprocess
import json

from api.config import settings
from api.services.nfe_ini import _gerar_linhas_ini
from api.services.acbr_monitor import ACBrMonitorClient, ACBrMonitorError
from api.database import (
    buscar_erp_empresa, listar_erp_empresas,
    buscar_erp_cliente, buscar_erp_produto,
    buscar_erp_nota, buscar_erp_operacao,
)

server = Server("nfe-hub")


acbr: ACBrMonitorClient | None = None


def _get_acbr() -> ACBrMonitorClient:
    global acbr
    if acbr is None:
        acbr = ACBrMonitorClient(
            host=settings.acbr_host,
            port=settings.acbr_port,
            timeout=settings.acbr_timeout,
        )
    return acbr


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="gerar_nfe",
            description="Gera um arquivo INI de NF-e e envia para a SEFAZ via ACBrMonitor. "
                        "Retorna a chave de acesso da NF-e gerada.",
            inputSchema={
                "type": "object",
                "properties": {
                    "emitente": {"type": "object", "properties": {
                        "cnpj": {"type": "string"}, "ie": {"type": "string"},
                        "razao_social": {"type": "string"}, "logradouro": {"type": "string"},
                        "numero": {"type": "string"}, "bairro": {"type": "string"},
                        "municipio": {"type": "string"}, "uf": {"type": "string"},
                        "cep": {"type": "string"}, "cod_municipio": {"type": "integer"},
                        "fone": {"type": "string"}, "crt": {"type": "string"},
                        "certificado_serial": {"type": "string", "description": "Serial do certificado A1. Obrigatorio se multiempresa."},
                    }, "required": ["cnpj", "razao_social", "uf"]},
                    "destinatario": {"type": "object", "properties": {
                        "cnpj_cpf": {"type": "string"}, "ie": {"type": "string"},
                        "razao_social": {"type": "string"}, "logradouro": {"type": "string"},
                        "numero": {"type": "string"}, "bairro": {"type": "string"},
                        "municipio": {"type": "string"}, "uf": {"type": "string"},
                        "cep": {"type": "string"}, "cod_municipio": {"type": "integer"},
                        "fone": {"type": "string"}, "ind_ie_dest": {"type": "string"},
                    }, "required": ["cnpj_cpf", "razao_social", "uf"]},
                    "itens": {
                        "type": "array",
                        "items": {"type": "object", "properties": {
                            "produto": {"type": "string"}, "descricao": {"type": "string"},
                            "ncm": {"type": "string"}, "cfop": {"type": "string"},
                            "unidade": {"type": "string"}, "quantidade": {"type": "number"},
                            "valor_unitario": {"type": "number"}, "cst_icms": {"type": "string"},
                            "aliquota_icms": {"type": "number"},
                        }, "required": ["produto", "ncm", "cfop", "quantidade", "valor_unitario"]},
                    },
                    "tp_amb": {"type": "integer", "description": "1=producao, 2=homologacao", "default": 2},
                },
                "required": ["emitente", "destinatario", "itens"],
            },
        ),
        Tool(
            name="consultar_nfe",
            description="Consulta o status de uma NF-e na SEFAZ pela chave de acesso.",
            inputSchema={
                "type": "object",
                "properties": {
                    "chave": {"type": "string", "description": "Chave de acesso de 44 digitos"},
                },
                "required": ["chave"],
            },
        ),
        Tool(
            name="cancelar_nfe",
            description="Cancela uma NF-e na SEFAZ.",
            inputSchema={
                "type": "object",
                "properties": {
                    "chave": {"type": "string"},
                    "justificativa": {"type": "string"},
                },
                "required": ["chave", "justificativa"],
            },
        ),
        Tool(
            name="status_acbr",
            description="Verifica o status do ACBrMonitor.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="importar_dados",
            description="Importa dados do SQL Server (ERP) para o PostgreSQL local. "
                        "Tabelas disponiveis: empresas, clientes, produtos, notas, itens, parcelas, operacoes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tabelas": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista de tabelas para importar. Padrao: todas.",
                        "default": ["empresas", "clientes", "produtos", "notas", "itens", "parcelas", "operacoes"],
                    },
                },
            },
        ),
        Tool(
            name="buscar_empresa",
            description="Busca empresa (emitente) no banco local. Retorna dados completos com certificado serial.",
            inputSchema={
                "type": "object",
                "properties": {
                    "cnpj": {"type": "string", "description": "CNPJ da empresa"},
                    "codigo_erp": {"type": "integer", "description": "Codigo da empresa no ERP"},
                },
            },
        ),
        Tool(
            name="buscar_cliente",
            description="Busca cliente/destinatario no banco local por CNPJ/CPF, nome ou codigo ERP.",
            inputSchema={
                "type": "object",
                "properties": {
                    "cnpj_cpf": {"type": "string"},
                    "nome": {"type": "string"},
                    "codigo_erp": {"type": "integer"},
                    "limit": {"type": "integer", "default": 10},
                },
            },
        ),
        Tool(
            name="buscar_produto",
            description="Busca produto no banco local por codigo, descricao ou NCM.",
            inputSchema={
                "type": "object",
                "properties": {
                    "codigo": {"type": "string"},
                    "descricao": {"type": "string"},
                    "ncm": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                },
            },
        ),
        Tool(
            name="sincronizar_odoo",
            description="Sincroniza dados do ERP (PostgreSQL local) para o Odoo via SQL direto. "
                        "Rapido: ~160 registros/s. Tabelas: clientes, produtos.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tabelas": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista de tabelas para sincronizar. Padrao: todas.",
                        "default": ["clientes", "produtos"],
                    },
                },
            },
        ),
        Tool(
            name="buscar_nota",
            description="Busca nota fiscal no banco local (dados do ERP).",
            inputSchema={
                "type": "object",
                "properties": {
                    "registro": {"type": "integer"},
                    "nota": {"type": "integer"},
                    "serie": {"type": "string"},
                    "cnpj_cpf": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "gerar_nfe":
            return await _tool_gerar_nfe(arguments)
        elif name == "consultar_nfe":
            return await _tool_consultar_nfe(arguments)
        elif name == "cancelar_nfe":
            return await _tool_cancelar_nfe(arguments)
        elif name == "status_acbr":
            return await _tool_status_acbr()
        elif name == "importar_dados":
            return await _tool_importar_dados(arguments)
        elif name == "buscar_empresa":
            return await _tool_buscar_empresa(arguments)
        elif name == "buscar_cliente":
            return await _tool_buscar_cliente(arguments)
        elif name == "buscar_produto":
            return await _tool_buscar_produto(arguments)
        elif name == "sincronizar_odoo":
            return await _tool_sincronizar_odoo(arguments)
        elif name == "buscar_nota":
            return await _tool_buscar_nota(arguments)
        else:
            raise ValueError(f"Ferramenta desconhecida: {name}")
    except Exception as e:
        return [TextContent(type="text", text=f"ERRO: {e}")]


def _build_fatnot(arguments: dict) -> dict:
    e = arguments["emitente"]
    d = arguments["destinatario"]
    return {
        "REGISTRO": 0, "EMPRESA": 1, "NOTA": 0, "SERIE": "1",
        "MODELO": 55, "EMISSAO": datetime.now().strftime("%Y-%m-%d"),
        "SAIDA": datetime.now().strftime("%Y-%m-%d"),
        "TP_SAIDA_ENTR": "S", "SITUACAO": 0, "OPERACAO": "VENDA",
        "DESTINATARIO": d["cnpj_cpf"], "NOME": d["razao_social"],
        "CGC_CPF": d["cnpj_cpf"], "INSCRICAO_RG": d.get("ie", ""),
        "ENDERECO": d.get("logradouro", ""), "NUMERO": d.get("numero", ""),
        "COMPLEMENTO": "", "BAIRRO": d.get("bairro", ""),
        "CIDADE": d.get("municipio", ""), "ESTADO": d["uf"],
        "CEP": d.get("cep", ""), "CONSUMIDOR": "S", "VENDA_SITE": "N",
        "OBS_CORPO_NF": "", "P_ICMS_INTER_PART": 0, "P_ICMS_UF_DEST": 0,
        "V_FCP_UF_DEST": 0, "V_ICMS_UF_DEST": 0, "V_ICMS_UF_REMET": 0,
        "TDESCONTO": 0, "TFRETE": 0, "TSEGURO": 0, "TDESPESAS": 0,
        "BASE_ICMS": 0, "VALOR_ICMS": 0, "BASESUB": 0, "TICMSSUB": 0,
        "BASE_PIS": 0, "BASE_COFINS": 0, "TPIS": 0, "TCOFINS": 0,
        "TOTICMSDESONE": 0, "VLR_II": 0, "TSERVICO": 0,
        "INSCRICAO_SUFRAMA": "", "INDIEDEST": 1, "PRESENCIAL": "1",
        "VENDAINT": "0", "REVENDA": "N", "CONTRIBUINTE": "",
        "PRODUTO": 0,
    }


def _build_cademp(e: dict) -> dict:
    return {
        "EMPRESA": 1, "NOME": e["razao_social"], "TIPO_INSCRICAO": 1,
        "CNPJ": e["cnpj"], "INSCRICAO_FEDERAL": e["cnpj"],
        "INSCRICAO_ESTADUAL": e.get("ie", ""),
        "ENDERECO": e.get("logradouro", ""), "NUMERO": e.get("numero", ""),
        "COMPLEMENTO": "", "BAIRRO": e.get("bairro", ""),
        "CIDADE": e.get("municipio", ""), "ESTADO": e["uf"],
        "CEP": e.get("cep", ""), "FONE": e.get("fone", ""),
        "COD_MUN_IBGE": str(e.get("cod_municipio", "")),
        "MUNICIPIO_IBGE": e.get("municipio", ""),
        "SIMPLES": 1 if e.get("crt", "3") == "1" else 3,
        "EMAIL": "",
        "CERTIFICADO_SERIAL": e.get("certificado_serial", ""),
    }


def _build_cadcli(d: dict) -> dict:
    return {
        "CLIENTE": d["cnpj_cpf"],
        "COD_MUN_IBGE": str(d.get("cod_municipio", "")),
        "CIDADE": d.get("municipio", ""), "ESTADO": d["uf"],
        "ENDERECO": d.get("logradouro", ""), "NUMERO": d.get("numero", ""),
        "COMPLEMENTO": "", "BAIRRO": d.get("bairro", ""),
        "CEP": d.get("cep", ""), "CGC_CPF": d["cnpj_cpf"],
        "INSCRICAO_RG": d.get("ie", ""), "FONE": d.get("fone", ""),
        "PAIS": "1058", "NOME_PAIS": "BRASIL",
    }


def _build_itens(raw: list) -> list[dict]:
    itens = []
    for i, item in enumerate(raw):
        qtd = float(item["quantidade"])
        vun = float(item["valor_unitario"])
        vtot = qtd * vun
        itens.append({
            "ITEM": i + 1, "PRODUTO": item.get("produto", ""),
            "DESCRICAO": item.get("descricao", item.get("produto", "")),
            "QUANTIDADE": qtd, "UNIDADE": item.get("unidade", "UN"),
            "VALOR": vun, "TPRODUTO": vtot, "CFOP": item["cfop"],
            "NCM": item["ncm"], "CEST": item.get("cest", ""),
            "ORIGEM": item.get("origem", "0"),
            "TIPO_ITEM": item.get("tipo_item", "00"),
            "DESCONTO": 0, "OUTRAS": 0, "DESPESAS": 0,
            "ICMS_CST": item.get("cst_icms", "00"),
            "PICMS": float(item.get("aliquota_icms", 0)),
            "BASE_ICMS": 0, "TICMS": 0, "REDUCAO": 0,
            "CST_IPI": "99", "PIPI": 0, "BASE_IPI": 0, "TIPI": 0,
            "CST_PIS": "07", "PPIS": 0, "BASE_PIS": 0, "TPIS": 0,
            "CST_COFINS": "07", "PCOFINS": 0, "BASE_COFINS": 0,
            "TCOFINS": 0, "IBPT_VLR_IMPOSTO": 0,
            "VALOR_CALCULO": vtot, "DCIMAIS_CALCULO": qtd,
            "UNID_COM": item.get("unidade", "UN"),
            "UNID_TRIB": item.get("unidade", "UN"),
            "DSC_CADASTRO": (item.get("descricao", "") or item.get("produto", ""))[:120],
            "ACESSORIOS": "", "PEDIDO_CLIENTE": "", "ITEM_PED_CLIENTE": 0,
            "EX_TIPI": "", "VLICMSDESON": 0, "MOTDESON": "",
            "PCRED_SN": 0, "VCRED_ICMS_SN": 0, "PORC_IVA": 0,
            "ICMS_ST": 0, "TICMS_RETIDO": 0, "BASE_ICMS_ST": 0,
            "PERC_DEV": 0,
            "P_FCP_UF_DEST": 0, "V_FCP_UF_DEST": 0,
            "P_ICMS_INTER": 0, "V_ICMS_UF_DEST": 0, "V_ICMS_UF_REMET": 0,
            "VLR_IMP": 0, "COD_BENEF": "",
        })
    return itens


async def _tool_gerar_nfe(arguments: dict) -> list[TextContent]:
    fatnot = _build_fatnot(arguments)
    cademp = _build_cademp(arguments["emitente"])
    cadcli = _build_cadcli(arguments["destinatario"])
    itens = _build_itens(arguments["itens"])
    fatope = {"DESCRICAO_NF": "VENDA", "MOVIMENTACAO": 1, "FIN_DEVOLUCAO": "N", "ACORDO_DIF_ALIQ": "N"}
    fatfin = []
    transp = None

    linhas, nota, serie, cnf, chave = _gerar_linhas_ini(
        fatnot=fatnot, cademp=cademp, cadcli=cadcli,
        fatope=fatope, itens=itens, fatfin=fatfin,
        transp=transp, cod_benef_map={},
        tp_amb=arguments.get("tp_amb", 2),
    )

    client = _get_acbr()
    cert_serial = cademp.get("CERTIFICADO_SERIAL") or settings.certificado_serial
    if cert_serial:
        client.set_certificado(cert_serial)
    resposta = client.criar_enviar_nfe("\r\n".join(linhas))

    return [TextContent(type="text", text=f"Chave: {chave}\nResposta: {resposta}")]


async def _tool_consultar_nfe(arguments: dict) -> list[TextContent]:
    client = _get_acbr()
    resposta = client.consultar(arguments["chave"])
    return [TextContent(type="text", text=resposta)]


async def _tool_cancelar_nfe(arguments: dict) -> list[TextContent]:
    client = _get_acbr()
    resposta = client.cancelar(arguments["chave"], arguments["justificativa"])
    return [TextContent(type="text", text=resposta)]


async def _tool_importar_dados(arguments: dict) -> list[TextContent]:
    script = str(Path(__file__).resolve().parent.parent / "scripts/migracao/importar_sqlserver.py")
    tabelas = arguments.get("tabelas", [])
    cmd = [sys.executable, script]
    if tabelas:
        cmd.extend(["--tabelas"] + tabelas)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        saida = result.stdout or ""
        if result.stderr:
            saida += f"\nSTDERR:\n{result.stderr}"
        if result.returncode != 0:
            saida = f"ERRO (codigo {result.returncode}):\n{saida}"
    except subprocess.TimeoutExpired:
        saida = "ERRO: importacao excedeu 5 minutos"
    except Exception as e:
        saida = f"ERRO: {e}"

    return [TextContent(type="text", text=saida)]


async def _tool_sincronizar_odoo(arguments: dict) -> list[TextContent]:
    script = str(Path(__file__).resolve().parent.parent / "scripts/migracao/sincronizar_odoo.py")
    tabelas = arguments.get("tabelas", [])
    cmd = [sys.executable, script]
    if tabelas:
        cmd.extend(["--tabelas"] + tabelas)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        saida = result.stdout or ""
        if result.stderr:
            saida += f"\nSTDERR:\n{result.stderr}"
        if result.returncode != 0:
            saida = f"ERRO (codigo {result.returncode}):\n{saida}"
    except subprocess.TimeoutExpired:
        saida = "ERRO: sincronizacao excedeu 10 minutos"
    except Exception as e:
        saida = f"ERRO: {e}"

    return [TextContent(type="text", text=saida)]


async def _tool_status_acbr() -> list[TextContent]:
    try:
        client = _get_acbr()
        status = client.status()
        return [TextContent(type="text", text=f"ACBrMonitor OK: {status}")]
    except ACBrMonitorError as e:
        return [TextContent(type="text", text=f"ACBrMonitor ERRO: {e}")]


async def _tool_buscar_empresa(arguments: dict) -> list[TextContent]:
    cnpj = arguments.get("cnpj")
    codigo = arguments.get("codigo_erp")
    if codigo:
        dados = buscar_erp_empresa(codigo_erp=codigo)
    elif cnpj:
        dados = buscar_erp_empresa(cnpj=cnpj)
    else:
        dados = listar_erp_empresas()
    return [TextContent(type="text", text=json.dumps(
        dados if isinstance(dados, list) else [dados] if dados else [],
        indent=2, default=str, ensure_ascii=False,
    ))]


async def _tool_buscar_cliente(arguments: dict) -> list[TextContent]:
    dados = buscar_erp_cliente(
        cnpj_cpf=arguments.get("cnpj_cpf"),
        nome=arguments.get("nome"),
        codigo_erp=arguments.get("codigo_erp"),
        limit=arguments.get("limit", 10),
    )
    return [TextContent(type="text", text=json.dumps(
        dados, indent=2, default=str, ensure_ascii=False,
    ))]


async def _tool_buscar_produto(arguments: dict) -> list[TextContent]:
    dados = buscar_erp_produto(
        codigo=arguments.get("codigo"),
        descricao=arguments.get("descricao"),
        ncm=arguments.get("ncm"),
        limit=arguments.get("limit", 10),
    )
    return [TextContent(type="text", text=json.dumps(
        dados, indent=2, default=str, ensure_ascii=False,
    ))]


async def _tool_buscar_nota(arguments: dict) -> list[TextContent]:
    dados = buscar_erp_nota(
        registro=arguments.get("registro"),
        nota=arguments.get("nota"),
        serie=arguments.get("serie"),
        cnpj_cpf=arguments.get("cnpj_cpf"),
        limit=arguments.get("limit", 10),
    )
    return [TextContent(type="text", text=json.dumps(
        dados, indent=2, default=str, ensure_ascii=False,
    ))]


async def run():
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="nfe-hub",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
