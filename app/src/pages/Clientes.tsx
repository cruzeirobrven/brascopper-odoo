import { useEffect, useState, useCallback } from 'react'
import { api } from '../lib/api'
import { DataGrid } from '../components/DataGrid'
import { Modal } from '../components/Modal'
import { Users, Search } from 'lucide-react'

export function Clientes() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<any>(null)
  const [filters, setFilters] = useState({ nome: '', cnpj_cpf: '' })

  const load = useCallback(() => {
    setLoading(true)
    const params: any = { limit: 50 }
    if (filters.nome) params.nome = filters.nome
    if (filters.cnpj_cpf) params.cnpj_cpf = filters.cnpj_cpf
    api.clientes.list(params).then((r) => { setData(r.clientes); setLoading(false) })
  }, [filters])

  useEffect(() => { load() }, [load])

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Users className="w-6 h-6 text-emerald-500" />
        <div>
          <h1 className="text-xl font-bold text-gray-800">Clientes</h1>
          <p className="text-sm text-gray-500">{data.length} cliente(s)</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            value={filters.nome}
            onChange={(e) => setFilters((f) => ({ ...f, nome: e.target.value }))}
            placeholder="Nome..."
            className="pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm w-64 focus:outline-none focus:ring-2 focus:ring-nfe-400"
          />
        </div>
        <input
          value={filters.cnpj_cpf}
          onChange={(e) => setFilters((f) => ({ ...f, cnpj_cpf: e.target.value }))}
          placeholder="CNPJ/CPF..."
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm w-48 focus:outline-none focus:ring-2 focus:ring-nfe-400"
        />
      </div>

      <DataGrid
        data={data}
        loading={loading}
        searchPlaceholder="Filtrar resultados..."
        onRowClick={setSelected}
      />

      <Modal open={!!selected} onClose={() => setSelected(null)} title="Detalhes do Cliente" wide>
        {selected && (
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
        )}
      </Modal>
    </div>
  )
}
