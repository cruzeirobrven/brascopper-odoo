#!/bin/bash
set -e

echo "=== Criando extensão vector ==="
sudo -u postgres psql -d brascopper_pdd -c "CREATE EXTENSION IF NOT EXISTS vector;"
echo "✓ vector criada"

echo ""
echo "=== Rodando migrações Django ==="
cd /home/emerson/brascopper_pdd
python3 manage.py migrate
echo "✓ Migrações concluídas"

echo ""
echo "=== Coletando statics ==="
python3 manage.py collectstatic --noinput
echo "✓ Static coletado"

echo ""
echo "=== Testando ==="
python3 manage.py check
echo "✓ Tudo pronto!"
