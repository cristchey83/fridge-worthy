// Fridge-Worthy page behavior: share buttons, copy link, copy Chat prompt,
// and nav highlighting. No network calls, no analytics.
(function () {
  'use strict';

  // The share URL comes from <link rel="canonical"> so SITE_URL lives in one place (index.html).
  var canonical = document.querySelector('link[rel="canonical"]');
  var URL_ = canonical ? canonical.href : location.href;
  var TITLE = "Fridge-Worthy: from 20 emails a week to only what's Fridge-Worthy";
  var TEXT = "From 20 emails a week to only what's Fridge-Worthy. An open-source guide to taming school communications.";
  var SUBJECT = "From 20 emails a week to only what's Fridge-Worthy";
  var BODY = "Hi! Thought of you. A parent built this to filter all the school emails down to the few updates that matter.\n\n" +
    "The one rule: \"Would a parent change their schedule, prepare their child, or do something?\" If not, it stays off the page.\n\n" +
    "There's a no-code version that takes 10 minutes:\n" + URL_;
  var MSG = TEXT + ' ' + URL_;

  var status = document.getElementById('copy-status');

  // Copy text to the clipboard, with a textarea fallback for older browsers.
  // done(true) on success, done(false) if the copy failed.
  function copyText(text, done) {
    function fallback() {
      var t = document.createElement('textarea');
      var ok = false;
      t.value = text;
      t.setAttribute('readonly', '');
      t.className = 'copy-buffer';
      document.body.appendChild(t);
      t.select();
      try { ok = document.execCommand('copy') === true; } catch (e) { ok = false; }
      document.body.removeChild(t);
      done(ok);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () { done(true); }, fallback);
    } else { fallback(); }
  }

  // Show "Copied ✓" (or the button's failure note) for a moment, then restore its label.
  function flasher(btn, label, announce, failMsg) {
    var timer;
    return function (ok) {
      btn.textContent = ok ? 'Copied ✓' : failMsg;
      btn.classList.toggle('copied', ok);
      status.textContent = ok ? announce : failMsg;
      clearTimeout(timer);
      timer = setTimeout(function () {
        btn.textContent = label;
        btn.classList.remove('copied');
        status.textContent = '';
      }, ok ? 1800 : 4000);
    };
  }

  document.getElementById('share-preview').textContent = MSG;
  document.getElementById('sms-link').href = 'sms:?&body=' + encodeURIComponent(MSG);
  document.getElementById('mail-link').href = 'mailto:?subject=' + encodeURIComponent(SUBJECT) + '&body=' + encodeURIComponent(BODY);
  document.getElementById('wa-link').href = 'https://wa.me/?text=' + encodeURIComponent(MSG);

  var copyBtn = document.getElementById('copy-link');
  var flashLink = flasher(copyBtn, 'Copy link', 'Link copied', "Couldn't copy. Select the link below");
  copyBtn.addEventListener('click', function () { copyText(URL_, flashLink); });

  // "Copy the Chat prompt": the prompt text is stored in a <template> in index.html.
  var promptBtn = document.getElementById('copy-prompt');
  var promptTpl = document.getElementById('chat-prompt');
  if (promptBtn && promptTpl) {
    // The prompt is hidden, so on failure point to the Chat guide (the row link just above), which shows it.
    var flashPrompt = flasher(promptBtn, promptBtn.getAttribute('data-label'), 'Chat prompt copied',
      "Couldn't copy. Open the Chat guide");
    promptBtn.addEventListener('click', function () {
      copyText(promptTpl.content.textContent, flashPrompt);
    });
  }

  function showShareSection() {
    document.getElementById('share').scrollIntoView({ behavior: 'smooth', block: 'center' });
    setTimeout(function () { copyBtn.focus({ preventScroll: true }); }, 500);
  }

  document.querySelectorAll('.js-share').forEach(function (b) {
    b.addEventListener('click', function () {
      if (navigator.share) {
        // The user closing the share sheet is an AbortError; any other failure falls back to the share section.
        navigator.share({ title: TITLE, text: TEXT, url: URL_ }).catch(function (e) {
          if (!e || e.name !== 'AbortError') showShareSection();
        });
      } else {
        showShareSection();
      }
    });
  });

  if (!('IntersectionObserver' in window)) return;

  // Underline the nav item for the section on screen.
  var navItems = [].slice.call(document.querySelectorAll('nav.jump .links a, nav.jump .chip'));
  function idOf(el) { return el.dataset.navId || el.hash.slice(1); }
  function setActive(id) {
    navItems.forEach(function (el) {
      if (id && idOf(el) === id) el.setAttribute('aria-current', 'true'); else el.removeAttribute('aria-current');
    });
  }
  // At the very bottom, "More" wins even if a shorter section sits in the band.
  function atBottom() { return innerHeight + scrollY >= document.documentElement.scrollHeight - 4; }
  var navIO = new IntersectionObserver(function (entries) {
    if (atBottom()) { setActive('more'); return; }
    entries.forEach(function (e) { if (e.isIntersecting) setActive(e.target.dataset.nav || null); });
  }, { rootMargin: '-30% 0px -60% 0px' });
  document.querySelectorAll('main > section, main > header').forEach(function (s) { navIO.observe(s); });
  addEventListener('scroll', function () { if (atBottom()) setActive('more'); }, { passive: true });
})();
