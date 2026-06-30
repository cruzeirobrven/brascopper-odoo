---
tags:
  - nfe
  - fluxo
  - ini
created: 2026-06-28
---

# Fluxo de Geracao e Envio de NFe

## Visao Geral do Processo

```
Dados ERP → Validacao → Montagem INI → ACBrMonitor → SEFAZ → Resultado
```

## 1. Entrada de Dados

A API recebe os dados da NF-e no seguinte formato JSON:

```json
{
  "registro": 12345,
  "empresa": 1,
  "operacao": "VENDA",
  "emitente": { "cnpj": "11222333000181", ... },
  "destinatario": { "cpf_cnpj": "99888777000199", ... },
  "itens": [
    {
      "produto": "ABC123",
      "descricao": "PRODUTO X",
      "ncm": "84713000",
      "cfop": "5102",
      "quantidade": 10,
      "valor_unitario": 150.00,
      ...
    }
  ],
  "parcelas": [
    { "valor": 1500.00, "vencimento": "2026-07-28", "tipo_venc": 1 }
  ],
  "transportador": { ... }
}
```

## 2. Estrutura do Arquivo INI

O ACBrMonitor consome um arquivo INI com secoes delimitadas por `[Secao]`.
O comando `NFE.CriarEnviarNFe=<caminho_do_ini>` dispara o processamento.

### Secoes do INI

```
[Identificacao]      ← Dados gerais da nota
[Emitente]           ← CNPJ, razao, endereco do emitente
[Destinatario]       ← CNPJ/CPF, nome, endereco do destinatario
[Produto001]         ← Produto 1 (dados + tributacao)
[ICMS001]            ← ICMS do produto 1
[IPI001]             ← IPI do produto 1 (se aplicavel)
[PIS001]             ← PIS do produto 1
[COFINS001]          ← COFINS do produto 1
[ICMSUFDest001]      ← DIFAL do produto 1 (se interestadual)
[Produto002]         ← Produto 2
...                  ← repete para N itens
[Total]              ← Totais da nota
[Transportador]      ← Dados do transporte
[Vol001]             ← Volumes (se houver)
[Cobr]               ← Fatura
[Dup001]             ← Duplicata 1
[Dup002]             ← Duplicata 2 (se houver)
[pag001]             ← Pagamento 1
[pag002]             ← Pagamento 2 (se houver)
[InfAdic]            ← Informacoes complementares
```

## 3. Regras de Negocio Implementadas

### Identificacao
- `cNF`: `registro % 100_000_000 || 1`, diferente de `nNF`
- `natOp`: descricao da operacao (60 chars)
- `mod`: 55 (NF-e)
- `tpNF`: 0=entrada, 1=saida (baseado em `TP_SAIDA_ENTR` e `MOVIMENTACAO`)
- `idDest`: 1=intra, 2=inter, 3=exterior
- `indPres`: 1=presencial, 2=internet, 9=outros
- `indFinal`: 1=consumidor final, 0=nao
- `finNFe`: 1=normal, 2=complementar, 3=ajuste, 4=devolucao

### Emitente
- `CRT`: 1=Simples, 3=Regime Normal
- `CNPJCPF`: prioriza Inscricao Federal se TIPO_INSCRICAO=1, senao CNPJ
- Campos de endereco do CADEMP

### Destinatario
- `indIEDest`: 1=contribuinte IE, 2=isento, 9=nao contribuinte/PF
- `ISUF`: Suframa se existir
- Endereco: prefere FATNOT, fallback CADCLI
- `cPais`/`xPais`: do CADCLI (default 1058/BRASIL)

### Produto / Tributacao
- `vUnCom`: calculado via `VALOR_CALCULO / DCIMAIS_CALCULO` quando ambos > 0, fallback `VALOR`
- `indTot`: 0 se TIPO_ITEM 5/8/9, 1 caso contrario
- `vProd`: icms_imob = 0; usa TPRODUTO ou calcula qtd * vUnCom
- ICMS: CST/CSOSN, reducao, desonerado, credito SN, ST, FCP-ST
- DIFAL: se P_ICMS_INTER_PART > 0 e sem acordo de dif. aliq.
- IPI/PIS/COFINS: CST, aliquota, base, valor

### Transportador
- `modFrete`: mapeamento FATTRANSP.TRANSPORTE → 0/1/2/3/4/9
- Dados da transportadora, placa, volumes (peso, especie, marca)

### Cobranca / Pagamento
- Fatura com valor total das parcelas
- Duplicatas individualizadas
- Pagamento: mapeamento TIPO_VENC → tPag (boleto=15, credito=03, debito=04, cheque=02, outros=99)
- Cartao: CNPJ operadora, bandeira, autorizacao

## 4. Comandos ACBrMonitor

| Comando | Funcao |
|---------|--------|
| `NFE.CriarEnviarNFe=<path_ini>` | Gerar + Enviar NFe |
| `NFE.Consultar=<chave>` | Consultar situacao |
| `NFE.Cancelar=<chave>,<just>` | Cancelar NFe |
| `NFE.Inutilizar=<cnpj>,<mod>,<serie>,<nIni>,<nFim>,<just>` | Inutilizar numeracao |
| `NFE.CCe=<chave>,<correcao>` | Carta de Correcao |
| `NFE.Status` | Status do servico |
| `NFE.ImprimirDANFE=<chave>` | Imprimir DANFE |

## 5. Mapeamento Tabelas → INI

Cobertura completa em [[estado-do-projeto]] e nos fontes de referencia em `/opt/nferef/fontes/`.
