---
tags: [brascopper, django, amm, git]
created: 2026-06-25
---

# AMM Drill-Down por Produto + Git Init

## Git — repositório inicializado

- `git init` em `D:\BRASC\PRG\06082025\pdd\`
- Branch: `master`
- `.gitignore` exclui: venv, __pycache__, .env, staticfiles, metabase-data, logs, *.db, e ~80 pastas de módulos Harbour (age, amm, ban, fat, fin, ...)
- Commit inicial: **1.019 arquivos, 174.446 linhas** de código Django

Fluxo de atualização:

```bash
# Após mudanças:
git add -A
git commit -m "descrição"

# Após sincronizar para servidor 210:
.\deploy\0_copiar_para_servidor.ps1
# RDP no 210:
.\deploy\4_atualizar.ps1
```

---

## AMM — Drill-Down Produto → Clientes

### Rota

| URL | Nome | Parâmetros |
|-----|------|-----------|
| `/precificacao/amm/produto/<it_px>/<it_co>/` | `precificacao:amm_produto_drill` | GET: data_ini, data_fim, impostos (multi) |

### Como usar

1. Abrir AMM (`/precificacao/amm/`) e calcular um período
2. Na tabela "Análise por Produto", clicar no nome de qualquer produto
3. Abre página com tabela de clientes: metros, kg MP, faturamento, impostos, R$ MP, M%, % do total

### Filtros preservados

A URL de drill-down inclui automaticamente os mesmos filtros do relatório pai:
```
/precificacao/amm/produto/001/009/?data_ini=01/06/2026&data_fim=30/06/2026&impostos=3
```

### Arquivos

| Arquivo | Mudança |
|---------|---------|
| `precificacao/views_amm.py` | Nova view `amm_produto_drill` |
| `precificacao/urls.py` | Nova rota `amm_produto_drill` |
| `templates/precificacao/amm_relatorio.html` | Produto → link clicável |
| `templates/precificacao/amm_produto_drill.html` | Novo template drill-down |
