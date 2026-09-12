// Inject a copy-to-clipboard button into every <pre> block inside an article.
// Runs once on DOMContentLoaded; no dependencies. Uses navigator.clipboard
// with a fallback to document.execCommand for older browsers.
(function () {
  'use strict';

  function buttonSvg() {
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512" aria-hidden="true" focusable="false" width="14" height="14"><path fill="currentColor" d="M384 336H192c-8.8 0-16-7.2-16-16V64c0-8.8 7.2-16 16-16l140.1 0L400 115.9V320c0 8.8-7.2 16-16 16zM192 384H384c35.3 0 64-28.7 64-64V115.9c0-12.7-5.1-24.9-14.1-33.9L366.1 14.1c-9-9-21.2-14.1-33.9-14.1H192c-35.3 0-64 28.7-64 64V320c0 35.3 28.7 64 64 64zM64 128c-35.3 0-64 28.7-64 64V448c0 35.3 28.7 64 64 64H256c35.3 0 64-28.7 64-64V416H272v32c0 8.8-7.2 16-16 16H64c-8.8 0-16-7.2-16-16V192c0-8.8 7.2-16 16-16H96V128H64z"/></svg>';
  }

  function copy(text, btn) {
    var done = function () {
      var orig = btn.innerHTML;
      btn.innerHTML = 'Copied';
      btn.classList.add('copied');
      setTimeout(function () {
        btn.innerHTML = orig;
        btn.classList.remove('copied');
      }, 1500);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done).catch(function () {
        fallbackCopy(text, done);
      });
    } else {
      fallbackCopy(text, done);
    }
  }

  function fallbackCopy(text, done) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.position = 'absolute';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); } catch (_) { /* ignore */ }
    document.body.removeChild(ta);
    done();
  }

  function attach() {
    var blocks = document.querySelectorAll('main article pre');
    for (var i = 0; i < blocks.length; i++) {
      var pre = blocks[i];
      if (pre.querySelector('.copy-btn')) continue;
      pre.classList.add('has-copy');
      var btn = document.createElement('button');
      btn.className = 'copy-btn';
      btn.type = 'button';
      btn.setAttribute('aria-label', 'Copy code to clipboard');
      btn.innerHTML = buttonSvg();
      (function (targetPre, button) {
        button.addEventListener('click', function () {
          var code = targetPre.querySelector('code');
          var text = (code ? code.innerText : targetPre.innerText).replace(/\n$/, '');
          copy(text, button);
        });
      })(pre, btn);
      pre.appendChild(btn);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', attach);
  } else {
    attach();
  }
})();
