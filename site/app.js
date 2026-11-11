"use strict";

const report = window.REHEARSAL;
const sourceStatus = window.SOURCES;
const experiment = window.MULTIMODAL;
const select = id => document.getElementById(id);
const english = document.documentElement.lang === "en";
const t = (chinese, translation) => english ? translation : chinese;
const siteRoot = new URL(".", document.currentScript.src);
const portNames = {
  "Airport": "香港国际机场",
  "Express Rail Link West Kowloon": "西九龙高铁站",
  "Lok Ma Chau Spur Line": "落马洲支线",
  "Shenzhen Bay": "深圳湾",
  "Lo Wu": "罗湖",
  "Hong Kong-Zhuhai-Macao Bridge": "港珠澳大桥",
  "Heung Yuen Wai": "香园围",
  "Macau Ferry Terminal": "港澳客轮码头",
  "Man Kam To": "文锦渡",
  "China Ferry Terminal": "中国客运码头",
};
const groupNames = {
  "Mainland Visitors": t("内地访客", "Mainland visitors"),
  "Other Visitors": t("其他访客", "Other visitors"),
};
const historicalModels = english ? {
  chronos_joint_calendar: "Chronos-2 + calendar",
  weekday_mean4: "Four-week same-weekday mean",
} : report.models;
const mediaModels = experiment && (english ? experiment.labelsEn : experiment.labels);
const number = new Intl.NumberFormat(t("zh-CN", "en-HK"), { maximumFractionDigits: 0 });
const compact = new Intl.NumberFormat(t("zh-CN", "en-HK"), { notation: "compact", maximumFractionDigits: 1 });
const portName = name => english ? name : portNames[name] || name;
const dateRange = (start, end) => start + t(" 至 ", " to ") + end;
const roundName = n => t(`第 ${n} 轮`, `Round ${n}`);
let roundIndex = 0;

function element(tag, content) {
  const node = document.createElement(tag);
  node.textContent = content;
  return node;
}

function fillOptions(id, entries) {
  select(id).replaceChildren(...entries.map(([value, label]) => new Option(label, value)));
}

function replaceTable(id, rows) {
  select(id).replaceChildren(...rows.map(cells => {
    const tr = document.createElement("tr");
    for (const value of cells) tr.append(element("td", value));
    return tr;
  }));
}

function plotInsets(width) {
  return { left: width < 490 ? 44 : 56, right: width - 18 };
}

function plotStep(span) {
  const rough = span / 4;
  const unit = 10 ** Math.floor(Math.log10(rough));
  return [1, 2, 5, 10].find(factor => factor * unit >= rough) * unit;
}

function drawChart(canvas, chartRows, selected, historical) {
  if (!chartRows.length) return;
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  if (!width || !height) return;
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.round(width * ratio);
  canvas.height = Math.round(height * ratio);
  const ctx = canvas.getContext("2d");
  ctx.scale(ratio, ratio);
  const { left, right } = plotInsets(width);
  const top = 12;
  const bottom = height - 28;
  const values = chartRows.flatMap(row => row.slice(historical ? 1 : 2));
  const max = Math.max(1, ...values);
  const low = Math.min(...values);
  const span = Math.max(1, max - low);
  const step = plotStep(span);
  const min = Math.max(0, Math.floor((low - span * .05) / step) * step);
  const peak = Math.ceil((max + span * .05) / step) * step;
  const last = chartRows.length - 1;
  const x = i => left + (right - left) * i / last;
  const y = value => bottom - (bottom - top) * (value - min) / (peak - min);
  if (historical) {
    ctx.fillStyle = "#e9f0f9";
    ctx.fillRect(left, top, (right - left) / (2 * last), bottom - top);
  }
  ctx.font = "11px system-ui";
  ctx.fillStyle = "#526477";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  for (let value = min; value <= peak + step / 10; value += step) {
    ctx.strokeStyle = "#e0e9f5";
    ctx.beginPath();
    ctx.moveTo(left, y(value));
    ctx.lineTo(right, y(value));
    ctx.stroke();
    ctx.fillText(compact.format(value), left - 6, y(value));
  }
  ctx.textAlign = "center";
  const ticks = width < 510 ? [0, 4, 9, 14] : [0, 2, 4, 6, 8, 10, 12, 14];
  for (const index of ticks) ctx.fillText(chartRows[index][0].slice(5), x(index), bottom + 14);
  ctx.beginPath();
  chartRows.forEach((row, i) => ctx.lineTo(x(i), y(row[4])));
  for (let i = chartRows.length - 1; i >= 0; i--) ctx.lineTo(x(i), y(chartRows[i][3]));
  ctx.closePath();
  const theme = getComputedStyle(canvas);
  ctx.fillStyle = theme.getPropertyValue("--plot-band").trim();
  ctx.fill();
  ctx.strokeStyle = "#93b2d6";
  ctx.setLineDash([3, 3]);
  ctx.beginPath();
  ctx.moveTo(x(selected), top);
  ctx.lineTo(x(selected), bottom);
  ctx.stroke();
  ctx.setLineDash([]);
  const columns = [[2, theme.getPropertyValue("--plot-line").trim()]];
  if (historical) columns.push([1, theme.getPropertyValue("--ink").trim()]);
  for (const [column, color] of columns) {
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.2;
    ctx.beginPath();
    chartRows.forEach((row, i) => ctx.lineTo(x(i), y(row[column])));
    ctx.stroke();
    ctx.fillStyle = color;
    chartRows.forEach((row, i) => {
      ctx.beginPath();
      ctx.arc(x(i), y(row[column]), i === selected ? 4 : 2.25, 0, 2 * Math.PI);
      ctx.fill();
    });
  }
}

