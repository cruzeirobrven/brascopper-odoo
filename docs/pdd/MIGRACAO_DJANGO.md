# Migracao do PDD para Django

Documento de continuidade para migrar o sistema PDD legado para Django.

## Objetivo

Migrar o PDD legado, hoje baseado principalmente em programas Harbour/xBase/CGI (`.prg`, `.dbf`, `.ntx`, executaveis e HTML gerado), para uma aplicacao Django organizada por dominios de negocio, preservando:

- menu e permissoes por usuario;
- consultas, filtros, drill-downs e relatorios;
- dados historicos e codigos de referencia usados pela operacao;
- aparencia funcional das telas antigas quando isso reduzir risco de transicao.

## Estado Atual do Codigo

### Legado

- `pdd/pdd.prg` contem o menu principal e grande parte da logica de navegacao por formularios CGI.
- Os modulos legados aparecem como pastas curtas, por exemplo `cus`, `fat`, `pdm`, `apr`, `ban`, `rcx`, `run`, `ctb`, `pgr`, etc.
- As telas legadas usam formularios POST para `/cgi-bin/<modulo>` e repassam campos como `wrnomr`, `wmaouf`, `wemail` e `wsenha`.
- O acesso a dados no legado usa arquivos xBase/DBF em diretorios como `/hd2/redb/brasc/cgi/arq`, alem de arquivos locais encontrados no projeto.
- Ha arquivos DBF relevantes em `fat/fatx`, `ivc/pedid.dbf`, `mes/g1.dbf` e `mes/h1.dbf`.

### Django

- O projeto Django existe em `brascopper_pdd`.
- `manage.py check` passou sem erros usando `venv_django/Scripts/python.exe`.
- Apenas o app `core` esta ativo em `INSTALLED_APPS`.
- Apps de dominio ja existem, mas ainda estao vazios: `custos`, `comercial`, `producao`, `financeiro`, `planejamento`, `suprimentos`, `expedicao`, `recebimentos`, `contabilidade`.
- `core.models` ja define uma primeira base compartilhada:
  - `Filial`
  - `CentroResultado`
  - `Fornecedor`
  - `MovimentoFinanceiro`
  - `PerfilUsuario`
- `core.views.menu_principal` monta um menu inicial, mas aponta para namespaces ainda nao implementados, como `comercial:apr`, `custos:custo_mes`, `producao:planejamento`, `financeiro:contas_pagar`.

### Prototipos e Bases Auxiliares

- `app_pdd_complete.py` e `pdd_modern_architecture.py` sao prototipos Streamlit/SQLite com ideias de dashboard, login, drill-down e entidades.
- `create_pdd_database.py` cria/popula `brascopper_pdd.db` com tabelas demonstrativas:
  - `usuarios`
  - `centros_custo`
  - `movimentos_financeiros`
  - `fornecedores`
  - `produtos`
  - `maquinas`
  - `producao`
  - `vendas`
  - `estoque`
- `brascopper_cus.db` concentra o piloto de custos:
  - `fconta`
  - `gercus`
  - `fincus`
- `pdd_html` guarda capturas HTML de telas antigas, incluindo menu principal, APR e CUS. Esse diretorio deve ser usado como referencia visual e funcional, nao como codigo final.

## Riscos e Pontos de Atencao

- O menu Django atual pode quebrar na renderizacao se tentar resolver URLs de apps ainda sem `urls.py`.
- `requirements.txt` nao inclui Django nem `python-decouple`, embora o projeto Django dependa deles.
- O `Dockerfile` e `docker-compose.yml` ainda estao direcionados para Streamlit/CUS, nao para Django.
- `.env` contem credenciais e chaves em texto claro; antes de versionar ou publicar, mover segredos para ambiente seguro.
- Ha diferencas entre banco local SQLite de prototipo, PostgreSQL configurado no Django e possivel origem real em DBF/SQL Server.
- Alguns textos aparecem com sinais de encoding incorreto em arquivos e terminal. Padronizar tudo em UTF-8 antes de ampliar templates e mensagens.
- Permissoes do legado estao misturadas ao menu e a regras por usuario. Em Django, isso deve virar grupos, permissoes e validacoes nas views.

## Estrategia Recomendada

### 1. Estabilizar a Base Django

