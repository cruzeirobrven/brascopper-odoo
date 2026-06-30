"""
API REST para consulta de dados do ERP (tabelas espelho no PostgreSQL).
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query

from api.auth import verificar_api_key
from api.database import (
    buscar_erp_empresa, listar_erp_empresas,
    buscar_erp_cliente, buscar_erp_produto,
    buscar_erp_nota, buscar_erp_operacao,
)

router = APIRouter(dependencies=[Depends(verificar_api_key)])
logger = logging.getLogger(__name__)


@router.get("/erp/empresas")
async def listar_empresas():
    dados = listar_erp_empresas()
    return {"empresas": dados}


@router.get("/erp/empresas/{codigo_erp}")
async def obter_empresa(codigo_erp: int):
    dados = buscar_erp_empresa(codigo_erp=codigo_erp)
    if not dados:
        raise HTTPException(404, "Empresa nao encontrada")
    return dados


@router.get("/erp/clientes")
async def pesquisar_clientes(
    cnpj_cpf: str = Query(None),
    nome: str = Query(None),
    codigo_erp: int = Query(None),
    empresa: int = Query(None),
    limit: int = Query(20, ge=1, le=200),
):
    dados = buscar_erp_cliente(
        cnpj_cpf=cnpj_cpf, nome=nome,
        codigo_erp=codigo_erp, empresa_erp=empresa,
        limit=limit,
    )
    return {"clientes": dados, "total": len(dados)}


@router.get("/erp/produtos")
async def pesquisar_produtos(
    codigo: str = Query(None),
    descricao: str = Query(None),
    ncm: str = Query(None),
    limit: int = Query(20, ge=1, le=200),
):
    dados = buscar_erp_produto(
        codigo=codigo, descricao=descricao,
        ncm=ncm, limit=limit,
    )
    return {"produtos": dados, "total": len(dados)}


@router.get("/erp/notas")
async def pesquisar_notas(
    registro: int = Query(None),
    nota: int = Query(None),
    serie: str = Query(None),
    cnpj_cpf: str = Query(None),
    limit: int = Query(20, ge=1, le=200),
):
    dados = buscar_erp_nota(
        registro=registro, nota=nota,
        serie=serie, cnpj_cpf=cnpj_cpf,
        limit=limit,
    )
    return {"notas": dados, "total": len(dados)}


@router.get("/erp/operacoes")
async def listar_operacoes(codigo: int = Query(None)):
    dados = buscar_erp_operacao(codigo=codigo)
    return {"operacoes": dados}
