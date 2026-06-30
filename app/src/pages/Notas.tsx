import { useEffect, useState, useCallback } from 'react'
import { api } from '../lib/api'
import { DataGrid } from '../components/DataGrid'
import { Modal } from '../components/Modal'
import { FileText, Search, Send, ExternalLink } from 'lucide-react'
import type { ColumnDef } from '@tanstack/react-table'

export function Notas() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<any>(null)
  const [filters, setFilters] = useState({ nota: '', cnpj_cpf: '' })
  const [emitting, setEmitting] = useState<number | null>(null)
  const [result, setResult] = useState<string | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    const params: any = { limit: 30 }
    if (filters.nota) params.nota = parseInt(filters.nota)
    if (filters.cnpj_cpf) params.cnpj_cpf = filters.cnpj_cpf
    api.notas.list(params).then((r) => { setData(r.notas); setLoading(false) })
  }, [filters])

  useEffect(() => { load() }, [load])

  const emitir = async (registro: number) => {
    setEmitting(registro)
    try {
      const r = await api.nfe.emitirDoErp(registro)
      setResult(`NF-e ${r.numero}: ${r.sucesso ? 'OK' : 'ERRO'} — ${r.mensagem}`)
    } catch (e: any) {
      setResult(`ERRO: ${e.message}`)
    }
    setEmitting(null)
  }

  const columns: ColumnDef<any>[] = [
    { accessorKey: 'registro', header: 'Registro' },
    { accessorKey: 'nota', header: 'Número' },
    { accessorKey: 'serie', header: 'Série' },
    { accessorKey: 'nome', header: 'Cliente', cell: (info) => {
      const v = info.getValue() as string
      return v?.length > 40 ? v.slice(0, 40) + '...' : v
    }},
    { accessorKey: 'cgc_cpf', header: 'CNPJ/CPF' },
    { accessorKey: 'cidade', header: 'Cidade' },
    { accessorKey: 'estado', header: 'UF' },
    { accessorKey: 'emissao', header: 'Emissão', cell: (info) => {
      const v = info.getValue() as string
      return v ? v.slice(0, 10) : '-'
    }},
    { accessorKey: 'tgeral', header: 'Valor', cell: (info) => {
      const v = info.getValue() as number
      return v?.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) ?? '-'
    }},
    {
      id: 'actions',
      header: '',
      cell: (info) => (
        <button
          onClick={(e) => { e.stopPropagation(); emitir(info.row.original.registro) }}
          disabled={emitting === info.row.original.registro}
          className="p-1.5 rounded-lg text-nfe-600 hover:bg-nfe-50 disabled:opacity-40"
          title="Emitir NF-e"
        >
          <Send className="w-4 h-4" />
        </button>
      ),
    },
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <FileText className="w-6 h-6 text-amber-500" />
        <div>
          <h1 className="text-xl font-bold text-gray-800">Notas Fiscais</h1>
          <p className="text-sm text-gray-500">{data.length} nota(s)</p>
        </div>
      </div>

      <div className="flex gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            value={filters.nota}
            onChange={(e) => setFilters((f) => ({ ...f, nota: e.target.value }))}
            placeholder="Número da nota..."
            className="pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm w-48 focus:outline-none focus:ring-2 focus:ring-nfe-400"
          />
        </div>
        <input
          value={filters.cnpj_cpf}
          onChange={(e) => setFilters((f) => ({ ...f, cnpj_cpf: e.target.value }))}
          placeholder="CNPJ/CPF do cliente..."
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm w-52 focus:outline-none focus:ring-2 focus:ring-nfe-400"
        />
      </div>

      {result && (
        <div className={`p-3 rounded-lg text-sm ${result.includes('OK') ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-red-50 text-red-700 border border-red-200'}`}>
          {result}
          <button onClick={() => setResult(null)} className="ml-3 underline">Fechar</button>
        </div>
      )}

      <DataGrid
        data={data}
        loading={loading}
        searchPlaceholder="Filtrar notas..."
        onRowClick={setSelected}
        columns={columns}
      />

      <Modal open={!!selected} onClose={() => setSelected(null)} title="Detalhes da Nota Fiscal" wide>
        {selected && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              {Object.entries(selected).map(([k, v]) => (
                <div key={k}>
                  <span className="text-gray-400 text-xs uppercase">{k.replace(/_/g, ' ')}</span>
                  <p className="font-medium text-gray-800 mt-0.5">
                    {v === null || v === undefined ? '-' : String(v)}
                  </p>
                </div>
              ))}
            </div>
            <button
              onClick={() => emitir(selected.registro)}
              disabled={emitting !== null}
              className="px-4 py-2 bg-nfe-500 text-white rounded-lg text-sm hover:bg-nfe-600 disabled:opacity-50"
            >
              {emitting === selected.registro ? 'Emitindo...' : 'Emitir NF-e'}
            </button>
          </div>
        )}
      </Modal>
    </div>
  )
}
