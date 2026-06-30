#!/usr/bin/env python3
"""
Exporta dados do PostgreSQL (erp_*) para Odoo via XML-RPC.
Idempotente: usa external_id (ir.model.data) para evitar duplicatas.
Otimizado com batch create/write para 10k+ registros.

Uso:
  python3 exportar_para_odoo.py                    # tudo
  python3 exportar_para_odoo.py --tabelas clientes  # so clientes
  python3 exportar_para_odoo.py --tabelas empresas clientes produtos
"""
import sys, os, json, hashlib
from datetime import datetime, date
from pathlib import Path
from xmlrpc.client import ServerProxy, Fault as RPCFault
from itertools import islice

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from api.database import get_cursor

ODOO_URL = "http://100.119.223.92:8069"
ODOO_DB = "odoo18"
ODOO_USER = "admin"
ODOO_PWD = "br@123456"

STATE_FILE = Path("/tmp/odoo_export_state.json")
BATCH_SIZE = 500


class Odoo:
    def __init__(self):
        self.common = ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
        self.uid = self.common.authenticate(ODOO_DB, ODOO_USER, ODOO_PWD, {})
        self.models = ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
        self._cache = {}
        print(f"  Conectado (UID={self.uid})")

    def _call(self, model, method, *args):
        return self.models.execute_kw(ODOO_DB, self.uid, ODOO_PWD, model, method, *args)

    def search(self, model, domain):
        return self._call(model, 'search', [domain])

    def read(self, model, ids, fields=None):
        kwargs = {'fields': fields} if fields else {}
        return self._call(model, 'read', [ids], kwargs)

    def create(self, model, vals_list):
        return self._call(model, 'create', [vals_list])

    def write(self, model, ids, vals_dict):
        return self._call(model, 'write', [ids, vals_dict])

    def get_existing_refs(self, model):
        """Retorna dict {ext_name: res_id} para module='nfe_hub'"""
        refs = self.search('ir.model.data', [
            ('module', '=', 'nfe_hub'),
            ('model', '=', model),
        ])
        if not refs:
            return {}
        data = self.read('ir.model.data', refs, ['name', 'res_id'])
        return {r['name']: r['res_id'] for r in data}

    def batch_upsert(self, model, records, ext_id_fn, vals_fn, skip_refs=False):
        existing = self.get_existing_refs(model)
        to_create = []
        to_create_ext = []
        to_update = {}
        total = len(records)

        for rec in records:
            ext = ext_id_fn(rec)
            vals = vals_fn(rec, ext)
            if ext in existing:
                to_update[existing[ext]] = vals
            else:
                to_create.append(vals)
                to_create_ext.append(ext)

        created_ids = []
        for i in range(0, len(to_create), BATCH_SIZE):
            chunk = to_create[i:i + BATCH_SIZE]
            ids = self.create(model, chunk)
            created_ids.extend(ids)
            print(f"    criados {len(created_ids)}/{len(to_create)}", end='\r')

        if created_ids and not skip_refs:
            ref_vals = []
            for ext, res_id in zip(to_create_ext, created_ids):
                ref_vals.append({
                    'module': 'nfe_hub',
                    'name': ext,
                    'model': model,
                    'res_id': res_id,
                })
            for i in range(0, len(ref_vals), BATCH_SIZE):
                self.create('ir.model.data', ref_vals[i:i + BATCH_SIZE])
            print()

        for rid, vals in to_update.items():
            self.write(model, rid, vals)

        return len(to_update), len(to_create)

    def batch_create_by_code(self, model, records, code_field, code_fn, vals_fn):
        """Cria registros usando um campo unico (ex: default_code) para dedup."""
        existing_codes = set()
        for i in range(0, len(records), 5000):
            chunk = records[i:i+5000]
            codes = [code_fn(r) for r in chunk]
            found = self.search(model, [(code_field, 'in', codes)])
            if found:
                data = self.read(model, found, [code_field])
                existing_codes.update(r[code_field] for r in data if r.get(code_field))

        to_create = []
        records_created = 0
        for rec in records:
            code = code_fn(rec)
            if code in existing_codes:
                continue
            to_create.append(vals_fn(rec, code))

        for i in range(0, len(to_create), BATCH_SIZE):
            chunk = to_create[i:i + BATCH_SIZE]
            self.create(model, chunk)
            records_created += len(chunk)
            print(f"    criados {records_created}/{len(to_create)}", end='\r')

        print()
        return 0, len(to_create)

    def search_state_id(self, uf):
        if not uf:
            return False
        key = f'state_{uf}'
        if key not in self._cache:
            states = self.search('res.country.state', [('code', '=', uf)])
            self._cache[key] = states[0] if states else False
        return self._cache[key]

    def search_country_id(self, code='BR'):
        key = f'country_{code}'
        if key not in self._cache:
            countries = self.search('res.country', [('code', '=', code)])
            self._cache[key] = countries[0] if countries else False
        return self._cache[key]

    def buscar_tipo_doc(self, code):
        key = f'tipodoc_{code}'
        if key not in self._cache:
            types = self.search('l10n_latam.identification.type', [('name', '=', code)])
            self._cache[key] = types[0] if types else False
        return self._cache[key]


