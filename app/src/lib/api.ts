const BASE = '/api/v1'
const KEY = 'nfe-dev-key'

async function req<T>(url: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'X-API-Key': KEY, 'Content-Type': 'application/json', ...opts?.headers },
    ...opts,
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`)
  return res.json()
}

export const api = {
  // Empresas
  empresas: {
    list: () => req<{ empresas: any[] }>('/erp/empresas'),
    get: (id: number) => req<any>(`/erp/empresas/${id}`),
  },

  // Clientes
  clientes: {
    list: (params?: Record<string, any>) => {
      const q = new URLSearchParams(params || {}).toString()
      return req<{ clientes: any[]; total: number }>(`/erp/clientes${q ? `?${q}` : ''}`)
    },
  },

  // Produtos
  produtos: {
    list: (params?: Record<string, any>) => {
      const q = new URLSearchParams(params || {}).toString()
      return req<{ produtos: any[]; total: number }>(`/erp/produtos${q ? `?${q}` : ''}`)
    },
  },

  // Notas
  notas: {
    list: (params?: Record<string, any>) => {
      const q = new URLSearchParams(params || {}).toString()
      return req<{ notas: any[]; total: number }>(`/erp/notas${q ? `?${q}` : ''}`)
    },
  },

  // Operações
  operacoes: {
    list: () => req<{ operacoes: any[] }>('/erp/operacoes'),
  },

  // NF-e
  nfe: {
    emitirDoErp: (registro_erp: number, tp_amb = 2) =>
      req<{ sucesso: boolean; mensagem: string; chave: string; numero: string }>('/nfe/emitir-do-erp', {
        method: 'POST',
        body: JSON.stringify({ registro_erp, tp_amb }),
      }),
    gerar: (body: any) =>
      req<{ sucesso: boolean; mensagem: string; chave: string; numero: string }>('/nfe/gerar', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    status: () => req<{ api: string; acbr_monitor: { ok: boolean; status: string } }>('/status'),
  },

  // Import
  importar: (tabelas?: string[]) =>
    fetch(`${BASE}/nfe/importar`, {
      method: 'POST',
      headers: { 'X-API-Key': KEY, 'Content-Type': 'application/json' },
      body: JSON.stringify({ tabelas }),
    }).then(r => r.text()),
}
