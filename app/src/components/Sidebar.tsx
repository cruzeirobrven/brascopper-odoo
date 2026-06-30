import {
  LayoutDashboard,
  Building2,
  Users,
  Package,
  FileText,
  Send,
  Import,
  Activity,
} from 'lucide-react'
import type { TabId } from '../types'

interface SidebarProps {
  active: TabId
  onTab: (tab: TabId) => void
}

const tabs: { id: TabId; label: string; icon: React.ReactNode }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard className="w-5 h-5" /> },
  { id: 'empresas', label: 'Empresas', icon: <Building2 className="w-5 h-5" /> },
  { id: 'clientes', label: 'Clientes', icon: <Users className="w-5 h-5" /> },
  { id: 'produtos', label: 'Produtos', icon: <Package className="w-5 h-5" /> },
  { id: 'notas', label: 'Notas Fiscais', icon: <FileText className="w-5 h-5" /> },
  { id: 'emitir', label: 'Emitir NF-e', icon: <Send className="w-5 h-5" /> },
]

export function Sidebar({ active, onTab }: SidebarProps) {
  return (
    <aside className="fixed left-0 top-0 h-full w-60 bg-gray-900 text-white flex flex-col z-40">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-gray-800">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-nfe-500 flex items-center justify-center">
            <FileText className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold">NFeHub</h1>
            <p className="text-[10px] text-gray-400">Painel de Controle</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-3 px-2 space-y-1 overflow-y-auto">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => onTab(t.id)}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              active === t.id
                ? 'bg-nfe-600 text-white'
                : 'text-gray-300 hover:bg-gray-800 hover:text-white'
            }`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </nav>

      {/* Status */}
      <div className="px-4 py-3 border-t border-gray-800">
        <div className="flex items-center gap-2 text-xs text-gray-400">
          <Activity className="w-3 h-3" />
          <span>ACBrMonitor</span>
        </div>
      </div>
    </aside>
  )
}
