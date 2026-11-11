"use strict";

const report = window.REHEARSAL;
const sourceStatus = window.SOURCES;
const select = id => document.getElementById(id);
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
const groupNames = { "Mainland Visitors": "内地访客", "Other Visitors": "其他访客" };
const number = new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 0 });
const compact = new Intl.NumberFormat("zh-CN", { notation: "compact", maximumFractionDigits: 1 });
let roundIndex = 0;
let chartRows = [];

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

function drawChart() {
  if (!chartRows.length) return;
  const canvas = select("chart");
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  if (!width || !height) return;
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.round(width * ratio);
  canvas.height = Math.round(height * ratio);
  const ctx = canvas.getContext("2d");
  ctx.scale(ratio, ratio);
  const left = width < 490 ? 45 : 58;
  const right = width - 18;
  const top = 12;
  const bottom = height - 28;
  const max = Math.max(1, ...chartRows.flatMap(row => row.slice(1)));
  const min = Math.max(0, Math.min(...chartRows.map(row => Math.min(row[1], row[3]))) - max * .08);
  const peak = max * 1.08;
  const x = i => left + (right - left) * i / 14;
  const y = value => bottom - (bottom - top) * (value - min) / (peak - min);
  ctx.fillStyle = "#eef3f6";
  ctx.fillRect(left, top, (right - left) / 28, bottom - top);
  ctx.font = "11px system-ui";
  ctx.fillStyle = "#526477";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  for (let i = 0; i <= 4; i++) {
    const value = min + (peak - min) * i / 4;
    ctx.strokeStyle = "#e0e8eb";
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
  ctx.fillStyle = "rgba(12, 156, 134, .20)";
  ctx.fill();
  for (const [column, color] of [[2, "#007d71"], [1, "#14263a"]]) {
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.2;
    ctx.beginPath();
    chartRows.forEach((row, i) => ctx.lineTo(x(i), y(row[column])));
    ctx.stroke();
    ctx.fillStyle = color;
    chartRows.forEach((row, i) => {
      ctx.beginPath();
      ctx.arc(x(i), y(row[column]), 2.6, 0, 2 * Math.PI);
      ctx.fill();
    });
  }
}

function render() {
  const round = report.rounds[roundIndex];
  const port = select("port").value;
  const group = select("group").value;
  const model = select("model").value;
  const index = report.series.findIndex(([p, g]) => p === port && g === group);
  chartRows = round.data.filter(row => row[1] === index).map(([day, , actual, values]) => [day, actual, ...values[model]]);
  select("chart-title").textContent = (portNames[port] || port) + " · " + groupNames[group];
  select("chart-subtitle").textContent = round.origin + " 至 " + round.end + " · " + report.models[model];
  select("workbook").href = "exports/rehearsal-round-" + round.number + ".xlsx";
  select("workbook").title = "练习 Excel 含该轮 Chronos-2 + 日历的全部 20 条序列";
  const scores = round.scores[model];
  select("scores").replaceChildren(...[
    ["本轮 MASE", scores.mase.toFixed(3)],
    ["本轮缩放 Winkler", scores.winkler.toFixed(3)],
    ["本轮区间覆盖率", (scores.coverage * 100).toFixed(1) + "%"],
  ].map(([label, value]) => {
    const box = document.createElement("div");
    box.append(element("dt", label), element("dd", value));
    return box;
  }));
  replaceTable("daily", chartRows.map(([day, ...values]) => [day, ...values.map(value => number.format(value))]));
  replaceTable("releases", round.baselineReleases.map(release => [release.release, release.historyThrough, release.mase.toFixed(3)]));
  document.querySelectorAll(".round").forEach((button, i) => button.setAttribute("aria-pressed", String(roundIndex === i)));
  drawChart();
}

fillOptions("port", [...new Set(report.series.map(([port]) => port))].map(port => [port, portNames[port] || port]));
fillOptions("group", Object.entries(groupNames));
fillOptions("model", Object.entries(report.models));
for (const id of ["port", "group", "model"]) select(id).addEventListener("change", render);
report.rounds.forEach((round, i) => {
  const button = element("button", "");
  button.type = "button";
  button.className = "round";
  button.append(element("b", "第 " + round.number + " 轮"), element("span", round.origin));
  button.addEventListener("click", () => { roundIndex = i; render(); });
  select("rounds").append(button);
});

const templates = new Set(sourceStatus.templateRounds);
replaceTable("schedule", report.rounds.map(round => [
  "第 " + round.number + " 轮",
  round.officialReleases[0] + " 至 " + round.officialReleases[2],
  round.official + " 23:59",
  round.official + " 至 " + round.officialEnd,
  templates.has(round.number) ? "已发布" : sourceStatus.organizerError ? "本次未核实" : "待发布",
]));
select("checked").textContent = "最近一次来源检查 " + sourceStatus.checkedAt;
const live = sourceStatus.passengers;
select("passenger-status").textContent = "模拟快照覆盖 " + report.source.first_date + " 至 " + report.source.last_date
  + "。 " + (live ? "当前公开源可见到 " + live.through + "。" : "本次未取得更新的官方客流。");
select("template-status").textContent = sourceStatus.organizerError ? "本次未核实发布状态。" :
  (sourceStatus.database ? "训练库已发布" : "训练库待发布") + "，已发布模板 " + templates.size + " / 5 轮。";
new ResizeObserver(drawChart).observe(select("chart"));
render();