Antes de migrar novas telas:

- adicionar `django`, `python-decouple`, `pandas`, `openpyxl`, `psycopg2-binary` e bibliotecas DBF necessarias ao `requirements.txt`;
- corrigir `setup_django.bat`, que hoje tem `server@echo off` e entra em `brascopper_pdd` antes de criar apps;
- criar `urls.py` minimo para cada app de dominio ou remover links nao implementados do menu;
- ativar gradualmente os apps em `INSTALLED_APPS`;
- criar migrations para o `core`;
- decidir se o banco de desenvolvimento sera PostgreSQL ou SQLite temporario;
- revisar encoding dos arquivos Python e templates.

### 2. Transformar o Menu Legado em Inventario Migravel

O menu principal em `pdd/pdd.prg` deve virar uma tabela ou estrutura Django com:

- secao;
- codigo legado do CGI;
- nome exibido;
- app Django destino;
- rota Django destino;
- parametros herdados;
- perfil/grupo permitido;
- status de migracao.

Mapa inicial por area:

| Secao legado | Codigos principais | App Django sugerido |
| --- | --- | --- |
| BRASCOPPER 2021/2025 | `apr`, `amm`, `cus` | `comercial`, `custos` |
| INFORMATICA | `ppr`, `fmd`, `ore`, `fxi`, `rcx1`, `txe` | `planejamento`, `comercial`, `recebimentos`, `financeiro` |
| COMERCIAL | `fat`, `ore`, `amm`, `far`, `pmp`, `rbr`, `mes`, `est`, `fpr`, `esb`, `amp` | `comercial` |
| RECEBIMENTOS | `rcx`, `xle`, `etq` | `recebimentos` |
| PRODUCAO | `pdm`, `pdp`, `bmi`, `ras`, `mas`, `esg`, `est` | `producao` |
| EXPEDICAO | `cnt`, `run`, `bes`, `tsu` | `expedicao` |
| CONTABILIDADE | `ctb` | `contabilidade` |
| CUSTO | `cus`, `cuv`, `cst`, `ivc`, `cup` | `custos` |
| PLANEJAMENTO | `par`, `aprMP`, `apr`, `kgp`, `pmp`, `pma`, `mxx`, `mes`, `ore`, `esr` | `planejamento` |
| FINANCEIRO | `cpg`, `crc`, `ban`, `ext`, `cre`, `ore`, `ivc` | `financeiro` |
| SUPRIMENTOS/COMPRAS | `fxo` | `suprimentos` |
| QUALIDADE/ENGENHARIA | `tab`, `rif`, links externos | novo app ou `core`/links externos |

### 3. Comecar Pelo Modulo CUS

O melhor piloto e `CUS` porque ja ha:

- capturas HTML em `pdd_html`;
- prototipos `app_cus*.py`;
- scripts de migracao `migrate_data_cus_sqlite.py`;
- banco `brascopper_cus.db`;
- tabelas pequenas e compreensiveis (`fconta`, `gercus`, `fincus`);
- telas de pesquisa, resultado e drill-down.

Fluxo sugerido para `custos`:

1. Criar models Django para `Conta`, `GrupoCusto` e `LancamentoCusto`.
2. Mapear campos:
   - `fconta.fcod` -> codigo da conta/fornecedor;
   - `fconta.fnome` -> nome;
   - `gercus.gcod` -> codigo do grupo;
   - `gercus.gdesc` -> descricao do grupo;
   - `fincus.cdata` -> data;
   - `fincus.entid` -> identificador do movimento;
   - `fincus.fcod` -> conta;
   - `fincus.gr_px` -> grupo;
   - `fincus.unidade` -> filial/unidade;
   - `fincus.dour` -> tipo/indicador legado;
   - `fincus.cuvlr` -> valor;
   - `fincus.descricao` -> descricao.
3. Criar migration de schema.
4. Criar comando Django `importar_cus` para carregar os dados do SQLite/DBF.
5. Criar tela de selecao de mes.
6. Criar tela de resultado agregada.
7. Criar drill-down por grupo/conta mantendo o comportamento das capturas.
8. Validar totais contra `app_cus_sqlite_fixed.py` e os HTMLs capturados.

### 4. Migrar por Tela, Nao por Pasta

