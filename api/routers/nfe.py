import logging
from decimal import Decimal
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from pydantic import BaseModel
from api.auth import verificar_api_key
from api.config import settings
from api.schemas import (
    GerarNFeRequest, NFeResponse, CancelarRequest,
    CCeRequest, InutilizarRequest,
)
from api.services.nfe_ini import _gerar_linhas_ini, _gerar_chave_acesso, NFeIniGerado
from api.services.acbr_monitor import ACBrMonitorClient, ACBrMonitorError
from api.services.emissao_erp import buscar_nota_completa


class EmitirDoErpRequest(BaseModel):
    registro_erp: int
    tp_amb: int = 2

router = APIRouter(dependencies=[Depends(verificar_api_key)])
logger = logging.getLogger(__name__)


def _get_acbr() -> ACBrMonitorClient:
    return ACBrMonitorClient(
        host=settings.acbr_host,
        port=settings.acbr_port,
        timeout=settings.acbr_timeout,
    )


def _dados_para_dict(req: GerarNFeRequest) -> dict:
    """Converte o request Pydantic para o formato esperado pelo gerador INI."""
    emit = req.emitente
    dest = req.destinatario

    fatnot = {
        "REGISTRO": req.registro,
        "EMPRESA": req.empresa,
        "NOTA": req.nota,
        "SERIE": req.serie,
        "MODELO": req.modelo,
        "EMISSAO": req.emissao,
        "SAIDA": req.saida,
        "TP_SAIDA_ENTR": req.tp_saida_entr,
        "SITUACAO": 0,
        "OPERACAO": req.operacao,
        "DESTINATARIO": req.destinatario.cnpj_cpf,
        "NOME": dest.razao_social,
        "CGC_CPF": dest.cnpj_cpf,
        "INSCRICAO_RG": dest.ie,
        "ENDERECO": dest.logradouro,
        "NUMERO": dest.numero,
        "COMPLEMENTO": dest.complemento,
        "BAIRRO": dest.bairro,
        "CIDADE": dest.municipio,
        "ESTADO": dest.uf,
        "CEP": dest.cep,
        "CONSUMIDOR": "S" if req.consumidor_final == "S" else "N",
        "VENDA_SITE": req.venda_site,
        "OBS_CORPO_NF": req.observacao,
        "P_ICMS_INTER_PART": float(req.p_icms_inter_part),
        "P_ICMS_UF_DEST": float(req.p_icms_uf_dest),
        "V_FCP_UF_DEST": float(req.v_fcp_uf_dest),
        "V_ICMS_UF_DEST": float(req.v_icms_uf_dest),
        "V_ICMS_UF_REMET": float(req.v_icms_uf_remet),
        "TDESCONTO": 0,
        "TFRETE": 0,
        "TSEGURO": 0,
        "TDESPESAS": 0,
        "TPRODUTO": sum(float(i.valor_total) for i in req.itens),
        "TGERAL": sum(float(i.valor_total) for i in req.itens),
        "BASE_ICMS": 0,
        "VALOR_ICMS": 0,
        "BASESUB": 0,
        "TICMSSUB": 0,
        "BASE_PIS": 0,
        "BASE_COFINS": 0,
        "TPIS": 0,
        "TCOFINS": 0,
        "TOTICMSDESONE": 0,
        "VLR_II": 0,
        "TSERVICO": 0,
        "INSCRICAO_SUFRAMA": dest.isuf,
        "INDIEDEST": int(dest.ind_ie_dest) if dest.ind_ie_dest.isdigit() else 0,
        "PRESENCIAL": "1",
        "VENDAINT": "0",
        "REVENDA": "N",
        "CONTRIBUINTE": "",
    }

    cademp = {
        "EMPRESA": req.empresa,
        "NOME": emit.razao_social,
        "TIPO_INSCRICAO": 1,
        "CNPJ": emit.cnpj_cpf,
        "INSCRICAO_FEDERAL": emit.cnpj_cpf,
        "INSCRICAO_ESTADUAL": emit.ie,
        "ENDERECO": emit.logradouro,
        "NUMERO": emit.numero,
        "COMPLEMENTO": emit.complemento,
        "BAIRRO": emit.bairro,
        "CIDADE": emit.municipio,
        "ESTADO": emit.uf,
        "CEP": emit.cep,
        "FONE": emit.fone,
        "COD_MUN_IBGE": str(emit.cod_municipio),
        "MUNICIPIO_IBGE": emit.municipio,
        "SIMPLES": 1 if emit.crt == "1" else 3,
        "EMAIL": "",
        "CERTIFICADO_SERIAL": emit.certificado_serial or "",
    }

    cadcli = {
        "CLIENTE": dest.cnpj_cpf,
        "COD_MUN_IBGE": str(dest.cod_municipio),
        "CIDADE": dest.municipio,
        "ESTADO": dest.uf,
        "ENDERECO": dest.logradouro,
        "NUMERO": dest.numero,
        "COMPLEMENTO": dest.complemento,
        "BAIRRO": dest.bairro,
        "CEP": dest.cep,
        "CGC_CPF": dest.cnpj_cpf,
        "INSCRICAO_RG": dest.ie,
        "FONE": dest.fone,
        "PAIS": dest.cod_pais,
        "NOME_PAIS": dest.nome_pais,
    }

    itens = []
    for i, item in enumerate(req.itens):
        itens.append({
            "ITEM": i + 1,
            "PRODUTO": item.produto,
            "DESCRICAO": item.descricao,
            "QUANTIDADE": float(item.quantidade),
            "UNIDADE": item.unidade,
            "VALOR": float(item.valor_unitario),
            "TPRODUTO": float(item.valor_total),
            "CFOP": item.cfop,
            "NCM": item.ncm,
            "CEST": item.cest,
            "ORIGEM": item.origem,
            "TIPO_ITEM": item.tipo_item,
            "DESCONTO": float(item.desconto),
            "OUTRAS": float(item.outras),
            "DESPESAS": float(item.despesas),
            "ICMS_CST": item.cst_icms,
            "PICMS": float(item.aliquota_icms),
            "BASE_ICMS": float(item.base_icms),
            "TICMS": float(item.valor_icms),
            "REDUCAO": float(item.reducao_icms),
            "CST_IPI": item.cst_ipi,
            "PIPI": float(item.aliquota_ipi),
            "BASE_IPI": float(item.base_ipi),
            "TIPI": float(item.valor_ipi),
            "CST_PIS": item.cst_pis,
            "PPIS": float(item.aliquota_pis),
            "BASE_PIS": float(item.base_pis),
            "TPIS": float(item.valor_pis),
            "CST_COFINS": item.cst_cofins,
            "PCOFINS": float(item.aliquota_cofins),
            "BASE_COFINS": float(item.base_cofins),
            "TCOFINS": float(item.valor_cofins),
            "IBPT_VLR_IMPOSTO": float(item.ibpt_vlr_imposto),
            "VALOR_CALCULO": float(item.valor_unitario * item.quantidade),
            "DCIMAIS_CALCULO": float(item.quantidade),
            "UNID_COM": item.unidade,
            "UNID_TRIB": item.unidade,
            "ICMS_CST": item.cst_icms,
            "IPI_CST": item.cst_ipi,
            "PIS_CST": item.cst_pis,
            "COFINS_CST": item.cst_cofins,
            "DSC_CADASTRO": item.descricao[:120],
            "ACESSORIOS": "",
            "PEDIDO_CLIENTE": "",
            "ITEM_PED_CLIENTE": 0,
            "EX_TIPI": "",
            "VLICMSDESON": 0,
            "MOTDESON": "",
            "PCRED_SN": 0,
            "VCRED_ICMS_SN": 0,
            "PORC_IVA": 0,
            "ICMS_ST": 0,
            "TICMS_RETIDO": 0,
            "BASE_ICMS_ST": 0,
            "PERC_DEV": 0,
            "P_FCP_UF_DEST": 0,
            "V_FCP_UF_DEST": 0,
            "P_ICMS_INTER": 0,
            "V_ICMS_UF_DEST": 0,
            "V_ICMS_UF_REMET": 0,
            "VLR_IMP": 0,
            "COD_BENEF": "",
        })

    fatfin = []
    for p in req.parcelas:
        fatfin.append({
            "ITEM": len(fatfin) + 1,
            "VALOR": float(p.valor),
            "VENCIMENTO": p.vencimento,
            "TIPO_VENC": p.tipo_venc,
            "CONTA": p.conta,
            "CNPJ_OPERADORA": p.cnpj_operadora,
            "BANDEIRA": p.bandeira,
            "AUTORIZACAO": p.autorizacao,
        })

    fatope = {
        "DESCRICAO_NF": "VENDA",
        "MOVIMENTACAO": 1,
        "FIN_DEVOLUCAO": "N" if req.finalidade != 4 else "S",
        "ACORDO_DIF_ALIQ": req.acordo_dif_aliq,
    }

    transp = None
    if req.transportador:
        t = req.transportador
        transp = {
            "TRANSPORTE": t.modalidade_frete,
            "TRANS_NOME": t.razao_social,
            "TRANS_CGC": t.cnpj_cpf,
            "TRANS_INSCR": t.ie,
            "TRANS_ENDER": t.logradouro,
            "TRANS_CIDADE": t.municipio,
            "TRANS_ESTADO": t.uf,
            "PLACA": t.placa,
            "PLACA_ESTADO": t.placa_estado,
            "VOL_QUANTIDADE": t.qtd_volumes,
            "VOL_ESPECIE": t.especie,
            "VOL_MARCA": t.marca,
            "VOL_NUMERO": t.numero_volumes,
            "PESO_LIQUIDO": float(t.peso_liquido),
            "PESO_BRUTO": float(t.peso_bruto),
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


@router.post("/nfe/gerar", response_model=NFeResponse)
async def gerar_nfe(req: GerarNFeRequest):
    dados = _dados_para_dict(req)

    ft = dados["fatnot"]
    ce = dados["cademp"]
    tp_amb = 2  # homologacao por padrao na API

    linhas, nota, serie, cnf, chave = _gerar_linhas_ini(
        fatnot=dados["fatnot"],
        cademp=dados["cademp"],
        cadcli=dados["cadcli"],
        fatope=dados["fatope"],
        itens=dados["itens"],
        fatfin=dados["fatfin"],
        transp=dados["transp"],
        cod_benef_map={},
        tp_amb=tp_amb,
    )

    acbr = _get_acbr()
    try:
        cert_serial = ce.get("CERTIFICADO_SERIAL") or settings.certificado_serial
        if cert_serial:
            acbr.set_certificado(cert_serial)
        resposta = acbr.criar_enviar_nfe("\r\n".join(linhas))
    except ACBrMonitorError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return NFeResponse(
        sucesso=not resposta.upper().startswith("ERRO"),
        mensagem=resposta,
        chave=chave,
        numero=str(nota),
    )


@router.post("/nfe/emitir-do-erp", response_model=NFeResponse)
async def emitir_do_erp(req: EmitirDoErpRequest):
    try:
        dados = buscar_nota_completa(req.registro_erp)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    linhas, nota, serie, cnf, chave = _gerar_linhas_ini(
        fatnot=dados["fatnot"],
        cademp=dados["cademp"],
        cadcli=dados["cadcli"],
        fatope=dados["fatope"],
        itens=dados["itens"],
        fatfin=dados["fatfin"],
        transp=dados["transp"],
        cod_benef_map={},
        tp_amb=req.tp_amb,
    )

    acbr = _get_acbr()
    try:
        cert_serial = dados["cademp"].get("CERTIFICADO_SERIAL") or settings.certificado_serial
        if cert_serial:
            acbr.set_certificado(cert_serial)
        resposta = acbr.criar_enviar_nfe("\r\n".join(linhas))
    except ACBrMonitorError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return NFeResponse(
        sucesso=not resposta.upper().startswith("ERRO"),
        mensagem=resposta,
        chave=chave,
        numero=str(nota),
    )


@router.get("/nfe/{chave}", response_model=NFeResponse)
async def consultar_nfe(chave: str):
    acbr = _get_acbr()
    try:
        resposta = acbr.consultar(chave)
    except ACBrMonitorError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return NFeResponse(sucesso=True, mensagem=resposta, chave=chave)


@router.post("/nfe/{chave}/cancelar", response_model=NFeResponse)
async def cancelar_nfe(chave: str, req: CancelarRequest):
    acbr = _get_acbr()
    try:
        resposta = acbr.cancelar(chave, req.justificativa)
    except ACBrMonitorError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return NFeResponse(
        sucesso=not resposta.upper().startswith("ERRO"),
        mensagem=resposta,
        chave=chave,
    )


@router.post("/nfe/inutilizar", response_model=NFeResponse)
async def inutilizar_nfe(req: InutilizarRequest):
    acbr = _get_acbr()
    try:
        resposta = acbr.inutilizar(
            req.cnpj, req.modelo, req.serie,
            req.n_nota_inicial, req.n_nota_final, req.justificativa,
        )
    except ACBrMonitorError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return NFeResponse(sucesso=not resposta.upper().startswith("ERRO"), mensagem=resposta)


@router.post("/nfe/{chave}/cce", response_model=NFeResponse)
async def cce_nfe(chave: str, req: CCeRequest):
    acbr = _get_acbr()
    try:
        resposta = acbr.cce(chave, req.correcao)
    except ACBrMonitorError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return NFeResponse(sucesso=True, mensagem=resposta, chave=chave)
