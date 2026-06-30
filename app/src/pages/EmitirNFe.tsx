import { useState, useEffect } from 'react'
import { api } from '../lib/api'
import { Search, Send, FileText, Loader2 } from 'lucide-react'

export function EmitirNFe() {
  const [registro, setRegistro] = useState('')
  const [tpAmb, setTpAmb] = useState(2)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [nota, setNota] = useState<any>(null)
  const [notaLoading, setNotaLoading] = useState(false)

  const buscarNota = async () => {
    if (!registro) return
    setNotaLoading(true)
    setNota(null)
    try {
      const r = await api.notas.list({ registro: parseInt(registro) })
      if (r.notas.length > 0) setNota(r.notas[0])
    } finally {
      setNotaLoading(false)
    }
  }

  const emitir = async () => {
    if (!registro) return
    setLoading(true)
    setResult(null)
    try {
      const r = await api.nfe.emitirDoErp(parseInt(registro), tpAmb)
      setResult(r)
    } catch (e: any) {
      setResult({ sucesso: false, mensagem: e.message })
    }
    setLoading(false)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Send className="w-6 h-6 text-nfe-500" />
        <div>
          <h1 className="text-xl font-bold text-gray-800">Emitir NF-e</h1>
          <p className="text-sm text-gray-500">Emita uma NF-e diretamente do ERP</p>
        </div>
      </div>

      {/* Busca */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm space-y-4">
        <div className="flex gap-3 items-end">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Registro ERP (FATNOT)</label>
            <input
              value={registro}
              onChange={(e) => setRegistro(e.target.value)}
              placeholder="Ex: 164"
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm w-40 focus:outline-none focus:ring-2 focus:ring-nfe-400"
            />
          </div>
          <button
            onClick={buscarNota}
            disabled={!registro || notaLoading}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm hover:bg-gray-200 disabled:opacity-40"
          >
            {notaLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Buscar'}
          </button>
        </div>

        {nota && (
          <div className="bg-gray-50 rounded-lg p-4 text-sm space-y-1">
            <p><span className="text-gray-400">Nº:</span> <strong>{nota.nota}</strong> Série {nota.serie}</p>
            <p><span className="text-gray-400">Cliente:</span> {nota.nome}</p>
            <p><span className="text-gray-400">CNPJ:</span> {nota.cgc_cpf}</p>
            <p><span className="text-gray-400">Valor:</span> R$ {(nota.tgeral ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</p>
          </div>
        )}
      </div>

      {/* Emissão */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm space-y-4">
        <h2 className="font-semibold text-gray-800">Configuração</h2>
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="radio"
              checked={tpAmb === 2}
              onChange={() => setTpAmb(2)}
              className="text-nfe-500"
            />
            Homologação
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="radio"
              checked={tpAmb === 1}
              onChange={() => setTpAmb(1)}
              className="text-nfe-500"
            />
            Produção
          </label>
        </div>

        <button
          onClick={emitir}
          disabled={!registro || loading}
          className="px-6 py-2.5 bg-nfe-500 text-white rounded-lg text-sm font-medium hover:bg-nfe-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {loading ? (
            <><Loader2 className="w-4 h-4 animate-spin" /> Emitindo...</>
          ) : (
            <><Send className="w-4 h-4" /> Emitir NF-e</>
          )}
        </button>

        {result && (
          <div className={`p-4 rounded-lg text-sm ${
            result.sucesso
              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
              : 'bg-red-50 text-red-800 border border-red-200'
          }`}>
            <p className="font-medium mb-1">{result.sucesso ? 'NF-e emitida com sucesso!' : 'Erro na emissão'}</p>
            {result.chave && <p className="text-xs mt-1">Chave: {result.chave}</p>}
            {result.numero && <p className="text-xs">Número: {result.numero}</p>}
            <p className="text-xs mt-1">{result.mensagem}</p>
          </div>
        )}
      </div>
    </div>
  )
}
