---
tags:
  - acbr
  - acbrmonitor
  - config
created: 2026-06-28
---

# ACBrMonitor — Configuracao e Operacao

## Localizacao

```
/opt/ACBrMonitor/
├── ACBrMonitor          ← Binario
├── ACBrMonitor.ini      ← Configuracao principal
├── ACBrNFeServicos.ini  ← Configuracao dos webservices SEFAZ
├── Logs/                ← Logs de operacao
├── Arqs/                ← XMLs gerados/processados
├── TXT/                 ← Arquivos TXT/INI de entrada/saida
├── PDF/                 ← DANFEs gerados
├── Schemas/             ← Schemas XSD
└── Logos/               ← Logomarcas para DANFE
```

## Configuracao Atual

```ini
[ACBrMonitor]
Modo_TCP=1              ← TCP habilitado (porta 3434)
Modo_TXT=0              ← TXT desabilitado
TCP_Porta=3434
TCP_TimeOut=10000
Gravar_Log=1
Arquivo_Log=LOG.TXT

[ACBrNFeMonitor]
ArquivoWebServices=/opt/ACBrMonitor/ACBrNFeServicos.ini
ValidarDigest=1
TimeoutWebService=15

[WebService]
Ambiente=1              ← 1=producao, 2=homologacao
UF=SP
Versao=4.00
FormaEmissaoNFe=0

[Certificado]            ← Configurar certificado A1/A3
SSLLib=4
ArquivoPFX=
Senha=

[Arquivos]
PathNFe=/opt/ACBrMonitor/Arqs
PathArqTXT=/opt/ACBrMonitor/TXT
PathPDF=/opt/ACBrMonitor/PDF

[DANFE]
PathPDF=/opt/ACBrMonitor/PDF
```

## Instalacao e Execucao

### Via Docker (atual)
```bash
docker run -d \
  --name acbrmonitor \
  -v /opt/ACBrMonitor:/opt/ACBrMonitor \
  -p 3434:3434 \
  ubuntu:20.04 \
  /opt/ACBrMonitor/ACBrMonitor
```

### Requisitos do Container
```bash
apt install -y libgtk2.0-0 libglib2.0-0 libcanberra-gtk-module gtk2-engines-pixbuf
```

## Comunicacao — ACBrMonitorPLUS

**ATENCAO:** Este projeto usa o **ACBrMonitorPLUS** (Ver. 1.4.x). O protocolo difere do ACBrMonitor classico:

1. **Terminador de comando:** `\r\n.\r\n` (CRLF + ponto + CRLF) — nao apenas `\r\n`
2. **Sintaxe:** `NFE.Metodo(parametros)` — com **parenteses**, nao `=` nem virgula simples
3. Os nomes dos metodos usam o prefixo `NFE.` (maiusculo)

## Teste de Comunicacao

```bash
printf 'NFE.StatusServico()\r\n.\r\n' | nc -w5 127.0.0.1 3434
```

Resposta esperada (homologacao):
```
OK: Servico em Operacao

[Status]
CStat=107
CUF=35
DhRecbto=...
Msg=Servico em Operacao
tpAmb=2
```

## Comandos Disponiveis (MonitorPLUS)

| Comando | Descricao |
|---------|-----------|
| `NFE.StatusServico()` | Status do servico SEFAZ |
| `NFE.CriarEnviarNFe(caminho_ini)` | Gerar XML e enviar |
| `NFE.ConsultarNFe(chave)` | Consultar situacao |
| `NFE.CancelarNFe(chave,justificativa)` | Cancelar |
| `NFE.InutilizarNFe(cnpj,mod,serie,nIni,nFim,just)` | Inutilizar |
| `NFE.CartaCorrecao(chave,correcao)` | Carta de Correcao |
| `NFE.ImprimirDANFe(chave)` | Imprimir DANFE |
| `NFE.ImprimirDANFePDF(chave)` | Imprimir DANFE em PDF |

## Respostas

O ACBrMonitorPLUS retorna respostas no formato:
```
OK: <mensagem>

[section]
key=value
```

Ou em caso de erro:
```
ERRO: <mensagem>
```

Toda resposta e terminada com o caractere `\x03` (ETX).

## Troubleshooting

- Verificar se a porta 3434 esta ouvindo: `ss -tlnp | grep 3434`
- Verificar logs: `tail -f /opt/ACBrMonitor/LOG.TXT`
- Certificado: configurar `ArquivoPFX` e `Senha` no INI
- Ambiente: `Ambiente=1` producao, `Ambiente=2` homologacao
