// Copyright 2026 AVIEN SOLUTIONS INC. All Rights Reserved.
//
// Event delegation shim.
//
// The strict CSP emitted by api.py drops 'unsafe-inline' from script-src, which
// means every inline on*= handler in index.html is blocked by the browser
// (hashes don't cover inline event handlers). Instead of adding 'unsafe-hashes'
// and hashing every handler body, we route every interaction through a
// document-level delegated listener keyed on data-action.
//
// Markup contract:
//   <button data-action="openSetup">...</button>
//   <button data-action="nav" data-arg="jobs">...</button>
//   <input  data-action="updateSetting" data-arg="feed" type="checkbox"/>
//   <input  data-action="handleResumeUpload" data-arg="setup" type="file"/>
//   <textarea data-action="chatKeydown"></textarea>
//
// ACTIONS entries carry both the target event type and the thin adapter that
// calls into the existing global function. All handler globals (openSetup,
// nav, etc.) are defined in the other frontend/js/*.js modules that are
// loaded with `defer`, so by the time DOMContentLoaded fires they all exist
// on window.

(function () {
  'use strict';

  function proxy(fnName) {
    return function () {
      var fn = window[fnName];
      if (typeof fn === 'function') return fn();
      console.warn('[events] missing global:', fnName);
    };
  }

  function proxyArg(fnName) {
    return function (el) {
      var fn = window[fnName];
      if (typeof fn === 'function') return fn(el.dataset.arg);
      console.warn('[events] missing global:', fnName);
    };
  }

  var ACTIONS = {
    // ── click: zero-arg proxies ──────────────────────────────────────────
    openSetup:             { type: 'click', fn: proxy('openSetup') },
    toggleTheme:           { type: 'click', fn: proxy('toggleTheme') },
    toggleSidebar:         { type: 'click', fn: proxy('toggleSidebar') },
    toggleChatOverlay:     { type: 'click', fn: proxy('toggleChatOverlay') },
    joinWaitlist:          { type: 'click', fn: proxy('joinWaitlist') },
    doLogin:               { type: 'click', fn: proxy('doLogin') },
    doSignup:              { type: 'click', fn: proxy('doSignup') },
    doLogout:              { type: 'click', fn: proxy('doLogout') },
    doForgotPassword:      { type: 'click', fn: proxy('doForgotPassword') },
    doChangePassword:      { type: 'click', fn: proxy('doChangePassword') },
    doGoogleAuth:          { type: 'click', fn: proxy('doGoogleAuth') },
    doDeleteAccount:       { type: 'click', fn: proxy('doDeleteAccount') },
    doExportData:          { type: 'click', fn: proxy('doExportData') },
    showAuthLogin:         { type: 'click', fn: proxy('showAuthLogin') },
    showAuthSignup:        { type: 'click', fn: proxy('showAuthSignup') },
    showForgotPassword:    { type: 'click', fn: proxy('showForgotPassword') },
    skipAuth:              { type: 'click', fn: proxy('skipAuth') },
    setupNext:             { type: 'click', fn: proxy('setupNext') },
    setupPrev:             { type: 'click', fn: proxy('setupPrev') },
    genResume:             { type: 'click', fn: proxy('genResume') },
    genCoverLetter:        { type: 'click', fn: proxy('genCoverLetter') },
    getMarket:             { type: 'click', fn: proxy('getMarket') },
    getTips:               { type: 'click', fn: proxy('getTips') },
    sendChat:              { type: 'click', fn: proxy('sendChat') },
    resetChat:             { type: 'click', fn: proxy('resetChat') },
    toggleAdvancedFilters: { type: 'click', fn: proxy('toggleAdvancedFilters') },
    refreshFeed:           { type: 'click', fn: proxy('refreshFeed') },
    loadFeedback:          { type: 'click', fn: proxy('loadFeedback') },
    loadKanbanBoard:       { type: 'click', fn: proxy('loadKanbanBoard') },
    loadPrepPackage:       { type: 'click', fn: proxy('loadPrepPackage') },
    calibrateSalary:       { type: 'click', fn: proxy('calibrateSalary') },
    negotiateSalary:       { type: 'click', fn: proxy('negotiateSalary') },
    compareOffers:         { type: 'click', fn: proxy('compareOffers') },
    createOffer:           { type: 'click', fn: proxy('createOffer') },
    createDream:           { type: 'click', fn: proxy('createDream') },
    saveDream:             { type: 'click', fn: proxy('saveDream') },
    findJobsForDream:      { type: 'click', fn: proxy('findJobsForDream') },
    submitDebrief:         { type: 'click', fn: proxy('submitDebrief') },
    submitUpdate:          { type: 'click', fn: proxy('submitUpdate') },
    closeUpdateModal:      { type: 'click', fn: proxy('closeUpdateModal') },
    downloadResume:        { type: 'click', fn: proxy('downloadResume') },
    openLinkedIn:          { type: 'click', fn: proxy('openLinkedIn') },
    trackApp:              { type: 'click', fn: proxy('trackApp') },

    // ── click: string-arg proxies ────────────────────────────────────────
    nav:                   { type: 'click', fn: proxyArg('nav') },
    startOnboardingPath:   { type: 'click', fn: proxyArg('startOnboardingPath') },
    switchInsightTab:      { type: 'click', fn: proxyArg('switchInsightTab') },
    switchInterviewTab:    { type: 'click', fn: proxyArg('switchInterviewTab') },

    // ── click: one-offs ──────────────────────────────────────────────────
    searchJobsV2: {
      type: 'click',
      fn: function () {
        if (typeof window.searchJobsV2 === 'function') window.searchJobsV2(1);
      },
    },

    // ── click: DOM helpers (replacing inline document.getElementById...) ─
    hideEl: {
      type: 'click',
      fn: function (el) {
        var t = document.getElementById(el.dataset.target);
        if (t) t.classList.add('hidden');
      },
    },
    focusEl: {
      type: 'click',
      fn: function (el) {
        var t = document.getElementById(el.dataset.target);
        if (t) t.focus();
      },
    },
    showPwSection: {
      type: 'click',
      fn: function () {
        var t = document.getElementById('changePasswordSection');
        if (t) t.style.display = '';
      },
    },
    hidePwSection: {
      type: 'click',
      fn: function () {
        var t = document.getElementById('changePasswordSection');
        if (t) t.style.display = 'none';
      },
    },
    setupToOnboarding: {
      type: 'click',
      fn: function () {
        var t = document.getElementById('setupModal');
        if (t) t.classList.add('hidden');
        if (typeof window.showOnboardingPath === 'function') window.showOnboardingPath();
      },
    },

    // ── change handlers ──────────────────────────────────────────────────
    handleResumeUpload: {
      type: 'change',
      fn: function (el, ev) {
        if (typeof window.handleResumeUpload === 'function') {
          window.handleResumeUpload(ev, el.dataset.arg);
        }
      },
    },
    updateSetting: {
      type: 'change',
      fn: function (el) {
        if (typeof window.updateSetting === 'function') {
          window.updateSetting(el.dataset.arg, el.checked);
        }
      },
    },

    // ── keydown handlers ─────────────────────────────────────────────────
    chatKeydown: {
      type: 'keydown',
      fn: function (el, ev) {
        if (typeof window.chatKeydown === 'function') window.chatKeydown(ev);
      },
    },
  };

  function dispatch(type, ev) {
    var el = ev.target && ev.target.closest ? ev.target.closest('[data-action]') : null;
    if (!el) return;
    var name = el.dataset.action;
    var action = ACTIONS[name];
    if (!action || action.type !== type) return;
    try {
      action.fn(el, ev);
    } catch (err) {
      console.error('[events] action failed:', name, err);
    }
  }

  document.addEventListener('click',   function (ev) { dispatch('click',   ev); });
  document.addEventListener('change',  function (ev) { dispatch('change',  ev); });
  document.addEventListener('keydown', function (ev) { dispatch('keydown', ev); });

  // Expose for debugging / third-party extension
  window.__ACTIONS__ = ACTIONS;
})();
