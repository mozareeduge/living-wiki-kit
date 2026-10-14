

'use strict';

var obsidian = require('obsidian');

// ── D3 Loader ───────────────────────────────────────────────────────────────
var d3 = require('./vendor/d3.min.js');
var FONT_NEWSREADER = require('./fonts/Newsreader.ttf');
var FONT_PUBLIC_SANS = require('./fonts/PublicSans.ttf');
function loadFonts() {
  if (typeof FontFace === 'undefined' || document.fonts.check('16px "LWF Newsreader"')) return;
  [['LWF Newsreader', FONT_NEWSREADER, '200 800'], ['LWF Public Sans', FONT_PUBLIC_SANS, '100 900']].forEach(function (f) {
    var face = new FontFace(f[0], 'url(' + f[1] + ')', { weight: f[2] });
    face.load().then(function () { document.fonts.add(face); }).catch(function () {});
  });
}
function loadD3() { return Promise.resolve(d3); }

// ── Constants ───────────────────────────────────────────────────────────────
var NOTE_TYPES = ['RNO', 'MNO', 'FO', 'NameO', 'RefO', 'RelO'];
var TYPE_COLORS = {
  RNO: '#8ab4f8', MNO: '#fdd663', FO: '#81c995',
  NameO: '#f28b82', RefO: '#c58af9', RelO: '#ff8b3d'
};
var TYPE_LABEL = { RNO: 'Note', MNO: 'Map', FO: 'Field', NameO: 'Name', RefO: 'Source', RelO: 'Relation' };
var typeLabel = function (t) { return TYPE_LABEL[t] || t; };
var ROUTE_MAX = 11;
var ROUTE_VISIBLE_MAX = 10;

// ── Deterministic PRNG ──────────────────────────────────────────────────────
function stableHash(text) {
  var h = 2166136261 >>> 0;
  for (var i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}
function seededUnit(seed) {
  var x = stableHash(seed) || 1;
  return function () {
    x ^= x << 13; x ^= x >>> 17; x ^= x << 5;
    return (x >>> 0) / 4294967296;
  };
}

// ── Graph Model ─────────────────────────────────────────────────────────────
var modelApi = require('./model.js');
var buildModel = modelApi.buildModel;
var buildFocusSet = modelApi.buildFocusSet;
// ── Node Metrics ────────────────────────────────────────────────────────────
function nodeMetrics(d) {
  switch (d.type) {
    case 'RNO': return { coreR: 6.2, outerR: 10.4, hitR: 19.4, collideR: 19.4, labelOffset: 19.4, haloR: 16.4, focusR: 18.4 };
    case 'MNO': return { coreR: 6.8, outerR: 7.0, hitR: 16, collideR: 16, labelOffset: 16, haloR: 13, focusR: 15 };
    case 'NameO': return { coreR: 0, outerR: 5, hitR: 14, collideR: 14, labelOffset: 14, haloR: 11, focusR: 13 };
    case 'RefO': return { coreR: 4, outerR: 5.66, hitR: 14.66, collideR: 14.66, labelOffset: 14.66, haloR: 11.66, focusR: 13.66 };
    case 'RelO': return { coreR: 7.5, outerR: 7.5, hitR: 16.5, collideR: 16.5, labelOffset: 16.5, haloR: 13.5, focusR: 15.5 };
    default: return { coreR: 6.2, outerR: 6.2, hitR: 15.2, collideR: 15.2, labelOffset: 15.2, haloR: 12.2, focusR: 14.2 };
  }
}

function irregularCirclePath(id, radius, points) {
  var rnd = seededUnit(id);
  var pts = [];
  for (var i = 0; i < points; i++) {
    var a = Math.PI * 2 * i / points;
    var r = radius * (0.955 + rnd() * 0.09);
    pts.push([Math.cos(a) * r, Math.sin(a) * r]);
  }
  return pts.map(function (p, i) {
    return (i ? 'L' : 'M') + p[0].toFixed(3) + ',' + p[1].toFixed(3);
  }).join(' ') + ' Z';
}

// ── Helpers ─────────────────────────────────────────────────────────────────
function isMobile() { return window.matchMedia('(max-width:860px)').matches; }
function prefersReducedMotion() { return window.matchMedia('(prefers-reduced-motion: reduce)').matches; }
function nextFrame() { return new Promise(function (r) { requestAnimationFrame(function () { requestAnimationFrame(r); }); }); }
function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }

// ── Plugin ──────────────────────────────────────────────────────────────────
var LivingWikiFieldPlugin = (function () {
  var Class = function () { obsidian.Plugin.apply(this, arguments); };
  Class.prototype = Object.create(obsidian.Plugin.prototype);
  Class.prototype.constructor = Class;

  Class.prototype.onload = function () {
    var self = this;
    loadFonts();
    this.model = null;
    this.activeId = null;
    this.routeEvents = [];
    this.hiddenTypes = {};
    NOTE_TYPES.forEach(function (t) { self.hiddenTypes[t] = false; });
    this.objectVisibility = {};
    this.soloSet = null;
    this.readerOpen = false;
    this.onboardingActive = false;
    this.aboutOpen = false;
    this.fieldTrace = { wear: {}, afterglows: [], activeClearingId: null };
    this.sim = null;
    this.svg = null;
    this.root = null;
    this.width = 0;
    this.height = 0;
    this.fitted = false;
    this.previewTimer = null;
    this.touchTimer = null;
    this.cameraInFlight = false;
    this.currentLightMode = 'field';
    this.appliedBlurPx = 0;

    this.registerView('lwf-field-view', function (leaf) { return new FieldView(leaf, self); });
    this.registerView('lwf-reader-view', function (leaf) { return new ReaderView(leaf, self); });
    this.registerView('lwf-route-view', function (leaf) { return new RouteView(leaf, self); });
    this.registerView('lwf-index-view', function (leaf) { return new IndexView(leaf, self); });

    var addMode = function (name, icon, type) {
      self.addCommand({ id: 'open-' + name, name: 'Open ' + name + ' view', callback: function () { self.activate(type); } });
      self.addRibbonIcon(icon, 'Living Wiki Field — ' + name, function () { self.activate(type); });
    };
    addMode('Field', 'net-unplugged', 'lwf-field-view');
    addMode('Reader', 'book-open', 'lwf-reader-view');
    addMode('Route', 'route', 'lwf-route-view');
    addMode('Index', 'list', 'lwf-index-view');

    this.addCommand({ id: 'rebuild-model', name: 'Rebuild field model', callback: function () { self.model = null; self.refreshAll(); new obsidian.Notice('Living Wiki Field: model rebuilt.'); } });
    this.addCommand({ id: 'clear-route', name: 'Clear route', callback: function () { self.routeEvents = []; self.refreshAll(); } });

    this.app.workspace.onLayoutReady(function () {
      self.getModel();
      loadD3().then(function () {
        self.initGraph();
        self.showThreshold();
      });
    });

    this.registerEvent(this.app.metadataCache.on('resolved', function () {
      self.model = null;
      self.refreshAll();
    }));
  };

  Class.prototype.onunload = function () {
    if (this.persistTimer) clearTimeout(this.persistTimer);
    ['lwf-field-view', 'lwf-reader-view', 'lwf-route-view', 'lwf-index-view'].forEach(function (t) {
      this.app.workspace.detachLeavesOfType(t);
    }, this);
  };

  Class.prototype.getModel = function () {
    if (!this.model) this.model = buildModel(this.app);
    return this.model;
  };

  Class.prototype.activate = function (type) {
    var self = this;
    this.app.workspace.getLeaf(true).setViewState({ type: type, active: true }).then(function () {
      var leaf = self.app.workspace.getMostRecentLeaf();
      if (leaf && leaf.view && leaf.view.onOuterChange) leaf.view.onOuterChange();
      self.refreshAll();
    });
  };

  Class.prototype.refreshAll = function () {
    var self = this;
    this.app.workspace.iterateAllLeaves(function (leaf) {
      var v = leaf.view;
      if (v && typeof v.getViewType === 'function' && /^lwf-/.test(v.getViewType()) && v.onOuterChange) {
        if (v.getViewType() === 'lwf-field-view') v.refresh(false);
        else v.onOuterChange();
      }
    });
  };

  Class.prototype.stepInto = function (id) {
    if (this.activeId === id) {
      var ev = { id: id, label: (this.model.byPath[id] || {}).label || id, source: 'field-click', index: this.routeEvents.length + 1 };
      this.routeEvents.push(ev);
      if (this.routeEvents.length > ROUTE_MAX) this.routeEvents = this.routeEvents.slice(-ROUTE_MAX);
    }
    this.activeId = id;
    this.refreshAll();
  };

  Class.prototype.openReader = function (id) {
    this.activeId = id;
    this.setReaderOpen(true);
    this.activate('lwf-reader-view');
  };

  Class.prototype.focusInField = function (id) {
    this.activeId = id;
    this.activate('lwf-field-view');
  };

  Class.prototype.toggleType = function (t, visible) {
    this.hiddenTypes[t] = !visible;
    this.refreshAll();
  };

  Class.prototype.setReaderOpen = function (open) {
    this.readerOpen = open;
    var main = document.querySelector('.bbf-main');
    if (main) main.classList.toggle('reader-open', open);
  };

  // ── Graph Init ────────────────────────────────────────────────────────────
  Class.prototype.initGraph = function () {
    if (this.svg && this.root) return;
    var self = this;
    var leaf = this.app.workspace.getLeavesOfType('lwf-field-view')[0] || this.app.workspace.getLeaf(true);
    leaf.setViewState({ type: 'lwf-field-view', active: true }).then(function () {
      var view = leaf.view;
      if (view && view.initGraph) view.initGraph();
    });
  };

  // ── Threshold ─────────────────────────────────────────────────────────────
  Class.prototype.showThreshold = function () {
    var self = this;
    var view = this.app.workspace.getActiveViewOfType(FieldView);
    if (!view) return;
    view.showThreshold();
  };

  return Class;
})();

