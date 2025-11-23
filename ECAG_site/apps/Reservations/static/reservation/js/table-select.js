(function () {
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
    document.querySelectorAll('.table-group.selected').forEach(g => g.classList.remove('selected'));
    const input = document.getElementById('selected_table_input');
    if (input) input.value = '';
    const display = document.getElementById('selected-table-display');
    if (display) display.textContent = 'None';
  }

  function onSelect(groupEl) {
    if (groupEl.classList.contains('disabled')) return;
    clearSelection();
    groupEl.classList.add('selected');
    const tableId = groupEl.getAttribute('data-table') || groupEl.id || '';
    const input = document.getElementById('selected_table_input');
    if (input) input.value = tableId;
    const display = document.getElementById('selected-table-display');
    if (display) display.textContent = tableId || 'None';
    try { window.dispatchEvent(new CustomEvent('table:selected', { detail: { tableId } })); } catch (e) { }
  }

  // Map party size to allowed seats (conservative)
  function allowedSeatsForParty(partySize) {
    const size = parseInt(partySize || '0', 10);
    if (size <= 2 && size >= 1) return 2;
    if (size >= 3) return 4;
    return 0;
  }

  // Validate time: hours within opening window and minutes in 15-minute increments
  function validateTime(timeStr) {
    if (!timeStr) return { ok: false, message: 'Please choose a time.' };
    const parts = timeStr.split(':');
    if (parts.length < 2) return { ok: false, message: 'Invalid time format.' };
    const hh = parseInt(parts[0], 10);
    const mm = parseInt(parts[1], 10);
    if (Number.isNaN(hh) || Number.isNaN(mm)) return { ok: false, message: 'Invalid time.' };
    // Business hours: open 15:00 - 23:00, last booking start 22:00
    if (hh < 15 || hh > 22) return { ok: false, message: 'Please choose an hour between 15:00 and 22:00.' };
    if (mm % 15 !== 0) return { ok: false, message: 'Please choose minutes in 15-minute increments (00, 15, 30, 45).' };
    return { ok: true };
  }

  // Validate date: must be today or in the future
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

  // Create and show a custom time picker popup near an anchor element.
  // Shows only allowed hours (15..22) and minutes in 15-minute increments.
  function showCustomTimePicker(input, anchorEl) {
    if (!input) return;
    // Close any existing picker
    const existing = document.querySelector('.rs-timepicker-popup');
    if (existing) existing.remove();

    const popup = document.createElement('div');
    popup.className = 'rs-timepicker-popup';
    popup.setAttribute('role', 'dialog');
    popup.setAttribute('aria-label', 'Choose time');
    Object.assign(popup.style, {
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
      overflow: 'auto',
    });

    // Build list of times
    const hours = [];
    for (let h = 15; h <= 22; h++) hours.push(h);
    const minutes = [0, 15, 30, 45];

    hours.forEach(h => {
      const hourRow = document.createElement('div');
      hourRow.style.display = 'flex';
      hourRow.style.gap = '6px';
      hourRow.style.marginBottom = '6px';
      hourRow.style.flexWrap = 'wrap';

      const hrLabel = document.createElement('div');
      hrLabel.textContent = (h < 10 ? '0' + h : '' + h) + ':';
      hrLabel.style.fontWeight = '600';
      hrLabel.style.marginRight = '6px';
      hrLabel.style.flex = '0 0 36px';
      hourRow.appendChild(hrLabel);

      const minList = (h === 22) ? [0] : minutes;
      minList.forEach(m => {
        const btn = document.createElement('button');
        btn.type = 'button';
        const mm = m < 10 ? '0' + m : '' + m;
        const hh = h < 10 ? '0' + h : '' + h;
        btn.textContent = hh + ':' + mm;
        btn.dataset.value = hh + ':' + mm;
        Object.assign(btn.style, {
          background: '#f3f4f6',
          border: 'none',
          padding: '6px 8px',
          borderRadius: '4px',
          cursor: 'pointer',
        });
        btn.addEventListener('click', () => {
          input.value = btn.dataset.value;
          input.dispatchEvent(new Event('change', { bubbles: true }));
          popup.remove();
        });
        btn.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); btn.click(); }
        });
        hourRow.appendChild(btn);
      });

      popup.appendChild(hourRow);
    });

    document.body.appendChild(popup);

    // Position the popup near the anchor or the input
    const rect = (anchorEl && anchorEl.getBoundingClientRect()) || input.getBoundingClientRect();
    const top = rect.bottom + window.scrollY + 6;
    let left = rect.left + window.scrollX;
    // ensure popup within viewport
    if (left + popup.offsetWidth > window.innerWidth - 8) left = window.innerWidth - popup.offsetWidth - 8;
    popup.style.left = (left) + 'px';
    popup.style.top = (top) + 'px';

    // Close on outside click or Esc
    function onDocClick(e) { if (!popup.contains(e.target) && e.target !== anchorEl) popup.remove(); }
    function onEsc(e) { if (e.key === 'Escape') popup.remove(); }
    setTimeout(() => document.addEventListener('click', onDocClick));
    document.addEventListener('keydown', onEsc);

    // Cleanup on remove
    const observer = new MutationObserver(() => {
      if (!document.body.contains(popup)) {
        document.removeEventListener('click', onDocClick);
        document.removeEventListener('keydown', onEsc);
        observer.disconnect();
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  // Expose to global so inline template script can call it
  try { window.showCustomTimePicker = showCustomTimePicker; } catch (e) {}

  function markTables(availableList) {
    const groups = Array.from(document.querySelectorAll('svg .table-group'));
    // Distinguish between "no availability info" (null/undefined)
    // and "explicitly no tables available" (empty array).
    if (availableList === null || availableList === undefined) {
      // No availability info -> enable all (fallback)
      groups.forEach(g => {
        g.classList.remove('disabled');
        g.setAttribute('aria-disabled', 'false');
        g.tabIndex = 0;
      });
      return;
    }

    // Build a set of identifiers that may match the SVG `data-table` values.
    // Server may return numeric `table_id` and `table_number`; SVG uses values like "T10".
    const availableSet = new Set();
    (availableList || []).forEach(t => {
      const tid = t.table_id || t.id || t.table || '';
      const tnum = t.table_number || t.number || '';
      if (tid !== undefined && tid !== null && String(tid).length) availableSet.add(String(tid));
      if (tnum !== undefined && tnum !== null && String(tnum).length) {
        availableSet.add(String(tnum));
        availableSet.add('T' + String(tnum));
      }
      // if server sent a prefixed id already, include it too
      if (typeof tid === 'string' && tid.length) availableSet.add(tid);
    });
    // If server returned an empty array, explicitly disable all tables (none available)
    if (availableSet.size === 0) {
      groups.forEach(g => {
        g.classList.add('disabled');
        g.setAttribute('aria-disabled', 'true');
        g.tabIndex = -1;
        g.classList.remove('selected');
      });
      return;
    }

    groups.forEach(g => {
      const id = (g.getAttribute('data-table') || g.id || '').toString();
      if (!id) return;
      const match = availableSet.has(id);
      if (match) {
        g.classList.remove('disabled');
        g.setAttribute('aria-disabled', 'false');
        g.tabIndex = 0;
      } else {
        g.classList.add('disabled');
        g.setAttribute('aria-disabled', 'true');
        g.tabIndex = -1;
        g.classList.remove('selected');
      }
    });
    // clear selection if no longer available
    const selected = document.getElementById('selected_table_input');
    if (selected && selected.value) {
      if (!availableSet.has(selected.value.toString())) {
        selected.value = '';
        const display = document.getElementById('selected-table-display');
        if (display) display.textContent = 'None';
      }
    }
  }

  async function fetchAvailable() {
    const dateInput = document.querySelector('input[type="date"][aria-label="Reservation date"]');
    const timeInput = document.querySelector('input[type="time"][aria-label="Reservation time"]');
    const partySelect = document.getElementById('party_size_select');
    if (!dateInput || !timeInput || !partySelect) return alert('Reservation inputs not found.');
    const date = dateInput.value;
    const time = timeInput.value;
    const party_size = partySelect.value;
    if (!date || !time) return alert('Please choose both a date and time.');
    // Validate date not in past
    const dateValidation = validateDate(date);
    if (!dateValidation.ok) return alert(dateValidation.message);
    if (!party_size) return alert('Please choose a party size.');

    const showButton = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.toLowerCase().includes('show available'));
    // Validate time against business rules before asking server
    const timeValidation = validateTime(time);
    if (!timeValidation.ok) {
      return alert(timeValidation.message);
    }
    if (showButton) { showButton.disabled = true; }

    try {
      const res = await fetch('/reservations/available/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken || '' },
        body: JSON.stringify({ date, time, party_size })
      });

      if (!res.ok) {
        if (res.status === 403) {
          alert('Please sign in to check availability.');
          return;
        }
        throw new Error('Server returned ' + res.status);
      }

      const data = await res.json();
      const available = data.available || data.available_tables || data.tables || [];
      markTables(available);
    } catch (err) {
      // log suppressed in production
      alert('Failed to check availability: ' + (err.message || err));
    } finally {
      if (showButton) showButton.disabled = false;
    }
  }

  // Update the reservation summary shown on the form
  function updateReservationSummary() {
    const dateInput = document.querySelector('input[type="date"][aria-label="Reservation date"]');
    const timeInput = document.querySelector('input[type="time"][aria-label="Reservation time"]');
    const partySelect = document.getElementById('party_size_select');
    const selectedInput = document.getElementById('selected_table_input');
    const dtEl = document.getElementById('reservation-summary-datetime');
    const detailsEl = document.getElementById('reservation-summary-details');

    const dateVal = dateInput ? dateInput.value : '';
    const timeVal = timeInput ? timeInput.value : '';
    const partyVal = partySelect ? partySelect.value : '';
    const tableVal = selectedInput ? selectedInput.value : '';

    if (!dtEl || !detailsEl) return;

    if (dateVal && timeVal) {
      try {
        const d = new Date(dateVal + 'T' + timeVal);
        const dateFmt = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' }).format(d);
        const timeFmt = new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(d);
        dtEl.textContent = `${dateFmt} — ${timeFmt}`;
      } catch (e) {
        dtEl.textContent = `${dateVal} — ${timeVal}`;
      }
    } else if (dateVal && !timeVal) {
      try {
        const d = new Date(dateVal + 'T00:00');
        const dateFmt = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' }).format(d);
        dtEl.textContent = `${dateFmt} — no time selected`;
      } catch (e) { dtEl.textContent = `${dateVal} — no time selected`; }
    } else {
      dtEl.textContent = 'No date or time selected';
    }

    let parts = [];
    if (partyVal) parts.push(partyVal + (partyVal === '1' ? ' Person' : ' Persons'));
    if (tableVal) parts.push('Table ' + tableVal);
    if (parts.length === 0) detailsEl.textContent = 'No party size or table selected';
    else detailsEl.textContent = parts.join(' · ');
  }

  async function confirmReservation() {
    const dateInput = document.querySelector('input[type="date"][aria-label="Reservation date"]');
    const timeInput = document.querySelector('input[type="time"][aria-label="Reservation time"]');
    const partySelect = document.getElementById('party_size_select');
    const selectedInput = document.getElementById('selected_table_input');
    if (!dateInput || !timeInput || !partySelect || !selectedInput) return alert('Form not found.');
    const date = dateInput.value;
    const time = timeInput.value;
    const party_size = partySelect.value;
    // Normalize table id: template uses IDs like "T5" but server expects numeric table_id
    const rawTableId = selectedInput.value;
    let table_id = rawTableId;
    // If value contains a numeric suffix like 'T5' -> '5'
    const m = String(rawTableId).match(/(\d+)$/);
    if (m) table_id = m[1];
    if (!date || !time) return alert('Please choose date and time.');
    if (!table_id) return alert('Please select a table.');

    const confirmButton = Array.from(document.querySelectorAll('button')).find(b => b.textContent && b.textContent.toLowerCase().includes('confirm reservation'));

    // Validate time on client before sending
    const timeValidation = validateTime(time);
    if (!timeValidation.ok) {
      if (confirmButton) confirmButton.disabled = false;
      return alert(timeValidation.message);
    }
    if (confirmButton) confirmButton.disabled = true;

    try {
      const res = await fetch('/reservations/confirm/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken || '' },
        body: JSON.stringify({ date, time, party_size, table_id })
      });

      if (res.status === 403) {
        // redirect to login
        const next = window.location.pathname + window.location.search;
        window.location.href = '/accounts/login/?next=' + encodeURIComponent(next);
        return;
      }

      if (!res.ok) {
        throw new Error('Server returned ' + res.status);
      }

      const data = await res.json();
      if (data.error) return alert(data.error);
      if (data.next) {
        window.location.href = data.next;
        return;
      }
      if (data.reservation_id) {
        alert('Reservation confirmed (ID: ' + data.reservation_id + ')');
        return;
      }
      alert('Reservation confirmed.');
    } catch (err) {
      // log suppressed in production
      alert('Failed to confirm reservation: ' + (err.message || err));
    } finally {
      if (confirmButton) confirmButton.disabled = false;
    }
  }

  function attachHandlers() {
    const groups = Array.from(document.querySelectorAll('svg .table-group'));
    groups.forEach(g => {
      g.setAttribute('role', 'button');
      if (!g.hasAttribute('tabindex')) g.setAttribute('tabindex', '0');
      g.addEventListener('click', e => onSelect(g));
      g.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect(g); }
      });
    });

    const partySelect = document.getElementById('party_size_select');
    if (partySelect) {
      partySelect.addEventListener('change', function () {
        const allowed = allowedSeatsForParty(partySelect.value);
        const groups = Array.from(document.querySelectorAll('svg .table-group'));
        groups.forEach(g => {
          const seats = parseInt(g.getAttribute('data-seats') || '0', 10);
          if (allowed === 0) g.classList.remove('disabled');
          else if (seats === allowed) g.classList.remove('disabled');
          else g.classList.add('disabled');
        });
        updateReservationSummary();
      });
    }

    // update summary when date/time change
    const dateInput = document.querySelector('input[type="date"][aria-label="Reservation date"]');
    const timeInput = document.querySelector('input[type="time"][aria-label="Reservation time"]');
    if (dateInput) dateInput.addEventListener('change', updateReservationSummary);
    if (timeInput) timeInput.addEventListener('change', updateReservationSummary);

    // enforce minimum date (today) for date input
    if (dateInput) {
      try {
        const now = new Date();
        const localToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const minIso = localToday.toISOString().slice(0, 10);
        dateInput.setAttribute('min', minIso);
      } catch (e) { /* ignore */ }
    }

    // update when a table is selected (custom event)
    try { window.addEventListener('table:selected', updateReservationSummary); } catch (e) {}

    // Wire Show/Confirm buttons — prefer explicit IDs when present
    const buttons = Array.from(document.querySelectorAll('button'));
    let showButton = document.getElementById('show-available-btn') || buttons.find(b => b.textContent && b.textContent.toLowerCase().includes('show available'));
    let confirmButton = document.getElementById('confirm-reservation-btn') || buttons.find(b => b.textContent && b.textContent.toLowerCase().includes('confirm reservation'));

    

    // Fallback: locate the reservation card and use its first/last buttons
    if (!showButton || !confirmButton) {
      const card = document.querySelector('.bg-white.rounded-lg.shadow.p-6');
      if (card) {
        const cardButtons = Array.from(card.querySelectorAll('button'));
        if (!showButton && cardButtons.length >= 1) showButton = cardButtons[0];
        if (!confirmButton && cardButtons.length >= 1) confirmButton = cardButtons[cardButtons.length - 1];
    
      }
    }

    if (showButton) showButton.addEventListener('click', e => { e.preventDefault(); fetchAvailable(); });

    if (confirmButton) confirmButton.addEventListener('click', e => { e.preventDefault(); confirmReservation(); });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', attachHandlers);
  else attachHandlers();

})();
// End of file