function chartControl(canvasId, readoutId, historical) {
  const canvas = select(canvasId);
  const readout = select(readoutId);
  let rows = [];
  let selected = 0;
  function update() {
    if (!rows.length) return;
    const [day, actual, point, low, high] = rows[selected];
    const parts = [day, t("点预测 ", "Forecast ") + number.format(point)];
    if (historical) parts.push(t("实况 ", "Observed ") + number.format(actual));
    parts.push(t("70% 区间 ", "70% interval ") + number.format(low) + "–" + number.format(high));
    readout.textContent = parts.join(" · ");
    drawChart(canvas, rows, selected, historical);
  }
  function pointAt(event) {
    if (!rows.length) return;
    const bounds = canvas.getBoundingClientRect();
    const { left, right } = plotInsets(bounds.width);
    const index = Math.round((event.clientX - bounds.left - left) / (right - left) * (rows.length - 1));
    const next = Math.max(0, Math.min(rows.length - 1, index));
    if (next !== selected) { selected = next; update(); }
  }
  canvas.addEventListener("pointerdown", pointAt);
  canvas.addEventListener("pointermove", event => { if (event.pointerType === "mouse") pointAt(event); });
  canvas.addEventListener("keydown", event => {
    if (!rows.length || !["ArrowLeft", "ArrowRight"].includes(event.key)) return;
    event.preventDefault();
    const delta = event.key === "ArrowRight" ? 1 : -1;
    selected = Math.max(0, Math.min(rows.length - 1, selected + delta));
    update();
  });
  new ResizeObserver(update).observe(canvas);
  return data => { rows = data; selected = 0; update(); };
}

const setHistoricalChart = chartControl("chart", "chart-readout", true);
const setMediaChart = chartControl("media-chart", "media-readout", false);

function render() {
  const round = report.rounds[roundIndex];
  const port = select("port").value;
  const group = select("group").value;
  const model = select("model").value;
  const index = report.series.findIndex(([p, g]) => p === port && g === group);
  const chartRows = round.data.filter(row => row[1] === index).map(([day, , actual, values]) => [day, actual, ...values[model]]);
  select("chart-title").textContent = portName(port) + " · " + groupNames[group];
  select("chart-subtitle").textContent = dateRange(round.origin, round.end) + " · " + historicalModels[model];
  select("workbook").href = new URL(`exports/rehearsal-round-${round.number}.xlsx`, siteRoot).href;
  select("workbook").title = t("练习 Excel 含该轮 Chronos-2 + 日历的全部 20 条序列",
    "Workbook with all 20 series from Chronos-2 + calendar");
  const scores = round.scores[model];
  select("scores").replaceChildren(...[
    [t("本轮 MASE", "Round MASE"), scores.mase.toFixed(3)],
    [t("本轮缩放 Winkler", "Round scaled Winkler"), scores.winkler.toFixed(3)],
    [t("本轮区间覆盖率", "Round interval coverage"), (scores.coverage * 100).toFixed(1) + "%"],
  ].map(([label, value]) => {
    const box = document.createElement("div");
    box.append(element("dt", label), element("dd", value));
    return box;
  }));
  replaceTable("daily", chartRows.map(([day, ...values]) => [day, ...values.map(value => number.format(value))]));
  replaceTable("releases", round.releases.map(release => [
    release.release, release.archiveAt, release.historyThrough, release.scores[model].mase.toFixed(3),
  ]));
  document.querySelectorAll(".round").forEach((button, i) => button.setAttribute("aria-pressed", String(roundIndex === i)));
  setHistoricalChart(chartRows);
}

const portOptions = [...new Set(report.series.map(([port]) => port))].map(port => [port, portName(port)]);
fillOptions("port", portOptions);
fillOptions("group", Object.entries(groupNames));
fillOptions("model", Object.entries(historicalModels));
for (const id of ["port", "group", "model"]) select(id).addEventListener("change", render);
report.rounds.forEach((round, i) => {
  const button = element("button", "");
  button.type = "button";
  button.className = "round";
  button.setAttribute("aria-label", roundName(round.number) + ", " + round.origin);
  button.append(element("b", roundName(round.number)), element("span", round.origin.slice(5)));
  button.addEventListener("click", () => { roundIndex = i; render(); });
  select("rounds").append(button);
});

