// ==========================================
// POSTHOG ANALYTICS (F11a)
// ==========================================
// Loaded only when POSTHOG_KEY is set (templates/_posthog.html), right after
// PostHog's own library (/ingest/static/array.js). If that library is missing
// (blocked, PostHog down), this file does nothing and the site works as usual.
(function () {
  var key = document.currentScript && document.currentScript.dataset.key;
  if (!key || !window.posthog || typeof window.posthog.init !== 'function') return;

  window.posthog.init(key, {
    api_host: '/ingest',               // our own domain -> not dropped by ad blockers
    ui_host: 'https://us.posthog.com', // links from the toolbar go to the right PostHog
    cookieless_mode: 'always',         // no cookies or local storage -> no cookie banner
    person_profiles: 'identified_only',
    capture_pageview: true,
    capture_pageleave: true,
    autocapture: true,                 // clicks on buttons/links; never what is typed in inputs
    disable_session_recording: true    // replay is not possible in cookieless "always" mode
  });
  // Label every event, so this site's data can always be separated from other apps.
  window.posthog.register({ app: 'buytelegrambots' });
})();
