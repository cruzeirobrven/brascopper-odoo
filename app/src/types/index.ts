export interface Empresa {
  codigo_erp: number
  cnpj: string
  nome: string
  fantasia?: string
  ie_federal?: string
  inscricao_estadual?: string
  endereco?: string
  numero?: string
  bairro?: string
  cidade?: string
  estado?: string
  cep?: string
  fone?: string
  email?: string
  simples?: boolean
  certificado_serial?: string
  ambiente?: number
  serie_nfe?: number
  ultimo_numnf?: number
}

export interface Cliente {
  codigo_erp: number
  empresa_erp: number
  cnpj_cpf: string
  nome: string
  fantasia?: string
  endereco?: string
  numero?: string
  bairro?: string
  cidade?: string
  estado?: string
  cep?: string
  fone_1?: string
  email?: string
  consumidor_final?: boolean
  contribuinte?: boolean
  ativo?: boolean
}

export interface Produto {
  codigo_erp: string
  descricao: string
  ncm?: string
  cest?: string
  unidade?: string
  cfop?: string
  icms_cst?: string
  icms_aliquota?: number
  ipi_cst?: string
  ipi_aliquota?: number
  pis_cst?: string
  pis_aliquota?: number
  cofins_cst?: string
  cofins_aliquota?: number
  peso_liquido?: number
  peso_bruto?: number
}

export interface NotaFiscal {
  registro: number
  empresa: number
  nota: number
  serie: string
  emissao: string
  saida?: string
  operacao: number
  situacao?: number
  nome: string
  cgc_cpf: string
  endereco?: string
  bairro?: string
  cidade?: string
  estado?: string
  tproduto?: number
  tgeral?: number
  base_icms?: number
  valor_icms?: number
}

export interface Operacao {
  operacao: number
  descricao: string
  descricao_nf?: string
  movimentacao?: number
  cst_icms?: string
  cst_ipi?: string
  cst_pis?: string
  cst_cofins?: string
}

export type TabId = 'dashboard' | 'empresas' | 'clientes' | 'produtos' | 'notas' | 'emitir'