const templates = new Set(sourceStatus.templateRounds);
replaceTable("schedule", report.rounds.map(round => [
  roundName(round.number),
  dateRange(round.officialReleases[0], round.officialReleases[2]),
  round.official + " 23:59",
  dateRange(round.official, round.officialEnd),
  templates.has(round.number) ? t("已发布", "Published") :
    sourceStatus.organizerError ? t("本次未核实", "Unverified") : t("待发布", "Pending"),
]));
select("checked").textContent = t("最近一次来源检查 ", "Sources last checked ") + sourceStatus.checkedAt;
const live = sourceStatus.passengers;
const coverageDates = dateRange(report.source.first_date, report.source.last_date);
select("passenger-status").textContent = t(`实绩核验数据覆盖 ${coverageDates}。`, `The validation data cover ${coverageDates}.`)
  + (live ? t(` 当前公开源可见到 ${live.through}。`, ` Public records currently run through ${live.through}.`)
    : t(" 本次未取得更新的官方客流。", " Updated official counts were unavailable at the last check."));
const templateCount = templates.size;
select("template-status").textContent = sourceStatus.organizerError
  ? t("本次未核实发布状态。", "Release status could not be verified at the last check.")
  : (sourceStatus.database ? t("训练库已发布。", "Training data published.") : t("训练库待发布。", "Training data pending."))
    + t(` 已发布模板 ${templateCount} / 5 轮。`, ` Templates published for ${templateCount} of 5 rounds.`);
render();

for (const metric of ["mase", "winkler"]) {
  const best = report.rounds.map(r => r.scores.chronos_joint_calendar[metric]).sort((a, b) => a - b).slice(0, 4);
  select("hero-" + metric).textContent = (best.reduce((a, b) => a + b, 0) / 4).toFixed(3);
}

function renderExperiment() {
  const port = select("media-port").value;
  const group = select("media-group").value;
  const model = select("media-model").value;
  const seriesIndex = experiment.series.findIndex(([p, g]) => p === port && g === group);
  const rows = experiment.data.filter(row => row[1] === seriesIndex).map(([day, , values]) => [day, null, ...values[model]]);
  select("media-chart-title").textContent = portName(port) + " · " + groupNames[group];
  select("media-chart-subtitle").textContent = dateRange(experiment.start, experiment.end) + " · " + mediaModels[model];
  replaceTable("media-daily", rows.map(([day, , ...values]) => [day, ...values.map(value => number.format(value))]));
  setMediaChart(rows);
}

if (experiment) {
  fillOptions("media-port", portOptions);
  fillOptions("media-group", Object.entries(groupNames));
  fillOptions("media-model", Object.entries(mediaModels).reverse());
  for (const id of ["media-port", "media-group", "media-model"]) select(id).addEventListener("change", renderExperiment);
  const metrics = Object.entries(experiment.metrics);
  replaceTable("media-scores", metrics.map(([key, score]) => [
    mediaModels[key], score.mase.toFixed(3), score.winkler.toFixed(3),
  ]));
  for (const [index, metric] of ["mase", "winkler"].entries()) {
    const best = Math.min(...metrics.map(([, scores]) => scores[metric]));
    const bestIndex = metrics.findIndex(([, score]) => score[metric] === best);
    select("media-scores").rows[bestIndex].cells[index + 1].classList.add("best-score");
  }
  select("media-score-note").textContent = t("每个模型按第 2–15 天评分，共 1,400 个目标。",
    "Days 2–15 were scored for 1,400 targets per model.");
  const postCount = number.format(experiment.posts);
  select("media-posts").textContent = t(`${postCount} 条帖子已编码`, `${postCount} posts encoded`);
  select("media-counts").replaceChildren(...[
    [t("正文", "Post text"), experiment.counts.text], [t("配图", "Photos"), experiment.counts.photo],
    [t("封面", "Thumbnails"), experiment.counts.thumbnail], [t("原视频", "Original videos"), experiment.counts.video],
  ].map(([label, count]) => {
    const box = document.createElement("div");
    box.append(element("dt", label), element("dd", number.format(count)));
    return box;
  }));
  const cutoff = experiment.cutoff.slice(0, 16).replace("T", " ");
  select("media-cutoff").textContent = t(`明细覆盖北京时间 ${cutoff} 前已取得的近 28 天内容。`,
    `Counts cover the 28 days of content available before ${cutoff} Beijing time.`);
  renderExperiment();
} else {
  select("multimodal").hidden = true;
}
