# Inventario Inicial de Telas do PDD

Inventario inicial extraido principalmente de `pdd/pdd.prg` e das capturas em `pdd_html`.

Use este arquivo como backlog da migracao. Ao migrar uma tela, preencher rota Django, origem dos dados, regra de permissao e status.

Status sugeridos: `nao iniciado`, `inventariado`, `modelado`, `importacao pronta`, `view pronta`, `validado`, `desativado no legado`.

| Codigo legado | Nome no menu | Area Django | Rota Django (atual) | Fonte inicial | Status |
| --- | --- | --- | --- | --- | --- |
| `apr` | Sistema APR - Pedidos de venda | `comercial` | `comercial:apr` | `apr/`, `pdd_html/Sistema APR*.html` | view pronta |
| `amm` | Analise de Margem Faturamento x M.Prima | `comercial` | `comercial:amm` | `amm/` | view pronta |
| `cus` | Custo/mes (pagamentos) | `custos` | `custos:custo_mes` | `cus/`, `brascopper_cus.db` | view pronta |
| `cuv` | Custo/mes (vencimentos) | `custos` | `custos:custo_vencimentos` | `cuv/` | view pronta |
| `cst` | Custo por Setor/mes (pagamentos) | `custos` | `custos:custo_setor` | `cst/` | view pronta |
| `ivc` | Planilhas diversas (custos) | `custos` | `custos:planilhas_diversas` | `ivc/`, `ivc/pedid.dbf` | view pronta |
| `cup` | DRE por caixa e competencia / mes | `custos` | `custos:dre_caixa_competencia` | `cup/` | view pronta |
| `fat` | Faturamento - periodo | `comercial` | `comercial:faturamento` | `fat/`, `fat/fatx/*.dbf` | view pronta |
| `far` | Faturamento / Rearme - diario / mes | `comercial` | `comercial:faturamento_rearme` | `far/` | view pronta |
| `fpr` | Vendas por periodo - produtos e clientes | `comercial` | `comercial:vendas_periodo` | `fpr/` | view pronta |
| `fmd` | Faturamento mensal (30 dias)/dia | `comercial` | `comercial:faturamento_mensal` | `fmd/` | view pronta |
| `pmp` | Pendencia pedido/venda x M.Prima | `producao` | `producao:pendencia_pedido_mp` | `pmp/` | view pronta |
| `rbr` | Bobinas e Rolos Especiais (reservados) | `comercial` | `comercial:bobinas_rolos_reservados` | `rbr/` | view pronta |
| `mes` | Notas fiscais saidas / periodo | `comercial` | `comercial:notas_fiscais_saidas` | `mes/`, `mes/*.dbf` | view pronta |
| `est` | Estoque de produtos acabados | `producao` | `producao:estoque_acabados` | `est/` | view pronta |
| `esb` | Estoque Prod./Acabados em PDF | `comercial` | `comercial:estoque_pdf` | `esb/` | view pronta |
| `amp` | Analise de Margem Ped.venda x M.Prima | `comercial` | `comercial:amm_pedido` | `amp/` | view pronta |
| `ppr` | Planejamento de Producao | `producao` | `producao:planejamento` | `ppr/` | view pronta |
| `par` | Fluxo de Materia Prima | `producao` | `producao:fluxo_materia_prima` | `par/` | view pronta |
| `aprMP` | Entrada de Produto Acabado x Materia Prima | `producao` | `producao:entrada_produto_mp` | `aprMP/` | view pronta |
| `kgp` | Kg Pendente (sem reserva) | `producao` | `producao:kg_pendente` | `kgp/` | view pronta |
| `pma` | Itens pendentes em atraso | `producao` | `producao:itens_pendentes_atraso` | `pma/` | view pronta |
| `ore` | Operacao Rearme | `producao` | `producao:operacao_rearme` | `ore/` | view pronta |
| `esr` | Estoque Entradas/Rearme | `producao` | `producao:estoque_entradas_rearme` | `esr/` | view pronta |
| `pdm` | Producao por maquina / dia | `producao` | `producao:producao_dia` | `pdm/` | view pronta |
| `pdp` | Producao por maquina / periodo | `producao` | `producao:producao_periodo` | `pdp/` | view pronta |
| `bmi` | Bobinas M.I. | `producao` | `producao:bobinas_mi` | `bmi/` | view pronta |
| `ras` | Rastreabilidade Produto final -> Materia Prima | `producao` | `producao:rastreabilidade_mp` | `ras/` | view pronta |
| `mas` | Desvios de massa / Producao/mes | `producao` | `producao:desvios_massa` | `mas/` | view pronta |
| `esg` | Estoque de MP e Produto Intermediario | `producao` | `producao:estoque_mp_pi` | `esg/` | view pronta |
| `cpg` | Contas a Pagar/periodo | `financeiro` | `financeiro:contas_pagar` | `cpg/` | view pronta |
| `crc` | Contas a Receber/periodo | `financeiro` | `financeiro:contas_receber` | `crc/` | view pronta |
| `ban` | Saldo bancos (geral) | `financeiro` | `financeiro:saldo_bancos` | `ban/` | view pronta |
| `ext` | Extrato bancos | `financeiro` | `financeiro:extrato_bancos` | `ext/` | view pronta |
| `cre` | Contas a Receber por cidade | `financeiro` | `financeiro:contas_receber_cidade` | `cre/` | view pronta |
| `rcx` | Recebimentos de produtos - NFe | `recebimentos` | `recebimentos:nfe_produtos` | `rcx/` | view pronta |
| `xle` | Entrada de produtos/servicos - periodo | `recebimentos` | `recebimentos:entrada_produtos_servicos` | `xle/` | view pronta |
| `etq` | Etiquetas de Identificacao - Recebimentos | `recebimentos` | `recebimentos:etiquetas_identificacao` | `etq/` | view pronta |
| `cnt` | Conferencia de canhotos | `expedicao` | `expedicao:conferencia_canhotos` | `cnt/` | view pronta |
| `run` | Romaneios a Expedir por Unidade | `expedicao` | `expedicao:romaneios_expedir` | `run/` | view pronta |
| `bes` | Relacao de Bobinas Nao Faturadas | `comercial` | `comercial:bobinas_nao_faturadas` | `bes/` | view pronta |
| `tsu` | Faturamento x Embarque / periodo | `comercial` | `comercial:faturamento_x_embarque` | `tsu/` | view pronta |
| `ctb` | Planilhas diversas - Contabilidade | `contabilidade` | `contabilidade:planilhas_diversas` | `ctb/` | view pronta |
| `fxo` | Materia Prima por faturas expedidas | `suprimentos` | `suprimentos:materia_prima_faturas` | `fxo/` | view pronta |
| `tab` | Tabela tecnica | `core` | `core:tabela_tecnica` | `tab/` | view pronta |
| `rif` | Relatorio de Inspecao Final | `core` | `core:rif` | `rif/` | view pronta |
| `age` | Agenda - Ramais | `core` | `core:agenda` | `age/` | view pronta |

## Itens com Regra Condicional

- `cnt` aparece no menu de expedicao apenas para usuario/nome equivalente a `THIAGO`.
- Links externos/internos como TV Brascopper, DGQ, engenharia e assistencia tecnica devem ser tratados como links controlados por permissao, nao necessariamente como views Django.

## Primeira Frente Recomendada

Priorizar `cus`, `fat`, `pdm`, `cpg`, `crc` e `ban`, nessa ordem:

1. `cus` tem dados e telas capturadas.
2. `fat` e APR concentram dados comerciais e DBFs grandes.
3. `pdm` representa producao e valida o padrao de filtros por data/maquina.
4. `cpg`, `crc` e `ban` fecham a primeira base financeira.

