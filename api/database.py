from contextlib import contextmanager
import logging

import psycopg2
import psycopg2.extras

from api.config import settings

logger = logging.getLogger(__name__)


def get_connection():
    return psycopg2.connect(
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.db_name,
        user=settings.db_user,
        password=settings.db_pass,
    )


@contextmanager
def get_cursor():
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Tabelas normalizadas (emissao) ───────────────────────────────────────────

def buscar_empresa_por_cnpj(cnpj: str) -> dict | None:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM empresas WHERE cnpj = %s AND ativo = TRUE", [cnpj])
        row = cur.fetchone()
        return dict(row) if row else None


def buscar_empresa_por_id(empresa_id: int) -> dict | None:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM empresas WHERE id = %s AND ativo = TRUE", [empresa_id])
        row = cur.fetchone()
        return dict(row) if row else None


def buscar_cliente_por_cnpj(empresa_id: int, cnpj_cpf: str) -> dict | None:
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM clientes WHERE empresa_id = %s AND cnpj_cpf = %s AND ativo = TRUE",
            [empresa_id, cnpj_cpf],
        )
        row = cur.fetchone()
        return dict(row) if row else None


def buscar_produto_por_codigo(empresa_id: int, codigo: str) -> dict | None:
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM produtos WHERE empresa_id = %s AND codigo = %s AND ativo = TRUE",
            [empresa_id, codigo],
        )
        row = cur.fetchone()
        return dict(row) if row else None


def salvar_nota_fiscal(dados: dict) -> int:
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO notas_fiscais
                (empresa_id, cliente_id, chave_acesso, numero, serie, modelo,
                 tp_nf, nat_op, finalidade, dh_emissao, dh_saida,
                 v_prod, v_desc, v_frete, v_seg, v_outro,
                 v_ipi, v_pis, v_cofins, v_icms, v_st, v_nf, v_tot_trib,
                 tp_amb, cstat, nprot, nrec, xmotivo, status, registro_erp, observacao)
            VALUES
                (%(empresa_id)s, %(cliente_id)s, %(chave_acesso)s, %(numero)s, %(serie)s, %(modelo)s,
                 %(tp_nf)s, %(nat_op)s, %(finalidade)s, %(dh_emissao)s, %(dh_saida)s,
                 %(v_prod)s, %(v_desc)s, %(v_frete)s, %(v_seg)s, %(v_outro)s,
                 %(v_ipi)s, %(v_pis)s, %(v_cofins)s, %(v_icms)s, %(v_st)s, %(v_nf)s, %(v_tot_trib)s,
                 %(tp_amb)s, %(cstat)s, %(nprot)s, %(nrec)s, %(xmotivo)s, %(status)s, %(registro_erp)s, %(observacao)s)
            RETURNING id
            """,
            dados,
        )
        return cur.fetchone()["id"]


def atualizar_status_nota(nota_id: int, status: str, cstat: str = "", nprot: str = "", xmotivo: str = ""):
    with get_cursor() as cur:
        cur.execute(
            """
            UPDATE notas_fiscais
            SET status = %s, cstat = %s, nprot = %s, xmotivo = %s, updated_at = NOW()
            WHERE id = %s
            """,
            [status, cstat, nprot, xmotivo, nota_id],
        )


# ── Tabelas ERP (espelho SQL Server) ─────────────────────────────────────────

def buscar_erp_empresa(codigo_erp: int = None, cnpj: str = None) -> dict | None:
    with get_cursor() as cur:
        if codigo_erp:
            cur.execute("SELECT * FROM erp_empresas WHERE codigo_erp = %s", [codigo_erp])
        elif cnpj:
            cur.execute("SELECT * FROM erp_empresas WHERE cnpj LIKE %s", [f'%{cnpj}%'])
        else:
            cur.execute("SELECT * FROM erp_empresas LIMIT 1")
        row = cur.fetchone()
        return dict(row) if row else None


def listar_erp_empresas() -> list[dict]:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM erp_empresas ORDER BY nome")
        return [dict(r) for r in cur.fetchall()]


def buscar_erp_cliente(
    cnpj_cpf: str = None,
    nome: str = None,
    codigo_erp: int = None,
    empresa_erp: int = None,
    limit: int = 20,
) -> list[dict]:
    with get_cursor() as cur:
        conditions = []
        params = []
        if cnpj_cpf:
            conditions.append("cnpj_cpf LIKE %s")
            params.append(f'%{cnpj_cpf}%')
        if nome:
            conditions.append("(nome ILIKE %s OR fantasia ILIKE %s)")
            params.extend([f'%{nome}%', f'%{nome}%'])
        if codigo_erp:
            conditions.append("codigo_erp = %s")
            params.append(codigo_erp)
        if empresa_erp:
            conditions.append("empresa_erp = %s")
            params.append(empresa_erp)

        sql = "SELECT * FROM erp_clientes"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY nome LIMIT %s"
        params.append(limit)

        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def buscar_erp_produto(
    codigo: str = None,
    descricao: str = None,
    ncm: str = None,
    limit: int = 20,
) -> list[dict]:
    with get_cursor() as cur:
        conditions = []
        params = []
        if codigo:
            conditions.append("codigo_erp LIKE %s")
            params.append(f'%{codigo}%')
        if descricao:
            conditions.append("(descricao ILIKE %s OR descricao_tecnica ILIKE %s)")
            params.extend([f'%{descricao}%', f'%{descricao}%'])
        if ncm:
            conditions.append("ncm LIKE %s")
            params.append(f'%{ncm}%')

        sql = "SELECT * FROM erp_produtos"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY descricao LIMIT %s"
        params.append(limit)

        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def buscar_erp_nota(
    registro: int = None,
    nota: int = None,
    serie: str = None,
    cnpj_cpf: str = None,
    limit: int = 20,
) -> list[dict]:
    with get_cursor() as cur:
        conditions = []
        params = []
        if registro:
            conditions.append("registro = %s")
            params.append(registro)
        if nota:
            conditions.append("nota = %s")
            params.append(nota)
        if serie:
            conditions.append("serie = %s")
            params.append(serie)
        if cnpj_cpf:
            conditions.append("cgc_cpf LIKE %s")
            params.append(f'%{cnpj_cpf}%')

        sql = "SELECT * FROM erp_notas"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY emissao DESC LIMIT %s"
        params.append(limit)

        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def buscar_erp_operacao(codigo: int = None) -> list[dict]:
    with get_cursor() as cur:
        if codigo:
            cur.execute("SELECT * FROM erp_operacoes WHERE operacao = %s", [codigo])
        else:
            cur.execute("SELECT * FROM erp_operacoes ORDER BY descricao")
        return [dict(r) for r in cur.fetchall()]