// ── Field View ──────────────────────────────────────────────────────────────
var FieldView = (function () {
  var Class = function (leaf, plugin) {
    obsidian.ItemView.call(this, leaf);
    this.plugin = plugin;
  };
  Class.prototype = Object.create(obsidian.ItemView.prototype);
  Class.prototype.getViewType = function () { return 'lwf-field-view'; };
  Class.prototype.getDisplayText = function () { return 'Field'; };
  Class.prototype.getIcon = function () { return 'net-unplugged'; };

  Class.prototype.onOpen = function () {
    var self = this;
    this.contentEl.addClass('bbf-root');
    this.contentEl.innerHTML = [
      '<div class="bbf-threshold" id="bbfThreshold">',
      '  <div class="bbf-threshold-card">',
      '    <h1>Living Wiki</h1>',
      '    <div class="bbf-sub">Every claim, with the evidence behind it.</div>',
      '    <div class="bbf-th-actions"><button data-enter="map">Open the archive</button></div>',
      '  </div>',
      '</div>',
      '<div class="bbf-app-frame">',
      '  <nav class="bbf-rail">',
      '    <button class="bbf-rail-btn" data-action="field">Map</button>',
      '    <button class="bbf-rail-btn" data-action="view">Filter</button>',
      '    <button class="bbf-rail-btn" data-action="index">List</button>',
      '    <button class="bbf-rail-btn" data-action="about">Guide</button>',
      '  </nav>',
      '  <main class="bbf-main" id="bbfMainLayout">',
      '    <section class="bbf-map-wrap">',
      '      <div class="bbf-map-title"><h1>Living Wiki</h1><div>Evidence map</div></div>',
      '      <div class="bbf-map-tools">',
      '        <button class="bbf-tool-btn" id="bbfFieldBtn">Fit map</button>',
      '        <button class="bbf-tool-btn" data-action="view">Filter</button>',
      '      </div>',
      '      <svg class="bbf-graph-svg" id="bbfGraphSvg"></svg>',
      '      <div class="bbf-field-prompt" id="bbfFieldPrompt"></div>',
      '      <div class="bbf-focus-readout" id="bbfFocusReadout"></div>',
      '    </section>',
      '    <section class="bbf-panel">',
      '      <div class="bbf-route" id="bbfRoute"></div>',
      '      <div class="bbf-reader" id="bbfReader"></div>',
      '    </section>',
      '  </main>',
      '</div>',
      '<aside class="bbf-drawer" id="bbfFieldViewDrawer">',
      '  <div class="bbf-drawer-head"><span>Field View</span><button class="bbf-drawer-close" data-close="bbfFieldViewDrawer">×</button></div>',
      '  <div class="bbf-drawer-body">',
      '    <div class="bbf-section-label">Object groups</div>',
      '    <div id="bbfTypeToggles"></div>',
      '    <div class="bbf-section-label">View</div>',
      '    <div id="bbfViewToggles"></div>',
      '  </div>',
      '  <div class="bbf-drawer-foot">',
      '    <button class="bbf-tool-btn" id="bbfRestoreField">Restore Field</button>',
      '    <button class="bbf-tool-btn" data-close="bbfFieldViewDrawer">Done</button>',
      '  </div>',
      '</aside>',
      '<aside class="bbf-drawer" id="bbfObjectDrawer">',
      '  <div class="bbf-drawer-head"><span>Index</span><button class="bbf-drawer-close" data-close="bbfObjectDrawer">×</button></div>',
      '  <div class="bbf-drawer-body"><input class="bbf-search" id="bbfObjectSearch" placeholder="search objects" /><div id="bbfObjectList"></div></div>',
      '  <div class="bbf-drawer-foot"><button class="bbf-tool-btn" id="bbfShowAll">Show All</button><button class="bbf-tool-btn" data-close="bbfObjectDrawer">Done</button></div>',
      '</aside>',
      '<aside class="bbf-drawer" id="bbfRouteDrawer">',
      '  <div class="bbf-drawer-head"><span>Route</span><button class="bbf-drawer-close" data-close="bbfRouteDrawer">×</button></div>',
      '  <div class="bbf-drawer-body"><div class="bbf-route-list" id="bbfRouteList"></div></div>',
      '  <div class="bbf-drawer-foot"><button class="bbf-tool-btn" id="bbfClearRoute">Clear Route</button><button class="bbf-tool-btn" data-close="bbfRouteDrawer">Done</button></div>',
      '</aside>',
      '<div class="bbf-about-panel" id="bbfAboutPanel">',
      '  <div class="bbf-about-head"><span>How to read this map</span><button class="bbf-about-close" id="bbfAboutClose">×</button></div>',
      '  <nav class="bbf-about-nav">',
      '    <button class="bbf-about-nav-btn" data-about-section="about-statement">Idea</button>',
      '    <span class="bbf-about-nav-sep">·</span>',
      '    <button class="bbf-about-nav-btn" data-about-section="about-how">Controls</button>',
      '    <span class="bbf-about-nav-sep">·</span>',
      '    <button class="bbf-about-nav-btn" data-about-section="about-grammar">Shapes</button>',
      '    <span class="bbf-about-nav-sep">·</span>',
      '    <button class="bbf-about-nav-btn" data-about-section="about-source">Memory</button>',
      '  </nav>',
      '  <div class="bbf-about-body" id="bbfAboutBody">',
      '    <section class="bbf-about-section" id="about-statement">',
      '      <div class="bbf-about-section-label">The idea</div>',
      '      <div class="bbf-prose"><p>Original documents never change. Every claim points back to the passage that supports it. AI suggestions stay <strong>candidates</strong> until a person accepts them. This map is a lens on that archive; it never edits it.</p></div>',
      '    </section>',
      '    <section class="bbf-about-section" id="about-how">',
      '      <div class="bbf-about-section-label">Controls</div>',
      '      <div class="bbf-about-tiles">',
      '        <div class="bbf-about-tile"><div class="bbf-about-tile-key">Map</div><div class="bbf-about-tile-desc">Click a record to read it. Drag to rearrange.</div></div>',
      '        <div class="bbf-about-tile"><div class="bbf-about-tile-key">Filter</div><div class="bbf-about-tile-desc">Hide record kinds you are not working with.</div></div>',
      '        <div class="bbf-about-tile"><div class="bbf-about-tile-key">List</div><div class="bbf-about-tile-desc">Search every record by title or kind.</div></div>',
      '        <div class="bbf-about-tile"><div class="bbf-about-tile-key">Route</div><div class="bbf-about-tile-desc">The trail of records you opened, in order.</div></div>',
      '        <div class="bbf-about-tile span-2"><div class="bbf-about-tile-key">Dashed ring</div><div class="bbf-about-tile-desc">A candidate: suggested, not yet accepted. Open it to see its evidence.</div></div>',
      '      </div>',
      '    </section>',
      '    <section class="bbf-about-section" id="about-grammar">',
      '      <div class="bbf-about-section-label">Shapes</div>',
      '      <div class="bbf-about-grammar-cards">',
      '        <div class="bbf-about-grammar-card"><div class="bbf-about-grammar-abbr">Note</div><div class="bbf-about-grammar-desc">A claim, summary or finding with its evidence.</div></div>',
      '        <div class="bbf-about-grammar-card"><div class="bbf-about-grammar-abbr">Map</div><div class="bbf-about-grammar-desc">A partial overview that groups other records.</div></div>',
      '        <div class="bbf-about-grammar-card"><div class="bbf-about-grammar-abbr">Field</div><div class="bbf-about-grammar-desc">A recurring topic that records gather around.</div></div>',
      '        <div class="bbf-about-grammar-card"><div class="bbf-about-grammar-abbr">Name</div><div class="bbf-about-grammar-desc">A person, place or term, tracked across sources.</div></div>',
      '        <div class="bbf-about-grammar-card"><div class="bbf-about-grammar-abbr">Source</div><div class="bbf-about-grammar-desc">A preserved original document or receipt.</div></div>',
      '        <div class="bbf-about-grammar-card"><div class="bbf-about-grammar-abbr">Relation</div><div class="bbf-about-grammar-desc">A stated link between two records.</div></div>',
      '      </div>',
      '    </section>',
      '    <section class="bbf-about-section" id="about-source">',
      '      <div class="bbf-about-section-label">Map memory</div>',
      '      <div class="bbf-prose"><p>Warm halos mark what you opened recently. Worn paths show what you return to. Everything outside your current neighbourhood softens. All of it is stored in this plugin only, never in the archive.</p></div>',
      '    </section>',
      '  </div>',
      '</div>',
      '<nav class="bbf-bottom-nav">',
      '  <button data-mobile="field">Field</button>',
      '  <button data-mobile="read">Read</button>',
      '  <button data-mobile="view">View</button>',
      '  <button data-mobile="index">Index</button>',
      '</nav>'
    ].join('');

    this.bindEvents();
    this.refresh(true);
  };

  Class.prototype.onClose = function () {
    if (this.sim) this.sim.stop();
  };

  Class.prototype.bindEvents = function () {
    var self = this;
    var root = this.contentEl;

    // Rail buttons
    root.querySelectorAll('.bbf-rail-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var action = btn.dataset.action;
        if (action === 'field') self.returnToField();
        if (action === 'view') self.openDrawer('bbfFieldViewDrawer');
        if (action === 'index') self.openIndex();
        if (action === 'about') self.openAbout();
      });
    });

    // Map tools
    var fieldBtn = root.querySelector('#bbfFieldBtn');
    if (fieldBtn) fieldBtn.addEventListener('click', function () { self.returnToField(); });

    // Drawer close buttons
    root.querySelectorAll('[data-close]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = btn.dataset.close;
        var el = root.querySelector('#' + id);
        if (el) el.classList.remove('open');
      });
    });

    // About close
    var aboutClose = root.querySelector('#bbfAboutClose');
    if (aboutClose) aboutClose.addEventListener('click', function () { self.closeAbout(); });

    // About nav
    root.querySelectorAll('[data-about-section]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = btn.dataset.aboutSection;
        var target = root.querySelector('#' + id);
        if (target) target.scrollIntoView({ behavior: 'smooth' });
      });
    });

    // Threshold enter
    root.querySelectorAll('[data-enter]').forEach(function (btn) {
      btn.addEventListener('click', function () { self.enterField(); });
    });

    // Bottom nav
    root.querySelectorAll('[data-mobile]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var m = btn.dataset.mobile;
        if (m === 'field') self.returnToField();
        if (m === 'read') self.setReaderOpen(true);
        if (m === 'view') self.openDrawer('bbfFieldViewDrawer');
        if (m === 'index') self.openIndex();
      });
    });

    // Restore field
    var restoreBtn = root.querySelector('#bbfRestoreField');
    if (restoreBtn) restoreBtn.addEventListener('click', function () {
      self.plugin.hiddenTypes = {};
      NOTE_TYPES.forEach(function (t) { self.plugin.hiddenTypes[t] = false; });
      self.plugin.objectVisibility = {};
      self.plugin.soloSet = null;
      self.plugin.filters = {}; self.renderFieldViewControls();
      self.updateVisibility();
    });

    // Show all
    var showAllBtn = root.querySelector('#bbfShowAll');
    if (showAllBtn) showAllBtn.addEventListener('click', function () {
      self.plugin.hiddenTypes = {};
      NOTE_TYPES.forEach(function (t) { self.plugin.hiddenTypes[t] = false; });
      self.plugin.objectVisibility = {};
      self.plugin.soloSet = null;
      self.plugin.filters = {}; self.renderFieldViewControls();
      self.updateVisibility();
    });

    // Clear route
    var clearRouteBtn = root.querySelector('#bbfClearRoute');
    if (clearRouteBtn) clearRouteBtn.addEventListener('click', function () {
      self.plugin.routeEvents = [];
      self.renderRoute();
      self.updateVisibility();
    });

    // Object search
    var searchInput = root.querySelector('#bbfObjectSearch');
    if (searchInput) searchInput.addEventListener('input', function () {
      self.renderObjectList(searchInput.value);
    });

    // Resize
    this.plugin.registerDomEvent(window, 'resize', function () { self.onResize(); });
  };

  Class.prototype.initGraph = function () {
    if (this.svg && this.root) return;
    var self = this;
    var svgEl = this.contentEl.querySelector('#bbfGraphSvg');
    if (!svgEl) return;

    this.svg = d3.select(svgEl);
    this.width = svgEl.clientWidth || 800;
    this.height = svgEl.clientHeight || 600;

    this.root = this.svg.append('g');
    this.clearingLayer = this.root.append('g');
    this.baseLayer = this.root.append('g');
    this.projectedLayer = this.root.append('g');
    this.wearLayer = this.root.append('g').attr('pointer-events', 'none');
    this.routeMemoryLayer = this.root.append('g').attr('pointer-events', 'none');
    this.nodeLayer = this.root.append('g');
    this.afterglowLayer = this.root.append('g').attr('pointer-events', 'none');

    this.zoom = d3.zoom().scaleExtent([0.55, 2.4]).on('zoom', function (ev) {
      self.plugin.transform = ev.transform;
      self.root.attr('transform', ev.transform);
      self.updateLabelVisibility();
    });
    this.svg.call(this.zoom).on('dblclick.zoom', null);
    this.svg.on('click', function () {
      if (self.plugin.activeId) self.returnToField();
    });

    this.buildGraph();

    // Initial fit
    this.svg.on('transition.end', function () {
      if (!self.plugin.fitted) {
        self.plugin.fitted = true;
        self.fitVisibleField();
      }
    });

    setTimeout(function () {
      if (!self.plugin.fitted) {
        self.plugin.fitted = true;
        self.fitVisibleField();
      }
    }, 5000);
  };

  Class.prototype.buildGraph = function () {
    var self = this;
    var model = this.plugin.getModel();
    if (this.sim) this.sim.stop();
    var nodes = model.nodes;
    var byId = {};
    nodes.forEach(function (n) { byId[n.id] = n; });

    var baseLinks = model.baseEdges.map(function (e) { return Object.assign({}, e); });
    var projectedLinks = model.projected.map(function (e) { return Object.assign({}, e); });
    var allForceLinks = baseLinks.concat(projectedLinks.map(function (e) {
      return Object.assign({}, e, { forceOnly: true });
    }));

    projectedLinks.forEach(function (e) { e.source = byId[e.source]; e.target = byId[e.target]; });
    this.sim = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(allForceLinks).id(function (d) { return d.id; })
        .distance(function (d) { return (d.kind === 'projected' ? 110 : 92) * (nodes.length < 40 ? 1.7 : 1); })
        .strength(function (d) { return d.kind === 'projected' ? 0.08 : 0.42; }))
      .force('charge', d3.forceManyBody().strength(function (d) {
        return d.type === 'RelO' ? -90 : d.type === 'RefO' ? -150 : -260;
      }))
      .force('collide', d3.forceCollide().radius(function (d) { return nodeMetrics(d).collideR + 18; }))
      .force('cluster', function (alpha) {
        nodes.forEach(function (d) {
          var c = [self.width / 2, self.height / 2];
          d.vx += (c[0] - d.x) * 0.035 * alpha;
          d.vy += (c[1] - d.y) * 0.035 * alpha;
        });
      });

    // Base edges
    this.baseSel = this.baseLayer.selectAll('line').data(baseLinks).join('line')
      .attr('class', 'bbf-link-base')
      .attr('stroke', 'var(--bbf-edge)')
      .attr('stroke-opacity', 0.55)
      .attr('stroke-width', 1);

    // Projected edges
    this.projSel = this.projectedLayer.selectAll('line').data(projectedLinks).join('line')
      .attr('class', 'bbf-link-proj')
      .attr('stroke', 'var(--bbf-edge-projected)')
      .attr('stroke-opacity', 0.35)
      .attr('stroke-width', function (d) { return Math.min(3, 0.55 + d.relos.length * 0.32); });

    // Projected hit areas
    this.projHitSel = this.projectedLayer.selectAll('line.hit').data(projectedLinks).join('line')
      .attr('class', 'hit')
      .attr('stroke', 'transparent')
      .attr('stroke-width', 16)
      .attr('pointer-events', 'stroke');

    // Wear layer
    this.wearSel = this.wearLayer.selectAll('line').data(baseLinks).join('line')
      .attr('class', 'bbf-wear')
      .attr('stroke-linecap', 'round')
      .attr('pointer-events', 'none')
      .attr('stroke-opacity', 0);

    // Nodes
    this.nodeSel = this.nodeLayer.selectAll('g.node').data(nodes).join('g')
      .attr('class', function (d) { return 'node ' + d.type; })
      .call(d3.drag()
        .on('start', function (ev, d) {
          if (!ev.active) self.sim.alphaTarget(0.25).restart();
          d.fx = d.x; d.fy = d.y;
        })
        .on('drag', function (ev, d) { d.fx = ev.x; d.fy = ev.y; })
        .on('end', function (ev, d) {
          if (!ev.active) self.sim.alphaTarget(0);
          d.fx = null; d.fy = null;
        }));

    this.nodeSel.each(function (d) {
      var g = d3.select(this); g.selectAll("*").remove();
      var m = nodeMetrics(d);
      g.append('circle').attr('class', 'bbf-node-route-halo').attr('r', m.haloR).attr('fill', 'none').attr('stroke', 'transparent').attr('stroke-width', 1);
      g.append('circle').attr('class', 'bbf-node-focus-ring').attr('r', m.focusR).attr('fill', 'none').attr('stroke', 'transparent').attr('stroke-width', 1.5);
      if (d.type === 'RNO') {
        g.append('circle').attr('class', 'bbf-rno-ring').attr('r', 10.4).attr('fill', 'none').attr('stroke', 'var(--bbf-rno-ring)').attr('stroke-width', 1.2);
        g.append('circle').attr('class', 'bbf-node-core').attr('r', 6.2).attr('fill', 'var(--bbf-node-fill)');
      } else if (d.type === 'MNO') {
        g.append('path').attr('class', 'bbf-node-core').attr('d', irregularCirclePath(d.id, 6.8, 14)).attr('fill', 'var(--bbf-node-fill)');
      } else if (d.type === 'NameO') {
        // text-only
      } else if (d.type === 'RefO') {
        g.append('rect').attr('class', 'bbf-node-core').attr('width', 8).attr('height', 8).attr('x', -4).attr('y', -4).attr('transform', 'rotate(45)').attr('fill', 'var(--bbf-refo-fill)');
      } else if (d.type === 'RelO') {
        g.append('circle').attr('class', 'bbf-node-core').attr('r', 7.5).attr('fill', 'none').attr('stroke', 'var(--bbf-relo-stroke)').attr('stroke-width', 1.3);
      } else {
        g.append('circle').attr('class', 'bbf-node-core').attr('r', 6.2).attr('fill', 'var(--bbf-node-fill)');
      }
      g.append('circle').attr('class', 'bbf-node-hit').attr('r', m.hitR);
    });

    // Labels
    this.nodeSel.append('text')
      .attr('class', 'bbf-node-label')
      .attr('text-anchor', 'middle')
      .attr('y', function (d) { return nodeMetrics(d).labelOffset; })
      .text(function (d) { var t = String(d.shortLabel || d.label).replace(/^\[C\]\s*/, '').replace(/^Candidate( claim)?:\s*/i, ''); return t.length > 26 ? t.slice(0, 25) + '…' : t; });

    this.nodeSel.append('title').text(function (d) { return d.label; });

    // Node events
    this.nodeSel
      .attr('tabindex', 0)
      .attr('role', 'button')
      .attr('aria-label', function (d) { return typeLabel(d.type) + ': ' + d.label; })
      .on('mouseenter', function (ev, d) {
        if (isMobile()) return;
        clearTimeout(self.plugin.previewTimer);
        self.plugin.previewTimer = setTimeout(function () { self.touchObject(d.id, { source: 'graph-hover' }); }, 200);
      })
      .on('mouseleave', function () {
        if (isMobile()) return;
        clearTimeout(self.plugin.previewTimer);
        self.clearTouch();
      })
      .on('click', function (ev, d) {
        ev.stopPropagation();
        self.clearTouch();
        if (isMobile()) return self.selectInField(d.id);
        self.focusObject(d.id, { source: 'graph' });
      })
      .on('keydown', function (ev, d) {
        if (ev.key === 'Enter' || ev.key === ' ') {
          ev.preventDefault();
          self.focusObject(d.id, { source: 'keyboard' });
        }
        if (ev.key === 'Escape') {
          self.clearTouch();
          self.closeAllDrawers();
        }
      });

    // Edge events
    this.projSel
      .on('mouseenter', function (ev, d) { if (!isMobile()) self.showEdgePreview(d, ev); })
      .on('mouseleave', function () { if (!isMobile()) self.hidePreview(); });

    this.projHitSel
      .on('mouseenter', function (ev, d) { if (!isMobile()) self.showEdgePreview(d, ev); })
      .on('mouseleave', function () { if (!isMobile()) self.hidePreview(); })
      .on('click', function (ev, d) {
        ev.stopPropagation();
        self.openProjectedEdge(d);
      });

    this.sim.on('tick', function () { self.updateGraphGeometry(); });

    this.updateVisibility();
    this.renderRoute();
    this.renderFieldViewControls();
  };

  Class.prototype.updateGraphGeometry = function () {
    var self = this;
    function applyLine(sel) {
      sel.each(function (d) {
        var s = d.source, t = d.target;
        var x1 = s.x + (s.apDx || 0), y1 = s.y + (s.apDy || 0);
        var x2 = t.x + (t.apDx || 0), y2 = t.y + (t.apDy || 0);
        if (isFinite(x1) && isFinite(y1) && isFinite(x2) && isFinite(y2)) {
          d3.select(this).attr('x1', x1).attr('y1', y1).attr('x2', x2).attr('y2', y2);
        }
      });
    }
    applyLine(this.baseSel);
    applyLine(this.projSel);
    applyLine(this.projHitSel);
    applyLine(this.wearSel);

    this.nodeSel.each(function (d) {
      var x = d.x + (d.apDx || 0), y = d.y + (d.apDy || 0);
      if (isFinite(x) && isFinite(y)) d3.select(this).attr('transform', 'translate(' + x + ',' + y + ')');
    });

    // Route memory
    this.routeMemoryLayer.selectAll('line.route-segment').each(function (d) {
      var x1 = d.source.x, y1 = d.source.y, x2 = d.target.x, y2 = d.target.y;
      if (isFinite(x1) && isFinite(y1) && isFinite(x2) && isFinite(y2)) {
        d3.select(this).attr('x1', x1).attr('y1', y1).attr('x2', x2).attr('y2', y2);
      }
    });

    // Clearing
    this.clearingLayer.selectAll('circle.bbf-clearing').each(function (d) {
      var x = d.node.x + (d.node.apDx || 0), y = d.node.y + (d.node.apDy || 0);
      if (isFinite(x) && isFinite(y)) d3.select(this).attr('cx', x).attr('cy', y);
    });
    this.clearingLayer.selectAll('line.bbf-clearing-spoke').each(function (d) {
      var x1 = d.source.x + (d.source.apDx || 0), y1 = d.source.y + (d.source.apDy || 0);
      var x2 = d.target.x + (d.target.apDx || 0), y2 = d.target.y + (d.target.apDy || 0);
      if (isFinite(x1) && isFinite(y1) && isFinite(x2) && isFinite(y2)) {
        d3.select(this).attr('x1', x1).attr('y1', y1).attr('x2', x2).attr('y2', y2);
      }
    });

    // Afterglow
    this.afterglowLayer.selectAll('circle.bbf-afterglow').each(function (d) {
      var x = d.node.x + (d.node.apDx || 0), y = d.node.y + (d.node.apDy || 0);
      if (isFinite(x) && isFinite(y)) d3.select(this).attr('cx', x).attr('cy', y);
    });

    if (this.plugin.activeId) {
      var n = this.plugin.model.byPath[this.plugin.activeId];
      if (n) this.positionReadout(n);
    }
  };

  // ── Visibility ────────────────────────────────────────────────────────────
  Class.prototype.nodeVisible = function (id) {
    var model = this.plugin.getModel();
    var n = model.byPath[id];
    if (!n) return false;
    if (this.plugin.soloSet) return this.plugin.soloSet.has(id);
    if (this.plugin.objectVisibility[id] === false) return false;
    return !this.plugin.hiddenTypes[n.type];
  };

  Class.prototype.edgeVisible = function (e) {
    var s = e.source.id || e.source, t = e.target.id || e.target;
    return this.nodeVisible(s) && this.nodeVisible(t);
  };

  Class.prototype.projectedVisible = function (e) {
    var a = e.source.id || e.source, b = e.target.id || e.target;
    return this.nodeVisible(a) && this.nodeVisible(b);
  };

  Class.prototype.updateLabelVisibility = function () {
    var self = this;
    var k = this.plugin.transform ? this.plugin.transform.k : 1;
    var focus = this.plugin.activeId ? buildFocusSet(this.plugin.app, this.plugin.getModel(), this.plugin.activeId) : null;
    var focusIds = focus ? new Set(focus.ids) : null;

    this.nodeSel.selectAll('text.bbf-node-label')
      .style('font-size', Math.max(10, Math.min(13, 13 / Math.max(1, k))) + 'px')
      .attr('display', function (d) {
        if (!self.nodeVisible(d.id)) return 'none';
        if (d.id === self.plugin.activeId) return null;
        if (focusIds && focusIds.has(d.id)) return null;
        if (d.candidate) return null;
        if (d.type === 'RefO' || d.type === 'RelO') return k < 1.6 ? 'none' : null;
        return k < 1.2 ? 'none' : null;
      })
      .classed('quiet', function (d) { return d.type === 'NameO' || d.type === 'RefO'; });
  };

  Class.prototype.updateVisibility = function () {
    var self = this;
    this.nodeSel.attr('display', function (d) { return self.nodeVisible(d.id) ? null : 'none'; });
    this.baseSel.attr('display', function (d) { return self.edgeVisible(d) ? null : 'none'; });
    this.projSel.attr('display', function (d) { return self.projectedVisible(d) ? null : 'none'; });
    this.projHitSel.attr('display', function (d) { return self.projectedVisible(d) ? null : 'none'; });

    if (!this.plugin.activeId) {
      this.transitionToFieldLighting({ duration: 0 });
    } else {
      this.presentFocus(this.plugin.activeId, buildFocusSet(this.plugin.app, this.plugin.getModel(), this.plugin.activeId), { lightDuration: 0 });
    }
    this.updateLabelVisibility();
    this.updateWearOverlay();
    this.drawRouteMemory({ duration: 0 });
  };

  // ── Camera ────────────────────────────────────────────────────────────────
  Class.prototype.animateCamera = function (transform, opts) {
    var self = this;
    var dur = prefersReducedMotion() ? 0 : (opts && opts.duration !== undefined ? opts.duration : 760);
    this.plugin.cameraInFlight = true;
    this.svg.transition().duration(dur).ease(d3.easeCubicInOut)
      .call(this.zoom.transform, transform)
      .on('end', function () { self.plugin.cameraInFlight = false; });
  };

  Class.prototype.getNodeBounds = function (items, padNode) {
    padNode = padNode || 34;
    var minX = d3.min(items, function (d) { return (d.x + (d.apDx || 0)) - padNode; });
    var maxX = d3.max(items, function (d) { return (d.x + (d.apDx || 0)) + padNode; });
    var minY = d3.min(items, function (d) { return (d.y + (d.apDy || 0)) - padNode; });
    var maxY = d3.max(items, function (d) { return (d.y + (d.apDy || 0)) + padNode; });
    return { minX: minX, maxX: maxX, minY: minY, maxY: maxY, width: Math.max(1, maxX - minX), height: Math.max(1, maxY - minY), cx: (minX + maxX) / 2, cy: (minY + maxY) / 2 };
  };

  Class.prototype.fitFocusFrame = function (focus, opts) {
    var self = this;
    opts = opts || {};
    var visible = focus.ids.map(function (id) { return self.plugin.model.byPath[id]; })
      .filter(function (d) { return d && d.x != null && d.y != null && self.nodeVisible(d.id); });
    if (!visible.length || this.width < 10 || this.height < 10) return;
    var bounds = this.getNodeBounds(visible, isMobile() ? 42 : 56);
    var padX = opts.padX !== undefined ? opts.padX : (isMobile() ? 42 : 72);
    var padY = opts.padY !== undefined ? opts.padY : (isMobile() ? 44 : 72);
    var usableW = Math.max(1, this.width - padX * 2);
    var usableH = Math.max(1, this.height - padY * 2);
    var k = Math.min(usableW / bounds.width, usableH / bounds.height);
    k = Math.max(isMobile() ? 0.62 : 0.72, Math.min(isMobile() ? 1.55 : 1.35, k));
    var biasX = isMobile() ? 0.50 : (window.innerWidth < 1100 ? 0.50 : 0.48);
    var biasY = isMobile() ? 0.48 : 0.56;
    var tx = this.width * biasX - k * bounds.cx;
    var ty = this.height * biasY - k * bounds.cy;
    this.animateCamera(d3.zoomIdentity.translate(tx, ty).scale(k), { duration: opts.duration !== undefined ? opts.duration : 760 });
  };

  Class.prototype.fitVisibleField = function (opts) {
    var self = this;
    opts = opts || {};
    var model = this.plugin.getModel();
    var visible = model.nodes.filter(function (d) { return self.nodeVisible(d.id); });
    if (!visible.length || this.width < 10 || this.height < 10) return;
    var bounds = this.getNodeBounds(visible, isMobile() ? 44 : 88);
    var pad = isMobile() ? 44 : 88;
    var k = Math.max(0.55, Math.min((this.width - pad * 2) / bounds.width, (this.height - pad * 2) / bounds.height, isMobile() ? 0.92 : 1.7));
    var cy = this.height / 2;
    var tx = this.width / 2 - k * bounds.cx;
    var ty = cy - k * bounds.cy;
    this.animateCamera(d3.zoomIdentity.translate(tx, ty).scale(k), { duration: opts.duration !== undefined ? opts.duration : 850 });
  };

  // ── Focus ─────────────────────────────────────────────────────────────────
  Class.prototype.focusObject = function (id, opts) {
    var self = this;
    opts = opts || {};
    this.plugin.activeId = id;
    var focus = buildFocusSet(this.plugin.app, this.plugin.getModel(), id);
    if (!focus) return;

    this.applyLocalAperture(focus);
    this.presentFocus(id, focus, { lightDuration: opts.lightDuration !== undefined ? opts.lightDuration : 520 });
    this.updateFocusRing(id);
    this.updateLabelVisibility();
    this.updateWearOverlay();
    this.drawRouteMemory({ duration: 0 });
    this.renderRoute();
    this.renderReader(id);
    this.positionReadout(this.plugin.model.byPath[id]);

    if (!isMobile() && opts.openReader !== false) {
      this.plugin.setReaderOpen(true);
    }

    if (opts.camera !== false) {
      this.fitFocusFrame(focus, { duration: opts.cameraDuration !== undefined ? opts.cameraDuration : 680 });
    }
  };

  Class.prototype.returnToField = function () {
    this.plugin.activeId = null;
    this.clearLocalAperture();
    this.transitionToFieldLighting({ duration: 0 });
    this.updateFocusRing(null);
    this.updateLabelVisibility();
    this.updateWearOverlay();
    this.drawRouteMemory({ duration: 0 });
    this.renderRoute();
    this.renderReader('');
    this.hideReadout();
    this.fitVisibleField({ duration: 0 });
  };

  Class.prototype.selectInField = function (id) {
    this.plugin.activeId = id;
    var focus = buildFocusSet(this.plugin.app, this.plugin.getModel(), id);
    if (focus) {
      this.applyLocalAperture(focus);
      this.presentFocus(id, focus, { lightDuration: 180 });
    }
    this.updateFocusRing(id);
    this.updateLabelVisibility();
    this.updateWearOverlay();
    this.drawRouteMemory({ duration: 0 });
    this.renderRoute();
    this.renderReader(id);
  };

  // ── Aperture ──────────────────────────────────────────────────────────────
  Class.prototype.clearLocalAperture = function () {
    var model = this.plugin.getModel();
    model.nodes.forEach(function (d) { d.apDx = 0; d.apDy = 0; });
    this.updateGraphGeometry();
  };

  Class.prototype.applyLocalAperture = function (focus) {
    var self = this;
    this.clearLocalAperture();
    if (!focus || !focus.coreId) return;
    var model = this.plugin.getModel();
    var core = model.byPath[focus.coreId];
    if (!core || core.x == null || core.y == null) return;
    var neighbors = focus.neighborIds.map(function (id) { return model.byPath[id]; })
      .filter(function (d) { return d && self.nodeVisible(d.id) && d.x != null && d.y != null; });
    if (neighbors.length < 4) { this.updateGraphGeometry(); return; }

    var near = neighbors.map(function (d) {
      return { d: d, dist: Math.hypot(d.x - core.x, d.y - core.y), ang: Math.atan2(d.y - core.y, d.x - core.x) };
    }).sort(function (a, b) { return a.ang - b.ang; }).slice(0, 14);

    var radiusA = isMobile() ? 54 : 62;
    var radiusB = isMobile() ? 82 : 92;
    var targets = near.map(function (item, i) {
      var r = i < 8 ? radiusA : radiusB;
      var angle = item.ang || (Math.PI * 2 * i / near.length);
      return { item: item, x: core.x + Math.cos(angle) * r, y: core.y + Math.sin(angle) * r };
    });

    var minSep = 40;
    for (var pass = 0; pass < 3; pass++) {
      for (var i = 0; i < targets.length; i++) {
        for (var j = i + 1; j < targets.length; j++) {
          var a = targets[i], b = targets[j];
          var dx = b.x - a.x, dy = b.y - a.y;
          var dist = Math.hypot(dx, dy);
          if (dist >= minSep) continue;
          if (dist < 1e-6) { dx = 1; dy = 0; dist = 1; }
          var push = (minSep - dist) / 2;
          var ux = dx / dist, uy = dy / dist;
          a.x -= ux * push; a.y -= uy * push;
          b.x += ux * push; b.y += uy * push;
        }
      }
    }

    targets.forEach(function (t) {
      var maxShift = isMobile() ? 56 : 74;
      var dx = t.x - t.item.d.x, dy = t.y - t.item.d.y;
      var mag = Math.hypot(dx, dy);
      if (mag > maxShift) { dx = dx / mag * maxShift; dy = dy / mag * maxShift; }
      t.item.d.apDx = dx;
      t.item.d.apDy = dy;
    });

    this.updateGraphGeometry();
  };

  // ── Lighting ──────────────────────────────────────────────────────────────
  Class.prototype.updateFocusRing = function (coreId) {
    var self = this;
    this.nodeSel.select('.bbf-node-focus-ring')
      .transition().duration(prefersReducedMotion() ? 0 : 420)
      .attr('stroke', function (d) { return d.id === coreId ? 'var(--bbf-focus)' : 'transparent'; })
      .attr('stroke-opacity', function (d) { return d.id === coreId ? 0.82 : 0; })
      .attr('stroke-width', function (d) { return d.id === coreId ? 1.35 : 1; });
  };

  Class.prototype.updateBodyBlur = function (mode) {
    var enable = !isMobile() && !prefersReducedMotion() && mode !== 'field';
    this.plugin.appliedBlurPx = enable ? 0.6 : 0;
    this.nodeSel.selectAll('.bbf-node-core, .bbf-rno-ring')
      .classed('bbf-cold-rest', function () {
        if (!enable) return false;
        var parent = this.parentNode;
        return parent && parent.getAttribute('data-bb-light') === 'cold-rest';
      });
  };

  Class.prototype.setNodeLightAttrs = function (focus, mode) {
    var self = this;
    var memberIds = mode === 'clearing' ? new Set([focus.coreId].concat(this.clearingMemberIdsFor(focus.coreId))) : new Set(focus.ids);
    this.nodeSel.each(function (d) {
      var isMember = memberIds.has(d.id);
      var isCore = d.id === focus.coreId;
      var light = isCore ? 'warm' : isMember ? 'warm' : 'cold-rest';
      d3.select(this).attr('data-bb-light', light);
    });
    this.updateBodyBlur(mode);
  };

  Class.prototype.presentFocus = function (id, focus, opts) {
    var self = this;
    opts = opts || {};
    this.currentLightMode = 'focus';
    this.setNodeLightAttrs(focus, 'focus');
    this.updateFocusRing(id);
    this.updateLabelVisibility();
  };

  Class.prototype.transitionToFieldLighting = function (opts) {
    var self = this;
    opts = opts || {};
    this.currentLightMode = 'field';
    this.nodeSel.each(function (d) {
      d3.select(this).attr('data-bb-light', 'field');
    });
    this.updateBodyBlur('field');
  };

  // ── Wear ──────────────────────────────────────────────────────────────────
  Class.prototype.updateWearOverlay = function () {
    var self = this;
    var wear = this.plugin.fieldTrace.wear;
    this.wearSel
      .attr('stroke', 'var(--bbf-focus)')
      .attr('stroke-width', function (d) {
        var key = d.source.id < d.target.id ? d.source.id + '::' + d.target.id : d.target.id + '::' + d.source.id;
        var count = wear[key] || 0;
        return Math.min(4, 0.5 + count * 0.3);
      })
      .attr('stroke-opacity', function (d) {
        var key = d.source.id < d.target.id ? d.source.id + '::' + d.target.id : d.target.id + '::' + d.source.id;
        var count = wear[key] || 0;
        return Math.min(0.6, count * 0.12);
      });
  };

  // ── Route Memory ──────────────────────────────────────────────────────────
  Class.prototype.drawRouteMemory = function (opts) {
    var self = this;
    opts = opts || {};
    var events = this.plugin.routeEvents;
    if (events.length < 2) {
      this.routeMemoryLayer.selectAll('line.route-segment').remove();
      return;
    }
    var segments = [];
    for (var i = 0; i < events.length - 1; i++) {
      var a = this.plugin.model.byPath[events[i].id];
      var b = this.plugin.model.byPath[events[i + 1].id];
      if (a && b) segments.push({ source: a, target: b });
    }
    this.routeMemoryLayer.selectAll('line.route-segment').data(segments).join('line')
      .attr('class', 'route-segment')
      .attr('stroke', 'var(--bbf-focus)')
      .attr('stroke-opacity', 0.35)
      .attr('stroke-width', 1.5)
      .attr('stroke-dasharray', '4,3');
  };

  // ── Clearing ──────────────────────────────────────────────────────────────
  Class.prototype.clearingMemberIdsFor = function (relOId) {
    var model = this.plugin.getModel();
    return (model.relations[relOId] || []).filter(function (id) { return self.nodeVisible(id); });
  };

  Class.prototype.updateClearing = function () {
    var self = this;
    var activeId = this.plugin.activeId;
    if (!activeId) {
      this.clearingLayer.selectAll('*').remove();
      return;
    }
    var model = this.plugin.getModel();
    var node = model.byPath[activeId];
    if (!node || node.type !== 'RelO') {
      this.clearingLayer.selectAll('*').remove();
      return;
    }
    var members = this.clearingMemberIdsFor(activeId);
    var allPts = [node].concat(members.map(function (id) { return model.byPath[id]; }).filter(Boolean));

    this.clearingLayer.selectAll('*').remove();
    var clearing = this.clearingLayer.selectAll('circle.bbf-clearing').data(allPts).join('circle')
      .attr('class', 'bbf-clearing')
      .attr('r', 20)
      .attr('fill', 'var(--bbf-clearing-fill)')
      .attr('pointer-events', 'none');

    var spokes = [];
    members.forEach(function (mid) {
      var m = model.byPath[mid];
      if (m) spokes.push({ source: node, target: m });
    });
    this.clearingLayer.selectAll('line.bbf-clearing-spoke').data(spokes).join('line')
      .attr('class', 'bbf-clearing-spoke')
      .attr('stroke', 'var(--bbf-clearing-member)')
      .attr('stroke-opacity', 0.3)
      .attr('stroke-width', 1)
      .attr('pointer-events', 'none');
  };

  // ── Micro Preview ─────────────────────────────────────────────────────────
  Class.prototype.touchObject = function (id, opts) {
    var self = this;
    var model = this.plugin.getModel();
    var n = model.byPath[id];
    if (!n) return;
    var readout = this.contentEl.querySelector('#bbfFocusReadout');
    if (!readout) return;
    readout.style.display = 'block';
    readout.innerHTML = '<div class="bbf-focus-readout-id">' + esc(n.id) + '</div>' +
      '<div class="bbf-focus-readout-type">' + esc(n.type) + '</div>' +
      '<div class="bbf-focus-readout-line">' + esc(n.label) + '</div>';
    var svgEl = this.contentEl.querySelector('#bbfGraphSvg');
    if (svgEl && n.x != null) {
      var rect = svgEl.getBoundingClientRect();
      var x = n.x + (n.apDx || 0) + 20;
      var y = n.y + (n.apDy || 0) - 10;
      readout.style.left = x + 'px';
      readout.style.top = y + 'px';
    }
  };

  Class.prototype.clearTouch = function () {
    var readout = this.contentEl.querySelector('#bbfFocusReadout');
    if (readout) readout.style.display = 'none';
  };

  Class.prototype.showEdgePreview = function (d, ev) {
    // Simplified edge preview
  };

  Class.prototype.hidePreview = function () {
    // Simplified
  };

  Class.prototype.openProjectedEdge = function (d) {
    // Simplified: focus source
    var s = d.source.id || d.source;
    this.focusObject(s, { source: 'projected-edge' });
  };

  Class.prototype.positionReadout = function (n) {
    var readout = this.contentEl.querySelector('#bbfFocusReadout');
    if (!readout || !n) return;
    var svgEl = this.contentEl.querySelector('#bbfGraphSvg');
    if (svgEl && n.x != null) {
      var x = n.x + (n.apDx || 0) + 20;
      var y = n.y + (n.apDy || 0) - 10;
      readout.style.left = x + 'px';
      readout.style.top = y + 'px';
    }
  };

  Class.prototype.hideReadout = function () {
    var readout = this.contentEl.querySelector('#bbfFocusReadout');
    if (readout) readout.style.display = 'none';
  };

  // ── Route ─────────────────────────────────────────────────────────────────
  Class.prototype.renderRoute = function () {
    var self = this;
    var routeEl = this.contentEl.querySelector('#bbfRoute');
    if (!routeEl) return;
    routeEl.innerHTML = '';
    if (!this.plugin.routeEvents.length) {
      routeEl.innerHTML = '<span class="bbf-route-empty">No route yet</span>';
      return;
    }
    var events = this.plugin.routeEvents.slice(-ROUTE_VISIBLE_MAX);
    events.forEach(function (ev, i) {
      if (i > 0) {
        var sep = document.createElement('span');
        sep.className = 'bbf-sep';
        sep.textContent = '→';
        routeEl.appendChild(sep);
      }
      var item = document.createElement('button');
      item.className = 'bbf-route-item' + (i === events.length - 1 ? ' current' : '');
      item.title = ev.label;
      item.textContent = ev.label || ev.id;
      item.addEventListener('click', function () { self.plugin.openReader(ev.id); });
      routeEl.appendChild(item);
    });
    var clearBtn = document.createElement('button');
    clearBtn.className = 'bbf-clear-route';
    clearBtn.textContent = 'Clear Route';
    clearBtn.addEventListener('click', function () {
      self.plugin.routeEvents = [];
      self.renderRoute();
      self.updateVisibility();
    });
    routeEl.appendChild(clearBtn);
  };

  // ── Reader ────────────────────────────────────────────────────────────────
  Class.prototype.renderReader = function (id) {
    var self = this;
    var readerEl = this.contentEl.querySelector('#bbfReader');
    if (!readerEl) return;
    readerEl.innerHTML = '';
    if (!id) {
      readerEl.innerHTML = '<div class="bbf-meta">READER</div><div class="bbf-prose"><p>Select an object in the field to read it here.</p></div>';
      return;
    }
    var model = this.plugin.getModel();
    var nd = model.byPath[id];
    if (!nd) {
      readerEl.innerHTML = '<div class="bbf-empty">Object not found.</div>';
      return;
    }
    var meta = document.createElement('div');
    meta.className = 'bbf-meta';
    meta.textContent = typeLabel(nd.type) + ' · ' + nd.id;
    readerEl.appendChild(meta);

    var title = document.createElement('div');
    title.className = 'bbf-title';
    title.textContent = nd.label;
    readerEl.appendChild(title);

    var target = this.plugin.app.vault.getAbstractFileByPath(nd.id);
    if (target instanceof obsidian.TFile) {
      this.plugin.app.vault.cachedRead(target).then(function (text) {
        var prose = document.createElement('div');
        prose.className = 'bbf-prose';
        obsidian.MarkdownRenderer.render(self.plugin.app, text, prose, target.path, self.plugin);
        readerEl.appendChild(prose);
      });
    }
  };

  // ── Drawers ───────────────────────────────────────────────────────────────
  Class.prototype.openDrawer = function (id) {
    var el = this.contentEl.querySelector('#' + id);
    if (el) el.classList.add('open');
  };

  Class.prototype.closeAllDrawers = function () {
    this.contentEl.querySelectorAll('.bbf-drawer').forEach(function (d) {
      d.classList.remove('open');
    });
  };

  Class.prototype.openIndex = function () {
    this.closeAllDrawers();
    this.openDrawer('bbfObjectDrawer');
    this.renderObjectList('');
  };

  Class.prototype.renderObjectList = function (query) {
    var self = this;
    var listEl = this.contentEl.querySelector('#bbfObjectList');
    if (!listEl) return;
    listEl.innerHTML = '';
    query = (query || '').toLowerCase();
    var model = this.plugin.getModel();
    var n = 0;
    model.nodes.forEach(function (nd) {
      if (n >= 300) return;
      if (query && nd.label.toLowerCase().indexOf(query) === -1 && typeLabel(nd.type).toLowerCase().indexOf(query) === -1) return;
      n++;
      var row = document.createElement('div');
      row.className = 'bbf-object-row';
      var otype = document.createElement('span');
      otype.className = 'bbf-otype';
      otype.textContent = typeLabel(nd.type);
      row.appendChild(otype);
      var label = document.createElement('span');
      label.className = 'bbf-olabel';
      label.textContent = nd.label;
      label.addEventListener('click', function () { self.plugin.openReader(nd.id); });
      row.appendChild(label);
      listEl.appendChild(row);
    });
    if (!n) listEl.innerHTML = '<div class="bbf-empty">No objects match.</div>';
  };

  Class.prototype.renderFieldViewControls = function () {
    var self = this;
    var typeToggles = this.contentEl.querySelector('#bbfTypeToggles');
    if (!typeToggles) return;
    typeToggles.innerHTML = '';
    NOTE_TYPES.forEach(function (t) {
      var row = document.createElement('div');
      row.className = 'bbf-toggle-row';
      var label = document.createElement('span');
      label.textContent = typeLabel(t);
      row.appendChild(label);
      var sw = document.createElement('div');
      sw.className = 'bbf-switch' + (!self.plugin.hiddenTypes[t] ? ' on' : '');
      sw.addEventListener('click', function () {
        self.plugin.toggleType(t, self.plugin.hiddenTypes[t]);
        sw.classList.toggle('on');
      });
      row.appendChild(sw);
      typeToggles.appendChild(row);
    });
  };

  // ── About ─────────────────────────────────────────────────────────────────
  Class.prototype.openAbout = function () {
    var panel = this.contentEl.querySelector('#bbfAboutPanel');
    if (panel) panel.classList.add('open');
  };

  Class.prototype.closeAbout = function () {
    var panel = this.contentEl.querySelector('#bbfAboutPanel');
    if (panel) panel.classList.remove('open');
  };

  // ── Threshold ─────────────────────────────────────────────────────────────
  Class.prototype.showThreshold = function () {
    var th = this.contentEl.querySelector('#bbfThreshold');
    if (th) {
      th.classList.remove('leaving');
      var card = th.querySelector('.bbf-threshold-card');
      if (card) {
        setTimeout(function () { card.style.opacity = '1'; }, 1600);
      }
    }
  };

  Class.prototype.enterField = function () {
    var self = this;
    var th = this.contentEl.querySelector('#bbfThreshold');
    if (th) {
      th.classList.add('leaving');
      setTimeout(function () { th.style.display = 'none'; }, 520);
    }
    this.plugin.setReaderOpen(true);
    this.fitVisibleField({ duration: 0 });
    this.startTacitOnboarding();
  };

  // ── Onboarding ────────────────────────────────────────────────────────────
  Class.prototype.startTacitOnboarding = function () {
    var self = this;
    this.plugin.onboardingActive = true;
    var stages = [
      { text: 'Start anywhere on the map.', groups: NOTE_TYPES, projected: false },
      { text: 'Each record keeps its sources, names and relations.', groups: NOTE_TYPES, projected: true },
      { text: 'Your route is kept as you read.', groups: NOTE_TYPES, projected: true }
    ];
    var stageIdx = 0;

    function showStage() {
      if (!self.plugin.onboardingActive) return;
      if (stageIdx >= stages.length) return finishOnboarding();
      var stage = stages[stageIdx];
      var prompt = self.contentEl.querySelector('#bbfFieldPrompt');
      if (prompt) {
        prompt.textContent = stage.text;
        prompt.classList.add('visible');
      }
      var hold = prefersReducedMotion() ? 400 : 2600;
      setTimeout(function () {
        if (prompt) prompt.classList.remove('visible');
        stageIdx++;
        setTimeout(showStage, prefersReducedMotion() ? 0 : 520);
      }, hold);
    }

    function finishOnboarding() {
      self.plugin.onboardingActive = false;
      var prompt = self.contentEl.querySelector('#bbfFieldPrompt');
      if (prompt) prompt.classList.remove('visible');
    }

    showStage();
  };

  // ── Refresh ───────────────────────────────────────────────────────────────
  Class.prototype.refresh = function (relayout) {
    if (this.svg) {
      this.buildGraph();
    }
  };

  Class.prototype.onResize = function () {
    var svgEl = this.contentEl.querySelector('#bbfGraphSvg');
    if (svgEl) {
      this.width = svgEl.clientWidth || 800;
      this.height = svgEl.clientHeight || 600;
      if (this.sim) {
        this.sim.force('center', d3.forceCenter(this.width / 2, this.height / 2));
        this.sim.alpha(0.08).restart();
      }
    }
  };

  Class.prototype.onOuterChange = function () {
    if (this.svg) this.buildGraph();
  };

  return Class;
})();

