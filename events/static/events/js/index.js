async function fetchEvents() {
  const category = document.getElementById("category").value;
  const city = document.getElementById("city").value;
  const search = document.getElementById("search").value;
  const startDate = document.getElementById("start_date").value;

  let url = "/api/events/?";
  if (category) url += `category=${encodeURIComponent(category)}&`;
  if (city) url += `city=${encodeURIComponent(city)}&`;
  if (startDate) url += `start_date=${encodeURIComponent(startDate)}T00:00&`;

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
        const item = document.createElement("div");
        item.className = "list-group-item";
        item.innerHTML = `
          <h5>${e.title}</h5>
          <p>${e.description || ""}</p>
          <small>
            ${e.category || ""} | ${e.venue || ""} (${e.city || ""}) |
            ${new Date(e.date).toLocaleString()}
          </small>
        `;
        eventList.appendChild(item);
      });
    }
  } catch (err) {
    console.error("Error fetching events:", err);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  fetchEvents();
  document.getElementById("filter-form").addEventListener("input", fetchEvents);
});
