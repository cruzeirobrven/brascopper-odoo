#!/usr/bin/env python3
"""
Agente de cotações — busca preços de metais (cobre, alumínio) e dólar
via APIs gratuitas e atualiza o banco brascopper_pdd.

APIs usadas:
  - AwesomeAPI: USD/BRL (gratuita, sem chave)
  - LME (London Metal Exchange): preços do cobre e alumínio
  - MetalPriceAPI.org: metais (requer chave gratuita)

Uso:
  python3 cotacoes_commodities.py [--dry-run]
  python3 cotacoes_commodities.py --interativo  (modo pergunta)
"""
import os, sys, json, time, re
from datetime import date, datetime
from urllib.request import Request, urlopen
from urllib.error import URLError

DRY_RUN = '--dry-run' in sys.argv
INTERATIVO = '--interativo' in sys.argv

DB_CONFIG = dict(
    host='localhost', user='brasc1', password='mara5534', dbname='brascopper_pdd'
)

COBRE_COD = '999.010'    # PVC (exemplo) - ajustar conforme mapeamento real
ALUMINIO_COD = '999.050'  # PVC tipo - ajustar

CURRENCY_ID = 1  # BRL


def fetch_usd_brl():
    """Cotação USD/BRL via AwesomeAPI (gratuita)."""
    try:
        req = Request(
            'https://economia.awesomeapi.com.br/json/last/USD-BRL',
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            bid = float(data['USDBRL']['bid'])
            return bid, data['USDBRL']['create_date']
    except Exception as e:
        print(f"  ⚠ AwesomeAPI: {e}")
        return None, None


def fetch_commodity_google_finance(symbol, expected_min, expected_max):
    """Preço de commodity via Google Finance."""
    try:
        req = Request(
            f'https://www.google.com/finance/quote/{symbol}',
            headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'}
        )
        with urlopen(req, timeout=15) as r:
            html = r.read().decode()
            prices = re.findall(r'(\d{1,3}(?:,\d{3})*\.\d{2})', html)
            for p in prices:
                val = float(p.replace(',', ''))
                if expected_min < val < expected_max:
                    return val
    except Exception as e:
        print(f"  ⚠ Google Finance {symbol}: {e}")
    return None


def fetch_lme_copper():
    """Preço do cobre via múltiplas fontes gratuitas."""
    val = fetch_commodity_google_finance('COPPER:COMEX', 7000, 12000)
    if val:
        return val
    # Fallback: Investing.com
    try:
        req = Request(
            'https://www.investing.com/commodities/copper',
            headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'}
        )
        with urlopen(req, timeout=15) as r:
            html = r.read().decode()
            prices = re.findall(r'(\d{1,3}(?:,\d{3})*\.\d{2})', html)
            for p in prices:
                val = float(p.replace(',', ''))
                if 7000 < val < 12000:
                    return val
    except Exception:
        pass
    return None


def fetch_lme_aluminum():
    """Preço do alumínio via múltiplas fontes gratuitas."""
    val = fetch_commodity_google_finance('ALUMINUM:COMEX', 1500, 4000)
    if val:
        return val
    # Fallback: TradingEconomics
    try:
        req = Request(
            'https://tradingeconomics.com/commodity/aluminum',
            headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'}
        )
        with urlopen(req, timeout=15) as r:
            html = r.read().decode()
            prices = re.findall(r'(\d{1,3}(?:,\d{3})*\.\d{2})', html)
            for p in prices:
                val = float(p.replace(',', ''))
                if 1500 < val < 4000:
                    return val
    except Exception:
        pass
    return None


def fetch_metalprice(symbol='COPPER'):
    """Tenta MetalPriceAPI (requer chave gratuita)."""
    api_key = os.environ.get('METALPRICE_API_KEY', '')
    if not api_key:
        return None, None
    try:
        url = f'https://api.metalpriceapi.com/v1/latest?api_key={api_key}&base=USD&currency=BRL&unit=kg'
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            # Retorna taxa USD/BRL e preço do metal
            return data.get('rates', {}).get('BRL'), data.get('rates', {}).get(symbol)
    except Exception as e:
        return None, None


def update_commodity_price(commodity_code, price, currency='BRL'):
    """Atualiza prec_commodity_price_period no banco."""
    import psycopg2

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    try:
        # Busca commodity_id
        cur.execute(
            "SELECT id FROM precificacao_commodity WHERE code = %s",
            (commodity_code,)
        )
        row = cur.fetchone()
        if not row:
            print(f"  ⚠ Commodity {commodity_code} não encontrada no banco")
            return False

        commodity_id = row[0]
        today = date.today()

        # Verifica se já existe preço para hoje
        cur.execute(
            "SELECT id FROM prec_commodity_price_period "
            "WHERE commodity_id = %s AND period = %s",
            (commodity_id, today)
        )
        existing = cur.fetchone()

        if existing:
            if not DRY_RUN:
                cur.execute(
                    "UPDATE prec_commodity_price_period SET price = %s, currency = %s "
                    "WHERE id = %s",
                    (price, currency, existing[0])
                )
            print(f"  ✓ {commodity_code}: R$ {price:.4f}/kg (atualizado)")
        else:
            if not DRY_RUN:
                cur.execute(
                    "INSERT INTO prec_commodity_price_period "
                    "(commodity_id, period, price, currency, active, source_file) "
                    "VALUES (%s, %s, %s, %s, true, 'cotacoes_commodities.py')",
                    (commodity_id, today, price, currency)
                )
            print(f"  ✓ {commodity_code}: R$ {price:.4f}/kg (inserido)")

        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        print(f"  ERRO ao atualizar {commodity_code}: {e}")
        return False
    finally:
        cur.close()
        conn.close()


def main():
    print(f"{'DRY RUN - ' if DRY_RUN else ''}Agente de Cotações")
    print("=" * 50)
    print(f"Data: {date.today().isoformat()}")
    print()

    # 1. USD/BRL
    print(">> Dólar (USD/BRL)")
    usd, timestamp = fetch_usd_brl()
    if usd:
        print(f"  ✓ USD = R$ {usd:.4f} ({timestamp})")
    else:
        print("  ✗ Não disponível")
    print()

    # 2. Cobre
    print(">> Cobre (LME)")
    copper_usd = fetch_lme_copper()
    if copper_usd:
        copper_brl = copper_usd * usd if usd else copper_usd
        print(f"  ✓ USD {copper_usd:.2f}/ton → R$ {copper_brl:.2f}/ton (R$ {copper_brl/1000:.4f}/kg)")
        update_commodity_price('COBRE', round(copper_brl / 1000, 4))
    else:
        print("  ✗ Não disponível")
    print()

    # 3. Alumínio
    print(">> Alumínio (LME)")
    al_usd = fetch_lme_aluminum()
    if al_usd:
        al_brl = al_usd * usd if usd else al_usd
        print(f"  ✓ USD {al_usd:.2f}/ton → R$ {al_brl:.2f}/ton (R$ {al_brl/1000:.4f}/kg)")
        update_commodity_price('ALUMINIO', round(al_brl / 1000, 4))
    else:
        print("  ✗ Não disponível")
    print()

    # 4. Modo interativo
    if INTERATIVO:
        print()
        print(">> Modo interativo — informe os preços manualmente:")
        for metal in ['COBRE', 'ALUMINIO', 'LIGA']:
            try:
                val = input(f"  Preço {metal} (R$/kg) [Enter=pular]: ")
                if val.strip():
                    update_commodity_price(metal, float(val.replace(',', '.')))
            except (ValueError, EOFError):
                pass

    print()
    print("Concluído!")


def atualizar_proda_from_commodities():
    """Atualiza legacy_proda.presi com base nos preços das commodities.
    Mapeia os produtos 999.XXX para as commodities correspondentes."""
    import psycopg2

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Mapeamento: commodity_code → lista de (pi_px, pi_co)
    MAP = {
        'COBRE': [('999', '010')],
        'ALUMINIO': [('999', '050')],
    }

    for commodity_code, produtos in MAP.items():
        cur.execute(
            "SELECT price FROM prec_commodity_price_period pc "
            "JOIN precificacao_commodity c ON c.id = pc.commodity_id "
            "WHERE c.code = %s ORDER BY pc.period DESC LIMIT 1",
            (commodity_code,)
        )
        row = cur.fetchone()
        if not row:
            continue
        price = row[0]
        today = date.today()

        for px, co in produtos:
            if not DRY_RUN:
                cur.execute(
                    "UPDATE legacy_proda SET presi = %s, prdat = %s "
                    "WHERE pi_px = %s AND pi_co = %s",
                    (price, today, px, co)
                )
            print(f"  ✓ legacy_proda {px}.{co}: presi = {price}")

    conn.commit()
    cur.close()
    conn.close()


if __name__ == '__main__':
    main()
    if not INTERATIVO:
        print()
        print(">> Atualizando legacy_proda...")
        atualizar_proda_from_commodities()
