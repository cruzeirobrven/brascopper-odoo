"""
Monta dados para emissao de NF-e a partir das tabelas ERP no PostgreSQL.
Usado pelo endpoint POST /api/v1/nfe/emitir-do-erp
"""
import logging
from datetime import datetime
from decimal import Decimal

from api.database import get_cursor

logger = logging.getLogger(__name__)


def buscar_nota_completa(registro_erp: int) -> dict:
    """Retorna dicionario completo para _gerar_linhas_ini (fatnot, cademp, etc.)
    a partir das tabelas ERP no PostgreSQL."""
    with get_cursor() as cur:
        # Busca nota
        cur.execute("SELECT * FROM erp_notas WHERE registro = %s", [registro_erp])
        fatnot_row = cur.fetchone()
        if not fatnot_row:
            raise ValueError(f"Nota REGISTRO={registro_erp} nao encontrada no banco local.")

        empresa_erp = fatnot_row["empresa"]
        destinatario_erp = fatnot_row["destinatario"]

        # Busca empresa
        cur.execute("SELECT * FROM erp_empresas WHERE codigo_erp = %s", [empresa_erp])
        empresa_row = cur.fetchone()
        if not empresa_row:
            raise ValueError(f"Empresa ERP={empresa_erp} nao encontrada.")

        # Busca cliente
        cur.execute(
            "SELECT * FROM erp_clientes WHERE empresa_erp = %s AND codigo_erp = %s",
            [empresa_erp, destinatario_erp],
        )
        cliente_row = cur.fetchone()

        # Busca operacao
        cur.execute("SELECT * FROM erp_operacoes WHERE operacao = %s", [fatnot_row["operacao"]])
        fatope_row = cur.fetchone()

        # Busca itens
        cur.execute(
            "SELECT * FROM erp_itens_nota WHERE registro = %s ORDER BY item",
            [registro_erp],
        )
        itens_rows = cur.fetchall()

        # Busca parcelas
        cur.execute(
            "SELECT * FROM erp_parcelas WHERE registro = %s ORDER BY parcela",
            [registro_erp],
        )
        parcelas_rows = cur.fetchall()

    # ── Monta fatnot (header) ──────────────────────────────────────────────
    fr = dict(fatnot_row)
    cert_serial = dict(empresa_row).get("certificado_serial") or ""

    fatnot = {
        "REGISTRO": fr.get("registro"),
        "EMPRESA": fr.get("empresa"),
        "NOTA": fr.get("nota") or 0,
        "SERIE": str(fr.get("serie") or "1"),
        "MODELO": fr.get("modelo") or "55",
        "EMISSAO": fr.get("emissao"),
        "SAIDA": fr.get("saida") or fr.get("emissao"),
        "TP_SAIDA_ENTR": fr.get("tp_saida_entr") or 1,
        "SITUACAO": fr.get("situacao"),
        "OPERACAO": fr.get("operacao"),
        "DESTINATARIO": fr.get("destinatario"),
        "NOME": fr.get("nome") or "",
        "CGC_CPF": fr.get("cgc_cpf") or "",
        "INSCRICAO_RG": fr.get("inscricao_rg") or "",
        "ENDERECO": fr.get("endereco") or "",
        "NUMERO": fr.get("numero") or "",
        "COMPLEMENTO": fr.get("complemento") or "",
        "BAIRRO": fr.get("bairro") or "",
        "CIDADE": fr.get("cidade") or "",
        "ESTADO": fr.get("estado") or "",
        "CEP": fr.get("cep") or "",
        "FONE": fr.get("fone") or "",
        "CONSUMIDOR": "S" if fr.get("consumidor") else "N",
        "VENDA_SITE": "S" if fr.get("venda_site") else "N",
        "VENDAINT": "1" if fr.get("venda_int") else "0",
        "PRESENCIAL": "1" if fr.get("presencial") else "0",
        "CONTRIBUINTE": "S" if fr.get("contribuinte") else "N",
        "OBS_CORPO_NF": fr.get("obs_corpo_nf") or "",
        "TPRODUTO": float(fr.get("tproduto") or 0),
        "TGERAL": float(fr.get("tgeral") or 0),
        "TDESCONTO": float(fr.get("tdesconto") or 0),
        "TFRETE": float(fr.get("tfrete") or 0),
        "TSEGURO": float(fr.get("tseguro") or 0),
        "TDESPESAS": float(fr.get("tdespesas") or 0),
        "BASE_ICMS": float(fr.get("base_icms") or 0),
        "VALOR_ICMS": float(fr.get("valor_icms") or 0),
        "BASESUB": float(fr.get("basesub") or 0),
        "TICMSSUB": float(fr.get("ticmssub") or 0),
        "TIPI": float(fr.get("tipi") or 0),
        "TPIS": float(fr.get("tpis") or 0),
        "TCOFINS": float(fr.get("tcofins") or 0),
        "TSERVICO": float(fr.get("tservico") or 0),
        "P_ICMS_INTER_PART": float(fr.get("p_icms_inter_part") or 0),
        "V_FCP_UF_DEST": float(fr.get("v_fcp_uf_dest") or 0),
        "V_ICMS_UF_DEST": float(fr.get("v_icms_uf_dest") or 0),
        "V_ICMS_UF_REMET": float(fr.get("v_icms_uf_remet") or 0),
        "TOTICMSDESONE": float(fr.get("toticmsdeson") or 0),
        "VLR_II": 0,
        "INSCRICAO_SUFRAMA": "",
        "INDIEDEST": 9,
        "REVENDA": "N",
    }

    # ── Monta cademp (emitente) ────────────────────────────────────────────
    er = dict(empresa_row)
    cademp = {
        "EMPRESA": er.get("codigo_erp"),
        "NOME": er.get("nome") or "",
        "TIPO_INSCRICAO": 1,
        "CNPJ": er.get("cnpj") or "",
        "INSCRICAO_FEDERAL": er.get("cnpj") or "",
        "INSCRICAO_ESTADUAL": er.get("inscricao_estadual") or "",
        "ENDERECO": er.get("endereco") or "",
        "NUMERO": er.get("numero") or "",
        "COMPLEMENTO": er.get("complemento") or "",
        "BAIRRO": er.get("bairro") or "",
        "CIDADE": er.get("cidade") or "",
        "ESTADO": er.get("estado") or "",
        "CEP": er.get("cep") or "",
        "FONE": er.get("fone") or "",
        "COD_MUN_IBGE": str(er.get("cod_mun_ibge") or ""),
        "MUNICIPIO_IBGE": er.get("cidade") or "",
        "SIMPLES": 1 if er.get("simples") else 3,
        "EMAIL": er.get("email") or "",
        "CERTIFICADO_SERIAL": cert_serial,
    }

    # ── Monta cadcli (destinatario) ────────────────────────────────────────
    if cliente_row:
        cr = dict(cliente_row)
        cadcli = {
            "CLIENTE": cr.get("codigo_erp"),
            "CGC_CPF": cr.get("cnpj_cpf") or "",
            "INSCRICAO_RG": cr.get("inscricao_rg") or "",
            "NOME": cr.get("nome") or "",
            "ENDERECO": cr.get("endereco") or "",
            "NUMERO": cr.get("numero") or "",
            "COMPLEMENTO": cr.get("complemento") or "",
            "BAIRRO": cr.get("bairro") or "",
            "CIDADE": cr.get("cidade") or "",
            "ESTADO": cr.get("estado") or "",
            "CEP": cr.get("cep") or "",
            "FONE": cr.get("fone_1") or "",
            "COD_MUN_IBGE": str(cr.get("cod_mun_ibge") or ""),
            "COD_PAIS": cr.get("cod_pais") or 1058,
            "NOME_PAIS": cr.get("sigla_pais") or "BRASIL",
        }
        fatnot["INDIEDEST"] = cr.get("ind_ie_dest") or 9
        fatnot["INSCRICAO_SUFRAMA"] = cr.get("insc_suframa") or ""
        fatnot["INSCRICAO_RG"] = cr.get("inscricao_rg") or fatnot.get("INSCRICAO_RG", "")
    else:
        cadcli = {
            "CLIENTE": fatnot["DESTINATARIO"],
            "CGC_CPF": fatnot["CGC_CPF"],
            "INSCRICAO_RG": "",
            "NOME": fatnot["NOME"],
            "ENDERECO": fatnot["ENDERECO"],
            "NUMERO": fatnot["NUMERO"],
            "COMPLEMENTO": fatnot.get("COMPLEMENTO", ""),
            "BAIRRO": fatnot["BAIRRO"],
            "CIDADE": fatnot["CIDADE"],
            "ESTADO": fatnot["ESTADO"],
            "CEP": fatnot["CEP"],
            "FONE": fatnot.get("FONE", ""),
            "COD_MUN_IBGE": "",
            "COD_PAIS": 1058,
            "NOME_PAIS": "BRASIL",
        }

    # ── Monta fatope ───────────────────────────────────────────────────────
    if fatope_row:
        oper = dict(fatope_row)
        fatope = {
            "DESCRICAO_NF": oper.get("descricao_nf") or "VENDA",
            "MOVIMENTACAO": oper.get("movimentacao") or 1,
            "FIN_DEVOLUCAO": "S" if oper.get("fin_devolucao") else "N",
            "ACORDO_DIF_ALIQ": "S" if oper.get("acordo_dif_aliq") else "N",
        }
    else:
        fatope = {
            "DESCRICAO_NF": "VENDA",
            "MOVIMENTACAO": 1,
            "FIN_DEVOLUCAO": "N",
            "ACORDO_DIF_ALIQ": "N",
        }

    # ── Monta itens ────────────────────────────────────────────────────────
    itens = []
    for row in itens_rows:
        ir = dict(row)
        qtd = float(ir.get("quantidade") or 0)
        vun = float(ir.get("valor") or 0)
        vtot = float(ir.get("tproduto") or 0) or qtd * vun
        itens.append({
            "ITEM": ir.get("item"),
            "PRODUTO": ir.get("produto") or "",
            "DESCRICAO": ir.get("descricao") or "",
            "QUANTIDADE": qtd,
            "UNIDADE": ir.get("unidade") or "UN",
            "VALOR": vun,
            "TPRODUTO": vtot,
            "CFOP": ir.get("cfop") or "",
            "NCM": "",
            "CEST": ir.get("cest") or "",
            "ORIGEM": 0,
            "TIPO_ITEM": 0,
            "DESCONTO": float(ir.get("desconto") or 0),
            "OUTRAS": 0,
            "DESPESAS": 0,
            "ICMS_CST": "",
            "PICMS": float(ir.get("picms") or 0),
            "BASE_ICMS": float(ir.get("base_icms") or 0),
            "TICMS": float(ir.get("ticms") or 0),
            "REDUCAO": float(ir.get("reducao") or 0),
            "CST_IPI": ir.get("cst_ipi") or "99",
            "PIPI": float(ir.get("pipi") or 0),
            "BASE_IPI": float(ir.get("base_ipi") or 0),
            "TIPI": float(ir.get("tipi") or 0),
            "CST_PIS": ir.get("cst_pis") or "01",
            "PPIS": float(ir.get("ppis") or 0),
            "BASE_PIS": float(ir.get("base_pis") or 0),
            "TPIS": float(ir.get("tpis") or 0),
            "CST_COFINS": ir.get("cst_cofins") or "01",
            "PCOFINS": float(ir.get("pcofins") or 0),
            "BASE_COFINS": float(ir.get("base_cofins") or 0),
            "TCOFINS": float(ir.get("tcofins") or 0),
            "IBPT_VLR_IMPOSTO": 0,
            "VALOR_CALCULO": vtot,
            "DCIMAIS_CALCULO": qtd,
            "UNID_COM": ir.get("unidade") or "UN",
            "UNID_TRIB": ir.get("unidade") or "UN",
            "DSC_CADASTRO": (ir.get("descricao") or "")[:120],
            "ACESSORIOS": "",
            "PEDIDO_CLIENTE": ir.get("pedido_cliente") or "",
            "ITEM_PED_CLIENTE": ir.get("item_ped_cliente") or 0,
            "EX_TIPI": "",
            "VLICMSDESON": 0,
            "MOTDESON": "",
            "PCRED_SN": 0,
            "VCRED_ICMS_SN": 0,
            "PORC_IVA": 0,
            "ICMS_ST": 0,
            "TICMS_RETIDO": float(ir.get("ticms_retido") or 0),
            "BASE_ICMS_ST": float(ir.get("base_icms_st") or 0),
            "PERC_DEV": 0,
            "P_FCP_UF_DEST": 0,
            "V_FCP_UF_DEST": 0,
            "P_ICMS_INTER": 0,
            "V_ICMS_UF_DEST": 0,
            "V_ICMS_UF_REMET": 0,
            "VLR_IMP": 0,
            "COD_BENEF": "",
        })
        # Busca NCM do produto
        if ir.get("produto"):
            cur = None
            try:
                with get_cursor() as c2:
                    c2.execute(
                        "SELECT ncm FROM erp_produtos WHERE codigo_erp = %s",
                        [ir["produto"]],
                    )
                    prod_row = c2.fetchone()
                    if prod_row and prod_row["ncm"]:
                        itens[-1]["NCM"] = prod_row["ncm"]
            except Exception:
                pass

    if not itens:
        raise ValueError(f"Nota REGISTRO={registro_erp} sem itens.")

    # ── Monta fatfin ───────────────────────────────────────────────────────
    fatfin = []
    for row in parcelas_rows:
        pr = dict(row)
        fatfin.append({
            "ITEM": pr.get("parcela"),
            "VALOR": float(pr.get("valor") or 0),
            "VENCIMENTO": pr.get("vencimento"),
            "TIPO_VENC": pr.get("tipo_venc") or 1,
            "CONTA": pr.get("conta") or "",
            "CNPJ_OPERADORA": "",
            "BANDEIRA": 0,
            "AUTORIZACAO": "",
        })

    # ── Monta transp ───────────────────────────────────────────────────────
    transp = None
    transportadora = fr.get("transportadora")
    trans_nome = fr.get("trans_nome") or ""
    trans_cgc = fr.get("trans_cgc") or ""
    if transportadora or trans_nome:
        transp = {
            "TRANSPORTE": transportadora or 9,
            "TRANS_NOME": trans_nome,
            "TRANS_CGC": trans_cgc,
            "TRANS_INSCR": fr.get("trans_inscr") or "",
            "TRANS_ENDER": fr.get("trans_ender") or "",
            "TRANS_CIDADE": fr.get("trans_cidade") or "",
            "TRANS_ESTADO": fr.get("trans_estado") or "",
            "PLACA": fr.get("placa") or "",
            "PLACA_ESTADO": fr.get("placa_estado") or "",
            "VOL_QUANTIDADE": fr.get("vol_quantidade") or 0,
            "VOL_ESPECIE": fr.get("vol_especie") or "",
            "VOL_MARCA": "",
            "VOL_NUMERO": "",
            "PESO_LIQUIDO": float(fr.get("peso_liquido") or 0),
            "PESO_BRUTO": float(fr.get("peso_bruto") or 0),
        }

    return {
        "fatnot": fatnot,
        "cademp": cademp,
        "cadcli": cadcli,
        "fatope": fatope,
        "itens": itens,
        "fatfin": fatfin,
        "transp": transp,
    }
