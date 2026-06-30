import { useEffect, useState, useCallback } from 'react'
import { api } from '../lib/api'
import { DataGrid } from '../components/DataGrid'
import { Modal } from '../components/Modal'
import { Package, Search } from 'lucide-react'

export function Produtos() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<any>(null)
  const [filters, setFilters] = useState({ descricao: '', codigo: '', ncm: '' })

  const load = useCallback(() => {
    setLoading(true)
    const params: any = { limit: 50 }
    if (filters.descricao) params.descricao = filters.descricao
    if (filters.codigo) params.codigo = filters.codigo
    if (filters.ncm) params.ncm = filters.ncm
    api.produtos.list(params).then((r) => { setData(r.produtos); setLoading(false) })
  }, [filters])

  useEffect(() => { load() }, [load])

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Package className="w-6 h-6 text-violet-500" />
        <div>
          <h1 className="text-xl font-bold text-gray-800">Produtos</h1>
          <p className="text-sm text-gray-500">{data.length} produto(s)</p>
        </div>
      </div>

      <div className="flex gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            value={filters.descricao}
            onChange={(e) => setFilters((f) => ({ ...f, descricao: e.target.value }))}
            placeholder="Descrição..."
            className="pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm w-72 focus:outline-none focus:ring-2 focus:ring-nfe-400"
          />
        </div>
        <input
          value={filters.codigo}
          onChange={(e) => setFilters((f) => ({ ...f, codigo: e.target.value }))}
          placeholder="Código..."
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm w-40 focus:outline-none focus:ring-2 focus:ring-nfe-400"
        />
        <input
          value={filters.ncm}
          onChange={(e) => setFilters((f) => ({ ...f, ncm: e.target.value }))}
          placeholder="NCM..."
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm w-36 focus:outline-none focus:ring-2 focus:ring-nfe-400"
        />
      </div>

      <DataGrid
        data={data}
        loading={loading}
        searchPlaceholder="Filtrar produtos..."
        onRowClick={setSelected}
      />

      <Modal open={!!selected} onClose={() => setSelected(null)} title="Detalhes do Produto" wide>
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
