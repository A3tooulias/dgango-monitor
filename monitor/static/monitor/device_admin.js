// Autocomplete διεύθυνσης για το πεδίο "Worksite address" στο admin του Device.
// Χρησιμοποιεί το ενσωματωμένο <datalist> του ίδιου του browser - ο browser
// αναλαμβάνει ολόκληρη την εμφάνιση/κύλιση της λίστας μόνος του, χωρίς καμία
// δική μας CSS, άρα καμία πιθανότητα προβλήματος εμφάνισης/scrollbar.
//
// Επίσης εμφανίζει/κρύβει τις ενότητες (fieldsets) ανάλογα με το επιλεγμένο
// "data_source" (αισθητήρας ή AgroMet).
(function () {
  function initAutocomplete() {
    const input = document.getElementById('id_worksite_address');
    if (!input) return;

    input.setAttribute('autocomplete', 'off');

    const datalist = document.createElement('datalist');
    datalist.id = 'worksite-address-suggestions';
    document.body.appendChild(datalist);
    input.setAttribute('list', datalist.id);

    let debounceTimer = null;

    input.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      const query = input.value.trim();
      if (query.length < 3) return;
      debounceTimer = setTimeout(() => search(query), 400);
    });

    async function search(query) {
      try {
        const res = await fetch('/api/geocode-search/?q=' + encodeURIComponent(query));
        const results = await res.json();
        datalist.innerHTML = '';
        results.forEach((r) => {
          const option = document.createElement('option');
          option.value = r.display_name;
          datalist.appendChild(option);
        });
      } catch (e) {
        // αγνόησε σιωπηλά - απλά δεν θα υπάρχουν προτάσεις αυτή τη φορά
      }
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