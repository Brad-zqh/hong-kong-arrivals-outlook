"use strict";

const report = window.REHEARSAL;
const sourceStatus = window.SOURCES;
const experiment = window.MULTIMODAL;
const select = id => document.getElementById(id);
const hasRehearsals = Boolean(select("forecast"));
const hasSchedule = Boolean(select("schedule"));
const t = siteLanguage.text;
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
  "Mainland Visitors": ["内地访客", "Mainland visitors"],
  "Other Visitors": ["其他访客", "Other visitors"],
};
const historicalModels = {
  chronos_joint_calendar: ["Chronos-2 + 日历", "Chronos-2 + calendar"],
  weekday_mean4: ["四周同星期均值", "Four-week weekday mean"],
};
const mediaModels = experiment && Object.fromEntries(Object.entries(experiment.labels)
  .map(([key, label]) => [key, [label, experiment.labelsEn[key]]]));
const number = new Intl.NumberFormat("en-HK", { maximumFractionDigits: 0 });
const compact = new Intl.NumberFormat("en-HK", { notation: "compact", maximumFractionDigits: 1 });
const portName = name => t(portNames[name] || name, name === "Airport" ? "Hong Kong International Airport" : name);
const dateRange = (start, end) => start + " – " + end;
const roundName = n => t(`第 ${n} 轮`, `Round ${n}`);
let roundIndex = 0;

function element(tag, content) {
  const node = document.createElement(tag);
  node.textContent = content;
  return node;
}

function localized(node, zh, en) {
  const english = element("span", en);
  const chinese = element("span", zh);
  english.className = "copy-en";
  chinese.className = "copy-zh";
  node.append(english, chinese);
  return node;
}

function fillOptions(id, entries) {
  const input = select(id);
  const value = input.value;
  input.replaceChildren(...entries.map(([key, label]) => new Option(label, key)));
  if (entries.some(([key]) => key === value)) input.value = value;
}

const labels = entries => Object.entries(entries).map(([key, pair]) => [key, t(...pair)]);

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

function drawChart(canvas, chartRows, selected) {
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
  const values = chartRows.flatMap(row => row.slice(1));
  const max = Math.max(1, ...values);
  const low = Math.min(...values);
  const span = Math.max(1, max - low);
  const step = plotStep(span);
  const min = Math.max(0, Math.floor((low - span * .05) / step) * step);
  const peak = Math.ceil((max + span * .05) / step) * step;
  const last = chartRows.length - 1;
  const x = i => left + (right - left) * i / last;
  const y = value => bottom - (bottom - top) * (value - min) / (peak - min);
  ctx.fillStyle = "#e9f0f9";
  ctx.fillRect(left, top, (right - left) / (2 * last), bottom - top);
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
  const tickStep = width < 510 ? 4 : 2;
  const ticks = chartRows.map((_, index) => index)
    .filter(index => index === last || (index % tickStep === 0 && index <= last - tickStep));
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
  const columns = [[2, "--plot-line", []], [1, "--ink", [6, 4]]];
  for (const [column, property, dash] of columns) {
    const color = theme.getPropertyValue(property).trim();
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.2;
    ctx.setLineDash(dash);
    ctx.beginPath();
    chartRows.forEach((row, i) => ctx.lineTo(x(i), y(row[column])));
    ctx.stroke();
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(x(selected), y(chartRows[selected][column]), 4, 0, 2 * Math.PI);
    ctx.fill();
  }
}

