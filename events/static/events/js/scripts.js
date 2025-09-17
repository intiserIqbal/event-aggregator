let map;
let markers = [];
let markerMap = {};

document.addEventListener("DOMContentLoaded", async () => {
  // Initialize map
  map = L.map("map").setView([23.8103, 90.4125], 12);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors"
  }).addTo(map);

  await populateDropdownFilters();
  restoreFilters();
  fetchEvents();

  // Filter listeners
  document.getElementById("filter-form").addEventListener("input", () => {
    saveFilters();
    fetchEvents();
  });

  document.getElementById("clear-filters").addEventListener("click", () => {
    localStorage.removeItem("filters");
    document.getElementById("filter-form").reset();
    fetchEvents();
  });

  document.querySelectorAll(".quick-filter").forEach(btn => {
    btn.addEventListener("click", (e) => {
      document.querySelectorAll(".quick-filter").forEach(b => b.classList.remove('active'));
      e.currentTarget.classList.add('active');
      applyQuickFilter(e.currentTarget.dataset.mode);
    });
  });
});

async function populateDropdownFilters() {
  try {
    const res = await fetch("/api/events/");
    const events = await res.json();

    const categorySet = new Set();
    const citySet = new Set();

    events.forEach(e => {
      if (e.category) categorySet.add(e.category);
      if (e.city) citySet.add(e.city);
    });

    const categorySelect = document.getElementById("category");
    const citySelect = document.getElementById("city");

    categorySelect.innerHTML = `<option value="">All Categories</option>`;
    citySelect.innerHTML = `<option value="">All Cities</option>`;

    Array.from(categorySet).sort().forEach(cat => {
      const opt = document.createElement("option");
      opt.value = cat;
      opt.textContent = cat;
      categorySelect.appendChild(opt);
    });

    Array.from(citySet).sort().forEach(c => {
      const opt = document.createElement("option");
      opt.value = c;
      opt.textContent = c;
      citySelect.appendChild(opt);
    });
  } catch (err) {
    console.error("Error populating filters:", err);
  }
}

function saveFilters() {
  const filters = {
    search: document.getElementById("search").value,
    city: document.getElementById("city").value,
    category: document.getElementById("category").value,
    start_date: document.getElementById("start_date").value
  };
  localStorage.setItem("filters", JSON.stringify(filters));
}

function restoreFilters() {
  const saved = localStorage.getItem("filters");
  if (saved) {
    const f = JSON.parse(saved);
    document.getElementById("search").value = f.search || "";
    document.getElementById("city").value = f.city || "";
    document.getElementById("category").value = f.category || "";
    document.getElementById("start_date").value = f.start_date || "";
  }
}

function applyQuickFilter(mode) {
  const now = new Date();
  const todayISO = now.toISOString().slice(0, 10);
  if (mode === 'today') {
    document.getElementById('start_date').value = todayISO;
  } else if (mode === 'weekend') {
    const d = new Date();
    const day = d.getDay();
    const daysToFriday = (5 - day + 7) % 7;
    d.setDate(d.getDate() + daysToFriday);
    document.getElementById('start_date').value = d.toISOString().slice(0, 10);
  } else {
    document.getElementById('start_date').value = "";
  }
  saveFilters();
  fetchEvents();
}

async function fetchEvents() {
  const category = document.getElementById("category").value;
  const city = document.getElementById("city").value;
  const search = document.getElementById("search").value;
  const startDate = document.getElementById("start_date").value;

  let url = "/api/events/?";
  if (category) url += `category=${encodeURIComponent(category)}&`;
  if (city) url += `city=${encodeURIComponent(city)}&`;
  if (startDate) url += `start_date=${encodeURIComponent(startDate)}T00:00&`;

  const loadingEl = document.getElementById("loading");
  loadingEl.style.display = "block";

  try {
    const res = await fetch(url);
    const events = await res.json();

    const filtered = events.filter(e => !search || e.title.toLowerCase().includes(search.toLowerCase()));

    const list = document.getElementById("event-list");
    list.innerHTML = "";

    if (filtered.length === 0) {
      list.innerHTML = `<div class="col-12"><div class="p-4 text-center text-muted">No events found. Try changing filters or <a href="/upload/">upload a CSV</a>.</div></div>`;
    } else {
      filtered.forEach(e => {
        const img = e.image_url && e.image_url.trim() !== ""
          ? e.image_url
          : `https://picsum.photos/seed/${encodeURIComponent(e.title)}/400/250`;

        const hasCoords = e.latitude && e.longitude;
        const col = document.createElement("div");
        col.className = "col-12";

        col.innerHTML = `
          <div class="card-event">
            <img class="thumb" src="${img}" alt="">
            <div class="meta">
              <h5>${escapeHtml(e.title)}</h5>
              <p class="small mb-1">${escapeHtml(e.description || '')}</p>
              <div class="small text-muted">${escapeHtml(e.category || '')} • ${escapeHtml(e.venue || '')} • ${new Date(e.date).toLocaleString()}</div>
              <div class="small text-muted">Uploaded by ${escapeHtml(e.owner || "Unknown")}</div>
              <div class="badges">
                ${e.is_free ? '<span class="badge-cta">Free</span>' : ''}
                ${e.is_almost_full ? '<span class="badge badge-danger">Almost full</span>' : ''}
                ${hasCoords ? `<button class="btn btn-sm btn-outline-primary btn-view btn-view-map" data-id="${e.id}">View on Map</button>` : `<div class="text-muted small">No map location</div>`}
              </div>
            </div>
          </div>
        `;
        list.appendChild(col);
      });
    }

    markers.forEach(m => map.removeLayer(m));
    markers = [];
    markerMap = {};

    filtered.forEach(e => {
      if (e.latitude && e.longitude) {
        const marker = L.marker([e.latitude, e.longitude]).addTo(map);
        marker.bindPopup(`<b>${escapeHtml(e.title)}</b><br>${escapeHtml(e.venue || '')}<br>${new Date(e.date).toLocaleString()}`);
        markers.push(marker);
        markerMap[e.id] = marker;
      }
    });

    if (markers.length > 0) {
      const group = new L.featureGroup(markers);
      map.fitBounds(group.getBounds().pad(0.2));
    }

    document.querySelectorAll('.btn-view-map').forEach(btn => {
      btn.addEventListener('click', (ev) => {
        const id = ev.currentTarget.dataset.id;
        const mk = markerMap[id];
        if (mk) {
          map.setView(mk.getLatLng(), 15);
          mk.openPopup();
        }
      });
    });

  } catch (err) {
    console.error(err);
  } finally {
    loadingEl.style.display = "none";
  }
}

function escapeHtml(s) {
  return String(s)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}
