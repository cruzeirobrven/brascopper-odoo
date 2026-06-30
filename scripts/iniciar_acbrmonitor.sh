#!/usr/bin/env bash
set -e

docker rm -f acbrmonitor 2>/dev/null || true

# Garante Comandos_Remotos=1 para aceitar conexoes do host
sed -i 's/^Comandos_Remotos=0/Comandos_Remotos=1/' /opt/ACBrMonitor/ACBrMonitor.ini

docker run -d \
  --name acbrmonitor \
  --restart unless-stopped \
  -e DISPLAY=:1 \
  -p 3434:3434 \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v /opt/ACBrMonitor:/opt/ACBrMonitor \
  -v /tmp/nfe_ini:/tmp/nfe_ini \
  ubuntu:20.04 \
  bash -c "apt update -qq && apt install -y -qq libgtk2.0-0 libglib2.0-0 libcanberra-gtk-module gtk2-engines-pixbuf 2>/dev/null && /opt/ACBrMonitor/ACBrMonitor"

echo ""
echo "Aguardando inicializacao..."
sleep 3

if ss -tlnp | grep -q 3434; then
    echo "OK - ACBrMonitor rodando na porta 3434"
else
    echo "ATENCAO: Porta 3434 ainda nao esta ouvindo."
    echo "Verifique a janela do ACBrMonitor e ative TCP/IP no menu Monitor."
fi
