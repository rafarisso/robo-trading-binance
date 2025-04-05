# ============================================
# ROBÔ DE TRADING COM RSI + MACD + GESTÃO DE RISCO
# Autor: Rafael Risso 
# Finalidade: Portfólio profissional - Automação de investimento em criptomoedas
# Estratégia: Compra quando RSI < 30 E MACD cruza para cima / Venda quando RSI > 70 E MACD cruza para baixo
# Inclui: Controle de Stop-Loss e Take-Profit
# ============================================

from binance.client import Client
from binance.enums import *
import pandas as pd
import time
import datetime
import logging

# ======================= CONFIGURAÇÃO INICIAL =======================
API_KEY = "Pv10tIYlUwMNUaAULutUPcvcV1g5jkD0Tn3EwIpjbnAR9rN0CBR6rgocSJIExTTDr"
API_SECRET = "IOitJou2FWJgWay6bgl270kg7nP1fPNUCiKdT0TDrKsxQBcrSk16F7CEQblgJZky"

SYMBOL = "BTCUSDT"
INTERVAL = Client.KLINE_INTERVAL_15MINUTE

RSI_COMPRA = 30
RSI_VENDA = 70
STOP_LOSS_PCT = -3.0
TAKE_PROFIT_PCT = 5.0
ALOCACAO_PCT = 0.3

client = Client(API_KEY, API_SECRET)

logging.basicConfig(filename='operacoes.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# Variável global para monitorar posição aberta
posicao_aberta = False
preco_entrada = 0.0

# ======================= FUNÇÕES AUXILIARES =======================
def calcular_rsi(fechamentos, periodo=14):
    delta = fechamentos.diff()
    ganho = delta.where(delta > 0, 0)
    perda = -delta.where(delta < 0, 0)
    media_ganho = ganho.rolling(window=periodo).mean()
    media_perda = perda.rolling(window=periodo).mean()
    rs = media_ganho / media_perda
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calcular_macd(fechamentos, rapido=12, lento=26, sinal=9):
    ema_rapida = fechamentos.ewm(span=rapido, adjust=False).mean()
    ema_lenta = fechamentos.ewm(span=lento, adjust=False).mean()
    macd = ema_rapida - ema_lenta
    sinal_line = macd.ewm(span=sinal, adjust=False).mean()
    return macd, sinal_line

def buscar_dados(symbol, interval, limite=100):
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limite)
    df = pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base', 'taker_buy_quote', 'ignore'])
    df['close'] = df['close'].astype(float)
    return df

def obter_saldo_usdt():
    return float(client.get_asset_balance(asset='USDT')['free'])

def obter_quantidade_cripto(simbolo_base):
    return float(client.get_asset_balance(asset=simbolo_base)['free'])

# ======================= LÓGICA DO ROBÔ =======================
def executar_trading():
    global posicao_aberta, preco_entrada

    df = buscar_dados(SYMBOL, INTERVAL)
    rsi = calcular_rsi(df['close'])
    macd, sinal = calcular_macd(df['close'])

    rsi_atual = rsi.iloc[-1]
    macd_atual = macd.iloc[-1]
    sinal_atual = sinal.iloc[-1]
    macd_anterior = macd.iloc[-2]
    sinal_anterior = sinal.iloc[-2]
    preco_atual = df['close'].iloc[-1]

    print(f"RSI: {rsi_atual:.2f} | MACD: {macd_atual:.4f} | Sinal: {sinal_atual:.4f} | Preço: {preco_atual:.2f}")

    cruzamento_cima = macd_anterior < sinal_anterior and macd_atual > sinal_atual
    cruzamento_baixo = macd_anterior > sinal_anterior and macd_atual < sinal_atual

    simbolo_base = SYMBOL.replace("USDT", "")

    # Se já comprou, verifica lucro ou prejuízo
    if posicao_aberta:
        variacao_pct = ((preco_atual - preco_entrada) / preco_entrada) * 100
        print(f"📈 Variação desde a entrada: {variacao_pct:.2f}%")

        if variacao_pct >= TAKE_PROFIT_PCT or variacao_pct <= STOP_LOSS_PCT:
            qtd = obter_quantidade_cripto(simbolo_base)
            if qtd > 0:
                ordem = client.order_market_sell(symbol=SYMBOL, quantity=round(qtd, 6))
                logging.info(f"VENDA por TP/SL executada: {ordem}")
                print("💰 Venda executada por TAKE PROFIT ou STOP LOSS!")
                posicao_aberta = False
                preco_entrada = 0.0

    # Compra
    elif rsi_atual < RSI_COMPRA and cruzamento_cima:
        saldo_usdt = obter_saldo_usdt()
        valor_compra = saldo_usdt * ALOCACAO_PCT
        if valor_compra > 10:
            ordem = client.order_market_buy(symbol=SYMBOL, quoteOrderQty=valor_compra)
            logging.info(f"COMPRA RSI+MACD executada: {ordem}")
            print("✅ Compra executada!")
            preco_entrada = preco_atual
            posicao_aberta = True

    # Venda padrão por RSI + MACD cruzado (caso esteja fora da posição)
    elif rsi_atual > RSI_VENDA and cruzamento_baixo:
        qtd = obter_quantidade_cripto(simbolo_base)
        if qtd > 0:
            ordem = client.order_market_sell(symbol=SYMBOL, quantity=round(qtd, 6))
            logging.info(f"VENDA RSI+MACD executada: {ordem}")
            print("✅ Venda executada!")
            posicao_aberta = False
            preco_entrada = 0.0

# ======================= EXECUÇÃO CONTÍNUA =======================
if __name__ == "__main__":
    while True:
        try:
            executar_trading()
            print("Aguardando próxima verificação...\n")
            time.sleep(60 * 10)
        except Exception as e:
            logging.error(f"Erro na execução: {str(e)}")
            print("Erro ocorrido. Verifique os logs.")
            time.sleep(60 * 5)

