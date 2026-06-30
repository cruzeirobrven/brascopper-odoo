"""
Importa dados do SQL Server (brven_brascopper) para PostgreSQL (nfehub)
Mapeamento direto das colunas reais do SQL Server.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pymssql
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime

SQL = {
    'server': '100.64.83.82:1433',
    'user': 'sa',
    'password': 'MULETA',
    'database': 'brven_brascopper',
    'charset': 'utf8',
    'timeout': 30,
}

PG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'nfehub',
    'password': 'nfehub123',
    'dbname': 'nfehub',
}

def v(val):
    if val is None:
        return None
    if isinstance(val, str):
        s = val.rstrip()
        return s if s else None
    return val

def to_bool(val):
    if val is None or val == 0 or val == '0' or val == 'N':
        return False
    return True

def to_str(val, maxlen=None):
    s = v(val)
    if s is not None and maxlen and len(s) > maxlen:
        s = s[:maxlen]
    return s

def to_num(val, default=0):
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def query(conn, sql):
    c = conn.cursor(as_dict=True)
    c.execute(sql)
    return c.fetchall()

def upsert(pg, table, data, conflict_col):
    if not data:
        return
    cols = list(data[0].keys())
    colnames = ','.join(cols)
    rows = [[r[c] for c in cols] for r in data]

    if conflict_col:
        updates = ','.join(f'{c}=EXCLUDED.{c}' for c in cols if c != conflict_col)
        if not updates:
            updates = f'{conflict_col}=EXCLUDED.{conflict_col}'
        sql = f'INSERT INTO {table} ({colnames}) VALUES %s ON CONFLICT ({conflict_col}) DO UPDATE SET {updates}'
    else:
        sql = f'INSERT INTO {table} ({colnames}) VALUES %s ON CONFLICT DO NOTHING'

    execute_values(pg.cursor(), sql, rows, page_size=500)
    pg.commit()

# ── Importers ────────────────────────────────────────────────────────────────

def ler_empresas(sql):
    rows = query(sql, '''
        SELECT EMPRESA, NOME, CNPJ, INSCRICAO_FEDERAL AS IE_FEDERAL,
               INSCRICAO_ESTADUAL, INSCRICAO_MUNICIPAL,
               ENDERECO, NUMERO, COMPLEMENTO, BAIRRO, CIDADE, ESTADO, CEP,
               FONE, EMAIL, SIMPLES, COD_MUNICIPIO, MUNICIPIO_IBGE, COD_MUN_IBGE,
               SIGLA_PAIS
        FROM CADEMP
    ''')
    result = []
    for r in rows:
        result.append({
            'codigo_erp': r['EMPRESA'],
            'cnpj': to_str(r['CNPJ']),
            'nome': to_str(r['NOME']),
            'ie_federal': to_str(r['IE_FEDERAL']),
            'inscricao_estadual': to_str(r['INSCRICAO_ESTADUAL']),
            'inscricao_municipal': to_str(r['INSCRICAO_MUNICIPAL']),
            'endereco': to_str(r['ENDERECO']),
            'numero': to_str(r['NUMERO']),
            'complemento': to_str(r['COMPLEMENTO']),
            'bairro': to_str(r['BAIRRO']),
            'cidade': to_str(r['CIDADE']),
            'estado': to_str(r['ESTADO']),
            'cep': to_str(r['CEP']),
            'cod_mun_ibge': str(r.get('COD_MUNICIPIO') or r.get('COD_MUN_IBGE') or ''),
            'fone': to_str(r['FONE']),
            'email': to_str(r['EMAIL']),
            'simples': to_bool(r['SIMPLES']),
            'sigla_pais': to_str(r['SIGLA_PAIS']) or 'BRASIL',
            'cod_pais': 1058,
        })
    return result

def ler_clientes(sql):
    rows = query(sql, '''
        SELECT CLIENTE, MEMPRESA, CGC_CPF, NOME, FANTASIA, TIPO,
               CONSUMIDOR_FINAL, CONTRIBUINTE, INDIEDEST,
               ENDERECO1, NUMERO, COMPLEMENTO, BAIRRO1, CIDADE, ESTADO1, CEP1,
               ENDERECO, BAIRRO, CIDADE AS CIDADE2, ESTADO, CEP,
               FONE_1, FONE_2, EMAIL, INSCR_SUFRAMA,
               COD_PAIS, SIGLA_PAIS, COD_MUN_IBGE,
               ATIVO, BLOQUEADO
        FROM CADCLI
    ''')
    result = []
    for r in rows:
        end = to_str(r['ENDERECO1']) or to_str(r['ENDERECO'])
        bai = to_str(r['BAIRRO1']) or to_str(r['BAIRRO'])
        cid = to_str(r['CIDADE']) or to_str(r.get('CIDADE2'))
        est = to_str(r['ESTADO1']) or to_str(r['ESTADO'])
        cp  = to_str(r['CEP1']) or to_str(r['CEP'])

        result.append({
            'codigo_erp': r['CLIENTE'],
            'empresa_erp': r['MEMPRESA'],
            'cnpj_cpf': to_str(r['CGC_CPF']),
            'nome': to_str(r['NOME']),
            'fantasia': to_str(r['FANTASIA']),
            'tipo': r['TIPO'] or 0,
            'consumidor_final': to_bool(r['CONSUMIDOR_FINAL']),
            'contribuinte': to_bool(r['CONTRIBUINTE']),
            'ind_ie_dest': r['INDIEDEST'] or 9,
            'endereco': end,
            'numero': to_str(r['NUMERO']),
            'complemento': to_str(r['COMPLEMENTO']),
            'bairro': bai,
            'cidade': cid,
            'estado': est,
            'cep': cp,
            'cod_mun_ibge': to_str(r['COD_MUN_IBGE']),
            'fone_1': to_str(r['FONE_1']),
            'fone_2': to_str(r['FONE_2']),
            'email': to_str(r['EMAIL']),
            'insc_suframa': to_str(r['INSCR_SUFRAMA']),
            'cod_pais': r.get('COD_PAIS') or 1058,
            'sigla_pais': to_str(r['SIGLA_PAIS']) or 'BRASIL',
            'ativo': to_bool(r['ATIVO']),
            'bloqueado': to_bool(r['BLOQUEADO']),
        })
    return result

def ler_produtos(sql):
    rows = query(sql, '''
        SELECT PRODUTO, DESCRICAO, DESCR_TECNICA,
               GRUPO, VENDA, EAN_PRODUTO,
               NCM, CEST, UNIDADE, UNID_TRIB, UNID_COM,
               ORIGEM, ICMS_CST, ICMS, IPI_CST, IPI,
               PIS_CST, PPIS, COFINS_CST, PCOFINS,
               PESO_LIQUIDO, PESO_BRUTO, REDUCAO, ATIVO
        FROM ESTPRO
    ''')
    result = []
    for r in rows:
        result.append({
            'codigo_erp': to_str(r['PRODUTO']),
            'descricao': to_str(r['DESCRICAO']),
            'descricao_tecnica': to_str(r['DESCR_TECNICA']),
            'grupo': to_str(r['GRUPO']),
            'preco_venda': to_num(r.get('VENDA'), 0),
            'codigo_barras': to_str(r['EAN_PRODUTO']),
            'ncm': to_str(r['NCM']),
            'cest': to_str(r['CEST']),
            'unidade': to_str(r['UNIDADE']) or 'UN',
            'unid_trib': to_str(r['UNID_TRIB']),
            'unid_com': to_str(r['UNID_COM']),
            'origem': r['ORIGEM'] or 0,
            'icms_cst': to_str(r['ICMS_CST']),
            'icms_aliquota': to_num(r.get('ICMS'), 0),
            'ipi_cst': to_str(r['IPI_CST']),
            'ipi_aliquota': to_num(r.get('IPI'), 0),
            'pis_cst': to_str(r['PIS_CST']),
            'pis_aliquota': to_num(r.get('PPIS'), 0),
            'cofins_cst': to_str(r['COFINS_CST']),
            'cofins_aliquota': to_num(r.get('PCOFINS'), 0),
            'peso_liquido': to_num(r.get('PESO_LIQUIDO'), 0),
            'peso_bruto': to_num(r.get('PESO_BRUTO'), 0),
            'reducao': to_num(r.get('REDUCAO'), 0),
            'ativo': to_bool(r.get('ATIVO', True)),
        })
    return result

def ler_grupos_produtos(sql):
    rows = query(sql, '''
        SELECT GRUPO, DESCRICAO, GCNCM, TIPOP, CLAFI, SIGLA, GRNOM
        FROM ESTGRP
    ''')
    result = []
    for r in rows:
        result.append({
            'grupo': to_str(r['GRUPO']),
            'descricao': to_str(r['DESCRICAO']),
            'ncm': to_str(r['GCNCM']),
            'tipo_produto': to_str(r['TIPOP']),
            'classificacao': to_str(r['CLAFI']),
            'sigla': to_str(r['SIGLA']),
            'nome_comercial': to_str(r['GRNOM']),
        })
    return result

def ler_grupos_usuarios(sql):
    rows = query(sql, 'SELECT GRUPO, DESCRICAO FROM USUGRP')
    result = []
    for r in rows:
        result.append({
            'grupo': to_str(r['GRUPO']),
            'descricao': to_str(r['DESCRICAO']),
        })
    return result

def ler_usuarios(sql):
    rows = query(sql, '''
        SELECT USUARIO, SENHA, GRUPO, MASTER, EMAIL, FUNC, VENDEDOR, ATIVO
        FROM USUCAD
    ''')
    result = []
    for r in rows:
        result.append({
            'usuario': to_str(r['USUARIO']),
            'senha': to_str(r['SENHA']),
            'grupo': to_str(r['GRUPO']),
            'master': to_str(r['MASTER']),
            'email': to_str(r['EMAIL']),
            'funcionario_codigo': r.get('FUNC'),
            'vendedor_codigo': r.get('VENDEDOR'),
            'ativo': to_bool(r.get('ATIVO', True)),
        })
    return result

def ler_programas(sql):
    rows = query(sql, 'SELECT PROGRAMA, DESCRICAO FROM USUPRG')
    result = []
    for r in rows:
        result.append({
            'programa': to_str(r['PROGRAMA']),
            'descricao': to_str(r['DESCRICAO']),
        })
    return result

def ler_permissoes(sql):
    rows = query(sql, '''
        SELECT GRUPO, PROGRAMA, SO_CONSULTA, INSERCAO, ALTERACAO, DELECAO
        FROM USUOPC
    ''')
    result = []
    for r in rows:
        result.append({
            'grupo': to_str(r['GRUPO']),
            'programa': to_str(r['PROGRAMA']),
            'so_consulta': to_str(r['SO_CONSULTA']),
            'insercao': to_str(r['INSERCAO']),
            'alteracao': to_str(r['ALTERACAO']),
            'delecao': to_str(r['DELECAO']),
        })
    return result

def ler_notas(sql):
    rows = query(sql, '''
        SELECT REGISTRO, NOTA, SERIE, EMPRESA, MODELO,
               EMISSAO, SAIDA, OPERACAO, SITUACAO, DESTINATARIO,
               CONSUMIDOR, NOME, CGC_CPF,
               ENDERECO, BAIRRO, CIDADE, ESTADO, CEP, NUMERO, COMPLEMENTO, FONE,
               TPRODUTO, TGERAL, TDESCONTO, TFRETE, TSEGURO, TDESPESAS,
               BASE_ICMS, VALOR_ICMS, BASESUB, TICMSSUB,
               TIPI, TPIS, TCOFINS, TSERVICO,
               OBS_CORPO_NF,
               TRANSPORTADORA, TRANS_NOME, TRANS_CGC, TRANS_INSCR,
               TRANS_ENDER, TRANS_CIDADE, TRANS_ESTADO,
               PLACA, PLACA_ESTADO,
               VOL_QUANTIDADE, VOL_ESPECIE, PESO_BRUTO, PESO_LIQUIDO,
               VENDA_SITE, VENDAINT AS VENDA_INT,
               PRESENCIAL, CONTRIBUINTE,
               P_ICMS_INTER_PART, V_FCP_UF_DEST,
               V_ICMS_UF_DEST, V_ICMS_UF_REMET, TOTICMSDESON
        FROM FATNOT
    ''')
    result = []
    for r in rows:
        result.append({
            'registro': r['REGISTRO'],
            'empresa': r['EMPRESA'],
            'nota': r['NOTA'],
            'serie': to_str(r['SERIE']),
            'modelo': to_str(r['MODELO']) or '55',
            'emissao': r['EMISSAO'],
            'saida': r['SAIDA'],
            'operacao': r['OPERACAO'],
            'situacao': r['SITUACAO'],
            'destinatario': r['DESTINATARIO'],
            'consumidor': to_bool(r['CONSUMIDOR']),
            'nome': to_str(r['NOME']),
            'cgc_cpf': to_str(r['CGC_CPF']),
            'endereco': to_str(r['ENDERECO']),
            'bairro': to_str(r['BAIRRO']),
            'cidade': to_str(r['CIDADE']),
            'estado': to_str(r['ESTADO']),
            'cep': to_str(r['CEP']),
            'numero': to_str(r['NUMERO']),
            'complemento': to_str(r['COMPLEMENTO']),
            'fone': to_str(r['FONE']),
            'tproduto': to_num(r['TPRODUTO']),
            'tgeral': to_num(r['TGERAL']),
            'tdesconto': to_num(r['TDESCONTO']),
            'tfrete': to_num(r['TFRETE']),
            'tseguro': to_num(r['TSEGURO']),
            'tdespesas': to_num(r['TDESPESAS']),
            'base_icms': to_num(r['BASE_ICMS']),
            'valor_icms': to_num(r['VALOR_ICMS']),
            'basesub': to_num(r['BASESUB']),
            'ticmssub': to_num(r['TICMSSUB']),
            'tipi': to_num(r['TIPI']),
            'tpis': to_num(r['TPIS']),
            'tcofins': to_num(r['TCOFINS']),
            'tservico': to_num(r['TSERVICO']),
            'obs_corpo_nf': to_str(r['OBS_CORPO_NF']),
            'transportadora': r['TRANSPORTADORA'],
            'trans_nome': to_str(r['TRANS_NOME']),
            'trans_cgc': to_str(r['TRANS_CGC']),
            'trans_inscr': to_str(r['TRANS_INSCR']),
            'trans_ender': to_str(r['TRANS_ENDER']),
            'trans_cidade': to_str(r['TRANS_CIDADE']),
            'trans_estado': to_str(r['TRANS_ESTADO']),
            'placa': to_str(r['PLACA']),
            'placa_estado': to_str(r['PLACA_ESTADO']),
            'vol_quantidade': to_num(r['VOL_QUANTIDADE']),
            'vol_especie': to_str(r['VOL_ESPECIE']),
            'peso_bruto': to_num(r['PESO_BRUTO']),
            'peso_liquido': to_num(r['PESO_LIQUIDO']),
            'venda_site': to_bool(r['VENDA_SITE']),
            'venda_int': to_bool(r.get('VENDA_INT', False)),
            'presencial': to_bool(r.get('PRESENCIAL', True)),
            'contribuinte': to_bool(r.get('CONTRIBUINTE', False)),
            'p_icms_inter_part': to_num(r['P_ICMS_INTER_PART']),
            'v_fcp_uf_dest': to_num(r['V_FCP_UF_DEST']),
            'v_icms_uf_dest': to_num(r['V_ICMS_UF_DEST']),
            'v_icms_uf_remet': to_num(r['V_ICMS_UF_REMET']),
            'toticmsdeson': to_num(r['TOTICMSDESON']),
        })
    return result

def ler_itens(sql):
    rows = query(sql, '''
        SELECT REGISTRO, ITEM, PRODUTO, DESCRICAO,
               QUANTIDADE, UNIDADE, VALOR, CFOP,
               BASE_ICMS, TICMS, PICMS,
               BASE_ICMS_ST, TICMS_ST, TICMS_RETIDO,
               REDUCAO_BASE_ICMS AS REDUCAO,
               DESCONTO, DESPESAS,
               BASE_IPI, TIPI, PIPI, CST_IPI,
               BASE_PIS, TPIS, PPIS, CST_PIS,
               BASE_COFINS, TCOFINS, PCOFINS, CST_COFINS,
               CEST, PEDIDO_CLIENTE, ITEM_PED_CLIENTE
        FROM FATITN
    ''')
    result = []
    for r in rows:
        result.append({
            'registro': r['REGISTRO'],
            'item': r['ITEM'],
            'produto': to_str(r['PRODUTO']),
            'descricao': to_str(r['DESCRICAO']),
            'quantidade': to_num(r['QUANTIDADE']),
            'unidade': to_str(r['UNIDADE']) or 'UN',
            'valor': to_num(r['VALOR']),
            'cfop': to_str(r['CFOP']),
            'base_icms': to_num(r['BASE_ICMS']),
            'ticms': to_num(r['TICMS']),
            'picms': to_num(r['PICMS']),
            'base_icms_st': to_num(r['BASE_ICMS_ST']),
            'ticms_st': to_num(r['TICMS_ST']),
            'ticms_retido': to_num(r['TICMS_RETIDO']),
            'reducao': to_num(r.get('REDUCAO')),
            'desconto': to_num(r['DESCONTO']),
            'despesas': to_num(r['DESPESAS']),
            'base_ipi': to_num(r['BASE_IPI']),
            'tipi': to_num(r['TIPI']),
            'pipi': to_num(r['PIPI']),
            'cst_ipi': to_str(r['CST_IPI']),
            'base_pis': to_num(r['BASE_PIS']),
            'tpis': to_num(r['TPIS']),
            'ppis': to_num(r['PPIS']),
            'cst_pis': to_str(r['CST_PIS']),
            'base_cofins': to_num(r['BASE_COFINS']),
            'tcofins': to_num(r['TCOFINS']),
            'pcofins': to_num(r['PCOFINS']),
            'cst_cofins': to_str(r['CST_COFINS']),
            'cest': to_str(r['CEST']),
            'pedido_cliente': to_str(r['PEDIDO_CLIENTE']),
            'item_ped_cliente': r.get('ITEM_PED_CLIENTE') or 0,
        })
    return result

def ler_parcelas(sql):
    rows = query(sql, '''
        SELECT REGISTRO, PARCELA, VENCIMENTO, VALOR, TIPO_VENC, CONTA
        FROM FATFIN
    ''')
    result = []
    for r in rows:
        venc = r['VENCIMENTO']
        if isinstance(venc, datetime):
            venc = venc.date()
        result.append({
            'registro': r['REGISTRO'],
            'parcela': r['PARCELA'],
            'vencimento': venc,
            'valor': to_num(r['VALOR']),
            'tipo_venc': r['TIPO_VENC'] or 1,
            'conta': to_str(r['CONTA']),
        })
    return result

def ler_operacoes(sql):
    rows = query(sql, '''
        SELECT OPERACAO, DESCRICAO, DESCRICAO_NF,
               MOVIMENTACAO, FIN_DEVOLUCAO, ACORDO_DIF_ALIQ,
               TIPO_ICMS, TIPO_IPI,
               CST_ICMS, CST_IPI, CST_PIS, CST_COFINS
        FROM FATOPE
    ''')
    result = []
    for r in rows:
        result.append({
            'operacao': r['OPERACAO'],
            'descricao': to_str(r['DESCRICAO']),
            'descricao_nf': to_str(r['DESCRICAO_NF']),
            'movimentacao': r['MOVIMENTACAO'] or 1,
            'fin_devolucao': to_bool(r['FIN_DEVOLUCAO']),
            'acordo_dif_aliq': to_bool(r['ACORDO_DIF_ALIQ']),
            'tipo_icms': r['TIPO_ICMS'] or 0,
            'tipo_ipi': r['TIPO_IPI'] or 0,
            'cst_icms': to_str(r['CST_ICMS']),
            'cst_ipi': to_str(r['CST_IPI']),
            'cst_pis': to_str(r['CST_PIS']),
            'cst_cofins': to_str(r['CST_COFINS']),
        })
    return result

# ── Main ─────────────────────────────────────────────────────────────────────

TABELAS = {
    'empresas':          ('erp_empresas',         'codigo_erp',   ler_empresas),
    'clientes':          ('erp_clientes',         None,           ler_clientes),
    'produtos':          ('erp_produtos',         'codigo_erp',   ler_produtos),
    'notas':             ('erp_notas',            'registro',     ler_notas),
    'itens':             ('erp_itens_nota',       None,           ler_itens),
    'parcelas':          ('erp_parcelas',         None,           ler_parcelas),
    'operacoes':         ('erp_operacoes',        'operacao',     ler_operacoes),
    'grupos_produtos':   ('erp_grupos_produtos',  'grupo',        ler_grupos_produtos),
    'grupos_usuarios':   ('erp_grupos_usuarios',  'grupo',        ler_grupos_usuarios),
    'usuarios':          ('erp_usuarios',         'usuario',      ler_usuarios),
    'programas':         ('erp_programas',        'programa',     ler_programas),
    'permissoes':        ('erp_permissoes',       None,           ler_permissoes),
}

def main(tabelas=None):
    if tabelas is None:
        tabelas = list(TABELAS.keys())

    print('Conectando SQL Server...')
    sql = pymssql.connect(**SQL)
    print('Conectando PostgreSQL...')
    pg = psycopg2.connect(**PG)

    stats = {}
    for nome in tabelas:
        if nome not in TABELAS:
            print(f'  Tabela desconhecida: {nome}')
            continue
        tbl, conflict, reader = TABELAS[nome]
        print(f'Lendo {nome}...')
        dados = reader(sql)
        if dados:
            upsert(pg, tbl, dados, conflict)
        stats[nome] = len(dados)
        print(f'  {len(dados)} registros')

    sql.close()
    pg.close()

    print('\nResumo:')
    for k, v in stats.items():
        print(f'  {k}: {v}')

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Importa SQL Server → PostgreSQL')
    parser.add_argument('--tabelas', nargs='+', help='Tabelas (padrao: todas)')
    args = parser.parse_args()
    main(args.tabelas)
