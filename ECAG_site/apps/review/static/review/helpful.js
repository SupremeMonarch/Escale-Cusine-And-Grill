(function () {
  'use strict';

  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  function showToast(msg, type = 'info') {
    let el = document.getElementById('helpful-toast');
    if (!el) {
      el = document.createElement('div');
      el.id = 'helpful-toast';
      el.setAttribute('aria-live', 'polite');
      el.style.position = 'fixed';
      el.style.right = '1rem';
      el.style.bottom = '1rem';
      el.style.padding = '0.6rem 0.9rem';
      el.style.borderRadius = '8px';
      el.style.boxShadow = '0 6px 18px rgba(0,0,0,0.12)';
      el.style.zIndex = 9999;
      el.style.fontSize = '0.95rem';
      document.body.appendChild(el);
    }
    el.textContent = msg;
    if (type === 'error') {
      el.style.background = '#fecaca';
      el.style.color = '#7f1d1d';
    } else {
      el.style.background = '#dcfce7';
      el.style.color = '#064e3b';
    }
    el.style.opacity = '1';
    setTimeout(() => { el.style.opacity = '0'; }, 2500);
  }

  document.addEventListener('click', async function (e) {
    const btn = e.target.closest('.helpful-btn');
    if (!btn) return;
    if (btn.disabled) return;

    const id = btn.getAttribute('data-review-id');
    if (!id) return;

    const reviewsContainer = document.getElementById('reviews-list');
    const helpfulTemplate = reviewsContainer ? reviewsContainer.dataset.helpfulTemplate : null;
    if (!helpfulTemplate) {
      showToast('Unable to find helpful endpoint.', 'error');
      return;
    }

    const csrftoken = getCookie('csrftoken');
    const url = helpfulTemplate.replace('0/', id + '/');

    const countSpan = btn.querySelector('.helpful-count span');
    let previous = null;
    if (countSpan) {
      previous = countSpan.textContent;
      const n = parseInt(previous || '0', 10);
      countSpan.textContent = (n + 1).toString();
    }
    btn.disabled = true;
    btn.classList.add('opacity-60', 'cursor-not-allowed');

    try {
      const resp = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrftoken,
        },
        body: JSON.stringify({}),
      });
      if (!resp.ok) {
        if (countSpan && previous !== null) countSpan.textContent = previous;
        btn.disabled = false;
        btn.classList.remove('opacity-60', 'cursor-not-allowed');
        showToast('Failed to register vote.', 'error');
        return;
      }

      const data = await resp.json();
      if (countSpan && typeof data.helpful !== 'undefined') {
        countSpan.textContent = String(data.helpful);
      }
      btn.disabled = true;
      showToast('Thanks for your feedback!');

    } catch (err) {
      if (countSpan && previous !== null) countSpan.textContent = previous;
      btn.disabled = false;
      btn.classList.remove('opacity-60', 'cursor-not-allowed');
      showToast('Network error — try again', 'error');
    }
  });

  document.addEventListener('DOMContentLoaded', function () {
    const highlightsLink = document.getElementById('highlights-helpful-link');
    if (!highlightsLink) return;
    highlightsLink.addEventListener('click', function (e) {
      e.preventDefault();
      const target = document.getElementById('reviews-list');
      if (target) {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        setTimeout(() => {
          const firstBtn = document.querySelector('.helpful-btn:not([disabled])');
          if (firstBtn) {
            firstBtn.focus();
            firstBtn.classList.add('ring-2', 'ring-amber-300');
            setTimeout(() => firstBtn.classList.remove('ring-2', 'ring-amber-300'), 1200);
          }
        }, 400);
      }
    });
  });
})();