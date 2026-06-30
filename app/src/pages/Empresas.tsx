import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { DataGrid } from '../components/DataGrid'
import { Modal } from '../components/Modal'
import { Building2 } from 'lucide-react'

export function Empresas() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<any>(null)

  useEffect(() => {
    api.empresas.list().then((r) => { setData(r.empresas); setLoading(false) })
  }, [])

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Building2 className="w-6 h-6 text-blue-500" />
        <div>
          <h1 className="text-xl font-bold text-gray-800">Empresas</h1>
          <p className="text-sm text-gray-500">{data.length} empresa(s) cadastrada(s)</p>
        </div>
      </div>

      <DataGrid
        data={data}
        loading={loading}
        searchPlaceholder="Pesquisar empresa por nome ou CNPJ..."
        onRowClick={setSelected}
      />

      <Modal open={!!selected} onClose={() => setSelected(null)} title="Detalhes da Empresa" wide>
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
