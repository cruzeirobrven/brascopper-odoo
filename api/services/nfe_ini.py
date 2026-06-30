"""Gera INI temporario de NF-e para envio ao ACBrMonitor.

Implementa as mesmas regras de TFFATNFE.Criar_NFE sem dependencia de componentes
ACBr ou form Delphi. O arquivo INI gerado e lido pelo ACBrMonitor via comando
NFE.CriarEnviarNFe (ACBR_NFE_SEND_TEMPLATE).

Cobertura por secao do INI:
  Identificacao  — finNFe (finalidade), tpNF, idDest, indPres, VendaInt
  Emitente       — CRT, xFant, todos os campos de endereco
  Destinatario   — ISUF, indIEDest, todos os campos
  Produto        — vUnCom via VALOR_CALCULO/DCIMAIS_CALCULO, IndTot, vDesc, vOutro, vFrete
  ICMS           — orig, CST/CSOSN, ST (pMVAST/vBCST/pICMSST/vICMSST), reducao,
                   desonerado, credito SN, FCP-ST
  ICMSUFDest     — difal interestadual (P_ICMS_INTER_PART)
  IPI/PIS/COFINS — CST, aliquota, base, valor
  Total          — vTotTrib (IBPT), vICMSDeson, vII, FCP, difal
  Transportador  — modFrete da FATTRANSP, dados transportadora, placa, volumes
  Cobr/Dup       — cabecalho fatura + duplicatas
  pag            — TIPO_VENC -> tPag (boleto=15, credito=03, debito=04, cheque=02, outros=99)
  InfAdic        — OBS_CORPO_NF

Nao implementado (raridade ou 2027+):
  DI/adi (importacao), Exportacao, Retirada, Entrega, AutXml, NFref, Reforma Tributaria IBS/CBS/IS
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import re




TMP_DIR = Path(__file__).resolve().parents[1] / "tmp" / "nfe"

# FATFIN.TIPO_VENC -> tPag (codigo de meio de pagamento da NF-e)
_TIPO_VENC_TPAG: dict[int, str] = {
    1: "15",   # prazo/boleto
    2: "15",   # a vista boleto
    3: "15",   # cheque pre (tratado como boleto)
    4: "15",   # outros boleto
    5: "15",   # duplicata mercantil
    7: "03",   # cartao de credito
    8: "04",   # cartao de debito
    9: "02",   # cheque
    10: "02",  # cheque pre-datado
    11: "99",  # outros
}

# FATTRANSP.TRANSPORTE -> modFrete
_TRANSPORTE_MODFRETE: dict[int, str] = {
    1: "0",  # emitente (CIF)
    2: "1",  # destinatario (FOB)
    3: "2",  # terceiros
    4: "3",  # remetente
    5: "4",  # destinatario
    9: "9",  # sem frete
}


# ──────────────────────────────────────────────────────────────────────────────
# Tipos
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class NFeIniGerado:
    path: Path
    chave_acesso: str = ""
    numero: int = 0
    serie: int = 0
    certificado_serial: str = ""


def _gerar_chave_acesso(
    uf: str, data_emissao: str, cnpj: str,
    modelo: str, serie: str, numero: str,
    tp_emis: str = "1",
) -> str:
    dig_uf = _digitos(uf)[:2] or "35"
    if isinstance(data_emissao, str):
        try:
            dt = datetime.strptime(data_emissao, "%d/%m/%Y")
        except ValueError:
            try:
                dt = datetime.strptime(data_emissao[:10], "%Y-%m-%d")
            except ValueError:
                dt = datetime.now()
    else:
        dt = data_emissao or datetime.now()
    ano = str(dt.year % 100).zfill(2)
    mes = str(dt.month).zfill(2)
    cnpj_base = _digitos(cnpj)[:14].zfill(14)
    mod = _digitos(modelo)[:2].zfill(2)
    serie_pad = _digitos(serie)[:3].zfill(3)
    nNF = _digitos(numero)[:9].zfill(9)
    tpEmis = tp_emis
    chave_sem_dv = f"{dig_uf}{ano}{mes}{cnpj_base}{mod}{serie_pad}{nNF}{tpEmis}"
    peso = 2
    soma = 0
    for char in reversed(chave_sem_dv):
        soma += int(char) * peso
        peso += 1
        if peso > 9:
            peso = 2
    resto = soma % 11
    dv = 0 if resto < 2 else 11 - resto
    return f"{chave_sem_dv}{dv}"


# ──────────────────────────────────────────────────────────────────────────────
# Helpers de formatacao
# ──────────────────────────────────────────────────────────────────────────────

def _texto(valor, limite: int | None = None) -> str:
    texto = "" if valor is None else str(valor).strip()
    if limite is not None:
        texto = texto[:limite]
    return texto

def _digitos(valor) -> str:
    """Extrai apenas digitos (0-9) de um valor."""
    return re.sub(r"\D", "", str(valor or ""))

def _inteiro(valor, padrao=0) -> int:
    """Converte valor para int; retorna padrao se invalido."""
    try:
        return int(str(valor or padrao).strip())
    except (ValueError, TypeError):
        s = _digitos(valor)
        return int(s) if s else padrao

def _decimal(valor, casas: int | None = None) -> Decimal:
    """Converte valor para Decimal."""
    d = Decimal(str(valor or 0))
    if casas is not None:
        fmt = "0." + "0" * casas
        d = d.quantize(Decimal(fmt), rounding=ROUND_HALF_UP)
    return d

def _decimal_str(valor, casas: int = 2) -> str:
    """Formata valor Decimal como string com N casas decimais."""
    fmt = "0." + "0" * casas
    return str(_decimal(valor).quantize(Decimal(fmt), rounding=ROUND_HALF_UP))

def _serie_ini(fatnot: dict) -> str:
    """Retorna a serie para o INI (1 se for 0)."""
    serie = _inteiro(fatnot.get("SERIE"), padrao=0)
    return str(serie) if serie else "1"

def _bool_s(valor) -> bool:
    return str(valor or "").strip().upper() == "S"

def _data_br(valor) -> str:
    if valor is None:
        return datetime.now().strftime("%d/%m/%Y")
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y")
    try:
        dt = datetime.strptime(str(valor)[:10], "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return datetime.now().strftime("%d/%m/%Y")


# ──────────────────────────────────────────────────────────────────────────────
# Regras de negocio
# ──────────────────────────────────────────────────────────────────────────────
def _data_emissao_ini(fatnot: dict, tp_amb: int = 1) -> str:
    emissao = fatnot.get("EMISSAO")
    if emissao:
        dt = emissao if isinstance(emissao, datetime) else datetime.strptime(str(emissao)[:10], "%Y-%m-%d")
    else:
        dt = datetime.now()
    # Formato brasileiro (DD/MM/AAAA HH:NN:SS) aceito pelo ACBrMonitorPLUS
    return dt.strftime("%d/%m/%Y %H:%M:%S")



def _data_saida_ini(fatnot: dict) -> str:
    """Retorna dhSaiEnt formatado ou data/hora atual."""
    saida = fatnot.get("DATA_SAIDA")
    if saida:
        dt = saida if isinstance(saida, datetime) else datetime.strptime(str(saida)[:10], "%Y-%m-%d")
    else:
        dt = datetime.now()
    return dt.strftime("%d/%m/%Y %H:%M:%S")

def _crt(cademp: dict) -> str:
    return "1" if _inteiro(cademp.get("SIMPLES")) == 1 else "3"


def _documento_emitente(cademp: dict) -> str:
    tipo = _inteiro(cademp.get("TIPO_INSCRICAO"), padrao=1)
    if tipo == 1:
        return _digitos(cademp.get("INSCRICAO_FEDERAL") or cademp.get("CNPJ"))
    return _digitos(cademp.get("CNPJ") or cademp.get("INSCRICAO_FEDERAL"))


def _ind_ie_dest(fatnot: dict) -> str:
    """1=contribuinte c/IE, 2=contribuinte isento, 9=nao contribuinte/PF."""
    documento = _digitos(fatnot.get("CGC_CPF"))
    if len(documento) == 11:
        return "9"
    ie = _digitos(fatnot.get("INSCRICAO_RG") or "")
    indiedest = _inteiro(fatnot.get("INDIEDEST"))
    if indiedest in (1, 2):
        return str(indiedest)
    return "1" if ie else "9"


def _id_dest(fatnot: dict, estado_empresa: str) -> str:
    """1=intraestadual, 2=interestadual, 3=exterior."""
    uf_dest = _texto(fatnot.get("ESTADO") or fatnot.get("DEST_UF"), 2).upper()
    uf_emit = _texto(estado_empresa, 2).upper()
    if uf_dest == "EX":
        return "3"
    if uf_dest and uf_dest != uf_emit:
        return "2"
    return "1"


def _ind_pres(fatnot: dict) -> str:
    """1=presencial, 2=internet, 9=outros."""
    venda_site = _texto(fatnot.get("VENDA_SITE")).upper()
    presencial = _texto(fatnot.get("PRESENCIAL"))
    vendaint = _texto(fatnot.get("VENDAINT"))
    if vendaint == "1":
        return "1"
    if venda_site == "S" or presencial == "2":
        return "2"
    return "1"


def _tp_nf(fatnot: dict, fatope: dict) -> str:
    """0=entrada, 1=saida."""
    tp_saida = _inteiro(fatnot.get("TP_SAIDA_ENTR"), padrao=1)
    if tp_saida == 2:
        return "0"
    movimentacao = _inteiro(fatope.get("MOVIMENTACAO"), padrao=1)
    return "0" if movimentacao == 2 else "1"


def _fin_nfe(fatope: dict, itens: list[dict]) -> str:
    """1=normal, 2=complementar, 3=ajuste, 4=devolucao."""
    if _bool_s(fatope.get("FIN_DEVOLUCAO")):
        return "4"
    for item in itens:
        tipo = _inteiro(item.get("TIPO_ITEM"))
        if tipo in (5, 8):
            return "2"
        if tipo == 9:
            return "3"
    return "1"


def _ind_tot(item: dict) -> str:
    """1=compoe total, 0=nao compoe (TIPO_ITEM 5/8/9)."""
    return "0" if _inteiro(item.get("TIPO_ITEM")) in (5, 8, 9) else "1"


def _vuncom(item: dict) -> Decimal:
    """Valor unitario preciso via VALOR_CALCULO/DCIMAIS_CALCULO ou fallback VALOR."""
    calc = _decimal(item.get("VALOR_CALCULO"), 0)
    dcim = _decimal(item.get("DCIMAIS_CALCULO"), 0)
    if calc > 0 and dcim > 0:
        return (calc / dcim).quantize(Decimal("1." + "0" * 10), rounding=ROUND_HALF_UP)
    return _decimal(item.get("VALOR"), 10)


def _cst_icms(item: dict) -> str:
    for chave in ("ICMS_CST", "CCF"):
        valor = _texto(item.get(chave)).replace(".", "").replace("-", "")









        if valor in ("00", "10", "20", "30", "40", "41", "50", "51", "60", "70", "90"):
            return valor



def _cfop(cfop) -> str:
    """Retorna CFOP formatado com 4 digitos."""
    return str(_inteiro(cfop)).zfill(4)

def _csosn(item: dict) -> str:
    """Retorna CSOSN (3 digitos) para Simples Nacional baseado no CST."""
    cst = _texto(item.get("ICMS_CST")).replace(".", "").replace("-", "")
    _map = {
        "00": "101",
        "10": "201",
        "20": "201",
        "30": "102",
        "40": "400",
        "41": "400",
        "50": "400",
        "51": "400",
        "60": "500",
        "70": "203",
        "90": "900",
    }
    return _map.get(cst, "900")

def _tipo_destino(emitente_uf: str, destinatario_uf: str) -> str:
    emitente = _texto(emitente_uf, 2).upper()
    destinatario = _texto(destinatario_uf, 2).upper()
    if not destinatario or destinatario == emitente:
        return "1"
    return "2"


# ──────────────────────────────────────────────────────────────────────────────
# Queries
# ──────────────────────────────────────────────────────────────────────────────

def _query_uma_linha(cursor, sql: str, params: list, mensagem: str) -> dict:
    cursor.execute(sql, params)
    row = cursor.fetchone()
    if not row:
        raise ValueError(mensagem)

    return dict(zip([d[0] for d in cursor.description], row))


def _query_varias_linhas(cursor, sql: str, params: list) -> list[dict]:
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    if not rows:
        return []
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in rows]


def _query_transportadora(cursor, registro: int) -> dict | None:
    """Tenta buscar dados de transporte da FATNOT (embutidos). Retorna None se nao existir."""
    try:
        cursor.execute(
            """
            SELECT TOP 1
                ISNULL(TRANSPORTE, 9)         AS TRANSPORTE,
                ISNULL(TRANS_NOME, '')        AS TRANS_NOME,
                ISNULL(TRANS_CGC, '')         AS TRANS_CGC,
                ISNULL(TRANS_INSCR, '')       AS TRANS_INSCR,
                ISNULL(TRANS_ENDER, '')       AS TRANS_ENDER,
                ISNULL(TRANS_CIDADE, '')      AS TRANS_CIDADE,
                ISNULL(TRANS_ESTADO, '')      AS TRANS_ESTADO,
                ISNULL(PLACA, '')             AS PLACA,
                ISNULL(PLACA_ESTADO, '')      AS PLACA_ESTADO,
                ISNULL(VOL_QUANTIDADE, 0)     AS VOL_QUANTIDADE,
                ISNULL(VOL_ESPECIE, '')       AS VOL_ESPECIE,
                ''                            AS VOL_MARCA,
                ''                            AS VOL_NUMERO,
                ISNULL(PESO_LIQUIDO, 0)       AS PESO_LIQUIDO,
                ISNULL(PESO_BRUTO, 0)         AS PESO_BRUTO
            FROM FATNOT
            WHERE REGISTRO = ?
            """,
            [registro],
        )
        row = cursor.fetchone()
        if row:
            return dict(zip([d[0] for d in cursor.description], row))
    except Exception:
        pass
    return None


def _query_cod_benef(cursor, registro: int) -> dict[int, str]:
    """Tenta buscar COD_BENEF de FATITN — coluna opcional (NT 2026)."""
    try:
        cursor.execute(
            "SELECT ITEM, ISNULL(COD_BENEF, '') AS COD_BENEF FROM FATITN WHERE REGISTRO = ?",
            [registro],
        )
        return {row[0]: str(row[1] or "").strip() for row in cursor.fetchall()}
    except Exception:
        return {}


# ──────────────────────────────────────────────────────────────────────────────
# Geracao do INI
# ──────────────────────────────────────────────────────────────────────────────

def _gerar_linhas_ini(
    fatnot: dict,
    cademp: dict,
    cadcli: dict,
    fatope: dict,
    itens: list[dict],
    fatfin: list[dict],
    transp: dict | None,
    cod_benef_map: dict[int, str] | None = None,
    tp_amb: int = 1,
) -> tuple[list[str], int, int, int, str]:
    # ──────────────────────────────────────────────────────────────────────────
    # Valores derivados
    # ──────────────────────────────────────────────────────────────────────────
    nota = _inteiro(fatnot.get("NOTA"))
    serie = _serie_ini(fatnot)
    emitente_cnpj = _documento_emitente(cademp)
    destinatario_cnpj = _digitos(fatnot.get("CGC_CPF") or cadcli.get("CGC_CPF"))

    if not emitente_cnpj:
        raise ValueError("CADEMP esta sem CNPJ valido para gerar o INI.")
    if not destinatario_cnpj:
        raise ValueError("CADCLI esta sem CNPJ valido para gerar o INI.")

    emitente_cmun = _digitos(cademp.get("COD_MUN_IBGE") or cademp.get("MUNICIPIO_IBGE"))
    destinatario_cmun = _digitos(cadcli.get("COD_MUN_IBGE"))
    if not emitente_cmun:
        raise ValueError("CADEMP esta sem COD_MUN_IBGE.")
    if not destinatario_cmun:
        raise ValueError("CADCLI esta sem COD_MUN_IBGE.")

    regime_simples = _crt(cademp) == "1"
    fin_nfe = _fin_nfe(fatope, itens)
    tp_nf = _tp_nf(fatnot, fatope)
    id_dest = _id_dest(fatnot, cademp.get("ESTADO") or "")
    ind_pres = _ind_pres(fatnot)
    ind_final = "1" if _texto(fatnot.get("CONSUMIDOR")).upper() == "S" else "0"
    nat_op = _texto(fatope.get("DESCRICAO_NF") or "VENDA", 60)

    # cNF diferente de nNF (RN-006)
    cnf = _inteiro(fatnot.get("REGISTRO")) % 100_000_000 or 1
    if cnf == nota:
        cnf = (cnf % 99_999_999) + 1

    # Acumuladores de totais
    total_prod = Decimal("0.00")
    total_bc_icms = Decimal("0.00")
    total_icms = Decimal("0.00")
    total_bc_st = Decimal("0.00")
    total_st = Decimal("0.00")
    total_bc_ipi = Decimal("0.00")
    total_ipi = Decimal("0.00")
    total_bc_pis = Decimal("0.00")
    total_pis = Decimal("0.00")
    total_bc_cofins = Decimal("0.00")
    total_cofins = Decimal("0.00")
    total_bc_icms_xml = Decimal("0.00")
    total_icms_xml = Decimal("0.00")
    total_bc_st_xml = Decimal("0.00")
    total_st_xml = Decimal("0.00")
    total_tot_trib = Decimal("0.00")
    total_desconto = Decimal("0.00")

    # ──────────────────────────────────────────────────────────────────────────
    # [Identificacao]
    # ──────────────────────────────────────────────────────────────────────────
    linhas: list[str] = [
        "[Identificacao]",
        f"cNF={cnf:08d}",
        f"natOp={nat_op}",
        "mod=55",
        f"serie={serie}",
        f"nNF={nota}",
        f"dhEmi={_data_emissao_ini(fatnot, tp_amb=tp_amb)}",
        f"dhSaiEnt={_data_saida_ini(fatnot)}",
        f"tpNF={tp_nf}",
        f"idDest={id_dest}",
        f"cMunFG={emitente_cmun}",
        "tpImp=1",
        "tpEmis=1",
        f"tpAmb={tp_amb}",
        f"finNFe={fin_nfe}",
        f"indFinal={ind_final}",
        f"indPres={ind_pres}",
        "procEmi=0",
        "verProc=0.2.0",
        "",
    ]

    # ──────────────────────────────────────────────────────────────────────────
    # [Emitente]
    # ──────────────────────────────────────────────────────────────────────────
    nome_emit = _texto(cademp.get("NOME"), 60)
    linhas += [
        "[Emitente]",
        f"CNPJCPF={emitente_cnpj}",
        f"xNome={nome_emit}",
        f"xFant={nome_emit}",
        f"IE={_digitos(cademp.get('INSCRICAO_ESTADUAL'))}",
        f"CRT={_crt(cademp)}",
        f"xLgr={_texto(cademp.get('ENDERECO'), 60)}",
        f"nro={_texto(cademp.get('NUMERO')) or 'S/N'}",
        f"xCpl={_texto(cademp.get('COMPLEMENTO'), 60)}",
        f"xBairro={_texto(cademp.get('BAIRRO'), 60)}",
        f"cMun={emitente_cmun}",
        f"xMun={_texto(cademp.get('CIDADE'), 60)}",
        f"UF={_texto(cademp.get('ESTADO'), 2)}",
        f"CEP={_digitos(cademp.get('CEP'))}",
        "cPais=1058",
        "xPais=BRASIL",
        f"fone={_digitos(cademp.get('FONE'))}",
        "",
    ]

    # ──────────────────────────────────────────────────────────────────────────
    # [Destinatario]
    # ──────────────────────────────────────────────────────────────────────────
    ind_ie_dest = _ind_ie_dest(fatnot)
    linhas += [
        "[Destinatario]",
        f"CNPJCPF={destinatario_cnpj}",
        f"xNome={_texto(fatnot.get('NOME'), 60)}",
        f"indIEDest={ind_ie_dest}",
    ]

    suframa = _digitos(fatnot.get("INSCRICAO_SUFRAMA") or "")
    if suframa:
        linhas.append(f"ISUF={suframa}")

    ie_dest = _digitos(fatnot.get("INSCRICAO_RG") or cadcli.get("INSCRICAO_RG"))
    if ie_dest and ind_ie_dest == "1":
        linhas.append(f"IE={ie_dest}")

    cod_pais_dest = _inteiro(cadcli.get("COD_PAIS"), padrao=1058)
    nome_pais_dest = _texto(cadcli.get("NOME_PAIS") or "BRASIL", 60)

    linhas += [
        f"xLgr={_texto(fatnot.get('ENDERECO') or cadcli.get('ENDERECO'), 60)}",
        f"nro={_texto(fatnot.get('NUMERO') or cadcli.get('NUMERO')) or 'S/N'}",
        f"xCpl={_texto(fatnot.get('COMPLEMENTO') or cadcli.get('COMPLEMENTO'), 60)}",
        f"xBairro={_texto(fatnot.get('BAIRRO') or cadcli.get('BAIRRO'), 60)}",
        f"cMun={destinatario_cmun}",
        f"xMun={_texto(fatnot.get('CIDADE') or cadcli.get('CIDADE'), 60)}",
        f"UF={_texto(fatnot.get('ESTADO') or cadcli.get('ESTADO'), 2)}",
        f"CEP={_digitos(fatnot.get('CEP') or cadcli.get('CEP'))}",
        f"cPais={cod_pais_dest}",
        f"xPais={nome_pais_dest}",
        f"fone={_digitos(cadcli.get('FONE') or '')}",
        "",
    ]

    # ──────────────────────────────────────────────────────────────────────────
    # [ProdutoNNN] + tributacao por item
    # ──────────────────────────────────────────────────────────────────────────
    p_icms_inter_part = _decimal(fatnot.get("P_ICMS_INTER_PART"))
    tem_difal = p_icms_inter_part > 0 and not _bool_s(fatope.get("ACORDO_DIF_ALIQ"))

    for indice, item in enumerate(itens, start=1):
        ncm = _digitos(item.get("NCM"))
        if not ncm:
            raise ValueError(
                f"Produto {item.get('PRODUTO')} sem NCM em ESTPRO; nao foi possivel gerar INI."
            )

        sufixo = f"{indice:03d}"
        quantidade = _decimal(item.get("QUANTIDADE"))
        vuncom = _vuncom(item)
        # vProd: usa TPRODUTO se disponivel (total do item no banco), senao calcula
        tproduto_item = _decimal(item.get("TPRODUTO"))
        valor_total = tproduto_item if tproduto_item > 0 else (
            (quantidade * vuncom).quantize(Decimal("1.00"), rounding=ROUND_HALF_UP)
        )
        # Produto especial ICMS_IMOB nao compoe valor
        if _texto(item.get("PRODUTO")).upper() == "ICMS_IMOB":
            valor_total = Decimal("0.00")

        v_desc_item = _decimal(item.get("DESCONTO")) + _decimal(item.get("VLICMSDESON"))
        v_outro_item = _decimal(item.get("OUTRAS"))
        v_frete_item = _decimal(item.get("DESPESAS"))
        ind_tot = _ind_tot(item)

        total_prod += valor_total
        total_bc_icms += _decimal(item.get("BASE_ICMS"))
        total_icms += _decimal(item.get("TICMS"))
        total_bc_st += _decimal(item.get("BASE_ICMS_ST"))
        # Prefere TICMS_RETIDO (retencao efetiva) sobre TICMS_ST
        ticms_st_item = _decimal(item.get("TICMS_RETIDO")) or _decimal(item.get("TICMS_ST"))
        total_st += ticms_st_item
        total_bc_ipi += _decimal(item.get("BASE_IPI"))
        total_ipi += _decimal(item.get("TIPI")) or (
            _decimal(item.get("BASE_IPI")) * _decimal(item.get("PIPI"), 4) / Decimal("100")
        ).quantize(Decimal("1.00"), rounding=ROUND_HALF_UP)
        total_bc_pis += _decimal(item.get("BASE_PIS"))
        total_pis += _decimal(item.get("TPIS"))
        total_bc_cofins += _decimal(item.get("BASE_COFINS"))
        total_cofins += _decimal(item.get("TCOFINS"))
        total_tot_trib += _decimal(item.get("IBPT_VLR_IMPOSTO"))
        total_desconto += _decimal(item.get("DESCONTO"))

        # totais XML (sem simples ou com credito SN)
        csosn_item = _csosn(item) if regime_simples else None
        if not regime_simples:
            total_bc_icms_xml += _decimal(item.get("BASE_ICMS"))
            total_icms_xml += _decimal(item.get("TICMS"))
            total_bc_st_xml += _decimal(item.get("BASE_ICMS_ST"))
            total_st_xml += ticms_st_item
        elif csosn_item in {"101", "201", "900"}:
            total_bc_icms_xml += _decimal(item.get("BASE_ICMS"))
            total_icms_xml += _decimal(item.get("TICMS"))
        if regime_simples and csosn_item in {"201", "500", "900"}:
            total_bc_st_xml += _decimal(item.get("BASE_ICMS_ST"))
            total_st_xml += ticms_st_item

        # -- Descricao do produto (com overflow para infAdProd) ---
        descricao_curta = _texto(item.get("DSC_CADASTRO") or item.get("DESCRICAO"), 120)
        descricao_longa = _texto(item.get("DESCRICAO"))
        acessorios = _texto(item.get("ACESSORIOS"))
        if acessorios:
            xprod = _texto(item.get("DSC_CADASTRO") or item.get("DESCRICAO"), 120)
            inf_ad_prod = acessorios[:500]
        elif len(descricao_longa) > 120:
            xprod = descricao_curta
            inf_ad_prod = descricao_longa[:500]
        else:
            xprod = descricao_longa[:120]
            inf_ad_prod = ""

        linhas += [
            f"[Produto{sufixo}]",
            f"cProd={_texto(item.get('PRODUTO'), 60)}",
            "cEAN=SEM GTIN",
            f"xProd={xprod}",
            f"NCM={ncm}",
            f"CFOP={_cfop(item.get('CFOP'))}",
            f"uCom={_texto(item.get('UNID_COM') or item.get('UNIDADE'), 6) or 'UN'}",
            f"qCom={_decimal_str(quantidade, 4)}",
            f"vUnCom={_decimal_str(vuncom, 10)}",
            f"vProd={_decimal_str(valor_total, 2)}",
            "cEANTrib=SEM GTIN",
            f"uTrib={_texto(item.get('UNID_TRIB') or item.get('UNIDADE'), 6) or 'UN'}",
            f"qTrib={_decimal_str(quantidade, 4)}",
            f"vUnTrib={_decimal_str(vuncom, 10)}",
            f"indTot={ind_tot}",
        ]

        cest = _digitos(item.get("CEST") or item.get("PROD_CEST"))
        if cest:
            linhas.append(f"CEST={cest}")

        ex_tipi = _texto(item.get("EX_TIPI"))
        if ex_tipi:
            linhas.append(f"EXTIPI={ex_tipi}")

        # cBenef (NT 2026 — SP obrigatorio para CST 20/50/51)
        cod_benef = cod_benef_map.get(_inteiro(item.get("ITEM")), "")
        if cod_benef:
            linhas.append(f"cBenef={cod_benef}")

        # xPed / nItemPed (pedido do cliente)
        xped = _texto(item.get("PEDIDO_CLIENTE"), 15)
        if xped:
            nitem_ped = _inteiro(item.get("ITEM_PED_CLIENTE"))
            linhas.append(f"xPed={xped}")
            linhas.append(f"nItemPed={nitem_ped:06d}")

        # vFrete / vDesc / vOutro por item
        if v_frete_item > 0:
            linhas.append(f"vFrete={_decimal_str(v_frete_item, 2)}")
        if v_desc_item > 0:
            linhas.append(f"vDesc={_decimal_str(v_desc_item, 2)}")
        if v_outro_item > 0:
            linhas.append(f"vOutro={_decimal_str(v_outro_item, 2)}")

        # infAdProd
        if inf_ad_prod:
            linhas.append(f"infAdProd={inf_ad_prod}")

        # pDevol/vIPIDevol (devolucao de compras)
        if _decimal(item.get("PERC_DEV")) > 0:
            linhas.append(f"pDevol={_decimal_str(item.get('PERC_DEV'), 2)}")
            linhas.append(f"vIPIDevol={_decimal_str(item.get('TIPI'), 2)}")

        linhas.append("")

        # ── [ICMSXXX] ────────────────────────────────────────────────────────
        linhas += [
            f"[ICMS{sufixo}]",
            f"orig={_inteiro(item.get('ORIGEM'))}",
        ]

        if regime_simples:
            linhas.append(f"CSOSN={_csosn(item)}")
            # Credito SN (CSOSN 101/201/900)
            pcred = _decimal(item.get("PCRED_SN"), 4)
            vcred = _decimal(item.get("VCRED_ICMS_SN"))
            if pcred > 0:
                linhas.append(f"pCredSN={_decimal_str(pcred, 4)}")
                linhas.append(f"vCredICMSSN={_decimal_str(vcred, 2)}")
        else:
            cst_icms = _cst_icms(item)
            linhas.append(f"CST={cst_icms}")
            # modBC=3 (valor da operacao)
            linhas.append("modBC=3")

            bc_icms = _decimal(item.get("BASE_ICMS"))
            p_icms = _decimal(item.get("PICMS"), 4)
            v_icms = _decimal(item.get("TICMS"))

            # Reducao de base (CST 20/70)
            p_red = _decimal(item.get("REDUCAO"), 4)
            if p_red > 0:
                linhas.append(f"pRedBC={_decimal_str(p_red, 4)}")

            linhas += [
                f"vBC={_decimal_str(bc_icms, 2)}",
                f"pICMS={_decimal_str(p_icms, 2)}",
                f"vICMS={_decimal_str(v_icms, 2)}",
            ]

            # ICMS desonerado
            v_deson = _decimal(item.get("VLICMSDESON"))
            motdeson = _texto(item.get("MOTDESON"))
            if v_deson > 0:
                linhas.append(f"vICMSDeson={_decimal_str(v_deson, 2)}")
                if motdeson.isdigit():
                    linhas.append(f"motDesICMS={motdeson}")

        # ICMS ST
        bc_st = _decimal(item.get("BASE_ICMS_ST"))
        v_icms_st = _decimal(item.get("TICMS_RETIDO")) or _decimal(item.get("TICMS_ST"))
        if bc_st > 0 or v_icms_st > 0:
            p_mva = _decimal(item.get("PORC_IVA"), 4)
            p_icms_st = _decimal(item.get("ICMS_ST"), 4)
            p_red_st = _decimal(item.get("REDUCAO"), 4)
            # Calcula pICMSST se nao vier do banco
            if p_icms_st == 0 and bc_st > 0 and v_icms_st > 0:
                p_icms_st = (v_icms_st / bc_st * Decimal("100")).quantize(
                    Decimal("1.00"), rounding=ROUND_HALF_UP
                )
            linhas += [
                "modBCST=4",
                f"pMVAST={_decimal_str(p_mva, 4)}",
            ]
            if p_red_st > 0:
                linhas.append(f"pRedBCST={_decimal_str(p_red_st, 4)}")
            linhas += [
                f"vBCST={_decimal_str(bc_st, 2)}",
                f"pICMSST={_decimal_str(p_icms_st, 2)}",
                f"vICMSST={_decimal_str(v_icms_st, 2)}",
            ]

        # FCP-ST por item
        p_fcp = _decimal(item.get("P_FCP_UF_DEST"), 4)
        v_fcp = _decimal(item.get("V_FCP_UF_DEST"))
        if p_fcp > 0 and bc_st > 0:
            linhas += [
                f"vBCFCPST={_decimal_str(bc_st, 2)}",
                f"pFCPST={_decimal_str(p_fcp, 4)}",
                f"vFCPST={_decimal_str(v_fcp, 2)}",
            ]

        linhas.append(f"vTotTrib={_decimal_str(item.get('IBPT_VLR_IMPOSTO') or 0, 2)}")
        linhas.append("")

        # ── [ICMSUFDEST] difal ────────────────────────────────────────────────
        if tem_difal and _decimal(item.get("V_ICMS_UF_DEST")) > 0:
            linhas += [
                f"[ICMSUFDest{sufixo}]",
                f"vBCUFDest={_decimal_str(item.get('BASE_ICMS'), 2)}",
                f"vBCFCPUFDest={_decimal_str(item.get('BASE_ICMS'), 2)}",
                f"pFCPUFDest={_decimal_str(item.get('P_FCP_UF_DEST'), 4)}",
                f"pICMSUFDest={_decimal_str(fatnot.get('P_ICMS_UF_DEST'), 4)}",
                f"pICMSInter={_decimal_str(item.get('P_ICMS_INTER'), 4)}",
                f"pICMSInterPart={_decimal_str(p_icms_inter_part, 4)}",
                f"vFCPUFDest={_decimal_str(item.get('V_FCP_UF_DEST'), 2)}",
                f"vICMSUFDest={_decimal_str(item.get('V_ICMS_UF_DEST'), 2)}",
                f"vICMSUFRemet={_decimal_str(item.get('V_ICMS_UF_REMET'), 2)}",
                "",
            ]

        # ── [IPIXXX] ──────────────────────────────────────────────────────────
        cst_ipi = _texto(item.get("CST_IPI") or item.get("IPI_CST") or "99", 2)
        v_ipi_item = _decimal(item.get("TIPI")) or (
            _decimal(item.get("BASE_IPI")) * _decimal(item.get("PIPI"), 4) / Decimal("100")
        ).quantize(Decimal("1.00"), rounding=ROUND_HALF_UP)
        linhas += [
            f"[IPI{sufixo}]",
            "cEnq=999",
            f"CST={cst_ipi}",
            f"vBC={_decimal_str(item.get('BASE_IPI'), 2)}",
            f"pIPI={_decimal_str(item.get('PIPI'), 2)}",
            f"vIPI={_decimal_str(v_ipi_item, 2)}",
            "",
        ]

        # ── [PISXXX] ──────────────────────────────────────────────────────────
        cst_pis = _texto(item.get("CST_PIS") or item.get("PIS_CST") or "01", 2)
        linhas += [
            f"[PIS{sufixo}]",
            f"CST={cst_pis}",
            f"vBC={_decimal_str(item.get('BASE_PIS') if _decimal(item.get('TPIS')) > 0 else 0, 2)}",
            f"pPIS={_decimal_str(item.get('PPIS'), 2)}",
            f"vPIS={_decimal_str(item.get('TPIS'), 2)}",
            "",
        ]

        # ── [COFINSXXX] ───────────────────────────────────────────────────────
        cst_cofins = _texto(item.get("CST_COFINS") or item.get("COFINS_CST") or "01", 2)
        linhas += [
            f"[COFINS{sufixo}]",
            f"CST={cst_cofins}",
f"vBC={_decimal_str(item.get('BASE_COFINS') if _decimal(item.get('TCOFINS')) > 0 else 0, 2)}",
            f"pCOFINS={_decimal_str(item.get('PCOFINS'), 2)}",
            f"vCOFINS={_decimal_str(item.get('TCOFINS'), 2)}",
            "",
        ]

    # ──────────────────────────────────────────────────────────────────────────
    # [Total]
    # ──────────────────────────────────────────────────────────────────────────
    desconto_geral = _decimal(fatnot.get("TDESCONTO"))
    frete_geral = _decimal(fatnot.get("TFRETE"))
    seguro = _decimal(fatnot.get("TSEGURO"))
    outras_geral = _decimal(fatnot.get("TDESPESAS"))
    v_icms_deson_total = _decimal(fatnot.get("TOTICMSDESONE"))
    v_ii_total = _decimal(fatnot.get("VLR_II"))
    v_fcp_uf_dest_total = _decimal(fatnot.get("V_FCP_UF_DEST"))
    v_icms_uf_dest_total = _decimal(fatnot.get("V_ICMS_UF_DEST"))
    v_icms_uf_remet_total = _decimal(fatnot.get("V_ICMS_UF_REMET"))

    v_desc_total_xml = v_icms_deson_total + total_desconto

    # Usa totais do banco quando disponiveis
    tproduto_fatnot = _decimal(fatnot.get("TPRODUTO"))
    tservico_fatnot = _decimal(fatnot.get("TSERVICO"))
    vprod_xml = tproduto_fatnot if tproduto_fatnot > 0 else (tservico_fatnot if tservico_fatnot > 0 else 0)

    total_nfe = (total_prod - desconto_geral + frete_geral + seguro + outras_geral).quantize(
        Decimal("1.00"), rounding=ROUND_HALF_UP,
    )

    linhas += [
        "[Total]",
        f"vBC={_decimal_str(total_bc_icms_xml, 2)}",
        f"vICMS={_decimal_str(total_icms_xml, 2)}",
        f"vICMSDeson={_decimal_str(v_icms_deson_total, 2)}",
        f"vBCST={_decimal_str(total_bc_st_xml, 2)}",
        f"vST={_decimal_str(total_st_xml, 2)}",
        "vFCP=0.00",
        f"vFCPST={_decimal_str(v_fcp_uf_dest_total, 2)}",
        "vFCPSTRet=0.00",
        f"vProd={_decimal_str(vprod_xml, 2)}",
        f"vFrete={_decimal_str(frete_geral, 2)}",
        f"vSeg={_decimal_str(seguro, 2)}",
        f"vDesc={_decimal_str(v_desc_total_xml, 2)}",
        f"vII={_decimal_str(v_ii_total, 2)}",
        f"vIPI={_decimal_str(total_ipi, 2)}",
        "vIPIDevol=0.00",
        f"vPIS={_decimal_str(total_pis, 2)}",
        f"vCOFINS={_decimal_str(total_cofins, 2)}",
        f"vOutro={_decimal_str(outras_geral, 2)}",
        f"vNF={_decimal_str(total_nfe, 2)}",
        f"vTotTrib={_decimal_str(total_tot_trib, 2)}",
    ]

    if tem_difal:
        linhas += [
            f"vFCPUFDest={_decimal_str(v_fcp_uf_dest_total, 2)}",
            f"vICMSUFDest={_decimal_str(v_icms_uf_dest_total, 2)}",
            f"vICMSUFRemet={_decimal_str(v_icms_uf_remet_total, 2)}",
        ]

    linhas.append("")

    # ──────────────────────────────────────────────────────────────────────────
    # [Transportador] + [VolXXX]
    # ──────────────────────────────────────────────────────────────────────────
    if transp:
        t_val = _inteiro(transp.get("TRANSPORTE"), padrao=9)
        mod_frete = _TRANSPORTE_MODFRETE.get(t_val, "9")
        linhas += [
            "[Transportador]",
            f"modFrete={mod_frete}",
        ]
        trans_cgc = _digitos(transp.get("TRANS_CGC") or "")
        if len(trans_cgc) >= 10:
            linhas += [
                f"CNPJCPF={trans_cgc}",
                f"xNome={_texto(transp.get('TRANS_NOME'), 60)}",
                f"IE={_digitos(transp.get('TRANS_INSCR') or '')}",
                f"xEnder={_texto(transp.get('TRANS_ENDER'), 60)}",
                f"xMun={_texto(transp.get('TRANS_CIDADE'), 60)}",
                f"UF={_texto(transp.get('TRANS_ESTADO'), 2)}",
            ]
        placa = _texto(transp.get("PLACA"), 8)
        if placa:
            linhas += [
                f"placa={placa}",
                f"UF={_texto(transp.get('PLACA_ESTADO'), 2)}",
            ]
        linhas.append("")

        q_vol = _inteiro(transp.get("VOL_QUANTIDADE"))
        if q_vol > 0:
            p_liq = _decimal(transp.get("PESO_LIQUIDO"), 3)
            p_bru = _decimal(transp.get("PESO_BRUTO"), 3)
            linhas += [
                "[Vol001]",
                f"qVol={q_vol}",
                f"esp={_texto(transp.get('VOL_ESPECIE'), 60)}",
                f"marca={_texto(transp.get('VOL_MARCA'), 60)}",
                f"nVol={_texto(transp.get('VOL_NUMERO'), 60)}",
                f"pesoL={_decimal_str(p_liq, 3)}",
                f"pesoB={_decimal_str(p_bru, 3)}",
                "",
            ]
    else:
        linhas += [
            "[Transportador]",
            "modFrete=9",
            "",
        ]

    # ──────────────────────────────────────────────────────────────────────────
    # [Cobr] + [DupXXX] — fatura e duplicatas
    # ──────────────────────────────────────────────────────────────────────────
    fatfin_cobr = [
        f for f in fatfin
        if not (_texto(f.get("CONTA")).upper() == "CARTEIRA" and _inteiro(f.get("TIPO_VENC")) == 2)
    ]

    if fatfin_cobr:
        t_cobranca = sum(_decimal(f.get("VALOR")) for f in fatfin_cobr)
        linhas += [
            "[Cobr]",
            f"vOrig={_decimal_str(t_cobranca, 2)}",
            f"vDesc=0.00",
            f"vLiq={_decimal_str(t_cobranca, 2)}",
            "",
        ]
        for idx, dup in enumerate(fatfin_cobr, start=1):
            linhas += [
                f"[Dup{idx:03d}]",
                f"nDup={_inteiro(dup.get('ITEM'), padrao=idx):03d}",
                f"dVenc={_data_br(dup.get('VENCIMENTO'))}",
                f"vDup={_decimal_str(dup.get('VALOR'), 2)}",
                "",
            ]

    # ──────────────────────────────────────────────────────────────────────────
    # [pagXXX] — meios de pagamento
    # ──────────────────────────────────────────────────────────────────────────
    if fatfin:
        for idx, pag in enumerate(fatfin, start=1):
            tipo_venc = _inteiro(pag.get("TIPO_VENC"), padrao=1)
            conta = _texto(pag.get("CONTA")).upper()
            venc = pag.get("VENCIMENTO")
            emissao = fatnot.get("EMISSAO")

            # indPag: 0=a vista, 1=a prazo
            # A vista: carteira a vista ou parcela unica com vencimento em ate 30 dias
            a_vista = (
                (conta == "CARTEIRA" and tipo_venc == 2) or
                (len(fatfin) == 1 and isinstance(venc, datetime) and isinstance(emissao, datetime)
                 and venc <= emissao + timedelta(days=30))
            )
            ind_pag = "0" if a_vista else "1"
            t_pag = _TIPO_VENC_TPAG.get(tipo_venc, "15")

            linhas += [
                f"[pag{idx:03d}]",
                f"indPag={ind_pag}",
                f"tPag={t_pag}",
                f"vPag={_decimal_str(pag.get('VALOR'), 2)}",
            ]

            # Dados de cartao (tipo 7=credito, 8=debito)
            if tipo_venc in (7, 8):
                cnpj_op = _digitos(pag.get("CNPJ_OPERADORA") or "")
                if cnpj_op:
                    linhas.append(f"CNPJ={cnpj_op}")
                tband = _inteiro(pag.get("BANDEIRA"))
                if tband:
                    linhas.append(f"tBand={tband:02d}")
                caut = _texto(pag.get("AUTORIZACAO"), 20)
                if caut:
                    linhas.append(f"cAut={caut}")

            linhas.append("")
    else:
        # Sem FATFIN: usa valor total como pagamento unico a prazo (boleto)
        linhas += [
            "[pag001]",
            "indPag=1",
            "tPag=15",
            f"vPag={_decimal_str(total_nfe, 2)}",
            "",
        ]

    # ──────────────────────────────────────────────────────────────────────────
    # [DadosAdicionais]
    # ──────────────────────────────────────────────────────────────────────────
    observacao = _texto(fatnot.get("OBS_CORPO_NF"), 5000)
    if observacao:
        linhas += [
            "[DadosAdicionais]",
            f"infCpl={observacao}",
            "",
        ]

    chave_acesso = _gerar_chave_acesso(
        uf=_texto(cademp.get("ESTADO"), 2),
        data_emissao=_data_emissao_ini(fatnot, tp_amb=tp_amb),
        cnpj=emitente_cnpj,
        modelo="55",
        serie=str(serie),
        numero=str(nota),
        tp_emis="1",
    )

    return linhas, nota, serie, cnf, chave_acesso


def gerar_ini_nfe(cursor, registro: int) -> NFeIniGerado:
    # ── FATNOT ────────────────────────────────────────────────────────────────
    fatnot = _query_uma_linha(
        cursor,
        """
        SELECT TOP 1
            REGISTRO, EMPRESA, NOTA, SERIE, MODELO, EMISSAO, SAIDA, SITUACAO, OPERACAO,
            DESTINATARIO, NOME, CGC_CPF, INSCRICAO_RG, ENDERECO, BAIRRO, CEP, CIDADE,
            ESTADO, NUMERO, COMPLEMENTO,
            BASE_ICMS, VALOR_ICMS, BASESUB, TICMSSUB,
            TPRODUTO, TGERAL, TDESCONTO, TFRETE, TSEGURO, TDESPESAS,
            BASE_PIS, BASE_COFINS, TPIS, TCOFINS,
            TIPO_DESTINATARIO, CONSUMIDOR, VENDA_SITE, DESTINATARIO,
            ISNULL(OBS_CORPO_NF, '')          AS OBS_CORPO_NF,
            ISNULL(VENDAINT, '0')             AS VENDAINT,
            ISNULL(TP_SAIDA_ENTR, 1)          AS TP_SAIDA_ENTR,
            ISNULL(PRESENCIAL, '1')           AS PRESENCIAL,
            ISNULL(INDIEDEST, 0)              AS INDIEDEST,
            ISNULL(P_ICMS_INTER_PART, 0)      AS P_ICMS_INTER_PART,
            ISNULL(P_ICMS_UF_DEST, 0)         AS P_ICMS_UF_DEST,
            ISNULL(V_FCP_UF_DEST, 0)          AS V_FCP_UF_DEST,
            ISNULL(V_ICMS_UF_DEST, 0)         AS V_ICMS_UF_DEST,
            ISNULL(V_ICMS_UF_REMET, 0)        AS V_ICMS_UF_REMET,
            ISNULL(TOTICMSDESONE, 0)          AS TOTICMSDESONE,
            ISNULL(VLR_II, 0)                 AS VLR_II,
            ISNULL(TSERVICO, 0)               AS TSERVICO,
            ISNULL(REVENDA, 'N')              AS REVENDA,
            ISNULL(INSCRICAO_SUFRAMA, '')     AS INSCRICAO_SUFRAMA,
            ISNULL(CONTRIBUINTE, '')          AS CONTRIBUINTE
        FROM FATNOT
        WHERE REGISTRO = ?
        """,
        [registro],
        f"FATNOT REGISTRO={registro} nao encontrada.",
    )

    # ── CADEMP ────────────────────────────────────────────────────────────────
    try:
        cursor.execute(
            "SELECT TOP 1 CERTIFICADO_SERIAL FROM CADEMP WHERE EMPRESA = ?",
            [fatnot.get("EMPRESA")],
        )
        row_cert = cursor.fetchone()
        cert_serial = str(row_cert[0]).strip() if row_cert and row_cert[0] else ""
    except Exception:
        cert_serial = ""

    cademp = _query_uma_linha(
        cursor,
        """
        SELECT TOP 1
            EMPRESA, NOME, TIPO_INSCRICAO, CNPJ, INSCRICAO_FEDERAL, INSCRICAO_ESTADUAL,
            ENDERECO, NUMERO, COMPLEMENTO, BAIRRO, CEP, CIDADE, ESTADO, FONE,
            COD_MUN_IBGE, MUNICIPIO_IBGE, EMAIL, SIMPLES
        FROM CADEMP
        WHERE EMPRESA = ?
        """,

        f"CADEMP EMPRESA={fatnot.get('EMPRESA')} nao encontrada.",
    )
    cademp["CERTIFICADO_SERIAL"] = cert_serial

    # ── CADCLI ────────────────────────────────────────────────────────────────
    cadcli = _query_uma_linha(
        cursor,
        """
        SELECT TOP 1
            CLIENTE, COD_MUN_IBGE, CIDADE, ESTADO, ENDERECO, BAIRRO, CEP,
            NUMERO, COMPLEMENTO, CGC_CPF, INSCRICAO_RG,
            ISNULL(FONE, '')   AS FONE,
            ISNULL(PAIS, 1058) AS COD_PAIS,
            ISNULL(NOME_PAIS, 'BRASIL') AS NOME_PAIS
        FROM CADCLI
        WHERE CLIENTE = ?
        """,

        f"CADCLI CLIENTE={fatnot.get('DESTINATARIO')} nao encontrado.",
    )

    # ── FATOPE ────────────────────────────────────────────────────────────────
    fatope: dict = {}
    operacao_id = _inteiro(fatnot.get("OPERACAO"))
    if operacao_id:
        cursor.execute(
            """
            SELECT TOP 1
                DESCRICAO_NF, MOVIMENTACAO,
                ISNULL(FIN_DEVOLUCAO, 'N')  AS FIN_DEVOLUCAO,
                ISNULL(ACORDO_DIF_ALIQ, 'N') AS ACORDO_DIF_ALIQ
            FROM FATOPE
            WHERE OPERACAO = ?
            """,
            [operacao_id],
        )
        row = cursor.fetchone()
        if row:
            fatope = dict(zip([d[0] for d in cursor.description], row))

    # ── FATITN ────────────────────────────────────────────────────────────────
    itens = _query_varias_linhas(
        cursor,
        """
        SELECT
            i.ITEM, i.PRODUTO, i.DESCRICAO, i.QUANTIDADE, i.UNIDADE, i.VALOR, i.CFOP,
            i.PICMS, i.BASE_ICMS, i.TICMS, i.PIPI, i.BASE_IPI, i.TPIS, i.PPIS,
            i.BASE_PIS, i.TCOFINS, i.PCOFINS, i.BASE_COFINS,
            i.CST_IPI, i.CST_PIS, i.CST_COFINS, i.CCF, i.CEST,
            i.BASE_ICMS_ST, i.TICMS_ST,
            ISNULL(i.TIPO_ITEM, 0)          AS TIPO_ITEM,
            ISNULL(i.DESCONTO, 0)           AS DESCONTO,
            ISNULL(i.VLICMSDESON, 0)        AS VLICMSDESON,
            ISNULL(i.OUTRAS, 0)             AS OUTRAS,
            ISNULL(i.DESPESAS, 0)           AS DESPESAS,
            ISNULL(i.VALOR_CALCULO, 0)      AS VALOR_CALCULO,
            ISNULL(i.DCIMAIS_CALCULO, 0)    AS DCIMAIS_CALCULO,
            ISNULL(i.IBPT_VLR_IMPOSTO, 0)  AS IBPT_VLR_IMPOSTO,
            ISNULL(i.MOTDESON, '')          AS MOTDESON,
            ISNULL(i.PCRED_SN, 0)          AS PCRED_SN,
            ISNULL(i.VCRED_ICMS_SN, 0)     AS VCRED_ICMS_SN,
            ISNULL(i.REDUCAO, 0)           AS REDUCAO,
            ISNULL(i.PORC_IVA, 0)          AS PORC_IVA,
            ISNULL(i.TICMS_RETIDO, 0)      AS TICMS_RETIDO,
            ISNULL(i.ICMS_ST, 0)           AS ICMS_ST,
            ISNULL(i.PERC_DEV, 0)          AS PERC_DEV,
            ISNULL(i.TIPI, 0)              AS TIPI,
            ISNULL(i.P_FCP_UF_DEST, 0)    AS P_FCP_UF_DEST,
            ISNULL(i.V_FCP_UF_DEST, 0)    AS V_FCP_UF_DEST,
            ISNULL(i.P_ICMS_INTER, 0)     AS P_ICMS_INTER,
            ISNULL(i.V_ICMS_UF_DEST, 0)   AS V_ICMS_UF_DEST,
            ISNULL(i.V_ICMS_UF_REMET, 0)  AS V_ICMS_UF_REMET,
            ISNULL(i.VLR_IMP, 0)          AS VLR_IMP,
            ISNULL(i.TPRODUTO, 0)         AS TPRODUTO,
            ISNULL(i.PEDIDO_CLIENTE, '')   AS PEDIDO_CLIENTE,
            ISNULL(i.ITEM_PED_CLIENTE, 0) AS ITEM_PED_CLIENTE,
            ISNULL(i.ACESSORIOS, '')       AS ACESSORIOS,
            ISNULL(i.DSC_CADASTRO, '')     AS DSC_CADASTRO,
            ISNULL(i.EX_TIPI, '')          AS EX_TIPI,
            p.NCM, p.CEST AS PROD_CEST, p.ORIGEM, p.ICMS_CST, p.IPI_CST,
            p.PIS_CST, p.COFINS_CST, p.UNID_COM, p.UNID_TRIB
        FROM FATITN i


        ORDER BY i.ITEM
        """,
        [registro],
    )
    if not itens:
        raise ValueError(f"FATITN REGISTRO={registro} nao possui itens.")

    # ── FATFIN ────────────────────────────────────────────────────────────────
    fatfin: list[dict] = []
    try:
        cursor.execute(
            """
            SELECT
                ITEM, VALOR,
                ISNULL(VENCIMENTO, EMISSAO)    AS VENCIMENTO,
                ISNULL(TIPO_VENC, 1)           AS TIPO_VENC,
                ISNULL(CONTA, '')              AS CONTA,
                ISNULL(CNPJ_OPERADORA, '')     AS CNPJ_OPERADORA,
                ISNULL(BANDEIRA, 0)            AS BANDEIRA,
                ISNULL(AUTORIZACAO, '')        AS AUTORIZACAO
            FROM FATFIN
            WHERE REGISTRO = ?
            ORDER BY ITEM
            """,
            [registro],
        )
        rows = cursor.fetchall()
        if rows:
            cols = [d[0] for d in cursor.description]
            fatfin = [dict(zip(cols, r)) for r in rows]
    except Exception:
        pass

    # ── FATTRANSP ─────────────────────────────────────────────────────────────
    transp = _query_transportadora(cursor, registro)

    # ── COD_BENEF (coluna opcional — NT 2026) ─────────────────────────────────
    cod_benef_map = _query_cod_benef(cursor, registro)

    linhas, nota, serie, cnf, chave_acesso = _gerar_linhas_ini(
        fatnot=fatnot,
        cademp=cademp,
        cadcli=cadcli,
        fatope=fatope,
        itens=itens,
        fatfin=fatfin,
        transp=transp,
        cod_benef_map=cod_benef_map,
    )

    path = (TMP_DIR / f"{registro:06d}.ini").resolve()
    path.write_text("\r\n".join(linhas))
    return NFeIniGerado(
        path=path, chave_acesso=chave_acesso,
        numero=nota, serie=serie,
        certificado_serial=cert_serial,
    )