Cada tela migrada deve ter um registro com:

- codigo legado (`cus`, `fat`, `pdm`, etc.);
- arquivo principal legado;
- arquivos de dados usados;
- parametros de entrada;
- filtros;
- colunas exibidas;
- calculos;
- regras de permissao;
- rota Django;
- template;
- testes ou consulta de validacao;
- status.

Estados sugeridos:

- `nao iniciado`
- `inventariado`
- `modelado`
- `importacao pronta`
- `view pronta`
- `validado com legado`
- `desativado no legado`

## Arquitetura Django Alvo

### Apps

- `core`: autenticacao, perfil, filial, menu, permissoes, base visual.
- `custos`: custo mensal, vencimentos, custo por setor, DRE.
- `comercial`: faturamento, APR, margem, pendencias, estoque acabado comercial.
- `producao`: producao por maquina, bobinas, rastreabilidade, estoque intermediario.
- `financeiro`: contas a pagar, contas a receber, saldo e extrato bancario.
- `planejamento`: fluxo de materia-prima, pendencias, entradas x materia-prima.
- `recebimentos`: NFe, entradas de produtos/servicos, etiquetas.
- `expedicao`: romaneios, bobinas nao faturadas, conferencia de canhotos.
- `suprimentos`: materia-prima por faturas expedidas, compras.
- `contabilidade`: planilhas e integracoes contabeis.

### Padrao de Implementacao por App

Cada app deve conter:

- `models.py` com entidades do dominio;
- `urls.py` com `app_name`;
- `views.py` com views protegidas por login e permissao;
- `services.py` para consultas, agregacoes e regras de negocio;
- `forms.py` para filtros;
- `templates/<app>/...` para telas;
- `management/commands/importar_<modulo>.py` para migracao de dados;
- testes de consulta e permissionamento.

Evitar colocar regras SQL complexas direto em `views.py`. Views devem montar filtros, chamar services e renderizar templates.

## Banco de Dados

O Django esta configurado para PostgreSQL:

- database: `brascopper_pdd`
- host: `localhost`
- port: `5432`

O `docker-compose.yml` atual sobe outro banco (`brascopper_cus`) na porta local `5433` e uma aplicacao Streamlit. Para Django, decidir um destes caminhos:

- ajustar `docker-compose.yml` para `web` Django + `postgres`;
- ou manter Postgres local e documentar bootstrap separado.

Recomendacao: usar PostgreSQL como destino final e SQLite apenas como fonte temporaria dos prototipos.

## Checklist de Continuidade

1. Criar `docs/INVENTARIO_TELAS.md` com uma linha por item de menu legado.
2. Corrigir `requirements.txt` para refletir o projeto Django.
3. Criar `urls.py` minimo nos apps de dominio.
4. Trocar os links do menu para resolverem apenas rotas existentes ou marcar itens como "em migracao".
5. Criar migrations do `core`.
6. Implementar `custos` como piloto.
7. Validar totais de CUS contra `brascopper_cus.db` e capturas HTML.
8. Migrar `comercial/faturamento` ou `producao/pdm` como segunda tela, pois sao centrais no menu.
9. Atualizar Docker para Django.
10. Criar testes automatizados para login, menu por permissao e primeira consulta de custos.

## Criterio de Aceite por Tela

Uma tela so deve ser considerada migrada quando:

- a rota Django existe e exige login;
- permissao de acesso equivale ao legado;
- filtros principais existem;
- resultados batem com o legado para pelo menos um periodo conhecido;
- totais e subtotais batem;
- drill-downs ou links secundarios foram migrados ou documentados como pendentes;
- template funciona em desktop sem depender dos HTMLs salvos;
- origem dos dados esta documentada;
- ha teste ou consulta de validacao reproduzivel.

## Proximas Edicoes Recomendadas no Codigo

1. Criar `custos/urls.py` e uma view placeholder `custo_mes` para permitir que o menu carregue sem erro.
2. Ativar `custos` em `INSTALLED_APPS`.
3. Substituir, no menu, URLs ainda inexistentes por uma rota `core:em_migracao` ate cada app estar pronto.
4. Criar models reais de `custos`.
5. Criar comando de importacao `importar_cus`.
6. Corrigir `requirements.txt` e Docker para Django.
