import type { TabId } from '../types'
import { Sidebar } from './Sidebar'
import { Dashboard } from '../pages/Dashboard'
import { Empresas } from '../pages/Empresas'
import { Clientes } from '../pages/Clientes'
import { Produtos } from '../pages/Produtos'
import { Notas } from '../pages/Notas'
import { EmitirNFe } from '../pages/EmitirNFe'

interface LayoutProps {
  tab: TabId
  onTab: (tab: TabId) => void
}

export function Layout({ tab, onTab }: LayoutProps) {
  return (
    <div className="min-h-screen">
      <Sidebar active={tab} onTab={onTab} />
      <main className="ml-60 p-6">
        <div className="max-w-7xl mx-auto">
          {tab === 'dashboard' && <Dashboard />}
          {tab === 'empresas' && <Empresas />}
          {tab === 'clientes' && <Clientes />}
          {tab === 'produtos' && <Produtos />}
          {tab === 'notas' && <Notas />}
          {tab === 'emitir' && <EmitirNFe />}
        </div>
      </main>
    </div>
  )
}
