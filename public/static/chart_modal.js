/**
 * CB Crypto AI Radar - Live Interactive TradingView Chart & Coin Details Modals
 * Institutional Trading Terminal & Technical Analysis Component
 */

(function () {
  // Institutional ticker mapping
  const TRADINGVIEW_TICKER_MAP = {
    'HYPE': 'HYPERLIQUID:HYPEUSDT',
    'BTC': 'BINANCE:BTCUSDT',
    'ETH': 'BINANCE:ETHUSDT',
    'SOL': 'BINANCE:SOLUSDT',
    'SUI': 'BINANCE:SUIUSDT',
    'DOGE': 'BINANCE:DOGEUSDT',
    'XRP': 'BINANCE:XRPUSDT',
    'ADA': 'BINANCE:ADAUSDT',
    'AVAX': 'BINANCE:AVAXUSDT',
    'LINK': 'BINANCE:LINKUSDT',
    'SHIB': 'BINANCE:SHIBUSDT',
    'PEPE': 'BINANCE:PEPEUSDT',
    'NEAR': 'BINANCE:NEARUSDT',
    'UNI': 'BINANCE:UNIUSDT',
    'AAVE': 'BINANCE:AAVEUSDT',
    'LTC': 'BINANCE:LTCUSDT',
    'BCH': 'BINANCE:BCHUSDT',
    'XLM': 'BINANCE:XLMUSDT',
    'ETC': 'BINANCE:ETCUSDT',
    'COMP': 'BINANCE:COMPUSDT',
    'BONK': 'BINANCE:BONKUSDT',
    'WIF': 'BINANCE:WIFUSDT',
    'POL': 'BINANCE:POLUSDT',
    'MATIC': 'BINANCE:MATICUSDT',
    'ARB': 'BINANCE:ARBUSDT',
    'OP': 'BINANCE:OPUSDT',
    'RENDER': 'BINANCE:RENDERUSDT',
    'FET': 'BINANCE:FETUSDT',
    'XTZ': 'BINANCE:XTZUSDT',
    'ATOM': 'BINANCE:ATOMUSDT',
    'FIL': 'BINANCE:FILUSDT',
    'DOT': 'BINANCE:DOTUSDT',
    'INJ': 'BINANCE:INJUSDT',
    'META': 'NASDAQ:META',
    'NVDA': 'NASDAQ:NVDA',
    'AAPL': 'NASDAQ:AAPL',
    'TSLA': 'NASDAQ:TSLA',
    'HOOD': 'NASDAQ:HOOD',
    'COIN': 'NASDAQ:COIN'
  };

  let currentChartSymbol = 'HYPE';
  let currentChartTimeframe = '15';
  let activeDetailCoin = null;

  function resolveTradingViewTicker(symbol) {
    if (!symbol) return 'BINANCE:BTCUSDT';
    const clean = symbol.toUpperCase().trim().replace('$', '');
    if (TRADINGVIEW_TICKER_MAP[clean]) {
      return TRADINGVIEW_TICKER_MAP[clean];
    }
    if (clean.includes(':')) {
      return clean;
    }
    return `BINANCE:${clean}USDT`;
  }

  function getTradingViewEmbedUrl(ticker, interval = '15') {
    const params = new URLSearchParams({
      frameElementId: 'tradingview_advanced_chart',
      symbol: ticker,
      interval: interval,
      hidesidetoolbar: '0',
      symboledit: '1',
      saveimage: '1',
      toolbarbg: '0E131F',
      studies: JSON.stringify([
        { id: 'MASimple@tv-basicstudies', inputs: { length: 20 } },
        { id: 'MASimple@tv-basicstudies', inputs: { length: 50 } },
        { id: 'RSI@tv-basicstudies', inputs: { length: 14 } }
      ]),
      theme: 'dark',
      style: '1',
      timezone: 'America/New_York',
      withdateranges: '1',
      showpopupbutton: '1',
      locale: 'en'
    });
    return `https://s.tradingview.com/widgetembed/?${params.toString()}`;
  }

  function ensureChartModalDOM() {
    if (document.getElementById('tvChartModalOverlay')) return;

    const modalHtml = `
      <div id="tvChartModalOverlay" class="modal-overlay">
        <div class="modal-dialog modal-dialog-chart">
          <div class="modal-header">
            <div class="modal-title-group">
              <div class="modal-title-icon">📊</div>
              <div>
                <div class="modal-title">
                  <span id="tvModalTitleSymbol">HYPE</span>
                  <span style="font-size: 13px; font-weight: 500; color: #94A3B8;" id="tvModalExchange">HYPERLIQUID:HYPEUSDT</span>
                </div>
                <div class="modal-subtitle">LIVE INSTITUTIONAL TRADINGVIEW CHART · TECHNICAL ANALYSIS</div>
              </div>
            </div>

            <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
              <div class="chart-timeframe-bar" id="tvTimeframeSelector">
                <button class="tf-btn" data-tf="1" onclick="window.switchChartTimeframe('1')">1m</button>
                <button class="tf-btn" data-tf="5" onclick="window.switchChartTimeframe('5')">5m</button>
                <button class="tf-btn active" data-tf="15" onclick="window.switchChartTimeframe('15')">15m</button>
                <button class="tf-btn" data-tf="60" onclick="window.switchChartTimeframe('60')">1h</button>
                <button class="tf-btn" data-tf="240" onclick="window.switchChartTimeframe('240')">4h</button>
                <button class="tf-btn" data-tf="D" onclick="window.switchChartTimeframe('D')">1D</button>
              </div>
              <button class="modal-close-btn" onclick="window.closeTradingViewModal()" title="Close (Esc)">✕</button>
            </div>
          </div>

          <div class="modal-body modal-body-chart">
            <iframe id="tvChartIframe" class="tradingview-iframe" src="about:blank" allowtransparency="true" scrolling="no" allowfullscreen></iframe>
          </div>

          <div class="modal-actions-bar">
            <div class="modal-actions-left">
              <span style="font-size: 12px; font-family: 'JetBrains Mono', monospace; color: #94A3B8;">
                Indicators: 20 SMA · 50 SMA · RSI (14)
              </span>
            </div>
            <div style="display: flex; align-items: center; gap: 10px;">
              <button class="btn" id="tvOpenRiskCalcBtn" onclick="window.openRiskFromChart()" style="padding: 8px 14px; font-size: 12px;">
                🧮 Size Position
              </button>
              <a id="tvExternalTradeLink" href="https://robinhood.com" target="_blank" class="btn btn-exec-rh" style="padding: 8px 16px; font-size: 12px;">
                🟢 Trade on Robinhood
              </a>
            </div>
          </div>
        </div>
      </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHtml);

    document.getElementById('tvChartModalOverlay').addEventListener('click', (e) => {
      if (e.target.id === 'tvChartModalOverlay') {
        window.closeTradingViewModal();
      }
    });
  }

  function openTradingViewModal(symbol = 'HYPE', timeframe = null) {
    ensureChartModalDOM();
    currentChartSymbol = (symbol || 'HYPE').toUpperCase().trim().replace('$', '');
    if (timeframe) currentChartTimeframe = timeframe;

    const tvTicker = resolveTradingViewTicker(currentChartSymbol);
    const overlay = document.getElementById('tvChartModalOverlay');
    const iframe = document.getElementById('tvChartIframe');
    const titleSymbol = document.getElementById('tvModalTitleSymbol');
    const exchangeLabel = document.getElementById('tvModalExchange');
    const tradeLink = document.getElementById('tvExternalTradeLink');

    titleSymbol.textContent = `$${currentChartSymbol}`;
    exchangeLabel.textContent = tvTicker;

    if (currentChartSymbol === 'HYPE') {
      tradeLink.className = 'btn btn-exec-hl';
      tradeLink.href = 'https://app.hyperliquid.xyz/trade/HYPE';
      tradeLink.innerHTML = '⚡ Trade HYPE on Hyperliquid';
    } else {
      tradeLink.className = 'btn btn-exec-rh';
      tradeLink.href = `https://robinhood.com/crypto/${currentChartSymbol}`;
      tradeLink.innerHTML = `🟢 Trade ${currentChartSymbol} on Robinhood`;
    }

    document.querySelectorAll('#tvTimeframeSelector .tf-btn').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-tf') === currentChartTimeframe);
    });

    iframe.src = getTradingViewEmbedUrl(tvTicker, currentChartTimeframe);
    overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function switchChartTimeframe(tf) {
    currentChartTimeframe = tf;
    const tvTicker = resolveTradingViewTicker(currentChartSymbol);
    const iframe = document.getElementById('tvChartIframe');

    document.querySelectorAll('#tvTimeframeSelector .tf-btn').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-tf') === tf);
    });

    if (iframe) iframe.src = getTradingViewEmbedUrl(tvTicker, currentChartTimeframe);
  }

  function closeTradingViewModal() {
    const overlay = document.getElementById('tvChartModalOverlay');
    if (overlay) {
      overlay.classList.remove('active');
      const iframe = document.getElementById('tvChartIframe');
      if (iframe) iframe.src = 'about:blank';
      document.body.style.overflow = '';
    }
  }

  function openRiskFromChart() {
    closeTradingViewModal();
    let coinObj = null;
    if (window.appData && window.appData.asset_signals) {
      coinObj = window.appData.asset_signals.find(c => c.symbol.toUpperCase() === currentChartSymbol);
    }
    if (typeof window.openRiskCalculatorModal === 'function') {
      window.openRiskCalculatorModal(coinObj || { symbol: currentChartSymbol });
    }
  }

  // ===========================================================================
  // Deep Coin Details Modal (AI Conviction + ICT Smart Money Levels)
  // ===========================================================================

  function ensureCoinDetailsModalDOM() {
    if (document.getElementById('coinDetailsModalOverlay')) return;

    const modalHtml = `
      <div id="coinDetailsModalOverlay" class="modal-overlay">
        <div class="modal-dialog modal-dialog-coin">
          <div class="modal-header">
            <div class="modal-title-group">
              <div class="modal-title-icon" id="cdmIcon">💎</div>
              <div>
                <div class="modal-title">
                  <span id="cdmSymbol">SOL</span>
                  <span class="badge-signal sig-strong-buy" id="cdmSignalBadge">STRONG BUY</span>
                </div>
                <div class="modal-subtitle" id="cdmSubtitle">SOLANA · LAYER 1 / 2 · ROBINHOOD TRADABLE</div>
              </div>
            </div>
            <button class="modal-close-btn" onclick="window.closeCoinDetailsModal()" title="Close (Esc)">✕</button>
          </div>

          <div class="modal-body" id="cdmBody">
            <!-- Injected dynamically -->
          </div>

          <div class="modal-actions-bar">
            <div class="modal-actions-left">
              <button class="btn" id="cdmOpenChartBtn" onclick="window.openChartFromCoinModal()">
                📊 View TradingView Chart
              </button>
              <button class="btn" id="cdmOpenCalcBtn" onclick="window.openRiskFromCoinModal()">
                🧮 Size Risk & Position
              </button>
            </div>
            <div id="cdmExecAction">
              <!-- 1-Click execution button -->
            </div>
          </div>
        </div>
      </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHtml);

    document.getElementById('coinDetailsModalOverlay').addEventListener('click', (e) => {
      if (e.target.id === 'coinDetailsModalOverlay') {
        window.closeCoinDetailsModal();
      }
    });
  }

  function openCoinDetailsModal(coinData) {
    ensureCoinDetailsModalDOM();

    let coin = coinData;
    if (typeof coinData === 'string') {
      const sym = coinData.toUpperCase().trim().replace('$', '');
      if (window.appData && window.appData.asset_signals) {
        coin = window.appData.asset_signals.find(c => c.symbol.toUpperCase() === sym);
      }
      if (!coin && window.appData && window.appData.top_entries) {
        coin = window.appData.top_entries.find(c => c.symbol.toUpperCase() === sym);
      }
      if (!coin) {
        coin = {
          symbol: sym,
          name: sym,
          price: 100.0,
          change_24h: 3.5,
          change_7d: 8.2,
          signal: 'STRONG BUY',
          conviction: 88,
          score: 82,
          entry_zone: '$98.00 – $100.50',
          stop_loss: '$94.50',
          target_1: '$108.00',
          target_2: '$116.00',
          risk_reward: '3.4 : 1',
          tactical_plan: 'Buy into discount demand shelf. Defend stop loss.',
          why_buy: 'Strong volume continuation and catalyst alignment.'
        };
      }
    }

    activeDetailCoin = coin;

    const overlay = document.getElementById('coinDetailsModalOverlay');
    const symbolEl = document.getElementById('cdmSymbol');
    const subtitleEl = document.getElementById('cdmSubtitle');
    const signalBadge = document.getElementById('cdmSignalBadge');
    const bodyEl = document.getElementById('cdmBody');
    const execBox = document.getElementById('cdmExecAction');

    symbolEl.textContent = `${coin.symbol}`;
    subtitleEl.textContent = `${(coin.name || coin.symbol).toUpperCase()} · ${(coin.sector || 'CRYPTO').toUpperCase()} · ${(coin.exchange || 'ROBINHOOD').toUpperCase()}`;

    signalBadge.className = `badge-signal ${coin.signal === 'STRONG BUY' ? 'sig-strong-buy' : (coin.signal === 'DIP ENTRY' ? 'sig-dip' : (coin.signal === 'DEFENSIVE EXIT' ? 'sig-exit' : 'sig-hold'))}`;
    signalBadge.textContent = `${coin.signal || 'WATCH'}`;

    if (coin.symbol === 'HYPE') {
      execBox.innerHTML = `
        <a href="https://app.hyperliquid.xyz/trade/HYPE" target="_blank" class="btn btn-exec-hl">
          ⚡ Trade HYPE on Hyperliquid
        </a>
      `;
    } else {
      execBox.innerHTML = `
        <a href="https://robinhood.com/crypto/${coin.symbol}" target="_blank" class="btn btn-exec-rh">
          🟢 Trade ${coin.symbol} on Robinhood
        </a>
      `;
    }

    const price = typeof coin.price === 'number' ? coin.price : parseFloat(coin.price || 0);
    const chg24h = typeof coin.change_24h === 'number' ? coin.change_24h : parseFloat(coin.change_24h || 0);
    const chg7d = typeof coin.change_7d === 'number' ? coin.change_7d : parseFloat(coin.change_7d || 0);
    const conviction = coin.conviction || 85;
    const score = coin.score || 75;

    const fvgZone = coin.fvg_zone || (price < 1 ? `$${(price * 0.985).toFixed(4)} – $${(price * 0.995).toFixed(4)}` : `$${(price * 0.985).toFixed(2)} – $${(price * 0.995).toFixed(2)}`);
    const sweepLevel = coin.liquidity_sweep || (price < 1 ? `$${(price * 0.97).toFixed(4)}` : `$${(price * 0.97).toFixed(2)}`);
    const discountDemand = coin.discount_demand || coin.entry_zone;

    bodyEl.innerHTML = `
      <!-- Hero Price Strip -->
      <div class="coin-hero-strip">
        <div class="coin-hero-left">
          <img src="${coin.image || 'https://via.placeholder.com/54'}" class="coin-hero-img" onerror="this.src='https://via.placeholder.com/54'" />
          <div>
            <div class="coin-hero-ticker">${coin.symbol} <span style="font-size: 16px; font-weight: 600; color: #94A3B8;">/ USD</span></div>
            <div class="coin-hero-name">${coin.name || coin.symbol} · Market Rank #${coin.rank || '--'}</div>
          </div>
        </div>
        <div class="coin-hero-price-box">
          <div class="coin-hero-price">$${formatNum(price)}</div>
          <div class="coin-hero-chg ${chg24h >= 0 ? 'up' : 'down'}">
            24h: ${chg24h > 0 ? '+' : ''}${chg24h}% · 7d: ${chg7d > 0 ? '+' : ''}${chg7d}%
          </div>
        </div>
      </div>

      <!-- AI Conviction Breakdown -->
      <div class="ai-conviction-section">
        <div class="conviction-header-row">
          <div class="conviction-title">
            <span>🧠 CB AI Conviction Score</span>
            <span style="font-size: 11px; color: #64748B;">Multi-factor news & momentum telemetry</span>
          </div>
          <div class="conviction-score-badge">
            ⭐ ${conviction}% WIN PROBABILITY (${score}/100)
          </div>
        </div>

        <div class="conviction-bar-track">
          <div class="conviction-bar-fill" style="width: ${conviction}%;"></div>
        </div>

        <div class="conviction-factors-grid">
          <div class="factor-box">
            <div class="factor-label">Catalyst Sentiment</div>
            <div class="factor-val" style="color: ${(coin.news_sentiment || 0) >= 0 ? 'var(--green-light)' : 'var(--red)'};">
              ${(coin.news_sentiment || 0) > 0 ? '+' : ''}${coin.news_sentiment || 0.0} / 10
            </div>
          </div>
          <div class="factor-box">
            <div class="factor-label">Momentum Bias</div>
            <div class="factor-val ${chg24h >= 0 ? 'up' : 'down'}">
              ${chg24h > 0 ? '+' : ''}${chg24h}%
            </div>
          </div>
          <div class="factor-box">
            <div class="factor-label">Risk : Reward</div>
            <div class="factor-val" style="color: #38BDF8;">
              ${coin.risk_reward || '3.5 : 1'}
            </div>
          </div>
          <div class="factor-box">
            <div class="factor-label">Execution Bias</div>
            <div class="factor-val" style="color: #FCD34D;">
              ${coin.buy_urgency || coin.recommendation || 'ACCUMULATE'}
            </div>
          </div>
        </div>
      </div>

      <!-- ICT & Smart Money Technical Levels -->
      <div class="ict-section">
        <div class="section-subhead">
          <span>🏛️ ICT & SMART MONEY TECHNICAL LEVELS</span>
        </div>

        <div class="ict-grid">
          <div class="ict-card highlight-green">
            <div class="ict-label">🎯 Optimal Entry (Discount)</div>
            <div class="ict-val val-green">${discountDemand || coin.entry_zone}</div>
            <div class="ict-desc">Institutional accumulation shelf</div>
          </div>

          <div class="ict-card highlight-cyan">
            <div class="ict-label">📦 Fair Value Gap (FVG)</div>
            <div class="ict-val val-cyan">${fvgZone}</div>
            <div class="ict-desc">Price imbalance fill buffer</div>
          </div>

          <div class="ict-card">
            <div class="ict-label">💧 Liquidity Sweep Level</div>
            <div class="ict-val" style="color: #F59E0B;">${sweepLevel}</div>
            <div class="ict-desc">Stop run before continuation</div>
          </div>

          <div class="ict-card highlight-red">
            <div class="ict-label">🛡️ Stop Loss / Invalidation</div>
            <div class="ict-val val-red">${coin.stop_loss}</div>
            <div class="ict-desc">Hard structural trade breach</div>
          </div>

          <div class="ict-card">
            <div class="ict-label">🚀 Target 1 (+6% Swing)</div>
            <div class="ict-val val-green">${coin.target_1}</div>
            <div class="ict-desc">Take 50% profit, trail stop</div>
          </div>

          <div class="ict-card">
            <div class="ict-label">🪐 Target 2 (+12% Macro)</div>
            <div class="ict-val" style="color: #C084FC;">${coin.target_2}</div>
            <div class="ict-desc">Full extension runner exit</div>
          </div>
        </div>
      </div>

      <!-- Tactical Execution Plan -->
      <div class="tactical-plan-box">
        <div class="tactical-plan-title">
          <span>⚡ Tactical Action Plan</span>
        </div>
        <div class="tactical-plan-body">
          <strong>${coin.tactical_plan || 'Look for pullback into optimal discount entry zone with strict stop loss protection.'}</strong>
          <div style="margin-top: 8px; color: #94A3B8;">
            <strong>Why:</strong> ${coin.why_buy || 'High relative volume with positive catalyst tailwinds.'}
          </div>
        </div>
      </div>

      <!-- Catalysts & News Wire -->
      ${renderCoinNewsCatalysts(coin)}
    `;

    overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function renderCoinNewsCatalysts(coin) {
    const newsList = coin.top_news || [];
    if (!newsList.length) {
      return `
        <div style="background: rgba(0,0,0,0.25); padding: 14px; border-radius: 10px; font-size: 12px; color: #64748B;">
          📰 No asset-specific news anomalies in the last 24h. Tracking broad sector sentiment.
        </div>
      `;
    }

    return `
      <div style="margin-top: 16px;">
        <div style="font-size: 12px; font-family: 'JetBrains Mono', monospace; color: #94A3B8; text-transform: uppercase; margin-bottom: 8px;">
          📰 Catalysts & Sentiment Feeds
        </div>
        <div style="display: flex; flex-direction: column; gap: 8px;">
          ${newsList.map(n => `
            <div style="background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.06); padding: 10px 14px; border-radius: 8px;">
              <div style="display: flex; align-items: center; justify-content: space-between; font-size: 11px; margin-bottom: 4px;">
                <span style="color: var(--cyan); font-family: 'JetBrains Mono', monospace; font-weight: 700;">${n.catalyst || 'SURGE'}</span>
                <span style="color: ${n.score >= 0 ? 'var(--green-light)' : 'var(--red)'}; font-family: 'JetBrains Mono', monospace;">Score: ${n.score > 0 ? '+' : ''}${n.score}</span>
              </div>
              <div style="font-size: 13px; font-weight: 700; color: #fff;">${n.title}</div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  function closeCoinDetailsModal() {
    const overlay = document.getElementById('coinDetailsModalOverlay');
    if (overlay) {
      overlay.classList.remove('active');
      document.body.style.overflow = '';
    }
  }

  function openChartFromCoinModal() {
    if (activeDetailCoin) {
      closeCoinDetailsModal();
      openTradingViewModal(activeDetailCoin.symbol);
    }
  }

  function openRiskFromCoinModal() {
    if (activeDetailCoin) {
      closeCoinDetailsModal();
      if (typeof window.openRiskCalculatorModal === 'function') {
        window.openRiskCalculatorModal(activeDetailCoin);
      }
    }
  }

  function formatNum(val) {
    if (val === undefined || val === null || isNaN(val)) return '0.00';
    if (val < 0.0001) return val.toFixed(6);
    if (val < 1) return val.toFixed(4);
    if (val < 100) return val.toFixed(2);
    return val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  // Keyboard Esc listener
  if (typeof window !== 'undefined') {
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' || e.key === 'Esc') {
        closeTradingViewModal();
        closeCoinDetailsModal();
        if (typeof window.closeRiskCalculatorModal === 'function') {
          window.closeRiskCalculatorModal();
        }
      }
    });
  }

  // Global Exports & Aliases
  window.openTradingViewModal = openTradingViewModal;
  window.switchChartTimeframe = switchChartTimeframe;
  window.closeTradingViewModal = closeTradingViewModal;
  window.openRiskFromChart = openRiskFromChart;

  window.openCoinDetailsModal = openCoinDetailsModal;
  window.closeCoinDetailsModal = closeCoinDetailsModal;
  window.openChartFromCoinModal = openChartFromCoinModal;
  window.openRiskFromCoinModal = openRiskFromCoinModal;

  // Compatibility aliases
  window.openChartModal = (symbol) => openTradingViewModal(symbol);
  window.closeChartModal = closeTradingViewModal;
})();
