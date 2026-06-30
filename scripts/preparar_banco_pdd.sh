#!/bin/bash
set -e

echo "=== Preparando banco brascopper_pdd ==="

# Criar usuário brasc1
sudo -u postgres psql -c "CREATE USER brasc1 WITH PASSWORD 'mara5534';" 2>/dev/null || echo "Usuário brasc1 já existe"

# Dar ownership do banco
sudo -u postgres psql -c "ALTER DATABASE brascopper_pdd OWNER TO brasc1;"
sudo -u postgres psql -d brascopper_pdd -c "GRANT ALL ON SCHEMA public TO brasc1;"
sudo -u postgres psql -d brascopper_pdd -c "ALTER SCHEMA public OWNER TO brasc1;"

echo ""
echo "✓ Banco pronto! Agora importe os dados do Windows:"
echo ""
echo "No Windows PowerShell (como Administrador):"
echo '  cd D:\BRASC\PRG\06082025\pdd'
echo '  $env:PGPASSWORD="mara5534"'
echo '  pg_dump -U postgres -h localhost -d brascopper_pdd --no-owner > C:\temp\brascopper_pdd.sql'
echo ""
echo "Depois copie o arquivo para este servidor e rode:"
echo "  PGPASSWORD=mara5534 psql -U brasc1 -h localhost -d brascopper_pdd < /caminho/do/arquivo.sql"
echo ""
