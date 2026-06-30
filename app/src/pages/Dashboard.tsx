import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import {
  Building2, Users, Package, FileText,
  TrendingUp, Activity, CheckCircle, XCircle,
} from 'lucide-react'

export function Dashboard() {
  const [stats, setStats] = useState<any>({})
  const [acbr, setAcbr] = useState<any>(null)

  useEffect(() => {
    Promise.all([
      api.empresas.list(),
      api.clientes.list({ limit: 1 }),
      api.produtos.list({ limit: 1 }),
      api.notas.list({ limit: 1 }),
      api.nfe.status(),
    ]).then(([emp, cli, pro, not, st]) => {
      setStats({
        empresas: emp.empresas.length,
        clientes: cli.total,
        produtos: pro.total,
        notas: not.total,
      })
      setAcbr(st.acbr_monitor)
    })
  }, [])

  const cards = [
    { label: 'Empresas', value: stats.empresas ?? '...', icon: Building2, color: 'bg-blue-500' },
    { label: 'Clientes', value: stats.clientes ?? '...', icon: Users, color: 'bg-emerald-500' },
    { label: 'Produtos', value: stats.produtos ?? '...', icon: Package, color: 'bg-violet-500' },
    { label: 'Notas Fiscais', value: stats.notas ?? '...', icon: FileText, color: 'bg-amber-500' },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">Visão geral do sistema NF-e</p>
      </div>

      {/* Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((c) => (
          <div key={c.label} className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">{c.label}</p>
                <p className="text-2xl font-bold text-gray-800 mt-1">{c.value}</p>
              </div>
              <div className={`${c.color} p-3 rounded-lg`}>
                <c.icon className="w-6 h-6 text-white" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* ACBrMonitor Status */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-800 mb-3">ACBrMonitor</h2>
        {acbr ? (
          <div className="flex items-center gap-3">
            {acbr.ok ? (
              <CheckCircle className="w-5 h-5 text-emerald-500" />
            ) : (
              <XCircle className="w-5 h-5 text-red-500" />
            )}
            <span className={acbr.ok ? 'text-emerald-700' : 'text-red-700'}>
              {acbr.ok ? 'Online' : 'Offline'} — {acbr.status}
            </span>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-gray-400">
            <Activity className="w-5 h-5 animate-pulse" />
            Verificando...
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-800 mb-3">Ações Rápidas</h2>
        <div className="flex gap-3">
          <a
            href="/docs"
            className="px-4 py-2 bg-nfe-500 text-white rounded-lg text-sm hover:bg-nfe-600 transition-colors"
          >
            Documentação da API
          </a>
        </div>
      </div>
    </div>
  )
}
