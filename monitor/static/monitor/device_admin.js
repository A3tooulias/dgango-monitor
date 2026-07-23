// Autocomplete διεύθυνσης για το πεδίο "Worksite address" στο admin του Device.
// Η λίστα προτάσεων τοποθετείται με position:fixed, υπολογισμένη με
// getBoundingClientRect() και προσαρτημένη απευθείας στο <body> - έτσι δεν
// μπορεί να κοπεί/κρυφτεί από κανένα εσωτερικό container του Django admin.
//
// Επίσης εμφανίζει/κρύβει ενότητες (fieldsets) ανάλογα με το "data_source".
(function () {
  function initAutocomplete() {
    const input = document.getElementById('id_worksite_address');
    if (!input) return;

    input.setAttribute('autocomplete', 'off');

    const list = document.createElement('div');
    list.style.cssText = [
      'position:fixed', 'z-index:99999', 'background:#171b20', 'border:1px solid #4a5561',
      'border-radius:6px', 'max-height:320px', 'overflow-y:auto', 'display:none',
      'box-shadow:0 8px 24px rgba(0,0,0,.6)',
    ].join(';');
    document.body.appendChild(list);

    function positionList() {
      const rect = input.getBoundingClientRect();
      list.style.left = rect.left + 'px';
      list.style.top = (rect.bottom + 4) + 'px';
      list.style.width = Math.max(rect.width, 380) + 'px';
    }

    let debounceTimer = null;

    input.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      const query = input.value.trim();
      if (query.length < 3) {
        list.style.display = 'none';
        return;
      }
      debounceTimer = setTimeout(() => search(query), 400);
    });

    window.addEventListener('scroll', () => {
      if (list.style.display !== 'none') positionList();
    }, true);
    window.addEventListener('resize', () => {
      if (list.style.display !== 'none') positionList();
    });

    document.addEventListener('click', (e) => {
      if (e.target !== input && !list.contains(e.target)) list.style.display = 'none';
    });

    async function search(query) {
      try {
        const res = await fetch('/api/geocode-search/?q=' + encodeURIComponent(query));
        const results = await res.json();
        renderResults(results);
      } catch (e) {
        list.style.display = 'none';
      }
    }

    function renderResults(results) {
      list.innerHTML = '';
      if (!results.length) {
        list.style.display = 'none';
        return;
      }
      results.forEach((r) => {
        const item = document.createElement('div');
        item.textContent = r.short_label;
        item.title = r.display_name;
        item.style.cssText = [
          'padding:10px 12px', 'cursor:pointer', 'font-size:.95rem', 'line-height:1.3',
          'color:#e9e7df', 'border-bottom:1px solid #2a3138',
        ].join(';');
        item.addEventListener('mouseenter', () => { item.style.background = '#2c3540'; });
        item.addEventListener('mouseleave', () => { item.style.background = 'transparent'; });
        // mousedown (όχι click) ώστε να προλαβαίνει πριν το input χάσει
        // εστίαση (blur) και κρύψει τη λίστα πριν προλάβει να καταγραφεί το κλικ.
        item.addEventListener('mousedown', (e) => {
          e.preventDefault();
          input.value = r.display_name;  // ΠΛΗΡΗΣ διεύθυνση - εγγυάται σωστή επανα-γεωκωδικοποίηση στο Save
          list.style.display = 'none';
        });
        list.appendChild(item);
      });
      positionList();
      list.style.display = 'block';
    }
  }

  function initDataSourceToggle() {
    const select = document.getElementById('id_data_source');
    if (!select) return;

    function update() {
      const value = select.value;
      document.querySelectorAll('.sensor-fieldset').forEach((el) => {
        el.style.display = value === 'sensor' ? '' : 'none';
      });
      document.querySelectorAll('.agromet-fieldset').forEach((el) => {
        el.style.display = value === 'agromet' ? '' : 'none';
      });
    }

    select.addEventListener('change', update);
    update();
  }

  function init() {
    initAutocomplete();
    initDataSourceToggle();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();