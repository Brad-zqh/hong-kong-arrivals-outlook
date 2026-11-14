"use strict";

(() => {
  const map = document.querySelector("#checkpoint-explorer");
  const { overview, harbour, inset } = window.CHECKPOINT_LOCATIONS;
  const picture = map.querySelector(".checkpoint-map-image");
  const viewport = map.querySelector(".checkpoint-viewport");
  const markers = map.querySelector(".checkpoint-markers");
  const selector = map.querySelector("select");
  const name = map.querySelector(".checkpoint-name");
  const mode = map.querySelector(".checkpoint-mode");
  const link = map.querySelector(".checkpoint-forecast");
  const tabs = [...map.querySelectorAll("[data-map-view]")];
  const points = [...overview, ...harbour];
  const t = siteLanguage.text;
  const names = { Airport: "Hong Kong International Airport", "Hong Kong-Zhuhai-Macao Bridge": "Hong Kong–Zhuhai–Macao Bridge Hong Kong Port" };
  const modes = { Air: "航空", Road: "公路", Rail: "铁路", Sea: "海路" };
  let selected = points[0];
  let view = "overview";
  let zoom = false;

  const label = point => t(point.zh, names[point.en] || point.en);

  function render() {
    const close = view === "harbour";
    const canvas = map.querySelector(".checkpoint-map-canvas");
    canvas.classList.toggle("is-zoomed", zoom);
    picture.src = `assets/checkpoint-${view}.webp`;
    picture.width = 1440;
    picture.height = close ? 936 : 1080;
    picture.alt = close ? t("维多利亚港街道地图", "Victoria Harbour street map") : t("香港城市路网地图", "Hong Kong street map");
    selector.replaceChildren(...points.map(point => new Option(`${point.id} · ${label(point)}`, String(point.id))));
    selector.value = String(selected.id);
    name.textContent = label(selected);
    mode.textContent = t(modes[selected.mode], selected.mode);
    const target = new URL("rehearsals.html", location.href);
    target.searchParams.set("port", selected.en);
    target.searchParams.set("lang", t("zh", "en"));
    link.href = target.href;
    for (const tab of tabs) tab.setAttribute("aria-pressed", String(tab.dataset.mapView === view));
    const visible = close ? harbour : overview;
    markers.replaceChildren(...visible.map(point => {
      const marker = document.createElement("button");
      marker.type = "button";
      marker.className = "checkpoint-marker";
      marker.dataset.point = point.id;
      marker.dataset.mode = point.mode;
      marker.style.left = `${point.x}%`;
      marker.style.top = `${point.y}%`;
      marker.textContent = point.id;
      marker.title = label(point);
      marker.setAttribute("aria-label", `${point.id} · ${label(point)}`);
      marker.setAttribute("aria-pressed", String(point.id === selected.id));
      marker.addEventListener("click", () => choose(point, true));
      return marker;
    }));
    if (!close) {
      const insetButton = document.createElement("button");
      insetButton.type = "button";
      insetButton.className = "checkpoint-marker checkpoint-inset";
      insetButton.style.left = `${inset[0]}%`;
      insetButton.style.top = `${inset[1]}%`;
      insetButton.textContent = "8–10 ↗";
      insetButton.setAttribute("aria-label", t("放大维港的三个口岸", "Open the three Victoria Harbour checkpoints"));
      insetButton.addEventListener("click", () => choose(harbour[0], true));
      markers.append(insetButton);
    }
  }

  function choose(point, focusMarker = false) {
    selected = point;
    view = harbour.includes(point) ? "harbour" : "overview";
    render();
    viewport.scrollLeft = (point.x / 100) * markers.clientWidth - viewport.clientWidth / 2;
    if (focusMarker) markers.querySelector(`[data-point="${point.id}"]`).focus({ preventScroll: true });
  }

  selector.addEventListener("change", () => choose(points.find(point => point.id === Number(selector.value))));
  for (const tab of tabs) {
    tab.addEventListener("click", () => choose((tab.dataset.mapView === "harbour" ? harbour : overview)[0]));
  }
  map.querySelector(".checkpoint-zoom").addEventListener("click", event => {
    zoom = !zoom;
    event.currentTarget.setAttribute("aria-pressed", String(zoom));
    render();
  });
  document.addEventListener("site-language-change", render);
  render();
  map.hidden = false;
})();
