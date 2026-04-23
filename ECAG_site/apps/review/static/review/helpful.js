(function ($) {
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

  function showToast(msg, type) {
    const toastType = type || 'info';
    let $el = $('#helpful-toast');

    if (!$el.length) {
      $el = $('<div>', {
        id: 'helpful-toast',
        'aria-live': 'polite'
      }).css({
        position: 'fixed',
        right: '1rem',
        bottom: '1rem',
        padding: '0.6rem 0.9rem',
        borderRadius: '8px',
        boxShadow: '0 6px 18px rgba(0,0,0,0.12)',
        zIndex: 9999,
        fontSize: '0.95rem'
      });
      $('body').append($el);
    }

    $el.text(msg);
    if (toastType === 'error') {
      $el.css({ background: '#fecaca', color: '#7f1d1d' });
    } else {
      $el.css({ background: '#dcfce7', color: '#064e3b' });
    }

    $el.css('opacity', '1');
    setTimeout(function () {
      $el.css('opacity', '0');
    }, 2500);
  }

  $(document).on('click', '.helpful-btn', function (e) {
    const $btn = $(this);
    if ($btn.prop('disabled')) return;

    const id = $btn.data('review-id');
    if (!id) return;

    const helpfulTemplate = $('#reviews-list').data('helpfulTemplate');
    if (!helpfulTemplate) {
      showToast('Unable to find helpful endpoint.', 'error');
      return;
    }

    const csrftoken = getCookie('csrftoken');
    const url = String(helpfulTemplate).replace('0/', String(id) + '/');

    const $countSpan = $btn.find('.helpful-count span');
    const previous = $countSpan.length ? $countSpan.text() : null;
    if ($countSpan.length) {
      const n = parseInt(previous || '0', 10);
      $countSpan.text(String(n + 1));
    }

    $btn.prop('disabled', true).addClass('opacity-60 cursor-not-allowed');

    $.ajax({
      url: url,
      method: 'POST',
      contentType: 'application/json',
      headers: { 'X-CSRFToken': csrftoken },
      data: JSON.stringify({})
    })
      .done(function (data) {
        if ($countSpan.length && typeof data.helpful !== 'undefined') {
          $countSpan.text(String(data.helpful));
        }
        $btn.prop('disabled', true);
        showToast('Thanks for your feedback!');
      })
      .fail(function () {
        if ($countSpan.length && previous !== null) $countSpan.text(previous);
        $btn.prop('disabled', false).removeClass('opacity-60 cursor-not-allowed');
        showToast('Failed to register vote.', 'error');
      });
  });

  $(function () {
    $('#highlights-helpful-link').on('click', function (e) {
      e.preventDefault();
      const target = $('#reviews-list').get(0);
      if (!target) return;

      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      setTimeout(function () {
        const $firstBtn = $('.helpful-btn:not([disabled])').first();
        if (!$firstBtn.length) return;

        $firstBtn.trigger('focus').addClass('ring-2 ring-amber-300');
        setTimeout(function () {
          $firstBtn.removeClass('ring-2 ring-amber-300');
        }, 1200);
      }, 400);
    });
  });
})(jQuery);