// ── Reader View ─────────────────────────────────────────────────────────────
var ReaderView = (function () {
  var Class = function (leaf, plugin) { obsidian.ItemView.call(this, leaf); this.plugin = plugin; };
  Class.prototype = Object.create(obsidian.ItemView.prototype);
  Class.prototype.getViewType = function () { return 'lwf-reader-view'; };
  Class.prototype.getDisplayText = function () { return 'Reader'; };
  Class.prototype.getIcon = function () { return 'book-open'; };

  Class.prototype.onOpen = function () {
    this.contentEl.addClass('bbf-root', 'bbf-pane');
    this.body = this.contentEl.createEl('div', { cls: 'bbf-reader' });
    this.refresh();
  };
  Class.prototype.onOuterChange = function () { this.refresh(); };
  Class.prototype.refresh = function () {
    var self = this, el = this.body, plugin = this.plugin;
    el.empty();
    if (!plugin.activeId) {
      el.createEl('div', { cls: 'bbf-empty', text: 'Select a node in Field to read it here.' });
      return;
    }
    var nd = plugin.model.byPath[plugin.activeId];
    if (!nd) {
      el.createEl('div', { cls: 'bbf-empty', text: 'Object not found.' });
      return;
    }
    var target = plugin.app.vault.getAbstractFileByPath(nd.id);
    if (target instanceof obsidian.TFile) {
      plugin.app.vault.cachedRead(target).then(function (text) {
        obsidian.MarkdownRenderer.render(plugin.app, text, el, target.path, plugin);
      });
    }
  };
  return Class;
})();

