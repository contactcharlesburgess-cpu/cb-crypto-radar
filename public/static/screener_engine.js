/**
 * CB Crypto AI Radar — Screener Engine, News Wire & Obsidian Sync Client
 * 
 * Features:
 * 1. Full Column Sorting Engine:
 *    - Columns: Rank, Symbol, Price, 24h %, 7d %, AI Conviction Score, Buy Zone, R:R
 *    - Toggling header switches between ascending/descending with arrow indicators (▲ / ▼).
 * 2. Quick Filter Pills:
 *    - 'MY_HOLDINGS': Filters to HYPE, SOL, META (with full position telemetry).
 *    - 'ALL': All 32 monitored assets.
 *    - 'BUY_ONLY': Signals 'STRONG BUY', 'DIP ENTRY', 'ACTIVE HOLD'.
 *    - 'AI & Compute', 'Mega Caps', 'Layer 1 / 2', 'DeFi', 'Memes', 'Payments & PoW'.
 *    - 'EXIT_ONLY': 'DEFENSIVE EXIT', 'TIGHTEN STOPS'.
 * 3. Search Bar:
 *    - Instant fuzzy search on symbol, name, or sector with clear button (✕) and '/' keyboard shortcut.
 * 4. Relative Time Formatter:
 *    - Real-time relative timing for news & squawks ("Just now", "3m ago", "1h ago", etc.) with exact time tooltips.
 * 5. Obsidian 1-Click Sync Handler:
 *    - POST to /api/sync.
 *    - Visual Toast: "⚡ Obsidian Vault Synced: Crypto Intelligence.md & Activity Log.md".
 *    - High-fidelity Web Audio confirmation chime.
 */

