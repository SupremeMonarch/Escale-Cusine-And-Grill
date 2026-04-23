(function ($) {
  'use strict';

  function getCookie(name) {
    const cookies = document.cookie ? document.cookie.split(';') : [];
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        return decodeURIComponent(cookie.substring(name.length + 1));
      }
    }
    return null;
  }

  const csrftoken = getCookie('csrftoken');

  function clearSelection() {
    $('.table-group.selected').removeClass('selected');
    $('#selected_table_input').val('');
    $('#selected-table-display').text('None');
  }

  function onSelect(groupEl) {
    const $group = $(groupEl);
    if ($group.hasClass('disabled')) return;

    clearSelection();
    $group.addClass('selected');

    const tableId = $group.attr('data-table') || groupEl.id || '';
    $('#selected_table_input').val(tableId);
    $('#selected-table-display').text(tableId || 'None');

    $(window).trigger('table:selected', [{ tableId: tableId }]);
  }

  function allowedSeatsForParty(partySize) {
    const size = parseInt(partySize || '0', 10);
    if (size <= 2 && size >= 1) return 2;
    if (size >= 3) return 4;
    return 0;
  }

  function validateTime(timeStr) {
    if (!timeStr) return { ok: false, message: 'Please choose a time.' };
    const parts = timeStr.split(':');
    if (parts.length < 2) return { ok: false, message: 'Invalid time format.' };

    const hh = parseInt(parts[0], 10);
    const mm = parseInt(parts[1], 10);
    if (Number.isNaN(hh) || Number.isNaN(mm)) return { ok: false, message: 'Invalid time.' };
    if (hh < 15 || hh > 22) return { ok: false, message: 'Please choose an hour between 15:00 and 22:00.' };
    if (mm % 15 !== 0) return { ok: false, message: 'Please choose minutes in 15-minute increments (00, 15, 30, 45).' };

    return { ok: true };
  }

  function validateDate(dateStr) {
    if (!dateStr) return { ok: false, message: 'Please choose a date.' };
    const parts = dateStr.split('-');
    if (parts.length !== 3) return { ok: false, message: 'Invalid date format.' };

    const y = parseInt(parts[0], 10);
    const m = parseInt(parts[1], 10) - 1;
    const d = parseInt(parts[2], 10);
    if (Number.isNaN(y) || Number.isNaN(m) || Number.isNaN(d)) return { ok: false, message: 'Invalid date.' };

    const sel = new Date(y, m, d);
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    if (sel < today) return { ok: false, message: 'Please select today or a future date.' };

    return { ok: true };
  }

  function showCustomTimePicker(input, anchorEl) {
    if (!input) return;

    $('.rs-timepicker-popup').remove();

    const $popup = $('<div>', {
      class: 'rs-timepicker-popup',
      role: 'dialog',
      'aria-label': 'Choose time'
    }).css({
      position: 'absolute',
      zIndex: 9999,
      background: '#fff',
      color: '#111',
      border: '1px solid rgba(0,0,0,0.12)',
      borderRadius: '6px',
      boxShadow: '0 6px 18px rgba(0,0,0,0.12)',
      padding: '8px',
      minWidth: '160px',
      maxHeight: '260px',
      overflow: 'auto'
    });

    const minutes = [0, 15, 30, 45];
    for (let h = 15; h <= 22; h++) {
      const $hourRow = $('<div>').css({
        display: 'flex',
        gap: '6px',
        marginBottom: '6px',
        flexWrap: 'wrap'
      });

      const hh = h < 10 ? '0' + h : '' + h;
      $('<div>')
        .text(hh + ':')
        .css({
          fontWeight: '600',
          marginRight: '6px',
          flex: '0 0 36px'
        })
        .appendTo($hourRow);

      const minList = h === 22 ? [0] : minutes;
      $.each(minList, function (_, m) {
        const mm = m < 10 ? '0' + m : '' + m;
        const val = hh + ':' + mm;

        $('<button>', {
          type: 'button',
          text: val,
          'data-value': val
        })
          .css({
            background: '#f3f4f6',
            border: 'none',
            padding: '6px 8px',
            borderRadius: '4px',
            cursor: 'pointer'
          })
          .on('click', function () {
            $(input).val(val).trigger('change');
            $popup.remove();
          })
          .on('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              $(this).trigger('click');
            }
          })
          .appendTo($hourRow);
      });

      $popup.append($hourRow);
    }

    $('body').append($popup);

    const rect = (anchorEl && anchorEl.getBoundingClientRect()) || input.getBoundingClientRect();
    const top = rect.bottom + window.scrollY + 6;
    let left = rect.left + window.scrollX;
    if (left + $popup.outerWidth() > window.innerWidth - 8) {
      left = window.innerWidth - $popup.outerWidth() - 8;
    }

    $popup.css({ left: left + 'px', top: top + 'px' });

    setTimeout(function () {
      $(document).on('click.rsTimePicker', function (e) {
        if (!$popup.is(e.target) && $popup.has(e.target).length === 0 && e.target !== anchorEl) {
          $popup.remove();
        }
      });
    }, 0);

    $(document).on('keydown.rsTimePicker', function (e) {
      if (e.key === 'Escape') $popup.remove();
    });

    const observer = new MutationObserver(function () {
      if (!document.body.contains($popup[0])) {
        $(document).off('click.rsTimePicker keydown.rsTimePicker');
        observer.disconnect();
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  try {
    window.showCustomTimePicker = showCustomTimePicker;
  } catch (e) {
    // ignore global assignment issues
  }

  function markTables(availableList) {
    const $groups = $('svg .table-group');

    if (availableList === null || availableList === undefined) {
      $groups.removeClass('disabled').attr('aria-disabled', 'false').attr('tabindex', '0');
      return;
    }

    const availableSet = new Set();
    $.each(availableList || [], function (_, t) {
      const tid = t.table_id || t.id || t.table || '';
      const tnum = t.table_number || t.number || '';

      if (tid !== undefined && tid !== null && String(tid).length) availableSet.add(String(tid));
      if (tnum !== undefined && tnum !== null && String(tnum).length) {
        availableSet.add(String(tnum));
        availableSet.add('T' + String(tnum));
      }
      if (typeof tid === 'string' && tid.length) availableSet.add(tid);
    });

    if (availableSet.size === 0) {
      $groups.addClass('disabled').attr('aria-disabled', 'true').attr('tabindex', '-1').removeClass('selected');
      return;
    }

    $groups.each(function () {
      const $g = $(this);
      const id = ($g.attr('data-table') || this.id || '').toString();
      if (!id) return;

      if (availableSet.has(id)) {
        $g.removeClass('disabled').attr('aria-disabled', 'false').attr('tabindex', '0');
      } else {
        $g.addClass('disabled').attr('aria-disabled', 'true').attr('tabindex', '-1').removeClass('selected');
      }
    });

    const selectedVal = $('#selected_table_input').val();
    if (selectedVal && !availableSet.has(String(selectedVal))) {
      $('#selected_table_input').val('');
      $('#selected-table-display').text('None');
    }
  }

  function fetchAvailable() {
    const $dateInput = $('input[type="date"][aria-label="Reservation date"]');
    const $timeInput = $('input[type="time"][aria-label="Reservation time"]');
    const $partySelect = $('#party_size_select');
    if (!$dateInput.length || !$timeInput.length || !$partySelect.length) return alert('Reservation inputs not found.');

    const date = $dateInput.val();
    const time = $timeInput.val();
    const party_size = $partySelect.val();

    if (!date || !time) return alert('Please choose both a date and time.');
    const dateValidation = validateDate(date);
    if (!dateValidation.ok) return alert(dateValidation.message);
    if (!party_size) return alert('Please choose a party size.');

    const $showButton = $('#show-available-btn').length
      ? $('#show-available-btn')
      : $('button').filter(function () {
          return ($(this).text() || '').toLowerCase().indexOf('show available') !== -1;
        }).first();

    const timeValidation = validateTime(time);
    if (!timeValidation.ok) return alert(timeValidation.message);

    if ($showButton.length) $showButton.prop('disabled', true);

    $.ajax({
      url: '/reservations/available/',
      method: 'POST',
      contentType: 'application/json',
      headers: { 'X-CSRFToken': csrftoken || '' },
      data: JSON.stringify({ date: date, time: time, party_size: party_size })
    })
      .done(function (data) {
        const available = data.available || data.available_tables || data.tables || [];
        markTables(available);
      })
      .fail(function (xhr) {
        if (xhr.status === 403) {
          alert('Please sign in to check availability.');
          return;
        }
        alert('Failed to check availability: Server returned ' + xhr.status);
      })
      .always(function () {
        if ($showButton.length) $showButton.prop('disabled', false);
      });
  }

  function updateReservationSummary() {
    const dateVal = $('input[type="date"][aria-label="Reservation date"]').val() || '';
    const timeVal = $('input[type="time"][aria-label="Reservation time"]').val() || '';
    const partyVal = $('#party_size_select').val() || '';
    const tableVal = $('#selected_table_input').val() || '';

    const $dtEl = $('#reservation-summary-datetime');
    const $detailsEl = $('#reservation-summary-details');
    if (!$dtEl.length || !$detailsEl.length) return;

    if (dateVal && timeVal) {
      try {
        const d = new Date(dateVal + 'T' + timeVal);
        const dateFmt = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' }).format(d);
        const timeFmt = new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(d);
        $dtEl.text(dateFmt + ' - ' + timeFmt);
      } catch (e) {
        $dtEl.text(dateVal + ' - ' + timeVal);
      }
    } else if (dateVal && !timeVal) {
      try {
        const d = new Date(dateVal + 'T00:00');
        const dateFmt = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' }).format(d);
        $dtEl.text(dateFmt + ' - no time selected');
      } catch (e) {
        $dtEl.text(dateVal + ' - no time selected');
      }
    } else {
      $dtEl.text('No date or time selected');
    }

    const parts = [];
    if (partyVal) parts.push(partyVal + (partyVal === '1' ? ' Person' : ' Persons'));
    if (tableVal) parts.push('Table ' + tableVal);

    if (parts.length === 0) $detailsEl.text('No party size or table selected');
    else $detailsEl.text(parts.join(' · '));
  }

  function confirmReservation() {
    const $dateInput = $('input[type="date"][aria-label="Reservation date"]');
    const $timeInput = $('input[type="time"][aria-label="Reservation time"]');
    const $partySelect = $('#party_size_select');
    const $selectedInput = $('#selected_table_input');

    if (!$dateInput.length || !$timeInput.length || !$partySelect.length || !$selectedInput.length) {
      return alert('Form not found.');
    }

    const date = $dateInput.val();
    const time = $timeInput.val();
    const party_size = $partySelect.val();
    const rawTableId = $selectedInput.val();

    let table_id = rawTableId;
    const m = String(rawTableId || '').match(/(\d+)$/);
    if (m) table_id = m[1];

    if (!date || !time) return alert('Please choose date and time.');
    if (!table_id) return alert('Please select a table.');

    const $confirmButton = $('#confirm-reservation-btn').length
      ? $('#confirm-reservation-btn')
      : $('button').filter(function () {
          return ($(this).text() || '').toLowerCase().indexOf('confirm reservation') !== -1;
        }).first();

    const timeValidation = validateTime(time);
    if (!timeValidation.ok) {
      if ($confirmButton.length) $confirmButton.prop('disabled', false);
      return alert(timeValidation.message);
    }

    if ($confirmButton.length) $confirmButton.prop('disabled', true);

    $.ajax({
      url: '/reservations/confirm/',
      method: 'POST',
      contentType: 'application/json',
      headers: { 'X-CSRFToken': csrftoken || '' },
      data: JSON.stringify({ date: date, time: time, party_size: party_size, table_id: table_id })
    })
      .done(function (data) {
        if (data.error) {
          alert(data.error);
          return;
        }
        if (data.next) {
          window.location.href = data.next;
          return;
        }
        if (data.reservation_id) {
          alert('Reservation confirmed (ID: ' + data.reservation_id + ')');
          return;
        }
        alert('Reservation confirmed.');
      })
      .fail(function (xhr) {
        if (xhr.status === 403) {
          const next = window.location.pathname + window.location.search;
          window.location.href = '/accounts/login/?next=' + encodeURIComponent(next);
          return;
        }
        alert('Failed to confirm reservation: Server returned ' + xhr.status);
      })
      .always(function () {
        if ($confirmButton.length) $confirmButton.prop('disabled', false);
      });
  }

  function attachHandlers() {
    const $groups = $('svg .table-group');

    $groups.attr('role', 'button');
    $groups.each(function () {
      const $g = $(this);
      if (!$g.attr('tabindex')) $g.attr('tabindex', '0');
    });

    $groups.on('click', function () {
      onSelect(this);
    });

    $groups.on('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onSelect(this);
      }
    });

    const $partySelect = $('#party_size_select');
    if ($partySelect.length) {
      $partySelect.on('change', function () {
        const allowed = allowedSeatsForParty($partySelect.val());
        $('svg .table-group').each(function () {
          const $g = $(this);
          const seats = parseInt($g.attr('data-seats') || '0', 10);
          if (allowed === 0 || seats === allowed) $g.removeClass('disabled');
          else $g.addClass('disabled');
        });
        updateReservationSummary();
      });
    }

    const $dateInput = $('input[type="date"][aria-label="Reservation date"]');
    const $timeInput = $('input[type="time"][aria-label="Reservation time"]');

    $dateInput.on('change', updateReservationSummary);
    $timeInput.on('change', updateReservationSummary);

    if ($dateInput.length) {
      try {
        const now = new Date();
        const localToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const minIso = localToday.toISOString().slice(0, 10);
        $dateInput.attr('min', minIso);
      } catch (e) {
        // ignore
      }
    }

    $(window).on('table:selected', updateReservationSummary);

    let $showButton = $('#show-available-btn');
    let $confirmButton = $('#confirm-reservation-btn');

    if (!$showButton.length || !$confirmButton.length) {
      const $card = $('.bg-white.rounded-lg.shadow.p-6').first();
      if ($card.length) {
        const $cardButtons = $card.find('button');
        if (!$showButton.length && $cardButtons.length >= 1) $showButton = $($cardButtons.get(0));
        if (!$confirmButton.length && $cardButtons.length >= 1) $confirmButton = $($cardButtons.get($cardButtons.length - 1));
      }
    }

    if ($showButton.length) {
      $showButton.on('click', function (e) {
        e.preventDefault();
        fetchAvailable();
      });
    }

    if ($confirmButton.length) {
      $confirmButton.on('click', function (e) {
        e.preventDefault();
        confirmReservation();
      });
    }

    updateReservationSummary();
  }

  $(attachHandlers);
})(jQuery);
