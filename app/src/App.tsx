import { useState } from 'react'
import { Layout } from './components/Layout'
import type { TabId } from './types'

export default function App() {
  const [tab, setTab] = useState<TabId>('dashboard')
  return <Layout tab={tab} onTab={setTab} />
}