function chartControl(canvasId, readoutId, inputId) {
  const canvas = select(canvasId);
  const readout = select(readoutId);
  const input = select(inputId);
  let rows = [];
  let selected = 0;
  function update() {
    if (!rows.length) return;
    const [day, actual, point, low, high] = rows[selected];
    const date = element("time", day);
    date.dateTime = day;
    const dateItem = element("span", t("日期", "Date"));
    dateItem.append(date);
    const parts = [
      [t("预测", "Forecast"), number.format(point)],
      [t("实况", "Observed"), number.format(actual)],
      [t("70% 区间", "70% interval"), number.format(low) + "–" + number.format(high)],
    ];
    const values = parts.map(([label, value]) => {
      const item = element("span", label);
      item.append(element("strong", value));
      return item;
    });
    readout.replaceChildren(dateItem, ...values);
    input.value = selected;
    input.setAttribute("aria-valuetext", [day, ...parts.map(([label, value]) => `${label} ${value}`)].join(", "));
    drawChart(canvas, rows, selected);
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
  canvas.addEventListener("pointermove", event => {
    if (event.pointerType === "mouse" || event.buttons === 1) pointAt(event);
  });
  input.addEventListener("input", () => {
    selected = input.valueAsNumber;
    update();
  });
  new ResizeObserver(() => drawChart(canvas, rows, selected)).observe(canvas);
  return (data, preserveDate) => {
    rows = data;
    if (!preserveDate) selected = 0;
    input.max = rows.length - 1;
    update();
  };
}

function renderRehearsal(setChart, preserveDate) {
  const round = report.rounds[roundIndex];
  const port = select("port").value;
  const group = select("group").value;
  const model = select("model").value;
  const index = report.series.findIndex(([p, g]) => p === port && g === group);
  const chartRows = round.data.filter(row => row[1] === index).map(([day, , actual, values]) => [day, actual, ...values[model]]);
  select("chart-title").textContent = portName(port);
  select("chart-subtitle").textContent = dateRange(round.origin, round.end) + " · " + t(...historicalModels[model]);
  const historyEnd = round.releases.at(-1).historyThrough;
  select("chart-data-cutoff").textContent = t(...groupNames[group]) + " · " + t("客流输入截至", "Arrivals through") + " " + historyEnd;
  select("workbook").href = new URL(`exports/rehearsal-round-${round.number}.xlsx`, siteRoot).href;
  select("workbook").title = t("练习 Excel 含该轮 Chronos-2 + 日历的全部 20 条序列",
    "Workbook with all 20 series from Chronos-2 + calendar");
  const scores = round.scores[model];
  select("scores").replaceChildren(...[
    ["MASE", "MASE", scores.mase.toFixed(3)],
    ["缩放 Winkler", "Scaled Winkler", scores.winkler.toFixed(3)],
    ["区间覆盖率", "Interval coverage", (scores.coverage * 100).toFixed(1) + "%"],
  ].map(([label, english, value]) => {
    const box = document.createElement("div");
    box.append(element("dt", t(label, english)), element("dd", value));
    return box;
  }));
  replaceTable("daily", chartRows.map(([day, ...values]) => [day, ...values.map(value => number.format(value))]));
  replaceTable("releases", round.releases.map(release => [
    release.release, release.archiveAt, release.historyThrough, release.scores[model].mase.toFixed(3),
  ]));
  document.querySelectorAll(".round").forEach((button, i) => button.setAttribute("aria-pressed", String(roundIndex === i)));
  setChart(chartRows, preserveDate === true);
}

const ports = [...new Set(report.series.map(([port]) => port))];
function renderOptions() {
  const portOptions = ports.map(port => [port, portName(port)]);
  if (hasRehearsals) {
    fillOptions("port", portOptions);
    fillOptions("group", labels(groupNames));
    fillOptions("model", labels(historicalModels));
  }
  if (experiment) {
    fillOptions("media-round", report.rounds.map(({ number }) => [String(number), roundName(number)]));
    fillOptions("media-port", portOptions);
    fillOptions("media-group", labels(groupNames));
    fillOptions("media-model", labels(mediaModels));
  }
}
renderOptions();
document.addEventListener("site-language-change", renderOptions);

function renderSchedule() {
  const templates = new Set(sourceStatus.templateRounds);
  select("schedule").replaceChildren(...report.rounds.map(round => {
    const row = document.createElement("tr");
    row.setAttribute("role", "row");
    const heading = element("th", roundName(round.number));
    heading.scope = "row";
    heading.setAttribute("role", "rowheader");
    row.append(heading);
    const dates = document.createElement("span");
    dates.className = "schedule-release";
    round.officialReleases.forEach(day => {
      const time = element("time", day);
      time.dateTime = `${day}T12:00+08:00`;
      dates.append(time);
    });
    const deadline = element("time", round.official + " 23:59");
    deadline.dateTime = `${round.official}T23:59+08:00`;
    const forecastDates = document.createElement("span");
    forecastDates.className = "schedule-window";
    forecastDates.append(element("time", round.official), " – ", element("time", round.officialEnd));
    const template = templates.has(round.number) ? t("已发布", "Published") :
      sourceStatus.organizerError ? t("本次未核实", "Unverified") : t("待发布", "Pending");
    for (const [label, value] of [
      [t("数据发布", "Releases"), dates], [t("提交截止", "Deadline"), deadline],
      [t("预测日期", "Forecast dates"), forecastDates], [t("模板", "Template"), template],
    ]) {
      const cell = document.createElement("td");
      cell.setAttribute("role", "cell");
      const mobileLabel = element("span", label);
      mobileLabel.className = "schedule-label";
      mobileLabel.setAttribute("aria-hidden", "true");
      cell.append(mobileLabel, value);
      row.append(cell);
    }
    return row;
  }));
  select("checked").textContent = t("更新检查", "Last checked") + " · " + sourceStatus.checkedAt;
  const live = sourceStatus.passengers;
  const coverageDates = dateRange(report.source.first_date, report.source.last_date);
  select("passenger-status").textContent = t("核验数据", "Validation data") + " · " + coverageDates
    + (live ? " · " + t("公开源截至", "Public data through") + " " + live.through : "");
  const templateCount = templates.size;
  select("template-status").textContent = sourceStatus.organizerError
    ? t("发布状态待核实", "Release status unverified")
    : (sourceStatus.database ? t("训练库已发布", "Training data published") : t("训练库待发布", "Training data pending"))
      + " · " + t("模板", "Templates") + " " + templateCount + "/5";
}
if (hasSchedule) {
  renderSchedule();
  document.addEventListener("site-language-change", renderSchedule);
}

if (hasRehearsals) {
  const setChart = chartControl("chart", "chart-readout", "chart-day");
  const render = preserveDate => renderRehearsal(setChart, preserveDate);
  for (const id of ["port", "group", "model"]) select(id).addEventListener("change", render);
  report.rounds.forEach((round, i) => {
    const button = element("button", "");
    button.type = "button";
    button.className = "round";
    const label = localized(document.createElement("b"), `第 ${round.number} 轮`, `Round ${round.number}`);
    const date = element("time", round.origin);
    date.dateTime = round.origin;
    button.append(label, date);
    button.addEventListener("click", () => { roundIndex = i; render(); });
    select("rounds").append(button);
  });
  for (const metric of ["mase", "winkler"]) {
    const best = report.rounds.map(r => r.scores.chronos_joint_calendar[metric]).sort((a, b) => a - b).slice(0, 4);
    select("hero-" + metric).textContent = (best.reduce((a, b) => a + b, 0) / 4).toFixed(3);
  }
  render();
  document.addEventListener("site-language-change", () => render(true));
}

if (experiment) {
  const setMediaChart = chartControl("media-chart", "media-readout", "media-day");
  const modelChoices = [];
  function renderExperiment(preserveDate) {
    const round = select("media-round").value;
    const port = select("media-port").value;
    const group = select("media-group").value;
    const model = select("media-model").value;
    const seriesIndex = experiment.series.findIndex(([p, g]) => p === port && g === group);
    const rows = experiment.data[round].filter(row => row[1] === seriesIndex)
      .map(([day, , actual, values]) => [day, actual, ...values[model]]);
    select("media-chart-title").textContent = portName(port) + " · " + t(...groupNames[group]);
    select("media-chart-subtitle").textContent = dateRange(rows[0][0], rows.at(-1)[0]) + " · " + t(...mediaModels[model]);
    replaceTable("media-daily", rows.map(([day, ...values]) => [day, ...values.map(value => number.format(value))]));
    for (const button of modelChoices) button.setAttribute("aria-pressed", String(button.value === model));
    setMediaChart(rows, preserveDate === true);
  }
  for (const id of ["media-round", "media-port", "media-group", "media-model"]) {
    select(id).addEventListener("change", renderExperiment);
  }
  const metrics = Object.entries(experiment.metrics);
  replaceTable("media-scores", metrics.map(([key, score]) => [
    "", score.mase.toFixed(3), score.winkler.toFixed(3),
  ]));
  metrics.forEach(([key], index) => {
    const button = localized(document.createElement("button"), ...mediaModels[key]);
    button.type = "button";
    button.className = "model-choice";
    button.value = key;
    button.addEventListener("click", () => {
      select("media-model").value = key;
      renderExperiment();
    });
    select("media-scores").rows[index].cells[0].append(button);
    modelChoices.push(button);
  });
  for (const [index, metric] of ["mase", "winkler"].entries()) {
    const best = Math.min(...metrics.map(([, scores]) => scores[metric]));
    const bestIndex = metrics.findIndex(([, score]) => score[metric] === best);
    select("media-scores").rows[bestIndex].cells[index + 1].classList.add("best-score");
  }
  renderExperiment();
  document.addEventListener("site-language-change", () => renderExperiment(true));
} else if (select("multimodal")) {
  select("multimodal").hidden = true;
}
