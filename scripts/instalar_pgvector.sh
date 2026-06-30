#!/bin/bash
set -e

echo "=== Instalando pgvector ==="

sudo cp /tmp/pgvector/vector.so /usr/lib/postgresql/14/lib/
echo "✓ .so copiado"

sudo cp /tmp/pgvector/vector.control /usr/share/postgresql/14/extension/
echo "✓ control copiado"

sudo cp /tmp/pgvector/sql/vector--0.8.3.sql /usr/share/postgresql/14/extension/
echo "✓ sql copiado"

echo ""
echo "=== Criando extensão no banco nfehub ==="
sudo -u postgres psql -d nfehub -c "CREATE EXTENSION IF NOT EXISTS vector;"
echo "✓ Extensão vector criada"

echo ""
echo "=== Verificando ==="
sudo -u postgres psql -d nfehub -c "SELECT * FROM pg_extension WHERE extname='vector';"
echo "✓ Concluído!"