(function (window) {
  'use strict';

  // State
  let currentSort = {
    column: 'score',     // Default sort by AI Conviction Score
    direction: 'desc'    // Default descending
  };

  let currentFilter = 'ALL';
  let searchQuery = '';
  let audioContext = null;

  // Web Audio Synthesizer: Confirmation Chime
  function getAudioContext() {
    if (!audioContext) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) {
        audioContext = new AudioCtx();
      }
    }
    if (audioContext && audioContext.state === 'suspended') {
      audioContext.resume();
    }
    return audioContext;
  }

  function playConfirmationChime() {
    try {
      const ctx = getAudioContext();
      if (!ctx) return;

      const now = ctx.currentTime;
      // High-tech ascending arpeggio chord (E5: 659.25Hz -> G#5: 830.61Hz -> B5: 987.77Hz)
      const osc1 = ctx.createOscillator();
      const osc2 = ctx.createOscillator();
      const gainNode = ctx.createGain();

      osc1.type = 'sine';
      osc2.type = 'triangle';

      osc1.frequency.setValueAtTime(659.25, now);
      osc1.frequency.exponentialRampToValueAtTime(987.77, now + 0.12);

      osc2.frequency.setValueAtTime(523.25, now);
      osc2.frequency.exponentialRampToValueAtTime(1318.51, now + 0.18);

      gainNode.gain.setValueAtTime(0.001, now);
      gainNode.gain.linearRampToValueAtTime(0.28, now + 0.03);
      gainNode.gain.exponentialRampToValueAtTime(0.001, now + 0.45);

      osc1.connect(gainNode);
      osc2.connect(gainNode);
      gainNode.connect(ctx.destination);

      osc1.start(now);
      osc2.start(now + 0.03);
      osc1.stop(now + 0.45);
      osc2.stop(now + 0.45);
    } catch (err) {
      console.warn('Audio chime playback failed:', err);
    }
  }

  // Relative Time Formatter
  function formatRelativeTime(dateInput) {
    if (!dateInput) return '--';

    let dateObj;
    if (dateInput instanceof Date) {
      dateObj = dateInput;
    } else if (typeof dateInput === 'number') {
      dateObj = new Date(dateInput);
    } else if (typeof dateInput === 'string') {
      dateObj = new Date(dateInput);
    }

    if (!dateObj || isNaN(dateObj.getTime())) {
      return String(dateInput);
    }

    const now = Date.now();
    const elapsedSec = Math.floor((now - dateObj.getTime()) / 1000);

    if (elapsedSec < 45) {
      return 'Just now';
    }
    if (elapsedSec < 90) {
      return '1m ago';
    }
    if (elapsedSec < 3600) {
      const mins = Math.floor(elapsedSec / 60);
      return `${mins}m ago`;
    }
    if (elapsedSec < 7200) {
      return '1h ago';
    }
    if (elapsedSec < 86400) {
      const hours = Math.floor(elapsedSec / 3600);
      return `${hours}h ago`;
    }
    if (elapsedSec < 172800) {
      return '1d ago';
    }
    const days = Math.floor(elapsedSec / 86400);
    return `${days}d ago`;
  }

  // Visual Toast
  function showToast(text, isError = false) {
    let t = document.getElementById('toast');
    if (!t) {
      t = document.createElement('div');
      t.id = 'toast';
      document.body.appendChild(t);
    }
    t.textContent = text;
    t.style.display = 'block';
    t.style.borderColor = isError ? 'var(--red)' : 'var(--green)';
    t.style.color = isError ? '#FCA5A5' : '#FFFFFF';

    if (t._timeout) clearTimeout(t._timeout);
    t._timeout = setTimeout(() => {
      t.style.display = 'none';
    }, 3800);
  }

  // Format Number Utility
  function formatNum(n) {
    if (n === null || n === undefined || isNaN(n)) return '0.00';
    const num = Number(n);
    if (num < 0.0001 && num > 0) return num.toExponential(3);
    if (num < 1) return num.toFixed(4);
    if (num < 100) return num.toFixed(2);
    return num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  // Synthesize Charles Meta Platforms Holding if not present in crypto table
  function getMetaPositionItem(portfolio) {
    const metaP = portfolio?.meta || {};
    const price = metaP.price || 770.85;
    const entry = metaP.entry || 769.31;

    return {
      id: 'meta-platforms',
      symbol: 'META',
      name: 'Meta Platforms',
      sector: 'Mega Caps · Equity (Robinhood)',
      price: price,
      change_24h: 1.15,
      change_7d: 3.42,
      score: 95.0,
      conviction: 98,
      signal: 'ACTIVE HOLD',
      badge_class: 'badge-buy',
      entry_zone: '$769.31 (Filled)',
      entry_low: 769.31,
      entry_high: 770.85,
      stop_loss: 'Long-Term (None)',
      stop_loss_val: 0,
      target_1: '$850.00',
      target_1_val: 850.00,
      target_2: '$1,000.00',
      target_2_val: 1000.00,
      risk_reward: 'Compound',
      rr_ratio: 5.0,
      rank: 0,
      image: 'https://companiesmarketcap.com/img/company-logos/64/META.png',
      tactical_plan: 'Permanent long-term compounding. Filled at $769.31. Zero stop loss.',
      why_buy: '3.2B users, open-source AI moat (Llama), immense free cash flow & massive buybacks.'
    };
  }

  // Filtering Engine
  function filterAssets(assets, portfolio) {
    const search = (searchQuery || '').trim().toLowerCase();
    const myHoldingsSymbols = ['HYPE', 'SOL', 'META'];

    // If MY_HOLDINGS filter or search includes META, include META item
    let baseList = [...assets];
    const hasMeta = baseList.some(a => a.symbol === 'META');
    if (!hasMeta && (currentFilter === 'MY_HOLDINGS' || search.includes('meta'))) {
      baseList.unshift(getMetaPositionItem(portfolio));
    }

    return baseList.filter(a => {
      const sym = (a.symbol || '').toLowerCase();
      const nm = (a.name || '').toLowerCase();
      const sec = (a.sector || '').toLowerCase();

      // Search matching (fuzzy/substring across symbol, name, and sector)
      if (search) {
        const matches = sym.includes(search) || nm.includes(search) || sec.includes(search);
        if (!matches) return false;
      }

      // Quick Filter Pills
      if (currentFilter === 'ALL') {
        return true;
      }
      if (currentFilter === 'MY_HOLDINGS') {
        return myHoldingsSymbols.includes(a.symbol.toUpperCase());
      }
      if (currentFilter === 'BUY_ONLY') {
        return a.signal === 'STRONG BUY' || a.signal === 'DIP ENTRY' || a.signal === 'ACTIVE HOLD';
      }
      if (currentFilter === 'EXIT_ONLY') {
        return a.signal === 'DEFENSIVE EXIT' || a.signal === 'TIGHTEN STOPS';
      }
      if (currentFilter === 'AI & Compute') {
        return a.sector === 'AI & Compute';
      }
      if (currentFilter === 'Mega Caps') {
        return a.sector === 'Mega Caps' || a.sector.startsWith('Mega Caps');
      }
      if (currentFilter === 'Layer 1 / 2') {
        return a.sector === 'Layer 1 / 2';
      }
      if (currentFilter === 'DeFi') {
        return a.sector === 'DeFi';
      }
      if (currentFilter === 'Memes') {
        return a.sector === 'Memes';
      }
      if (currentFilter === 'Payments & PoW' || currentFilter === 'Payments & Pow') {
        const norm = (a.sector || '').toLowerCase();
        return norm === 'payments & pow';
      }

      return a.sector === currentFilter;
    });
  }

  // Sorting Engine
  function sortAssets(assets) {
    const { column, direction } = currentSort;
    const factor = direction === 'asc' ? 1 : -1;

    return assets.slice().sort((a, b) => {
      let valA, valB;

      switch (column) {
        case 'rank':
          valA = typeof a.rank === 'number' ? a.rank : 999;
          valB = typeof b.rank === 'number' ? b.rank : 999;
          return (valA - valB) * factor;

        case 'symbol':
          valA = (a.symbol || '').toUpperCase();
          valB = (b.symbol || '').toUpperCase();
          return valA.localeCompare(valB) * factor;

        case 'price':
          valA = Number(a.price) || 0;
          valB = Number(b.price) || 0;
          return (valA - valB) * factor;

        case 'change_24h':
          valA = Number(a.change_24h) || 0;
          valB = Number(b.change_24h) || 0;
          return (valA - valB) * factor;

        case 'change_7d':
          valA = Number(a.change_7d) || 0;
          valB = Number(b.change_7d) || 0;
          return (valA - valB) * factor;

        case 'conviction':
        case 'score':
          valA = Number(a.conviction || a.score) || 0;
          valB = Number(b.conviction || b.score) || 0;
          return (valA - valB) * factor;

        case 'entry_low':
        case 'entry_zone':
        case 'buy_zone':
          valA = Number(a.entry_low || a.price) || 0;
          valB = Number(b.entry_low || b.price) || 0;
          return (valA - valB) * factor;

        case 'risk_reward':
        case 'rr_ratio':
          valA = Number(a.rr_ratio) || 0;
          valB = Number(b.rr_ratio) || 0;
          return (valA - valB) * factor;

        case 'signal':
          valA = (a.signal || '').toUpperCase();
          valB = (b.signal || '').toUpperCase();
          return valA.localeCompare(valB) * factor;

        default:
          return 0;
      }
    });
  }

  // Header Sort Toggle
  function handleHeaderSort(column) {
    if (currentSort.column === column) {
      currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
    } else {
      currentSort.column = column;
      if (column === 'rank' || column === 'symbol') {
        currentSort.direction = 'asc';
      } else {
        currentSort.direction = 'desc';
      }
    }
    updateHeaderSortIndicators();
    renderTable();
  }

  // Update Table Header Sort Indicators (▲ / ▼ / ⇅)
  function updateHeaderSortIndicators() {
    const thElements = document.querySelectorAll('th[data-sort]');
    thElements.forEach(th => {
      const col = th.getAttribute('data-sort');
      let iconSpan = th.querySelector('.sort-icon');
      if (!iconSpan) {
        iconSpan = document.createElement('span');
        iconSpan.className = 'sort-icon';
        th.appendChild(iconSpan);
      }

      if (col === currentSort.column || 
         (col === 'score' && currentSort.column === 'conviction') ||
         (col === 'conviction' && currentSort.column === 'score')) {
        th.classList.add('sort-active');
        iconSpan.textContent = currentSort.direction === 'asc' ? ' ▲' : ' ▼';
        iconSpan.style.color = 'var(--green-light)';
        iconSpan.style.opacity = '1';
      } else {
        th.classList.remove('sort-active');
        iconSpan.textContent = ' ⇅';
        iconSpan.style.color = 'var(--text-dim)';
        iconSpan.style.opacity = '0.4';
      }
    });
  }

  // Render Screener Table
  function renderTable() {
    const tbody = document.getElementById('screenerBody');
    if (!tbody) return;

    const data = window.appData || {};
    const rawAssets = data.asset_signals || [];
    const portfolio = data.portfolio || {};

    const filtered = filterAssets(rawAssets, portfolio);
    const sorted = sortAssets(filtered);

    if (!sorted.length) {
      tbody.innerHTML = `
        <tr>
          <td colspan="12" style="text-align: center; padding: 48px; color: var(--text-dim);">
            <div style="font-size: 24px; margin-bottom: 8px;">🔍</div>
            <div style="font-size: 15px; font-weight: 700; color: #fff;">No matching assets found</div>
            <div style="font-size: 13px; margin-top: 4px;">Try clearing your search query or selecting 'All Tradable (32)'</div>
            <button class="btn" onclick="window.clearSearch(); window.setEngineFilter('ALL');" style="margin-top: 16px; padding: 8px 16px; font-size: 12px;">Reset Filters</button>
          </td>
        </tr>`;
      return;
    }

    tbody.innerHTML = sorted.map((c, idx) => {
      let badgeStyle = 'sig-hold';
      if (c.signal === 'STRONG BUY') badgeStyle = 'sig-strong-buy';
      else if (c.signal === 'DIP ENTRY') badgeStyle = 'sig-dip';
      else if (c.signal === 'ACTIVE HOLD') badgeStyle = 'sig-strong-buy';
      else if (c.signal === 'TIGHTEN STOPS') badgeStyle = 'sig-warning';
      else if (c.signal === 'DEFENSIVE EXIT') badgeStyle = 'sig-exit';

      const isMyHolding = ['HYPE', 'SOL', 'META'].includes(c.symbol.toUpperCase());
      const holdingBadge = isMyHolding
        ? `<span style="background: rgba(245, 158, 11, 0.15); border: 1px solid #F59E0B; color: #FCD34D; font-size: 10px; font-weight: 800; padding: 2px 6px; border-radius: 4px; margin-left: 6px;">PORTFOLIO</span>`
        : '';

      const rankDisplay = c.rank === 0 || c.rank === '⭐ Core' ? '⭐' : (c.rank || idx + 1);
      const chg24 = parseFloat(c.change_24h) || 0;
      const chg7 = parseFloat(c.change_7d) || 0;

      return `
        <tr class="tr-clickable ${isMyHolding ? 'row-holding' : ''}" onclick="window.openChartModal ? window.openChartModal('${c.symbol}', '${c.name}', '${formatNum(c.price)}', ${chg24}, '${c.entry_zone}', '${c.stop_loss}', '${c.target_1}', '${c.risk_reward}') : null" title="Click for Live Interactive TradingView Chart & ICT Levels">
          <td style="color: var(--text-dim); font-family: var(--font-mono); font-weight: 700;">${rankDisplay}</td>
          <td>
            <div class="symbol-flex">
              <img src="${c.image}" class="coin-img-sm" onerror="this.src='https://via.placeholder.com/32'" />
              <div>
                <div class="coin-bold">${c.symbol} ${holdingBadge}</div>
                <div class="coin-dim">${c.name} · ${c.sector}</div>
              </div>
            </div>
          </td>
          <td class="font-mono" style="font-weight: 700; color: #fff;">$${formatNum(c.price)}</td>
          <td class="font-mono ${chg24 >= 0 ? 'val-green' : 'val-red'}" style="font-weight: 700;">${chg24 > 0 ? '+' : ''}${chg24.toFixed(2)}%</td>
          <td class="font-mono ${chg7 >= 0 ? 'val-green' : 'val-red'}" style="font-weight: 700;">${chg7 > 0 ? '+' : ''}${chg7.toFixed(2)}%</td>
          <td><span class="badge-signal ${badgeStyle}">${c.signal}</span></td>
          <td>
            <div style="display: flex; align-items: center; gap: 6px;">
              <span class="font-mono" style="font-weight: 800; color: ${c.score >= 70 ? 'var(--green-light)' : (c.score >= 50 ? 'var(--cyan)' : 'var(--amber)')};">${c.conviction || Math.round(c.score)}%</span>
              <span style="font-size: 11px; color: var(--text-dim);">(${c.score})</span>
            </div>
          </td>
          <td class="font-mono val-green" style="font-weight: 600;">${c.entry_zone || '--'}</td>
          <td class="font-mono val-cyan" style="font-weight: 600;">${c.target_1 || '--'}</td>
          <td class="font-mono val-red" style="font-weight: 600;">${c.stop_loss || '--'}</td>
          <td class="font-mono" style="font-weight: 600;">${c.risk_reward || (c.rr_ratio ? c.rr_ratio + ' : 1' : '--')}</td>
          <td>
            <div style="display: flex; gap: 4px; align-items: center;" onclick="event.stopPropagation()">
              <button class="btn btn-xs" onclick="window.loadSymbolIntoRiskCalc ? window.loadSymbolIntoRiskCalc('${c.symbol}') : null" title="Size 1%-2% Risk Setup">🧮</button>
              <button class="btn btn-xs btn-cta" onclick="window.openChartModal ? window.openChartModal('${c.symbol}', '${c.name}', '${formatNum(c.price)}', ${chg24}, '${c.entry_zone}', '${c.stop_loss}', '${c.target_1}', '${c.risk_reward}') : null" title="Open Live Chart">📈</button>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  }

  // Quick Filter Pill Selection
  function setFilter(filter, el) {
    currentFilter = filter;
    document.querySelectorAll('.pill-btn').forEach(p => {
      const pFilter = p.getAttribute('data-filter') || p.textContent.trim();
      if (p.getAttribute('data-filter') === filter || pFilter === filter || p === el) {
        p.classList.add('active');
      } else {
        p.classList.remove('active');
      }
    });
    renderTable();
  }

  // Search Input Handler
  function handleSearchInput(val) {
    if (typeof val === 'string') {
      searchQuery = val;
    } else {
      const input = document.getElementById('searchInput');
      searchQuery = input ? input.value : '';
    }

    const clearBtn = document.getElementById('clearSearchBtn');
    const kbdHint = document.getElementById('searchKbdHint');
    if (clearBtn) {
      clearBtn.style.display = searchQuery ? 'flex' : 'none';
    }
    if (kbdHint) {
      kbdHint.style.display = searchQuery ? 'none' : 'block';
    }

    renderTable();
  }

  // Clear Search
  function clearSearch() {
    const input = document.getElementById('searchInput');
    if (input) {
      input.value = '';
      input.focus();
    }
    searchQuery = '';
    const clearBtn = document.getElementById('clearSearchBtn');
    const kbdHint = document.getElementById('searchKbdHint');
    if (clearBtn) clearBtn.style.display = 'none';
    if (kbdHint) kbdHint.style.display = 'block';
    renderTable();
  }

  // Render News Wire with Relative Timing
  function renderNews() {
    const container = document.getElementById('newsContainer');
    if (!container) return;

    const articles = window.appData?.crypto_news || [];
    if (!articles.length) {
      container.innerHTML = '<div style="color: var(--text-dim); padding: 24px;">No breaking crypto intelligence loaded.</div>';
      return;
    }

    container.innerHTML = articles.map(art => {
      const relTime = formatRelativeTime(art.pubDate);
      const exactTime = art.pubDate || '';
      const sentBadge = art.sentiment === 'BULLISH' ? 'sig-strong-buy' : (art.sentiment === 'BEARISH' ? 'sig-exit' : 'sig-hold');

      return `
        <div class="news-item">
          <div class="news-top">
            <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
              <span class="badge-signal ${sentBadge}">
                ${art.sentiment} (${art.score > 0 ? '+' : ''}${art.score})
              </span>
              <span style="font-size: 11px; font-family: var(--font-mono); color: var(--cyan);">${art.catalyst || 'Catalyst'}</span>
              <span style="font-size: 11px; color: var(--text-dim);">${art.source}</span>
            </div>
            <span style="font-family: var(--font-mono); font-size: 12px; color: var(--green-light); font-weight: 700;" title="${exactTime}">
              ⏱️ ${relTime}
            </span>
          </div>
          <a href="${art.link}" target="_blank" class="news-headline">${art.title}</a>
          <div class="news-body">${art.summary || ''}</div>
          <div class="news-takeaway">🎯 <strong>AI Trader Takeaway:</strong> ${art.takeaway || 'Monitor momentum.'}</div>
        </div>
      `;
    }).join('');
  }

  // Render FinancialJuice Live Squawk with Relative Timing
  function renderSquawk() {
    const container = document.getElementById('squawkContainer');
    if (!container) return;

    const squawks = window.appData?.financial_juice || [];
    if (!squawks.length) {
      container.innerHTML = '<div style="color: var(--text-dim); padding: 24px;">No live macro squawks loaded.</div>';
      return;
    }

    container.innerHTML = squawks.map(sq => {
      const relTime = formatRelativeTime(sq.pubDate);
      const exactTime = sq.pubDate || '';
      const sentBadge = sq.sentiment === 'BULLISH' ? 'sig-strong-buy' : (sq.sentiment === 'BEARISH' ? 'sig-exit' : 'sig-hold');

      return `
        <div class="news-item">
          <div class="news-top">
            <span class="badge-signal ${sentBadge}">
              ${sq.sentiment} (${sq.score > 0 ? '+' : ''}${sq.score})
            </span>
            <span style="font-family: var(--font-mono); font-size: 12px; color: var(--cyan); font-weight: 700;" title="${exactTime}">
              ⚡ ${relTime}
            </span>
          </div>
          <div style="font-size: 15px; font-weight: 700; color: #fff; margin-bottom: 6px;">${sq.title}</div>
          <div class="news-takeaway">⚡ <strong>Squawk Impact:</strong> ${sq.takeaway || 'Macro volatility watch.'}</div>
        </div>
      `;
    }).join('');
  }

  // Obsidian 1-Click Sync Handler
  async function syncObsidian() {
    const syncButtons = document.querySelectorAll('.btn-sync-obsidian, button[onclick*="syncObsidian"]');
    syncButtons.forEach(btn => {
      btn.dataset.origText = btn.innerHTML;
      btn.innerHTML = '⏳ Syncing Vault...';
      btn.disabled = true;
    });

    try {
      const res = await fetch('/api/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (!res.ok) {
        throw new Error(`Sync failed with HTTP ${res.status}`);
      }

      const result = await res.json();
      console.log('[OBSIDIAN SYNC SUCCESS]', result);

      // 1. Play high-tech confirmation chime
      playConfirmationChime();

      // 2. Show visual toast
      showToast('⚡ Obsidian Vault Synced: Crypto Intelligence.md & Activity Log.md', false);

      // Button feedback
      syncButtons.forEach(btn => {
        btn.innerHTML = '✅ Vault Synced!';
        setTimeout(() => {
          btn.innerHTML = btn.dataset.origText || '⚡ Sync Obsidian Vault';
          btn.disabled = false;
        }, 2500);
      });
    } catch (err) {
      console.error('[OBSIDIAN SYNC ERROR]', err);
      showToast('⚠️ Obsidian Sync Failed — check server logs', true);

      syncButtons.forEach(btn => {
        btn.innerHTML = '❌ Sync Failed';
        setTimeout(() => {
          btn.innerHTML = btn.dataset.origText || '⚡ Sync Obsidian Vault';
          btn.disabled = false;
        }, 2500);
      });
    }
  }

  // Keyboard shortcut listener ('/' to focus search, 'Escape' to clear)
  function initKeyboardShortcuts() {
    window.addEventListener('keydown', (e) => {
      const searchInput = document.getElementById('searchInput');
      if (!searchInput) return;

      const activeEl = document.activeElement;
      const isInput = activeEl && (
        activeEl.tagName === 'INPUT' ||
        activeEl.tagName === 'TEXTAREA' ||
        activeEl.isContentEditable
      );

      if (e.key === '/' && !isInput) {
        e.preventDefault();
        searchInput.focus();
        searchInput.select();
        if (typeof window.setTab === 'function') {
          window.setTab('screener');
        }
      } else if (e.key === 'Escape' && isInput && activeEl === searchInput) {
        clearSearch();
        searchInput.blur();
      }
    });
  }

  // Initialize Table Header Sort Listeners
  function initTableSortHeaders() {
    const table = document.querySelector('#tab-screener table');
    if (!table) return;

    const columnMap = [
      { index: 0, key: 'rank' },
      { index: 1, key: 'symbol' },
      { index: 2, key: 'price' },
      { index: 3, key: 'change_24h' },
      { index: 4, key: 'change_7d' },
      { index: 5, key: 'signal' },
      { index: 6, key: 'score' },
      { index: 7, key: 'entry_low' },
      { index: 8, key: 'target_1' },
      { index: 9, key: 'stop_loss' },
      { index: 10, key: 'rr_ratio' }
    ];

    const ths = table.querySelectorAll('thead th');
    ths.forEach((th, i) => {
      const match = columnMap.find(m => m.index === i);
      if (match) {
        th.setAttribute('data-sort', match.key);
        th.classList.add('sortable');
        th.style.cursor = 'pointer';
        th.style.userSelect = 'none';
        th.title = `Click to sort by ${th.textContent.trim()}`;

        if (!th.querySelector('.sort-icon')) {
          const icon = document.createElement('span');
          icon.className = 'sort-icon';
          icon.textContent = ' ⇅';
          icon.style.opacity = '0.4';
          th.appendChild(icon);
        }

        th.onclick = () => handleHeaderSort(match.key);
      }
    });

    updateHeaderSortIndicators();
  }

  // Enhance Search Bar with Clear Button
  function initSearchBar() {
    const searchInput = document.getElementById('searchInput');
    if (!searchInput) return;

    searchInput.addEventListener('input', () => handleSearchInput(searchInput.value));

    let clearBtn = document.getElementById('clearSearchBtn');
    if (!clearBtn && searchInput.parentElement) {
      clearBtn = document.createElement('button');
      clearBtn.id = 'clearSearchBtn';
      clearBtn.type = 'button';
      clearBtn.innerHTML = '✕';
      clearBtn.title = 'Clear search (Esc)';
      clearBtn.style.cssText = `
        position: absolute;
        right: 8px;
        top: 50%;
        transform: translateY(-50%);
        background: rgba(255, 255, 255, 0.12);
        border: none;
        border-radius: 50%;
        color: #fff;
        width: 18px;
        height: 18px;
        display: none;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        font-size: 10px;
        transition: all 0.2s;
        z-index: 5;
      `;
      clearBtn.onmouseover = () => {
        clearBtn.style.background = 'rgba(255, 255, 255, 0.25)';
      };
      clearBtn.onmouseout = () => {
        clearBtn.style.background = 'rgba(255, 255, 255, 0.12)';
      };
      clearBtn.onclick = clearSearch;

      const parent = searchInput.parentElement;
      if (window.getComputedStyle(parent).position === 'static') {
        parent.style.position = 'relative';
      }
      parent.appendChild(clearBtn);
    }
  }

  // Setup / Initialization
  function init() {
    initTableSortHeaders();
    initSearchBar();
    initKeyboardShortcuts();

    // Attach global hooks to window
    window.setFilter = setFilter;
    window.setEngineFilter = setFilter;
    window.handleHeaderSort = handleHeaderSort;
    window.setTableSort = handleHeaderSort;
    window.setEngineSearch = handleSearchInput;
    window.clearSearch = clearSearch;
    window.formatRelativeTime = formatRelativeTime;
    window.syncObsidian = syncObsidian;
    window.showToast = showToast;
    window.playConfirmationChime = playConfirmationChime;
    window.renderTable = renderTable;
    window.renderNews = renderNews;
    window.renderSquawk = renderSquawk;
    window.sortAssetList = sortAssets;
    window.getEngineFilter = () => currentFilter;
    window.getEngineSearch = () => searchQuery;

    // Periodic relative time update for active news/squawk feeds every 20 seconds
    setInterval(() => {
      if (document.getElementById('tab-news')?.style.display !== 'none') {
        renderNews();
      }
      if (document.getElementById('tab-squawk')?.style.display !== 'none') {
        renderSquawk();
      }
    }, 20000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Export module API to window
  window.ScreenerEngine = {
    setFilter,
    setEngineFilter: setFilter,
    handleHeaderSort,
    setTableSort: handleHeaderSort,
    renderTable,
    renderNews,
    renderSquawk,
    clearSearch,
    formatRelativeTime,
    syncObsidian,
    playConfirmationChime,
    showToast,
    getSort: () => ({ ...currentSort }),
    getFilter: () => currentFilter
  };

})(window);