// ── Route View ──────────────────────────────────────────────────────────────
var RouteView = (function () {
  var Class = function (leaf, plugin) { obsidian.ItemView.call(this, leaf); this.plugin = plugin; };
  Class.prototype = Object.create(obsidian.ItemView.prototype);
  Class.prototype.getViewType = function () { return 'lwf-route-view'; };
  Class.prototype.getDisplayText = function () { return 'Route'; };
  Class.prototype.getIcon = function () { return 'route'; };

  Class.prototype.onOpen = function () {
    this.contentEl.addClass('bbf-root', 'bbf-pane');
    this.body = this.contentEl.createEl('div', { cls: 'bbf-route' });
    this.refresh();
  };
  Class.prototype.onOuterChange = function () { this.refresh(); };
  Class.prototype.refresh = function () {
    var self = this, el = this.body, plugin = this.plugin;
    el.empty();
    if (!plugin.routeEvents.length) {
      el.createEl('div', { cls: 'bbf-empty', text: 'No route yet.' });
      return;
    }
    plugin.routeEvents.forEach(function (ev, i) {
      var row = el.createEl('div', { cls: 'bbf-route-row' });
      row.createEl('span', { cls: 'bbf-route-idx', text: String(i + 1) });
      var nd = plugin.model.byPath[ev.id];
      if (nd) {
        var visit = row.createEl('button', { text: nd.label });
        visit.addEventListener('click', function () { plugin.openReader(ev.id); });
      } else {
        row.createEl('span', { text: (ev.label || ev.id) + ' (record unavailable)' });
      }
    });
  };
  return Class;
})();

