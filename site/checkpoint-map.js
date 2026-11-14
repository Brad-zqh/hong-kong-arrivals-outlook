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
  const names = { Airport: "Hong Kong International Airport", "Hong Kong-Zhuhai-Macao Bridge": "Hong Kong–Zhuhai–Macao Bridge Hong Kong Port", "Express Rail Link West Kowloon": "Hong Kong West Kowloon Station" };
  const modes = { Air: "航空", Road: "公路", Rail: "铁路", Sea: "海路" };
  const platformNames = { x: "X", instagram: "Instagram", tiktok: "TikTok" };
  const setForecast = chartControl("checkpoint-chart", "checkpoint-readout", "checkpoint-day");
  const roundInput = select("checkpoint-round");
  const groupInput = select("checkpoint-group");
  const modelInput = select("checkpoint-model");
  const historyModelKeys = new Set(Object.keys(historicalModels));
  let selected = points[0];
  let view = "overview";
  let zoom = false;

  const label = point => t(point.zh, names[point.en] || point.en);

  function renderForecast(preserveDate = false) {
    const round = report.rounds.find(item => String(item.number) === roundInput.value);
    const group = groupInput.value;
    const model = modelInput.value;
    const history = historyModelKeys.has(model);
    const data = history ? round.data : experiment.data[round.number];
    const series = history ? report.series : experiment.series;
    const index = series.findIndex(([port, visitor]) => port === selected.en && visitor === group);
    const rows = data.filter(row => row[1] === index)
      .map(([date, , actual, values]) => [date, actual, ...values[model]]);
    setForecast(rows, preserveDate === true);
    const target = new URL(history ? "rehearsals.html" : "index.html#multimodal", location.href);
    target.searchParams.set("port", selected.en);
    target.searchParams.set("group", group);
    target.searchParams.set("round", round.number);
    target.searchParams.set("model", model);
    target.searchParams.set("lang", t("zh", "en"));
    link.href = target.href;
  }

  function renderEvidence() {
    const labels = { ...platformNames, weibo: t("微博", "Weibo"), douyin: t("抖音", "Douyin"), xiaohongshu: t("小红书", "Xiaohongshu") };
    const coverage = window.CHECKPOINT_EVIDENCE;
    select("checkpoint-evidence-dates").textContent = dateRange(coverage.first, coverage.last);
    const entries = Object.entries(coverage.ports[selected.id] || {}).sort((left, right) =>
      right[1].reduce((sum, n) => sum + n, 0) - left[1].reduce((sum, n) => sum + n, 0));
    select("checkpoint-evidence-empty").hidden = entries.length > 0;
    replaceTable("checkpoint-evidence-rows", entries.map(([platform, counts]) =>
      [labels[platform], ...counts.map(value => number.format(value))]));
    const example = select("checkpoint-open-example");
    example.replaceChildren();
    if (selected.id === 8) {
      const photo = document.createElement("img");
      photo.src = "assets/west-kowloon.webp";
      photo.loading = "lazy";
      photo.alt = t("香港西九龙站西翼入口", "West entrance of West Kowloon Station");
      photo.width = 1000;
      photo.height = 750;
      const caption = element("small", t("口岸照片示例 · ", "Checkpoint photo example · "));
      const source = element("a", "Qwer132477 · CC BY-SA 4.0");
      source.href = "https://commons.wikimedia.org/wiki/File:Hong_Kong_West_Kowloon_Station_exterior%EF%BC%88West%EF%BC%892021_08_part2.jpg";
      caption.append(source, t(" · 缩放及裁切", " · Resized and cropped"));
      example.append(photo, caption);
    }
    if (harbour.includes(selected)) {
      const clip = element("a", t("附近场景：维港天星小轮视频 ↓", "Nearby scene: Victoria Harbour ferry clip ↓"));
      clip.href = "#harbour-clip";
      example.append(clip);
    }
  }

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
    renderForecast();
    renderEvidence();
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
  function initializeFilters() {
    fillOptions("checkpoint-round", report.rounds.map(round => [String(round.number), roundName(round.number)]));
    fillOptions("checkpoint-group", labels(groupNames));
    fillOptions("checkpoint-model", [...labels(historicalModels), ...labels(mediaModels)]);
  }
  for (const control of [roundInput, groupInput, modelInput]) control.addEventListener("change", renderForecast);
  document.addEventListener("site-language-change", () => {
    initializeFilters();
    render();
    renderForecast(true);
    renderEvidence();
  });
  initializeFilters();
  map.hidden = false;
  choose(selected);
})();
