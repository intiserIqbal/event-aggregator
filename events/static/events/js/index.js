let map;
let markers = [];
let markerMap = {}; // store markers by event ID for quick lookup

document.addEventListener("DOMContentLoaded", async () => {
  map = L.map("map").setView([23.8103, 90.4125], 12);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors"
  }).addTo(map);

  await populateFilters();
  restoreFilters();
  fetchEvents();

  document.getElementById("filter-form").addEventListener("input", () => {
    saveFilters();
    fetchEvents();
  });

  document.getElementById("clear-filters").addEventListener("click", () => {
    localStorage.removeItem("filters");
    document.getElementById("filter-form").reset();
    fetchEvents();
  });
});

async function populateFilters() {
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
    const filters = JSON.parse(saved);
    document.getElementById("search").value = filters.search || "";
    document.getElementById("city").value = filters.city || "";
    document.getElementById("category").value = filters.category || "";
    document.getElementById("start_date").value = filters.start_date || "";
  }
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

    const filtered = events.filter(e =>
      !search || e.title.toLowerCase().includes(search.toLowerCase())
    );

    const eventList = document.getElementById("event-list");
    eventList.innerHTML = "";

    if (filtered.length === 0) {
      eventList.innerHTML = "<p>No events found.</p>";
    } else {
      filtered.forEach(e => {
        const hasCoords = e.latitude && e.longitude;
        const item = document.createElement("div");
        item.className = "list-group-item";
        item.innerHTML = `
          <h5>${e.title}</h5>
          <p>${e.description || ""}</p>
          <small>
            ${e.category || ""} | ${e.venue || ""} (${e.city || ""}) |
            ${new Date(e.date).toLocaleString()}
          </small>
          ${
            hasCoords
              ? `<button class="btn btn-sm btn-outline-primary mt-2 view-map" data-id="${e.id}">View on Map</button>`
              : `<div class="text-muted mt-1"><em>No map location available</em></div>`
          }
        `;
        eventList.appendChild(item);
      });
    }

    markers.forEach(m => map.removeLayer(m));
    markers = [];
    markerMap = {};

    filtered.forEach(e => {
      if (e.latitude && e.longitude) {
        const marker = L.marker([e.latitude, e.longitude]).addTo(map);
        marker.bindPopup(`
          <b>${e.title}</b><br>
          ${e.venue || ""}, ${e.city || ""}<br>
          ${new Date(e.date).toLocaleString()}
        `);
        markers.push(marker);
        markerMap[e.id] = marker;
      }
    });

    if (markers.length > 0) {
      const group = new L.featureGroup(markers);
      map.fitBounds(group.getBounds().pad(0.2));
    }

    // Attach "View on Map" click events
    document.querySelectorAll(".view-map").forEach(btn => {
      btn.addEventListener("click", e => {
        const id = e.target.dataset.id;
        const marker = markerMap[id];
        if (marker) {
          map.setView(marker.getLatLng(), 15);
          marker.openPopup();
        }
      });
    });

  } catch (err) {
    console.error("Error fetching events:", err);
  } finally {
    loadingEl.style.display = "none";
  }
}