// ── Index View ──────────────────────────────────────────────────────────────
var IndexView = (function () {
  var Class = function (leaf, plugin) { obsidian.ItemView.call(this, leaf); this.plugin = plugin; };
  Class.prototype = Object.create(obsidian.ItemView.prototype);
  Class.prototype.getViewType = function () { return 'lwf-index-view'; };
  Class.prototype.getDisplayText = function () { return 'Index'; };
  Class.prototype.getIcon = function () { return 'list'; };

  Class.prototype.onOpen = function () {
    this.contentEl.addClass('bbf-root', 'bbf-pane');
    this.body = this.contentEl.createEl('div', { cls: 'bbf-view' });
    this.refresh();
  };
  Class.prototype.onOuterChange = function () { this.refresh(); };
  Class.prototype.refresh = function () {
    var self = this, el = this.body, plugin = this.plugin, model = plugin.getModel();
    el.empty();
    var vhead = el.createEl('div', { cls: 'bbf-pane-head' });
    vhead.createEl('span', { text: 'VIEW — object visibility' });
    var groups = el.createEl('div', { cls: 'bbf-groups' });
    NOTE_TYPES.forEach(function (t) {
      var cnt = model.nodes.filter(function (n) { return n.type === t; }).length;
      var lab = groups.createEl('label', { cls: 'bbf-group' + (plugin.hiddenTypes[t] ? ' is-off' : '') });
      var cb = lab.createEl('input', { type: 'checkbox' });
      cb.checked = !plugin.hiddenTypes[t];
      cb.addEventListener('change', function () { plugin.toggleType(t, !cb.checked); });
      lab.createEl('span', { text: typeLabel(t) + '  (' + cnt + ')' });
    });
    var ihead = el.createEl('div', { cls: 'bbf-pane-head' });
    ihead.createEl('span', { text: 'INDEX — notes' });
    var input = el.createEl('input', { type: 'text', cls: 'bbf-search', placeholder: 'filter by title / type…' });
    var list = el.createEl('div', { cls: 'bbf-index-list' });
    function drawList(q) {
      list.empty();
      q = (q || '').toLowerCase();
      var n = 0;
      model.nodes.forEach(function (nd) {
        if (n >= 300) return;
        if (q && nd.label.toLowerCase().indexOf(q) === -1 && typeLabel(nd.type).toLowerCase().indexOf(q) === -1) return;
        n++;
        var row = list.createEl('div', { cls: 'bbf-row' });
        var lab = row.createEl('span', { cls: 'bbf-row-label', text: nd.label });
        lab.addEventListener('click', function () { plugin.openReader(nd.id); });
        var act = row.createEl('span', { cls: 'bbf-row-act', text: 'field' });
        act.addEventListener('click', function () { plugin.focusInField(nd.id); });
      });
      if (!n) list.createEl('div', { cls: 'bbf-empty', text: 'no notes match.' });
    }
    drawList('');
    input.addEventListener('input', function () { drawList(input.value); });
  };
  return Class;
})();

require('./extensions.js').install(LivingWikiFieldPlugin, FieldView, ReaderView, IndexView);
module.exports = LivingWikiFieldPlugin;
