from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal
from datetime import date


class EmitenteSchema(BaseModel):
    cnpj_cpf: str = Field(..., max_length=14)
    ie: str = ""
    razao_social: str = Field(..., max_length=60)
    fantasia: str = ""
    logradouro: str = Field(..., max_length=60)
    numero: str = ""
    complemento: str = ""
    bairro: str = Field(..., max_length=60)
    cod_municipio: int = Field(..., ge=1000000, le=9999999)
    municipio: str = Field(..., max_length=60)
    uf: str = Field(..., min_length=2, max_length=2)
    cep: str = ""
    fone: str = ""
    crt: str = Field("3", pattern=r"^[13]$")
    certificado_serial: str = ""


class DestinatarioSchema(BaseModel):
    cnpj_cpf: str = Field(..., max_length=14)
    ie: str = ""
    isuf: str = ""
    ind_ie_dest: str = Field("9", pattern=r"^[129]$")
    razao_social: str = Field(..., max_length=60)
    logradouro: str = Field(..., max_length=60)
    numero: str = ""
    complemento: str = ""
    bairro: str = Field(..., max_length=60)
    cod_municipio: int = Field(..., ge=1000000, le=9999999)
    municipio: str = Field(..., max_length=60)
    uf: str = Field(..., min_length=2, max_length=2)
    cep: str = ""
    fone: str = ""
    cod_pais: int = 1058
    nome_pais: str = "BRASIL"


class ItemSchema(BaseModel):
    produto: str = Field(..., max_length=60)
    descricao: str = Field(..., max_length=120)
    ncm: str = Field(..., min_length=8, max_length=8)
    cfop: str = Field(..., min_length=4, max_length=4)
    unidade: str = "UN"
    quantidade: Decimal = Field(..., gt=0)
    valor_unitario: Decimal = Field(..., ge=0)
    valor_total: Decimal = Field(..., ge=0)
    tipo_item: int = 0
    desconto: Decimal = Decimal("0")
    outras: Decimal = Decimal("0")
    despesas: Decimal = Decimal("0")
    cst_icms: str = "00"
    csosn: str = ""
    origem: int = 0
    aliquota_icms: Decimal = Decimal("0")
    base_icms: Decimal = Decimal("0")
    valor_icms: Decimal = Decimal("0")
    reducao_icms: Decimal = Decimal("0")
    cst_ipi: str = "99"
    aliquota_ipi: Decimal = Decimal("0")
    base_ipi: Decimal = Decimal("0")
    valor_ipi: Decimal = Decimal("0")
    cst_pis: str = "01"
    aliquota_pis: Decimal = Decimal("0")
    base_pis: Decimal = Decimal("0")
    valor_pis: Decimal = Decimal("0")
    cst_cofins: str = "01"
    aliquota_cofins: Decimal = Decimal("0")
    base_cofins: Decimal = Decimal("0")
    valor_cofins: Decimal = Decimal("0")
    cest: str = ""
    ibpt_vlr_imposto: Decimal = Decimal("0")


class ParcelaSchema(BaseModel):
    valor: Decimal = Field(..., gt=0)
    vencimento: Optional[str] = None
    tipo_venc: int = 1
    conta: str = ""
    cnpj_operadora: str = ""
    bandeira: int = 0
    autorizacao: str = ""


class TransportadorSchema(BaseModel):
    modalidade_frete: int = 9
    cnpj_cpf: str = ""
    razao_social: str = ""
    ie: str = ""
    logradouro: str = ""
    municipio: str = ""
    uf: str = ""
    placa: str = ""
    placa_estado: str = ""
    qtd_volumes: int = 0
    especie: str = ""
    marca: str = ""
    numero_volumes: str = ""
    peso_liquido: Decimal = Decimal("0")
    peso_bruto: Decimal = Decimal("0")


class GerarNFeRequest(BaseModel):
    registro: int = 0
    empresa: int = 1
    operacao: int = 0
    nota: int = 0
    serie: int = 0
    modelo: int = 55
    emissao: Optional[str] = None
    saida: Optional[str] = None
    tp_saida_entr: int = 1
    consumidor_final: str = "N"
    venda_site: str = "N"
    finalidade: int = 1
    observacao: str = ""

    emitente: EmitenteSchema
    destinatario: DestinatarioSchema
    itens: list[ItemSchema]
    parcelas: list[ParcelaSchema] = []
    transportador: Optional[TransportadorSchema] = None

    # DIFAL
    p_icms_inter_part: Decimal = Decimal("0")
    p_icms_uf_dest: Decimal = Decimal("0")
    v_fcp_uf_dest: Decimal = Decimal("0")
    v_icms_uf_dest: Decimal = Decimal("0")
    v_icms_uf_remet: Decimal = Decimal("0")
    acordo_dif_aliq: str = "N"


class NFeResponse(BaseModel):
    sucesso: bool
    mensagem: str
    chave: str = ""
    numero: str = ""
    protocolo: str = ""
    xml: str = ""


class CancelarRequest(BaseModel):
    justificativa: str = Field(..., min_length=15)


class CCeRequest(BaseModel):
    correcao: str = Field(..., min_length=15)


class InutilizarRequest(BaseModel):
    cnpj: str = Field(..., min_length=14, max_length=14)
    modelo: str = "55"
    serie: str = "1"
    n_nota_inicial: str
    n_nota_final: str
    justificativa: str = Field(..., min_length=15)
