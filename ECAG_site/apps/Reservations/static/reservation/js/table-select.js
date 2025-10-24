(function(){
  function clearSelection() {
    document.querySelectorAll('.table-group.selected').forEach(g => {
      g.classList.remove('selected');
    });
    var input = document.getElementById('selected_table_input');
    if (input) input.value = '';
    var display = document.getElementById('selected-table-display');
    if (display) display.textContent = 'None';
  }

  function isSelectable(groupEl, partySize) {
    var seats = parseInt(groupEl.getAttribute('data-seats') || '0', 10);
    return seats === partySize;
  }

  function onSelect(groupEl) {
    // ignore clicks on disabled groups
    if (groupEl.classList.contains('disabled')) return;
    clearSelection();
    groupEl.classList.add('selected');
    var tableId = groupEl.getAttribute('data-table') || groupEl.id || '';
    var input = document.getElementById('selected_table_input');
    if (input) input.value = tableId;
    var display = document.getElementById('selected-table-display');
    if (display) display.textContent = tableId || 'None';
    try {
      window.dispatchEvent(new CustomEvent('table:selected', { detail: { tableId: tableId } }));
    } catch (e) { }
  }

  function updateAvailability() {
    var select = document.getElementById('party_size_select');
    var size = parseInt(select && select.value ? select.value : '0', 10);
    var groups = Array.from(document.querySelectorAll('svg .table-group'));
  var allowedSeats = 0;
  if (size <= 2 && size >= 1) allowedSeats = 2;
  else if (size >= 3) allowedSeats = 4;
    groups.forEach(g => {
      var seats = parseInt(g.getAttribute('data-seats') || '0', 10);
      if (allowedSeats === 0) {
        g.classList.remove('disabled');
      } else {
        if (seats === allowedSeats) g.classList.remove('disabled');
        else g.classList.add('disabled');
      }
    });

    var current = document.getElementById('selected_table_input');
    if (current && current.value) {
      var selectedGroup = document.querySelector('svg .table-group.selected');
      if (selectedGroup) {
        var selSeats = parseInt(selectedGroup.getAttribute('data-seats') || '0', 10);
        if (selSeats !== size) {
          clearSelection();
        }
      }
    }
  }

  function attachHandlers() {
    var groups = Array.from(document.querySelectorAll('svg .table-group'));
    groups.forEach(g => {
      g.setAttribute('role','button');
      g.setAttribute('tabindex', '0');
      g.addEventListener('click', function(e){
        onSelect(g);
      });
      g.addEventListener('keydown', function(e){
        if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') {
          e.preventDefault();
          onSelect(g);
        }
      });
    });

    var partySelect = document.getElementById('party_size_select');
    if (partySelect) {
      partySelect.addEventListener('change', function(){
        updateAvailability();
      });
      updateAvailability();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', attachHandlers);
  } else {
    attachHandlers();
  }
})();
