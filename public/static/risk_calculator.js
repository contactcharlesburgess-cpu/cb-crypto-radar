/**
 * CB Crypto AI Radar - Interactive Position Sizing & Risk Management Calculator
 * Institutional Capital Preservation Engine (1%–2% Rule, Real-time R:R Targets)
 */

(function () {
  const calcState = {
    accountEquity: 5000.00,
    riskMode: 'pct', // 'pct' or 'fixed'
    riskPct: 2.0,
    riskDollar: 100.00,
    entryPrice: 93.11,
    stopLossPrice: 89.50,
    selectedSymbol: 'HYPE'
  };

  function ensureRiskCalculatorDOM() {
    if (document.getElementById('riskCalcModalOverlay')) return;

    const modalHtml = `
      <div id="riskCalcModalOverlay" class="modal-overlay">
        <div class="modal-dialog modal-dialog-risk">
          <div class="modal-header">
            <div class="modal-title-group">
              <div class="modal-title-icon" style="background: linear-gradient(135deg, #06B6D4 0%, #10B981 100%);">🧮</div>
              <div>
                <div class="modal-title">
                  <span>POSITION & RISK SIZING CALCULATOR</span>
                  <span class="badge-signal sig-strong-buy" id="calcAssetBadge" style="font-size: 11px;">$HYPE</span>
                </div>
                <div class="modal-subtitle">INSTITUTIONAL 1%–2% RISK RULES · ASYMMETRIC R:R PROFIT TARGETS</div>
              </div>
            </div>
            <button class="modal-close-btn" onclick="window.closeRiskCalculatorModal()" title="Close (Esc)">✕</button>
          </div>

          <div class="modal-body">
            
            <!-- Quick Fill from Asset Bar -->
            <div class="quick-fill-bar">
              <span style="font-size: 12px; font-family: 'JetBrains Mono', monospace; color: #94A3B8;">⚡ Quick Fill Asset:</span>
              <select id="calcAssetSelector" class="quick-fill-select" onchange="window.onSelectQuickFillAsset(this.value)">
                <option value="HYPE">HYPE (Hyperliquid)</option>
                <option value="SOL">SOL (Solana)</option>
                <option value="BTC">BTC (Bitcoin)</option>
                <option value="ETH">ETH (Ethereum)</option>
                <option value="SUI">SUI (Sui)</option>
                <option value="DOGE">DOGE (Dogecoin)</option>
                <option value="PEPE">PEPE (Pepe)</option>
                <option value="NEAR">NEAR (Near Protocol)</option>
                <option value="AVAX">AVAX (Avalanche)</option>
                <option value="LINK">LINK (Chainlink)</option>
                <option value="RENDER">RENDER (Render)</option>
              </select>
              <span style="font-size: 11px; color: #64748B; margin-left: auto;">Auto-populates price & AI stop</span>
            </div>

            <div class="risk-grid">
              
              <!-- Left Column: Inputs -->
              <div class="risk-input-card">
                
                <!-- Account Equity -->
                <div class="calc-group">
                  <div class="calc-label">
                    <span>ACCOUNT PORTFOLIO EQUITY</span>
                    <span style="color: #64748B;">Total Capital</span>
                  </div>
                  <div class="calc-input-wrapper">
                    <span class="calc-input-prefix">$</span>
                    <input type="number" step="100" id="inputEquity" class="calc-input" value="5000" oninput="window.onCalcInputChange()" />
                  </div>
                </div>

                <!-- Risk Mode & Amount -->
                <div class="calc-group">
                  <div class="calc-label">
                    <span>MAX RISK PER TRADE</span>
                    <span id="labelRiskMode" style="color: var(--green-light); font-weight: 700;">2.0% ($100.00)</span>
                  </div>
                  
                  <div class="calc-input-wrapper">
                    <span class="calc-input-prefix">%</span>
                    <input type="number" step="0.5" id="inputRiskPct" class="calc-input" value="2.0" oninput="window.onCalcRiskPctChange()" />
                  </div>

                  <div class="risk-presets-row">
                    <span class="preset-chip" onclick="window.setRiskPreset(1.0)">1.0% ($50)</span>
                    <span class="preset-chip active" id="chip2pct" onclick="window.setRiskPreset(2.0)">2.0% ($100)</span>
                    <span class="preset-chip" onclick="window.setRiskPreset(3.0)">3.0% ($150)</span>
                    <span class="preset-chip" onclick="window.setRiskPreset(5.0)">5.0% ($250)</span>
                  </div>
                </div>

                <!-- Entry Price -->
                <div class="calc-group">
                  <div class="calc-label">
                    <span>ENTRY SPOT PRICE</span>
                    <span id="calcCurrentPriceHint" style="color: var(--cyan);">Live: $93.11</span>
                  </div>
                  <div class="calc-input-wrapper">
                    <span class="calc-input-prefix">$</span>
                    <input type="number" step="any" id="inputEntryPrice" class="calc-input" value="93.11" oninput="window.onCalcInputChange()" />
                  </div>
                </div>

                <!-- Stop Loss Price -->
                <div class="calc-group">
                  <div class="calc-label">
                    <span style="color: #F87171;">STOP LOSS (INVALIDATION)</span>
                    <span id="calcStopDistHint" style="color: #F87171;">-3.88% Distance</span>
                  </div>
                  <div class="calc-input-wrapper">
                    <span class="calc-input-prefix">$</span>
                    <input type="number" step="any" id="inputStopLoss" class="calc-input" value="89.50" oninput="window.onCalcInputChange()" />
                  </div>
                </div>

              </div>

              <!-- Right Column: Outputs & Target Ladder -->
              <div class="risk-output-card">
                
                <!-- Position Size Hero Box -->
                <div class="calc-stat-hero" id="calcHeroBox">
                  <div class="calc-hero-label">RECOMMENDED POSITION SIZE</div>
                  <div class="calc-hero-val" id="resPositionDollars">$2,579.22</div>
                  <div class="calc-hero-sub" id="resTokenQty">27.700 HYPE Tokens · 51.6% Allocation</div>
                </div>

                <!-- Dynamic Risk Warning / Alert -->
                <div id="calcWarningBox" style="display: none;"></div>

                <!-- Key Metrics List -->
                <div class="calc-results-list">
                  <div class="calc-result-row">
                    <span class="calc-res-label">Max Dollar Loss at Stop:</span>
                    <span class="calc-res-val" style="color: var(--red);" id="resMaxDollarLoss">-$100.00 (-2.00%)</span>
                  </div>
                  <div class="calc-result-row">
                    <span class="calc-res-label">Per-Token Risk Amount:</span>
                    <span class="calc-res-val" id="resPerTokenRisk">$3.61</span>
                  </div>
                  <div class="calc-result-row">
                    <span class="calc-res-label">Portfolio Exposure %:</span>
                    <span class="calc-res-val" id="resPortfolioPct">51.6%</span>
                  </div>
                </div>

                <!-- Profit Target Ladder (1:2, 1:3, 1:5) -->
                <div class="target-ladder">
                  <div class="ladder-header">🎯 ASYMMETRIC R:R PROFIT TARGETS</div>
                  <div class="ladder-row">
                    <span style="color: #94A3B8;">Target 1 (1:2 R:R):</span>
                    <strong style="color: var(--green-light);" id="ladderT1">$100.33</strong>
                    <span style="color: var(--green-light);" id="ladderT1Profit">+$200.00 (+7.7%)</span>
                  </div>
                  <div class="ladder-row">
                    <span style="color: #94A3B8;">Target 2 (1:3 R:R):</span>
                    <strong style="color: var(--cyan);" id="ladderT2">$103.94</strong>
                    <span style="color: var(--cyan);" id="ladderT2Profit">+$300.00 (+11.6%)</span>
                  </div>
                  <div class="ladder-row">
                    <span style="color: #94A3B8;">Target 3 (1:5 R:R):</span>
                    <strong style="color: #C084FC;" id="ladderT3">$111.16</strong>
                    <span style="color: #C084FC;" id="ladderT3Profit">+$500.00 (+19.4%)</span>
                  </div>
                </div>

              </div>

            </div>

          </div>

          <div class="modal-actions-bar">
            <div class="modal-actions-left">
              <button class="btn" onclick="window.copyTradePlanToClipboard()">
                📋 Copy Trade Plan
              </button>
              <button class="btn" onclick="window.openChartFromCalculator()">
                📊 View Chart
              </button>
            </div>
            <div id="calcTradeExecBtn">
              <!-- Execution Button -->
            </div>
          </div>
        </div>
      </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHtml);
    populateAssetDropdown();

    document.getElementById('riskCalcModalOverlay').addEventListener('click', (e) => {
      if (e.target.id === 'riskCalcModalOverlay') {
        window.closeRiskCalculatorModal();
      }
    });
  }

  function populateAssetDropdown() {
    const select = document.getElementById('calcAssetSelector');
    if (!select || !window.appData || !window.appData.asset_signals) return;

    const assets = window.appData.asset_signals;
    select.innerHTML = assets.map(c => `
      <option value="${c.symbol}" ${c.symbol === calcState.selectedSymbol ? 'selected' : ''}>
        ${c.symbol} - $${c.price < 1 ? c.price.toFixed(4) : c.price.toFixed(2)} (${c.signal})
      </option>
    `).join('');
  }

  function openRiskCalculatorModal(coinData = null) {
    ensureRiskCalculatorDOM();
    populateAssetDropdown();

    if (coinData) {
      let coin = coinData;
      if (typeof coinData === 'string') {
        const sym = coinData.toUpperCase().trim().replace('$', '');
        if (window.appData && window.appData.asset_signals) {
          coin = window.appData.asset_signals.find(c => c.symbol.toUpperCase() === sym) || { symbol: sym };
        } else {
          coin = { symbol: sym };
        }
      }

      calcState.selectedSymbol = coin.symbol || 'HYPE';
      if (coin.price) calcState.entryPrice = parseFloat(coin.price);
      if (coin.stop_loss_val) {
        calcState.stopLossPrice = parseFloat(coin.stop_loss_val);
      } else if (coin.stop_loss) {
        const parsed = parseFloat(coin.stop_loss.replace(/[^0-9.]/g, ''));
        if (!isNaN(parsed) && parsed > 0) calcState.stopLossPrice = parsed;
      } else if (calcState.entryPrice > 0) {
        calcState.stopLossPrice = parseFloat((calcState.entryPrice * 0.965).toFixed(4));
      }

      const select = document.getElementById('calcAssetSelector');
      if (select) select.value = calcState.selectedSymbol;

      const entryInput = document.getElementById('inputEntryPrice');
      if (entryInput) entryInput.value = calcState.entryPrice;

      const stopInput = document.getElementById('inputStopLoss');
      if (stopInput) stopInput.value = calcState.stopLossPrice;
    }

    const badge = document.getElementById('calcAssetBadge');
    if (badge) badge.textContent = `$${calcState.selectedSymbol}`;

    updateCalculatorExecButton(calcState.selectedSymbol);
    calculateRisk();

    const overlay = document.getElementById('riskCalcModalOverlay');
    overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function updateCalculatorExecButton(symbol) {
    const container = document.getElementById('calcTradeExecBtn');
    if (!container) return;

    if (symbol === 'HYPE') {
      container.innerHTML = `
        <a href="https://app.hyperliquid.xyz/trade/HYPE" target="_blank" class="btn btn-exec-hl">
          ⚡ Trade HYPE on Hyperliquid
        </a>
      `;
    } else {
      container.innerHTML = `
        <a href="https://robinhood.com/crypto/${symbol}" target="_blank" class="btn btn-exec-rh">
          🟢 Trade ${symbol} on Robinhood
        </a>
      `;
    }
  }

  function closeRiskCalculatorModal() {
    const overlay = document.getElementById('riskCalcModalOverlay');
    if (overlay) {
      overlay.classList.remove('active');
      document.body.style.overflow = '';
    }
  }

  function setRiskPreset(pct) {
    calcState.riskPct = pct;
    const input = document.getElementById('inputRiskPct');
    if (input) input.value = pct;

    document.querySelectorAll('.preset-chip').forEach(c => {
      c.classList.toggle('active', c.textContent.includes(`${pct}%`));
    });

    calculateRisk();
  }

  function onCalcRiskPctChange() {
    const val = parseFloat(document.getElementById('inputRiskPct').value) || 2.0;
    calcState.riskPct = Math.max(0.1, Math.min(25.0, val));
    document.querySelectorAll('.preset-chip').forEach(c => c.classList.remove('active'));
    calculateRisk();
  }

  function onCalcInputChange() {
    const eq = parseFloat(document.getElementById('inputEquity').value) || 5000.0;
    const entry = parseFloat(document.getElementById('inputEntryPrice').value) || 0;
    const stop = parseFloat(document.getElementById('inputStopLoss').value) || 0;

    calcState.accountEquity = Math.max(10, eq);
    calcState.entryPrice = entry;
    calcState.stopLossPrice = stop;

    calculateRisk();
  }

  function onSelectQuickFillAsset(symbol) {
    calcState.selectedSymbol = symbol;
    let coin = null;

    if (window.appData && window.appData.asset_signals) {
      coin = window.appData.asset_signals.find(c => c.symbol.toUpperCase() === symbol.toUpperCase());
    }

    if (coin) {
      calcState.entryPrice = parseFloat(coin.price);
      if (coin.stop_loss_val) {
        calcState.stopLossPrice = parseFloat(coin.stop_loss_val);
      } else {
        calcState.stopLossPrice = parseFloat((calcState.entryPrice * 0.965).toFixed(4));
      }
    } else if (symbol === 'HYPE') {
      calcState.entryPrice = 93.11;
      calcState.stopLossPrice = 89.50;
    } else if (symbol === 'SOL') {
      calcState.entryPrice = 114.40;
      calcState.stopLossPrice = 108.50;
    }

    const entryInput = document.getElementById('inputEntryPrice');
    const stopInput = document.getElementById('inputStopLoss');
    const badge = document.getElementById('calcAssetBadge');

    if (entryInput) entryInput.value = calcState.entryPrice;
    if (stopInput) stopInput.value = calcState.stopLossPrice;
    if (badge) badge.textContent = `$${symbol}`;
    
    updateCalculatorExecButton(symbol);
    calculateRisk();
  }

  function calculateRisk() {
    const equity = calcState.accountEquity;
    const riskPct = calcState.riskPct;
    const entry = calcState.entryPrice;
    const stop = calcState.stopLossPrice;
    const symbol = calcState.selectedSymbol || 'ASSET';

    const dollarRisk = equity * (riskPct / 100);
    calcState.riskDollar = dollarRisk;

    const riskLabel = document.getElementById('labelRiskMode');
    if (riskLabel) {
      riskLabel.textContent = `${riskPct.toFixed(1)}% ($${dollarRisk.toFixed(2)})`;
    }

    const hintPrice = document.getElementById('calcCurrentPriceHint');
    if (hintPrice) hintPrice.textContent = `Entry: $${entry.toFixed(entry < 1 ? 4 : 2)}`;

    const warnBox = document.getElementById('calcWarningBox');
    const heroBox = document.getElementById('calcHeroBox');
    const posDollarsEl = document.getElementById('resPositionDollars');
    const tokenQtyEl = document.getElementById('resTokenQty');
    const maxLossEl = document.getElementById('resMaxDollarLoss');
    const perTokenRiskEl = document.getElementById('resPerTokenRisk');
    const portPctEl = document.getElementById('resPortfolioPct');

    const t1El = document.getElementById('ladderT1');
    const t1ProfitEl = document.getElementById('ladderT1Profit');
    const t2El = document.getElementById('ladderT2');
    const t2ProfitEl = document.getElementById('ladderT2Profit');
    const t3El = document.getElementById('ladderT3');
    const t3ProfitEl = document.getElementById('ladderT3Profit');

    if (!posDollarsEl) return;

    if (entry <= 0) {
      posDollarsEl.textContent = '$0.00';
      tokenQtyEl.textContent = 'Enter a valid entry price.';
      return;
    }

    if (stop >= entry) {
      warnBox.style.display = 'flex';
      warnBox.className = 'calc-alert calc-alert-danger';
      warnBox.innerHTML = `⚠️ <strong>Invalid Stop Loss:</strong> Stop price ($${stop}) must be below Entry price ($${entry}) for Long positions.`;
      heroBox.style.borderColor = '#EF4444';
      posDollarsEl.textContent = 'Invalid Setup';
      tokenQtyEl.textContent = 'Stop loss is above or equal to entry.';
      return;
    }

    const stopDist = entry - stop;
    const stopDistPct = (stopDist / entry) * 100;

    const stopHint = document.getElementById('calcStopDistHint');
    if (stopHint) {
      stopHint.textContent = `-${stopDistPct.toFixed(2)}% Distance ($${stopDist.toFixed(entry < 1 ? 4 : 2)})`;
    }

    const tokenQty = dollarRisk / stopDist;
    const positionDollars = tokenQty * entry;
    const allocationPct = (positionDollars / equity) * 100;

    posDollarsEl.textContent = `$${positionDollars.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    tokenQtyEl.textContent = `${tokenQty < 10 ? tokenQty.toFixed(4) : tokenQty.toFixed(2)} ${symbol} Tokens · ${allocationPct.toFixed(1)}% of Portfolio`;

    maxLossEl.textContent = `-$${dollarRisk.toFixed(2)} (-${riskPct.toFixed(1)}%)`;
    perTokenRiskEl.textContent = `$${stopDist.toFixed(entry < 1 ? 4 : 2)}`;
    portPctEl.textContent = `${allocationPct.toFixed(1)}% (${allocationPct > 100 ? 'Leverage' : 'Spot'})`;

    const t1Price = entry + (2 * stopDist);
    const t1Profit = 2 * dollarRisk;
    const t1Pct = (2 * stopDistPct);

    const t2Price = entry + (3 * stopDist);
    const t2Profit = 3 * dollarRisk;
    const t2Pct = (3 * stopDistPct);

    const t3Price = entry + (5 * stopDist);
    const t3Profit = 5 * dollarRisk;
    const t3Pct = (5 * stopDistPct);

    const dec = entry < 1 ? 4 : 2;
    if (t1El) t1El.textContent = `$${t1Price.toFixed(dec)}`;
    if (t1ProfitEl) t1ProfitEl.textContent = `+$${t1Profit.toFixed(2)} (+${t1Pct.toFixed(1)}%)`;

    if (t2El) t2El.textContent = `$${t2Price.toFixed(dec)}`;
    if (t2ProfitEl) t2ProfitEl.textContent = `+$${t2Profit.toFixed(2)} (+${t2Pct.toFixed(1)}%)`;

    if (t3El) t3El.textContent = `$${t3Price.toFixed(dec)}`;
    if (t3ProfitEl) t3ProfitEl.textContent = `+$${t3Profit.toFixed(2)} (+${t3Pct.toFixed(1)}%)`;

    if (positionDollars > equity) {
      const lev = (positionDollars / equity).toFixed(1);
      warnBox.style.display = 'flex';
      warnBox.className = 'calc-alert calc-alert-warn';
      warnBox.innerHTML = `⚠️ <strong>Capital Warning:</strong> Position size ($${positionDollars.toFixed(0)}) exceeds account equity ($${equity.toFixed(0)}). Requires <strong>${lev}x leverage</strong> or widening stop distance.`;
      heroBox.style.borderColor = '#F59E0B';
    } else if (riskPct > 5.0) {
      warnBox.style.display = 'flex';
      warnBox.className = 'calc-alert calc-alert-danger';
      warnBox.innerHTML = `⚠️ <strong>High Risk Warning:</strong> Risking ${riskPct.toFixed(1)}% on a single trade violates institutional 1%–2% risk rules.`;
      heroBox.style.borderColor = '#EF4444';
    } else {
      warnBox.style.display = 'none';
      heroBox.style.borderColor = 'rgba(16, 185, 129, 0.35)';
    }
  }

  function copyTradePlanToClipboard() {
    const symbol = calcState.selectedSymbol;
    const equity = calcState.accountEquity;
    const riskPct = calcState.riskPct;
    const dollarRisk = calcState.riskDollar;
    const entry = calcState.entryPrice;
    const stop = calcState.stopLossPrice;
    const stopDist = entry - stop;
    const tokenQty = dollarRisk / stopDist;
    const posDollars = tokenQty * entry;
    const t1 = entry + (2 * stopDist);
    const t2 = entry + (3 * stopDist);
    const t3 = entry + (5 * stopDist);
    const dec = entry < 1 ? 4 : 2;

    const planText = `
🎯 CB CRYPTO AI RADAR · EXECUTION PLAN
---------------------------------------
Asset: ${symbol} / USD
Account Equity: $${equity.toLocaleString()}
Max Risk: $${dollarRisk.toFixed(2)} (${riskPct.toFixed(1)}%)

Entry Price: $${entry.toFixed(dec)}
Stop Loss: $${stop.toFixed(dec)} (-${((stopDist/entry)*100).toFixed(2)}%)
Tokens to Buy: ${tokenQty.toFixed(tokenQty < 10 ? 4 : 2)} ${symbol}
Total Position Size: $${posDollars.toFixed(2)} (${((posDollars/equity)*100).toFixed(1)}% of Portfolio)

Asymmetric Profit Targets:
• Target 1 (1:2 R:R): $${t1.toFixed(dec)} (+$${(dollarRisk * 2).toFixed(2)})
• Target 2 (1:3 R:R): $${t2.toFixed(dec)} (+$${(dollarRisk * 3).toFixed(2)})
• Target 3 (1:5 R:R): $${t3.toFixed(dec)} (+$${(dollarRisk * 5).toFixed(2)})
---------------------------------------
Generated via CB Crypto AI Radar on ${new Date().toLocaleTimeString()}
`.trim();

    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(planText).then(() => {
        if (typeof window.showToast === 'function') {
          window.showToast(`📋 ${symbol} Trade Plan copied to clipboard!`);
        } else {
          alert(`${symbol} Trade Plan copied!`);
        }
      }).catch(err => {
        console.error("Clipboard copy error:", err);
      });
    } else {
      alert(`${symbol} Trade Plan copied!`);
    }
  }

  function openChartFromCalculator() {
    closeRiskCalculatorModal();
    if (typeof window.openTradingViewModal === 'function') {
      window.openTradingViewModal(calcState.selectedSymbol);
    }
  }

  // Global Exports
  window.openRiskCalculatorModal = openRiskCalculatorModal;
  window.closeRiskCalculatorModal = closeRiskCalculatorModal;
  window.calculateRisk = calculateRisk;
  window.setRiskPreset = setRiskPreset;
  window.onCalcRiskPctChange = onCalcRiskPctChange;
  window.onCalcInputChange = onCalcInputChange;
  window.onSelectQuickFillAsset = onSelectQuickFillAsset;
  window.copyTradePlanToClipboard = copyTradePlanToClipboard;
  window.openChartFromCalculator = openChartFromCalculator;

  // Compatibility aliases
  window.loadSymbolIntoRiskCalc = (symbol) => openRiskCalculatorModal(symbol);
  window.initRiskCalculator = () => ensureRiskCalculatorDOM();
})();