# ── Exporters ────────────────────────────────────────────────────────────────

def exportar_empresas(odoo: Odoo):
    print("\n--- Empresas (res.partner) ---")
    with get_cursor() as cur:
        cur.execute("SELECT * FROM erp_empresas")
        rows = [dict(r) for r in cur.fetchall()]

    br_id = odoo.search_country_id()

    def ext_id(r):
        return f"empresa_{r['codigo_erp']}"

    def vals(r, ext):
        state_id = odoo.search_state_id(r.get('estado') or '')
        cnpj = (r.get('cnpj') or '').replace('.', '').replace('/', '').replace('-', '')
        return {
            'name': (r.get('nome') or 'Sem Nome')[:150],
            'company_type': 'company',
            'company_registry': cnpj,
            'ref': r.get('inscricao_estadual') or '',
            'street': r.get('endereco') or '',
            'street2': ((r.get('numero') or '') + ' ' + (r.get('complemento') or '')).strip(),
            'city': r.get('cidade') or '',
            'state_id': state_id,
            'country_id': br_id,
            'zip': r.get('cep') or '',
            'phone': r.get('fone') or '',
            'email': r.get('email') or '',
            'is_company': True,
            'active': True,
        }

    updated, created = odoo.batch_upsert('res.partner', rows, ext_id, vals)
    print(f"  {updated} atualizados, {created} criados")


def exportar_clientes(odoo: Odoo):
    print("\n--- Clientes (res.partner) ---")
    with get_cursor() as cur:
        cur.execute("SELECT * FROM erp_clientes ORDER BY codigo_erp")
        rows = [dict(r) for r in cur.fetchall()]

    br_id = odoo.search_country_id()

    def ext_id(r):
        return f"cliente_{r['empresa_erp']}_{r['codigo_erp']}"

    def vals(r, ext):
        doc = (r.get('cnpj_cpf') or '').replace('.', '').replace('/', '').replace('-', '')
        state_id = odoo.search_state_id(r.get('estado') or '')
        is_company = len(doc) > 11
        return {
            'name': (r.get('nome') or 'Sem Nome')[:150],
            'company_type': 'person',
            'company_registry': doc,
            'ref': r.get('inscricao_rg') or '',
            'street': r.get('endereco') or '',
            'street2': ((r.get('numero') or '') + ' ' + (r.get('complemento') or '')).strip(),
            'city': r.get('cidade') or '',
            'state_id': state_id,
            'country_id': br_id,
            'zip': (r.get('cep') or '').replace('.', '').replace('-', '')[:10],
            'phone': r.get('fone_1') or r.get('fone_2') or '',
            'email': r.get('email') or '',
            'is_company': is_company,
            'active': bool(r.get('ativo', True)),
        }

    updated, created = odoo.batch_upsert('res.partner', rows, ext_id, vals)
    print(f"  {updated} atualizados, {created} criados")


def exportar_produtos(odoo: Odoo):
    print("\n--- Produtos (product.template) ---")
    with get_cursor() as cur:
        cur.execute("SELECT * FROM erp_produtos ORDER BY codigo_erp")
        rows = [dict(r) for r in cur.fetchall()]

    uom_ids = odoo.search('uom.uom', [('name', '=', 'Unit(s)')])
    uom_id = uom_ids[0] if uom_ids else 1

    def code_fn(r):
        return str(r.get('codigo_erp') or '').strip()

    def vals(r, code):
        name = r.get('descricao') or code or 'Sem Nome'
        ncm = (r.get('ncm') or '').replace('.', '').strip()
        v = {
            'name': name[:200],
            'default_code': code,
            'type': 'consu',
            'uom_id': uom_id,
            'uom_po_id': uom_id,
            'list_price': float(r.get('preco_venda') or 0.0),
            'barcode': r.get('codigo_barras') or '',
            'active': bool(r.get('ativo', True)),
        }
        if ncm:
            v['description_sale'] = f"NCM: {ncm}"
        return v

    updated, created = odoo.batch_create_by_code('product.template', rows, 'default_code', code_fn, vals)
    print(f"  {created} produtos criados")


def salvar_state(tabelas):
    state = {
        'ultima_execucao': datetime.now().isoformat(),
        'tabelas': tabelas,
    }
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


# ── Main ─────────────────────────────────────────────────────────────────────

TABELAS = {
    'empresas': exportar_empresas,
    'clientes': exportar_clientes,
    'produtos': exportar_produtos,
}


def main(tabelas=None):
    if tabelas is None:
        tabelas = list(TABELAS.keys())

    print("=" * 50)
    print(f"Exportando para Odoo {ODOO_URL}")
    print(f"Tabelas: {', '.join(tabelas)}")
    print("=" * 50)

    odoo = Odoo()
    for nome in tabelas:
        if nome in TABELAS:
            TABELAS[nome](odoo)

    salvar_state(tabelas)
    print("\nConcluido!")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Exporta erp_* → Odoo')
    parser.add_argument('--tabelas', nargs='+', help='Tabelas (padrao: todas)')
    args = parser.parse_args()
    main(args.tabelas)
