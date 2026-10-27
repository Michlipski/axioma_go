/**
 * AXIOMA GO // 碁 (10x10) — Sovereign Tactile Board UI Controller
 * Pure Vanilla JavaScript (ES6+) — Zero External Dependencies
 */

(function () {
  'use strict';

  // Board Geometry Configuration
  const BOARD_SIZE = 10;
  const COLUMNS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K'];
  const SVG_SIZE = 680;
  const MARGIN = 55;
  const STEP = (SVG_SIZE - 2 * MARGIN) / (BOARD_SIZE - 1); // ~63.33px per intersection
  const STONE_RADIUS = 26;

  // Star Points (D4, G4, D7, G7 on 10x10, 0-indexed)
  const STAR_POINTS = [
    { x: 3, y: 3 },
    { x: 6, y: 3 },
    { x: 3, y: 6 },
    { x: 6, y: 6 }
  ];

  // Application State
  const state = {
    mode: 'free_play', // 'free_play' | 'showcase'
    board: Array.from({ length: BOARD_SIZE }, () => Array(BOARD_SIZE).fill('.')),
    currentPlayer: 'B',
    captures: { B: 0, W: 0 },
    lastMove: null,
    moveCount: 0,
    libertiesMap: {},
    atariGroups: [],
    gameOver: false,

    // Overlays
    showHeatmap: true,
    showAtariHalos: true,
    showCoordinates: true,

    // Showcase
    showcasesList: [],
    activeShowcaseId: 'snapback',
    showcaseData: null,
    currentPly: 0,
    autoPlayTimer: null,
    autoPlaySpeed: 1000, // ms per step

    // UI Cache
    hoverCoord: null
  };

  // DOM Elements
  const dom = {
    // Nav
    btnModeFreePlay: document.getElementById('btnModeFreePlay'),
    btnModeShowcase: document.getElementById('btnModeShowcase'),
    toggleHeatmap: document.getElementById('toggleHeatmap'),
    toggleAtariHalos: document.getElementById('toggleAtariHalos'),
    toggleCoords: document.getElementById('toggleCoords'),

    // Left Panel
    moveCountBadge: document.getElementById('moveCountBadge'),
    activeStonePreview: document.getElementById('activeStonePreview'),
    turnPlayerName: document.getElementById('turnPlayerName'),
    turnStatusDesc: document.getElementById('turnStatusDesc'),
    capturesBlackCount: document.getElementById('capturesBlackCount'),
    capturesWhiteCount: document.getElementById('capturesWhiteCount'),
    graveyardBlackStones: document.getElementById('graveyardBlackStones'),
    graveyardWhiteStones: document.getElementById('graveyardWhiteStones'),
    tacticalAlertBanner: document.getElementById('tacticalAlertBanner'),
    tacticalAlertText: document.getElementById('tacticalAlertText'),
    btnUndoMove: document.getElementById('btnUndoMove'),
    btnPassTurn: document.getElementById('btnPassTurn'),
    btnResetBoard: document.getElementById('btnResetBoard'),
    btnResignMatch: document.getElementById('btnResignMatch'),

    // Center Board SVG Layers
    goBoardSvg: document.getElementById('goBoardSvg'),
    layerCoords: document.getElementById('layerCoords'),
    layerGridLines: document.getElementById('layerGridLines'),
    layerStarPoints: document.getElementById('layerStarPoints'),
    layerHoverGhost: document.getElementById('layerHoverGhost'),
    layerAtariHalos: document.getElementById('layerAtariHalos'),
    layerStones: document.getElementById('layerStones'),
    layerLastMove: document.getElementById('layerLastMove'),
    layerHeatmap: document.getElementById('layerHeatmap'),
    layerClickInterceptors: document.getElementById('layerClickInterceptors'),
    hoverCoordReadout: document.getElementById('hoverCoordReadout'),

    // Right Showcase Panel
    panelShowcase: document.getElementById('panelShowcase'),
    selectShowcase: document.getElementById('selectShowcase'),
    showcaseName: document.getElementById('showcaseName'),
    showcaseJapanese: document.getElementById('showcaseJapanese'),
    showcaseStepCounter: document.getElementById('showcaseStepCounter'),
    showcaseDesc: document.getElementById('showcaseDesc'),
    stepSlider: document.getElementById('stepSlider'),
    btnStepFirst: document.getElementById('btnStepFirst'),
    btnStepPrev: document.getElementById('btnStepPrev'),
    btnAutoPlay: document.getElementById('btnAutoPlay'),
    btnStepNext: document.getElementById('btnStepNext'),
    btnStepLast: document.getElementById('btnStepLast'),
    btnForkPlay: document.getElementById('btnForkPlay'),
    playIcon: document.getElementById('playIcon'),
    playButtonText: document.getElementById('playButtonText'),
    threatBadge: document.getElementById('threatBadge'),
    commMoveCoord: document.getElementById('commMoveCoord'),
    commJapaneseTerm: document.getElementById('commJapaneseTerm'),
    commExplanation: document.getElementById('commExplanation'),
    speedButtons: document.querySelectorAll('.speed-btn'),

    // Toast Container
    toastContainer: document.getElementById('toastContainer')
  };

  // Coordinate Conversion Helpers
  // In Go: Row 1 is bottom, Row 10 is top. Column 0 is A, Column 9 is K.
  function toPixel(x, y) {
    const px = MARGIN + x * STEP;
    const py = MARGIN + (BOARD_SIZE - 1 - y) * STEP;
    return { px, py };
  }

  function coordToStr(x, y) {
    if (x >= 0 && x < COLUMNS.length && y >= 0 && y < BOARD_SIZE) {
      return `${COLUMNS[x]}${y + 1}`;
    }
    return `(${x},${y})`;
  }

  // Toast Notification System
  function showToast(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    dom.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      setTimeout(() => {
        if (toast.parentNode) toast.parentNode.removeChild(toast);
      }, 300);
    }, duration);
  }

  // API Client Methods
  async function apiGetState() {
    try {
      const res = await fetch('/api/state');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      console.error('API Error [getState]:', err);
      return null;
    }
  }

  async function apiPlay(x, y, color = null) {
    try {
      const res = await fetch('/api/play', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ x, y, color })
      });
      const data = await res.json();
      return { ok: res.ok, data };
    } catch (err) {
      return { ok: false, data: { error: err.message } };
    }
  }

  async function apiPass() {
    try {
      const res = await fetch('/api/pass', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      return await res.json();
    } catch (err) {
      return { error: err.message };
    }
  }

  async function apiUndo() {
    try {
      const res = await fetch('/api/undo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      const data = await res.json();
      return { ok: res.ok, data };
    } catch (err) {
      return { ok: false, data: { error: err.message } };
    }
  }

  async function apiReset() {
    try {
      const res = await fetch('/api/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      return await res.json();
    } catch (err) {
      return { error: err.message };
    }
  }

  async function apiGetShowcases() {
    try {
      const res = await fetch('/api/showcases');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      return data.showcases || [];
    } catch (err) {
      console.error('API Error [getShowcases]:', err);
      return [];
    }
  }

  async function apiGetShowcaseDetails(id) {
    try {
      const res = await fetch(`/api/showcases/${id}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      console.error(`API Error [getShowcaseDetails(${id})]:`, err);
      return null;
    }
  }

  async function apiForkShowcase(id, ply) {
    try {
      const res = await fetch(`/api/showcases/${id}/fork`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ply })
      });
      const data = await res.json();
      return { ok: res.ok, data };
    } catch (err) {
      return { ok: false, data: { error: err.message } };
    }
  }

  // SVG Board Construction (Static Grid Lines, Coordinates, Star Points)
  function initStaticBoardLayers() {
    // 1. Grid Lines
    let gridLinesHtml = '';
    for (let i = 0; i < BOARD_SIZE; i++) {
      const p1 = toPixel(i, 0);
      const p2 = toPixel(i, BOARD_SIZE - 1);
      // Vertical line
      gridLinesHtml += `<line x1="${p1.px}" y1="${p1.py}" x2="${p2.px}" y2="${p2.py}" />`;

      const p3 = toPixel(0, i);
      const p4 = toPixel(BOARD_SIZE - 1, i);
      // Horizontal line
      gridLinesHtml += `<line x1="${p3.px}" y1="${p3.py}" x2="${p4.px}" y2="${p4.py}" />`;
    }
    dom.layerGridLines.innerHTML = gridLinesHtml;

    // 2. Star Points (Hoshi)
    let starPointsHtml = '';
    STAR_POINTS.forEach(pt => {
      const { px, py } = toPixel(pt.x, pt.y);
      starPointsHtml += `<circle cx="${px}" cy="${py}" r="4.5" />`;
    });
    dom.layerStarPoints.innerHTML = starPointsHtml;

    // 3. Coordinate Labels (A-K, 1-10)
    let coordsHtml = '';
    const labelOffset = 26;
    for (let x = 0; x < BOARD_SIZE; x++) {
      const { px } = toPixel(x, 0);
      const colLabel = COLUMNS[x];
      // Top Label
      coordsHtml += `<text x="${px}" y="${MARGIN - labelOffset}" class="coord-text">${colLabel}</text>`;
      // Bottom Label
      coordsHtml += `<text x="${px}" y="${SVG_SIZE - MARGIN + labelOffset}" class="coord-text">${colLabel}</text>`;
    }
    for (let y = 0; y < BOARD_SIZE; y++) {
      const { py } = toPixel(0, y);
      const rowLabel = y + 1;
      // Left Label
      coordsHtml += `<text x="${MARGIN - labelOffset}" y="${py}" class="coord-text">${rowLabel}</text>`;
      // Right Label
      coordsHtml += `<text x="${SVG_SIZE - MARGIN + labelOffset}" y="${py}" class="coord-text">${rowLabel}</text>`;
    }
    dom.layerCoords.innerHTML = coordsHtml;

    // 4. Click Interceptors (Transparent hit-target circles for flawless clicking)
    let interceptorsHtml = '';
    for (let y = 0; y < BOARD_SIZE; y++) {
      for (let x = 0; x < BOARD_SIZE; x++) {
        const { px, py } = toPixel(x, y);
        interceptorsHtml += `
          <circle cx="${px}" cy="${py}" r="${STEP / 2}" 
                  fill="transparent" 
                  data-x="${x}" data-y="${y}" 
                  class="board-hit-target" />
        `;
      }
    }
    dom.layerClickInterceptors.innerHTML = interceptorsHtml;
  }

  // Dynamic Board Rendering (Stones, Atari Halos, Heatmap, Last Move)
  function renderBoard() {
    // Toggle coordinate visibility
    dom.layerCoords.style.display = state.showCoordinates ? 'block' : 'none';

    // 1. Render Stones
    let stonesHtml = '';
    for (let y = 0; y < BOARD_SIZE; y++) {
      for (let x = 0; x < BOARD_SIZE; x++) {
        const cell = state.board[y][x];
        if (cell === 'B' || cell === 'W') {
          const { px, py } = toPixel(x, y);
          const grad = cell === 'B' ? 'url(#blackStoneGrad)' : 'url(#whiteStoneGrad)';
          stonesHtml += `
            <circle cx="${px}" cy="${py}" r="${STONE_RADIUS}" 
                    fill="${grad}" 
                    data-x="${x}" data-y="${y}" 
                    class="stone-elem" />
          `;
        }
      }
    }
    dom.layerStones.innerHTML = stonesHtml;

    // 2. Render Pulsing Atari Threat Halos
    let atariHtml = '';
    if (state.showAtariHalos && state.atariGroups && state.atariGroups.length > 0) {
      state.atariGroups.forEach(group => {
        group.stones.forEach(([sx, sy]) => {
          const { px, py } = toPixel(sx, sy);
          atariHtml += `<circle cx="${px}" cy="${py}" r="${STONE_RADIUS + 4}" class="atari-halo" />`;
        });
      });
    }
    dom.layerAtariHalos.innerHTML = atariHtml;

    // 3. Render Last Move Ring
    let lastMoveHtml = '';
    if (state.lastMove && state.lastMove.x >= 0 && state.lastMove.y >= 0) {
      const { px, py } = toPixel(state.lastMove.x, state.lastMove.y);
      lastMoveHtml += `<circle cx="${px}" cy="${py}" r="${STONE_RADIUS + 3}" class="last-move-ring" />`;
    }
    dom.layerLastMove.innerHTML = lastMoveHtml;

    // 4. Render Liberty Heatmap Badges
    let heatmapHtml = '';
    if (state.showHeatmap) {
      for (let y = 0; y < BOARD_SIZE; y++) {
        for (let x = 0; x < BOARD_SIZE; x++) {
          const cell = state.board[y][x];
          if (cell === 'B' || cell === 'W') {
            const key = `${x},${y}`;
            const libs = state.libertiesMap[key];
            if (libs !== undefined) {
              const { px, py } = toPixel(x, y);
              let heatClass = 'heat-4';
              if (libs === 1) heatClass = 'heat-1';
              else if (libs === 2) heatClass = 'heat-2';
              else if (libs === 3) heatClass = 'heat-3';

              const textClass = (libs === 1 || cell === 'B') ? 'heat-text-light' : 'heat-text-dark';
              heatmapHtml += `
                <g class="heat-badge-group">
                  <circle cx="${px}" cy="${py}" r="9.5" class="heat-badge-bg ${heatClass}" />
                  <text x="${px}" y="${py}" class="heat-badge-text ${textClass}">${libs >= 4 ? '4+' : libs}</text>
                </g>
              `;
            }
          }
        }
      }
    }
    dom.layerHeatmap.innerHTML = heatmapHtml;
  }

  // Update Left Panel HUD (Turn, Prisoners, Alerts, Move Count)
  function updateHUD() {
    // Turn Display
    const isBlack = state.currentPlayer === 'B';
    dom.turnPlayerName.textContent = isBlack ? "BLACK'S TURN" : "WHITE'S TURN";
    dom.activeStonePreview.className = `stone-preview ${isBlack ? 'stone-black' : 'stone-white'}`;
    dom.moveCountBadge.textContent = `Move #${state.moveCount}`;

    if (state.mode === 'free_play') {
      dom.turnStatusDesc.textContent = isBlack
        ? 'Black stone ready to place'
        : 'White stone ready to place';
    } else {
      dom.turnStatusDesc.textContent = `Capture Showcase [${state.activeShowcaseId.toUpperCase()}]`;
    }

    // Prisoners / Graveyard
    const bCaptures = state.captures.B || 0;
    const wCaptures = state.captures.W || 0;
    dom.capturesBlackCount.textContent = bCaptures;
    dom.capturesWhiteCount.textContent = wCaptures;

    // Graveyard visual stone dots
    let bRackHtml = '';
    for (let i = 0; i < Math.min(bCaptures, 24); i++) {
      bRackHtml += '<span class="graveyard-dot dot-white"></span>';
    }
    dom.graveyardBlackStones.innerHTML = bRackHtml;

    let wRackHtml = '';
    for (let i = 0; i < Math.min(wCaptures, 24); i++) {
      wRackHtml += '<span class="graveyard-dot dot-black"></span>';
    }
    dom.graveyardWhiteStones.innerHTML = wRackHtml;

    // Tactical Alert Banner
    const atariCount = state.atariGroups ? state.atariGroups.length : 0;
    if (atariCount > 0) {
      dom.tacticalAlertBanner.className = 'tactical-banner banner-atari';
      const colors = state.atariGroups.map(g => g.color === 'B' ? 'Black' : 'White');
      const uniqueColors = [...new Set(colors)].join(' & ');
      dom.tacticalAlertText.textContent = `🚨 ATARI THREAT: ${uniqueColors} group in immediate danger! (1 liberty)`;
    } else if (state.lastMove && state.lastMove.captured > 0) {
      dom.tacticalAlertBanner.className = 'tactical-banner banner-warning';
      dom.tacticalAlertText.textContent = `⚡ CAPTURE: ${state.lastMove.captured} stone(s) captured!`;
    } else {
      dom.tacticalAlertBanner.className = 'tactical-banner banner-calm';
      dom.tacticalAlertText.textContent = '● Board State: Balanced (No groups in atari)';
    }
  }

  // Synchronize state from API payload
  function syncEngineState(data) {
    if (!data) return;
    state.board = data.board || state.board;
    state.currentPlayer = data.current_player || state.currentPlayer;
    state.captures = data.captures || state.captures;
    state.lastMove = data.last_move;
    state.moveCount = data.move_count || 0;
    state.libertiesMap = data.liberties_map || {};
    state.atariGroups = data.atari_groups || [];
    state.gameOver = !!data.game_over;

    renderBoard();
    updateHUD();
  }

  // Free Play Board Interaction
  async function handleBoardClick(x, y) {
    if (state.mode !== 'free_play') {
      showToast('Switch to Free Play mode or use "Fork & Play" to place stones.', 'warning');
      return;
    }

    if (state.board[y][x] !== '.') {
      showToast(`Intersection ${coordToStr(x, y)} is already occupied!`, 'warning');
      return;
    }

    const { ok, data } = await apiPlay(x, y, state.currentPlayer);
    if (!ok || !data.success) {
      showToast(data.message || data.error || 'Illegal move', 'danger');
      return;
    }

    syncEngineState(data);

    if (data.last_move && data.last_move.captured > 0) {
      showToast(`Captured ${data.last_move.captured} stone(s)!`, 'success');
    }
  }

  // Hover Ghost Stone Preview
  function handleBoardHover(x, y) {
    state.hoverCoord = { x, y };
    dom.hoverCoordReadout.textContent = `Intersection: ${coordToStr(x, y)}`;

    if (state.mode !== 'free_play' || state.board[y][x] !== '.') {
      dom.layerHoverGhost.innerHTML = '';
      return;
    }

    const { px, py } = toPixel(x, y);
    const grad = state.currentPlayer === 'B' ? 'url(#blackStoneGrad)' : 'url(#whiteStoneGrad)';
    dom.layerHoverGhost.innerHTML = `
      <circle cx="${px}" cy="${py}" r="${STONE_RADIUS}" 
              fill="${grad}" 
              class="ghost-stone" />
    `;
  }

  function handleBoardLeave() {
    state.hoverCoord = null;
    dom.hoverCoordReadout.textContent = 'Intersection: --';
    dom.layerHoverGhost.innerHTML = '';
  }

  // Showcase Controller Methods
  async function loadShowcase(showcaseId) {
    stopAutoPlay();
    state.activeShowcaseId = showcaseId;
    dom.selectShowcase.value = showcaseId;

    const sc = await apiGetShowcaseDetails(showcaseId);
    if (!sc) {
      showToast(`Failed to load showcase: ${showcaseId}`, 'danger');
      return;
    }

    state.showcaseData = sc;
    state.currentPly = 0;

    // Update showcase metadata card
    dom.showcaseName.textContent = sc.name;
    dom.showcaseJapanese.textContent = sc.japanese_term;
    dom.showcaseDesc.textContent = sc.description;
    dom.stepSlider.max = sc.steps.length - 1;
    dom.stepSlider.value = 0;

    applyShowcaseStep(0);
  }

  function applyShowcaseStep(ply) {
    if (!state.showcaseData || !state.showcaseData.steps) return;
    const steps = state.showcaseData.steps;
    if (ply < 0) ply = 0;
    if (ply >= steps.length) ply = steps.length - 1;

    state.currentPly = ply;
    dom.stepSlider.value = ply;
    dom.showcaseStepCounter.textContent = `Step ${ply} / ${steps.length - 1}`;

    const step = steps[ply];
    syncEngineState(step.state);

    // Update tactical commentary card
    dom.threatBadge.className = `threat-badge threat-${step.badge.toLowerCase()}`;
    dom.threatBadge.textContent = step.badge;

    dom.commMoveCoord.textContent = step.coord ? `Move: ${step.coord}` : 'Initial Setup';
    dom.commJapaneseTerm.textContent = step.japanese_term || '';
    dom.commExplanation.textContent = step.explanation;
  }

  function startAutoPlay() {
    if (state.autoPlayTimer) return;
    dom.btnAutoPlay.classList.add('active');
    dom.playButtonText.textContent = 'Pause';
    dom.playIcon.innerHTML = '<path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>';

    state.autoPlayTimer = setInterval(() => {
      if (!state.showcaseData) return;
      if (state.currentPly < state.showcaseData.steps.length - 1) {
        applyShowcaseStep(state.currentPly + 1);
      } else {
        stopAutoPlay();
      }
    }, state.autoPlaySpeed);
  }

  function stopAutoPlay() {
    if (state.autoPlayTimer) {
      clearInterval(state.autoPlayTimer);
      state.autoPlayTimer = null;
    }
    dom.btnAutoPlay.classList.remove('active');
    dom.playButtonText.textContent = 'Auto-Play';
    dom.playIcon.innerHTML = '<path d="M8 5v14l11-7z"/>';
  }

  function toggleAutoPlay() {
    if (state.autoPlayTimer) {
      stopAutoPlay();
    } else {
      if (state.showcaseData && state.currentPly >= state.showcaseData.steps.length - 1) {
        applyShowcaseStep(0);
      }
      startAutoPlay();
    }
  }

  // Fork Showcase into Free Play
  async function handleForkAndPlay() {
    stopAutoPlay();
    const { ok, data } = await apiForkShowcase(state.activeShowcaseId, state.currentPly);
    if (!ok || !data.success) {
      showToast(data.error || 'Failed to fork showcase position', 'danger');
      return;
    }

    setMode('free_play');
    syncEngineState(data);
    showToast(`⚡ Forked "${state.showcaseData.name}" at step ${state.currentPly} into Free Play!`, 'success', 4000);
  }

  // Mode Switching
  function setMode(newMode) {
    state.mode = newMode;
    if (newMode === 'free_play') {
      dom.btnModeFreePlay.classList.add('active');
      dom.btnModeShowcase.classList.remove('active');
      dom.panelShowcase.style.opacity = '0.5';
      showToast('Mode: Free Play — Click board to place stones.', 'info');
      // Refresh active server state
      apiGetState().then(syncEngineState);
    } else {
      dom.btnModeFreePlay.classList.remove('active');
      dom.btnModeShowcase.classList.add('active');
      dom.panelShowcase.style.opacity = '1';
      showToast('Mode: Capture Showcases — Step through tactical tesujis.', 'info');
      loadShowcase(state.activeShowcaseId);
    }
  }

  // Event Listeners Initialization
  function initEventListeners() {
    // Mode Navigation
    dom.btnModeFreePlay.addEventListener('click', () => setMode('free_play'));
    dom.btnModeShowcase.addEventListener('click', () => setMode('showcase'));

    // Overlay Toggles
    dom.toggleHeatmap.addEventListener('change', e => {
      state.showHeatmap = e.target.checked;
      renderBoard();
    });

    dom.toggleAtariHalos.addEventListener('change', e => {
      state.showAtariHalos = e.target.checked;
      renderBoard();
    });

    dom.toggleCoords.addEventListener('change', e => {
      state.showCoordinates = e.target.checked;
      renderBoard();
    });

    // Board Clicks & Hovers
    dom.layerClickInterceptors.addEventListener('click', e => {
      const target = e.target;
      if (target && target.classList.contains('board-hit-target')) {
        const x = parseInt(target.getAttribute('data-x'), 10);
        const y = parseInt(target.getAttribute('data-y'), 10);
        handleBoardClick(x, y);
      }
    });

    dom.layerClickInterceptors.addEventListener('mousemove', e => {
      const target = e.target;
      if (target && target.classList.contains('board-hit-target')) {
        const x = parseInt(target.getAttribute('data-x'), 10);
        const y = parseInt(target.getAttribute('data-y'), 10);
        handleBoardHover(x, y);
      }
    });

    dom.goBoardSvg.addEventListener('mouseleave', handleBoardLeave);

    // Free Play Controls
    dom.btnUndoMove.addEventListener('click', async () => {
      if (state.mode !== 'free_play') {
        showToast('Undo is available in Free Play mode', 'warning');
        return;
      }
      const { ok, data } = await apiUndo();
      if (!ok || !data.success) {
        showToast(data.message || 'No moves to undo', 'warning');
        return;
      }
      syncEngineState(data);
      showToast('↩ 1-Tap Functorial Undo: Reverted previous move', 'info');
    });

    dom.btnPassTurn.addEventListener('click', async () => {
      if (state.mode !== 'free_play') return;
      const data = await apiPass();
      syncEngineState(data);
      showToast(`⏭ ${state.currentPlayer === 'B' ? 'White' : 'Black'} passed turn.`, 'info');
    });

    dom.btnResetBoard.addEventListener('click', async () => {
      if (state.mode !== 'free_play') {
        setMode('free_play');
      }
      const data = await apiReset();
      syncEngineState(data);
      showToast('⟲ Board reset to empty state', 'info');
    });

    dom.btnResignMatch.addEventListener('click', async () => {
      if (state.mode !== 'free_play') return;
      const winner = state.currentPlayer === 'B' ? 'White' : 'Black';
      showToast(`⚐ ${state.currentPlayer === 'B' ? 'Black' : 'White'} resigns. ${winner} wins!`, 'warning', 4000);
      const data = await apiReset();
      syncEngineState(data);
    });

    // Showcase Controls
    dom.selectShowcase.addEventListener('change', e => {
      loadShowcase(e.target.value);
    });

    dom.stepSlider.addEventListener('input', e => {
      stopAutoPlay();
      applyShowcaseStep(parseInt(e.target.value, 10));
    });

    dom.btnStepFirst.addEventListener('click', () => {
      stopAutoPlay();
      applyShowcaseStep(0);
    });

    dom.btnStepPrev.addEventListener('click', () => {
      stopAutoPlay();
      applyShowcaseStep(state.currentPly - 1);
    });

    dom.btnAutoPlay.addEventListener('click', toggleAutoPlay);

    dom.btnStepNext.addEventListener('click', () => {
      stopAutoPlay();
      applyShowcaseStep(state.currentPly + 1);
    });

    dom.btnStepLast.addEventListener('click', () => {
      stopAutoPlay();
      if (state.showcaseData) {
        applyShowcaseStep(state.showcaseData.steps.length - 1);
      }
    });

    dom.btnForkPlay.addEventListener('click', handleForkAndPlay);

    // Speed Controls
    dom.speedButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        dom.speedButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.autoPlaySpeed = parseInt(btn.getAttribute('data-speed'), 10);
        if (state.autoPlayTimer) {
          stopAutoPlay();
          startAutoPlay();
        }
      });
    });

    // Keyboard Shortcuts
    window.addEventListener('keydown', e => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;

      if (e.key === 'ArrowRight' || e.key === ' ') {
        e.preventDefault();
        if (state.mode === 'showcase') {
          stopAutoPlay();
          applyShowcaseStep(state.currentPly + 1);
        }
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        if (state.mode === 'showcase') {
          stopAutoPlay();
          applyShowcaseStep(state.currentPly - 1);
        }
      } else if (e.key === 'u' || e.key === 'U') {
        dom.btnUndoMove.click();
      } else if (e.key === 'p' || e.key === 'P') {
        dom.btnPassTurn.click();
      } else if (e.key === 'h' || e.key === 'H') {
        dom.toggleHeatmap.click();
      }
    });
  }

  // Application Bootstrap
  async function init() {
    initStaticBoardLayers();
    initEventListeners();

    // Fetch initial board state from server
    const initialState = await apiGetState();
    if (initialState) {
      syncEngineState(initialState);
    }

    // Preload showcase library
    state.showcasesList = await apiGetShowcases();
    await loadShowcase('snapback');

    // Default to free play view with showcase enabled on tab
    setMode('free_play');

    console.log('⚡ Axioma Go (10x10) Sovereign Tactile Board UI initialized.');
  }

  // Launch on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
