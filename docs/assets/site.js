/* ============================================================
   Dinheiro em Pauta — comportamento compartilhado
   Barra de progresso de leitura, botão voltar ao topo, TOC
   scroll-spy, reveal-on-scroll (artigos) e setas da vitrine
   horizontal (home). Cada bloco é um no-op se os elementos que
   ele precisa não existirem na página atual.
   ============================================================ */
(function(){
  "use strict";

  /* ---------- toggle de tema (claro/escuro) ---------- */
  var themeToggle = document.getElementById('themeToggle');
  if (themeToggle) {
    var root = document.documentElement;
    var systemPrefersDark = function(){
      return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    };
    var isDarkNow = function(){
      var explicit = root.getAttribute('data-theme');
      if (explicit === 'dark') return true;
      if (explicit === 'light') return false;
      return systemPrefersDark();
    };
    themeToggle.setAttribute('aria-pressed', String(isDarkNow()));
    themeToggle.addEventListener('click', function(){
      var next = isDarkNow() ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      try { localStorage.setItem('ic-theme', next); } catch(e){}
      themeToggle.setAttribute('aria-pressed', String(next === 'dark'));
    });
  }

  /* ---------- menu compacto (Sobre / Artigos / Simuladores) ---------- */
  var menuToggle = document.getElementById('menuToggle');
  var siteMenu = document.getElementById('siteMenu');
  if (menuToggle && siteMenu) {
    var closeMenu = function(){
      siteMenu.hidden = true;
      menuToggle.setAttribute('aria-expanded', 'false');
    };
    var openMenu = function(){
      siteMenu.hidden = false;
      menuToggle.setAttribute('aria-expanded', 'true');
    };
    menuToggle.addEventListener('click', function(e){
      e.stopPropagation();
      if (siteMenu.hidden) openMenu(); else closeMenu();
    });
    document.addEventListener('click', function(e){
      if (!siteMenu.hidden && !siteMenu.contains(e.target) && e.target !== menuToggle) closeMenu();
    });
    document.addEventListener('keydown', function(e){
      if (e.key === 'Escape' && !siteMenu.hidden) { closeMenu(); menuToggle.focus(); }
    });
  }

  /* ---------- barra de progresso de leitura ---------- */
  var progressFill = document.getElementById('progressFill');
  if (progressFill) {
    var updateProgress = function(){
      var h = document.documentElement;
      var scrollTop = h.scrollTop || document.body.scrollTop;
      var scrollHeight = (h.scrollHeight || document.body.scrollHeight) - h.clientHeight;
      var pct = scrollHeight > 0 ? (scrollTop / scrollHeight) * 100 : 0;
      progressFill.style.width = pct.toFixed(2) + '%';
    };
    window.addEventListener('scroll', updateProgress, { passive: true });
    updateProgress();
  }

  /* ---------- botão voltar ao topo ---------- */
  var backToTop = document.getElementById('backToTop');
  if (backToTop) {
    var updateBackToTop = function(){
      if (window.scrollY > 600) { backToTop.classList.add('show'); }
      else { backToTop.classList.remove('show'); }
    };
    backToTop.addEventListener('click', function(){
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
    window.addEventListener('scroll', updateBackToTop, { passive: true });
    updateBackToTop();
  }

  /* ---------- navegação lateral (TOC) ---------- */
  var tocLinks = Array.prototype.slice.call(document.querySelectorAll('#tocRail a'));
  if (tocLinks.length) {
    var sections = tocLinks.map(function(a){
      return document.getElementById(a.getAttribute('href').slice(1));
    }).filter(Boolean);

    if ('IntersectionObserver' in window && sections.length) {
      var tocObserver = new IntersectionObserver(function(entries){
        entries.forEach(function(entry){
          var link = document.querySelector('#tocRail a[href="#' + entry.target.id + '"]');
          if (!link) return;
          if (entry.isIntersecting) {
            tocLinks.forEach(function(l){ l.classList.remove('active'); });
            link.classList.add('active');
          }
        });
      }, { rootMargin: '-45% 0px -50% 0px', threshold: 0 });
      sections.forEach(function(s){ tocObserver.observe(s); });
    }
  }

  /* ---------- reveal on scroll ---------- */
  var revealEls = document.querySelectorAll('.reveal');
  if (revealEls.length) {
    if ('IntersectionObserver' in window) {
      var revealObserver = new IntersectionObserver(function(entries, obs){
        entries.forEach(function(entry){
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            obs.unobserve(entry.target);
          }
        });
      }, { threshold: 0.1 });
      revealEls.forEach(function(el){ revealObserver.observe(el); });
    } else {
      revealEls.forEach(function(el){ el.classList.add('visible'); });
    }
  }

  /* ---------- vitrines horizontais (home) ---------- */
  document.querySelectorAll('.vitrine-track').forEach(function(track){
    var wrap = track.closest('.vitrine-wrap');
    var left = wrap.querySelector('.vitrine-arrow-left');
    var right = wrap.querySelector('.vitrine-arrow-right');
    var EPS = 2;

    function update(){
      var maxScroll = track.scrollWidth - track.clientWidth;
      if (maxScroll <= EPS) {
        left.hidden = true;
        right.hidden = true;
        track.classList.remove('has-more-left', 'has-more-right');
        return;
      }
      left.hidden = track.scrollLeft <= EPS;
      right.hidden = track.scrollLeft >= maxScroll - EPS;
      track.classList.toggle('has-more-left', track.scrollLeft > EPS);
      track.classList.toggle('has-more-right', track.scrollLeft < maxScroll - EPS);
    }

    [left, right].forEach(function(btn){
      btn.addEventListener('click', function(){
        var card = track.querySelector('.vitrine-card, .vitrine-empty');
        var step = card ? card.getBoundingClientRect().width + 16 : 300;
        var dir = btn === left ? -1 : 1;
        track.scrollBy({ left: dir * step, behavior: 'smooth' });
      });
    });

    track.addEventListener('scroll', update, { passive: true });
    window.addEventListener('resize', update);
    update();
  });

  /* ---------- curtir (artigo) ---------- */
  var likeBtn = document.getElementById('likeBtn');
  if (likeBtn && likeBtn.dataset.slug) {
    var LIKES_API = 'https://dinheiro-em-pauta-likes.dinheiroempauta.workers.dev';
    var slug = likeBtn.dataset.slug;
    var likeCountEl = document.getElementById('likeCount');
    var likeStorageKey = 'liked_' + slug;

    var setLikeCount = function(n){ if (likeCountEl) likeCountEl.textContent = n; };

    fetch(LIKES_API + '/likes?slug=' + slug)
      .then(function(r){ return r.json(); })
      .then(function(data){ setLikeCount(data.count); })
      .catch(function(){ setLikeCount('–'); });

    if (localStorage.getItem(likeStorageKey)) {
      likeBtn.classList.add('liked');
      likeBtn.setAttribute('aria-pressed', 'true');
    }

    likeBtn.addEventListener('click', function(){
      var isLiked = !!localStorage.getItem(likeStorageKey);
      if (isLiked) {
        likeBtn.classList.remove('liked');
        likeBtn.setAttribute('aria-pressed', 'false');
        localStorage.removeItem(likeStorageKey);
        fetch(LIKES_API + '/likes?slug=' + slug, { method: 'DELETE' })
          .then(function(r){ return r.json(); })
          .then(function(data){ setLikeCount(data.count); });
      } else {
        likeBtn.classList.add('liked');
        likeBtn.setAttribute('aria-pressed', 'true');
        localStorage.setItem(likeStorageKey, '1');
        fetch(LIKES_API + '/likes?slug=' + slug, { method: 'POST' })
          .then(function(r){ return r.json(); })
          .then(function(data){ setLikeCount(data.count); });
      }
    });
  }

  /* ---------- copiar link ---------- */
  var copyLinkBtn = document.getElementById('copyLinkBtn');
  if (copyLinkBtn) {
    copyLinkBtn.addEventListener('click', function(){
      navigator.clipboard.writeText(window.location.href).then(function(){
        copyLinkBtn.classList.add('copied');
        setTimeout(function(){ copyLinkBtn.classList.remove('copied'); }, 1600);
      });
    });
  }

  /* ---------- newsletter (Buttondown) ---------- */
  var newsletterToggle = document.getElementById('newsletterToggle');
  var newsletterForm = document.getElementById('newsletterForm');
  if (newsletterToggle && newsletterForm) {
    newsletterToggle.addEventListener('click', function(){
      var willShow = newsletterForm.hidden;
      newsletterForm.hidden = !willShow;
      newsletterToggle.setAttribute('aria-expanded', String(willShow));
      if (willShow) {
        var emailInput = newsletterForm.querySelector('input[type="email"]');
        if (emailInput) emailInput.focus();
      }
    });

    newsletterForm.addEventListener('submit', function(){
      var note = document.getElementById('newsletterNote');
      var fields = document.getElementById('newsletterFields');
      setTimeout(function(){
        if (note) {
          note.textContent = 'Inscrição enviada — confira seu e-mail para confirmar.';
          note.classList.add('success');
        }
        if (fields) fields.style.display = 'none';
      }, 400);
    });
  }

  /* ---------- sugerir um tema (Web3Forms) ---------- */
  var suggestToggle = document.getElementById('suggestToggle');
  var suggestForm = document.getElementById('suggestForm');
  if (suggestToggle && suggestForm) {
    var suggestTextarea = document.getElementById('suggest-message');
    var suggestCounter = document.getElementById('suggestCounter');
    var SUGGEST_MAXLEN = 500;

    var updateSuggestCounter = function(){
      var remaining = SUGGEST_MAXLEN - suggestTextarea.value.length;
      suggestCounter.textContent = remaining + ' caracteres restantes';
    };
    if (suggestTextarea && suggestCounter) {
      suggestTextarea.addEventListener('input', updateSuggestCounter);
      updateSuggestCounter();
    }

    suggestToggle.addEventListener('click', function(){
      var willShow = suggestForm.hidden;
      suggestForm.hidden = !willShow;
      suggestToggle.setAttribute('aria-expanded', String(willShow));
      if (willShow && suggestTextarea) suggestTextarea.focus();
    });

    suggestForm.addEventListener('submit', function(e){
      e.preventDefault();
      var note = document.getElementById('suggestNote');
      var fields = document.getElementById('suggestFields');
      var submitBtn = suggestForm.querySelector('.newsletter-submit');
      if (submitBtn) submitBtn.disabled = true;

      fetch('https://api.web3forms.com/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify(Object.fromEntries(new FormData(suggestForm)))
      })
        .then(function(r){ return r.json(); })
        .then(function(data){
          if (data.success) {
            if (note) {
              note.textContent = 'Sugestão enviada — obrigado!';
              note.classList.remove('error');
              note.classList.add('success');
            }
            if (fields) fields.style.display = 'none';
          } else {
            if (note) {
              note.textContent = 'Não deu pra enviar agora. Tenta de novo em instantes.';
              note.classList.add('error');
            }
            if (submitBtn) submitBtn.disabled = false;
          }
        })
        .catch(function(){
          if (note) {
            note.textContent = 'Não deu pra enviar agora. Tenta de novo em instantes.';
            note.classList.add('error');
          }
          if (submitBtn) submitBtn.disabled = false;
        });
    });
  }

  /* ---------- comentários (Cloudflare Worker próprio) ---------- */
  function setupComments(){
    var widgets = document.querySelectorAll('.comment-widget');
    if (!widgets.length) return;

    var formatDate = function(iso){
      var d = new Date(iso);
      if (isNaN(d.getTime())) return '';
      var datePart = d.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' }).replace('.', '');
      var timePart = d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
      return datePart + ', ' + timePart;
    };

    var buildReplyForm = function(widget, parentId){
      var template = widget.querySelector(':scope > .comment-form');
      var clone = template.cloneNode(true);
      clone.classList.add('comment-reply-form');
      clone.dataset.parentId = String(parentId);
      // cloneNode copia id/for literalmente — sem isso, um clique no
      // <label> de um formulário de resposta focava (e rolava a página
      // até) o campo do formulário PRINCIPAL lá no topo, porque os dois
      // ficavam com o mesmo id e o navegador segue sempre o primeiro do
      // documento. Sufixo pelo id do comentário respondido garante um id
      // novo mesmo com várias respostas abertas ao mesmo tempo.
      var suffix = '-reply-' + parentId;
      clone.querySelectorAll('[id]').forEach(function(el){ el.id += suffix; });
      clone.querySelectorAll('label[for]').forEach(function(el){ el.htmlFor += suffix; });
      clone.querySelectorAll('input,textarea').forEach(function(el){
        if (el.type === 'checkbox') { el.checked = false; } else { el.value = ''; }
      });
      var status = clone.querySelector('.comment-status');
      if (status) { status.hidden = true; status.textContent = ''; }
      bindForm(clone, widget);
      return clone;
    };

    var toggleReplyForm = function(item, parentId, widget){
      var existing = item.querySelector(':scope > .comment-reply-form');
      if (existing) { existing.remove(); return; }
      var form = buildReplyForm(widget, parentId);
      item.appendChild(form);
      var textarea = form.querySelector('textarea');
      if (textarea) textarea.focus();
    };

    var renderComment = function(c, widget, depth){
      var item = document.createElement('div');
      item.className = 'comment-item';

      var header = document.createElement('div');
      header.className = 'comment-item-header';

      var nick = document.createElement('span');
      nick.className = 'comment-nickname';
      nick.textContent = c.nickname;
      header.appendChild(nick);

      if (c.is_author) {
        var badge = document.createElement('span');
        badge.className = 'comment-badge-author';
        badge.textContent = 'Autor';
        header.appendChild(badge);
      }

      var date = document.createElement('span');
      date.className = 'comment-date';
      date.textContent = formatDate(c.created_at);
      header.appendChild(date);

      var message = document.createElement('p');
      message.className = 'comment-message';
      message.textContent = c.message;

      item.appendChild(header);
      item.appendChild(message);

      // Sem limite de profundidade: resposta de resposta é permitida (o
      // CSS de .comment-replies reduz o recuo visual nos níveis mais
      // fundos pra não estourar a largura em telas estreitas).
      var replyBtn = document.createElement('button');
      replyBtn.type = 'button';
      replyBtn.className = 'comment-reply-toggle';
      replyBtn.textContent = 'Responder';
      replyBtn.addEventListener('click', function(){ toggleReplyForm(item, c.id, widget); });
      item.appendChild(replyBtn);

      if (c.replies && c.replies.length) {
        var repliesEl = document.createElement('div');
        repliesEl.className = 'comment-replies';
        c.replies.forEach(function(r){ repliesEl.appendChild(renderComment(r, widget, depth + 1)); });
        item.appendChild(repliesEl);
      }

      return item;
    };

    var loadComments = function(widget){
      var slug = widget.dataset.slug;
      var api = widget.dataset.commentsApi;
      var listEl = widget.querySelector('.comment-list');
      if (!slug || !api || !listEl) return;
      listEl.innerHTML = '<p class="comment-loading">Carregando comentários…</p>';
      fetch(api + '/comments?slug=' + encodeURIComponent(slug))
        .then(function(r){ return r.json(); })
        .then(function(data){
          listEl.innerHTML = '';
          if (!data.comments || !data.comments.length) {
            listEl.innerHTML = '<p class="comment-empty">Seja o primeiro a comentar.</p>';
            return;
          }
          data.comments.forEach(function(c){ listEl.appendChild(renderComment(c, widget, 0)); });
        })
        .catch(function(){
          listEl.innerHTML = '<p class="comment-empty">Não foi possível carregar os comentários agora.</p>';
        });
    };

    var bindForm = function(form, widget){
      var textarea = form.querySelector('textarea');
      var counter = form.querySelector('.comment-counter');
      var maxLen = textarea ? (parseInt(textarea.getAttribute('maxlength'), 10) || 2000) : 2000;
      var updateCounter = function(){
        if (counter && textarea) counter.textContent = (maxLen - textarea.value.length) + ' caracteres restantes';
      };
      if (textarea && counter) {
        textarea.addEventListener('input', updateCounter);
        updateCounter();
      }

      form.addEventListener('submit', function(e){
        e.preventDefault();
        var api = widget.dataset.commentsApi;
        var slug = widget.dataset.slug;
        var nicknameEl = form.querySelector('[name="nickname"]');
        var emailEl = form.querySelector('[name="email"]');
        var honeypotEl = form.querySelector('[name="botcheck"]');
        var statusEl = form.querySelector('.comment-status');
        var submitBtn = form.querySelector('button[type="submit"]');

        var payload = {
          slug: slug,
          parent_id: form.dataset.parentId ? Number(form.dataset.parentId) : null,
          nickname: nicknameEl ? nicknameEl.value.trim() : '',
          email: emailEl ? emailEl.value.trim() : '',
          message: textarea ? textarea.value.trim() : '',
          botcheck: honeypotEl && honeypotEl.checked ? 'bot' : '',
        };

        if (submitBtn) submitBtn.disabled = true;
        fetch(api + '/comments', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
          .then(function(r){ return r.json().then(function(data){ return { ok: r.ok, data: data }; }); })
          .then(function(res){
            if (!statusEl) return;
            statusEl.hidden = false;
            if (res.ok) {
              statusEl.classList.remove('error');
              statusEl.classList.add('success');
              statusEl.textContent = 'Comentário enviado — ele passa por moderação antes de aparecer publicamente.';
              form.reset();
              updateCounter();
              if (form.classList.contains('comment-reply-form')) {
                setTimeout(function(){ form.remove(); }, 4000);
              }
            } else {
              statusEl.classList.remove('success');
              statusEl.classList.add('error');
              statusEl.textContent = 'Não foi possível enviar (' + (res.data && res.data.error ? res.data.error : 'erro') + '). Tente novamente.';
            }
          })
          .catch(function(){
            if (statusEl) { statusEl.hidden = false; statusEl.classList.remove('success'); statusEl.classList.add('error'); statusEl.textContent = 'Erro de conexão. Tente novamente.'; }
          })
          .finally(function(){
            if (submitBtn) submitBtn.disabled = false;
          });
      });
    };

    widgets.forEach(function(widget){
      var rootForm = widget.querySelector(':scope > .comment-form');
      if (rootForm) bindForm(rootForm, widget);
      loadComments(widget);
    });
  }
  setupComments();
})();
