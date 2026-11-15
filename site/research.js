"use strict";

document.addEventListener("DOMContentLoaded", () => {
  const data = window.forecastStudy;
  const el = (key) => document.getElementById(`research-${key}`);
  const t = siteLanguage.text;
  if (!data) {
    el("replay-status").textContent = t("评估数据暂不可用。", "Evaluation data are unavailable.");
    return;
  }

  const styles = {
    weekday4: ["四周同日基线", "Weekday mean", "#625973", "5 4"],
    direct_ridge: ["岭回归", "Ridge", "#315b91", "2 4"],
    learn_both: ["总量与份额", "Total + shares", "#403990", ""],
    direct_boost: ["梯度提升", "Gradient boosting", "#a62e38", "8 3"],
    chronos_joint_calendar: ["Chronos‑2 与日历", "Chronos‑2 + calendar", "#795223", ""],
    ordinary: ["普通日", "Ordinary days", "#403990", ""],
    holiday: ["公共假日", "Public holidays", "#a62e38", "6 4"],
  };
  const portZh = ["香港国际机场", "广深港高铁西九龙站", "落马洲支线", "深圳湾", "罗湖", "港珠澳大桥", "香园围", "港澳码头", "文锦渡", "中国客运码头"];
  const modelChoices = ["learn_both", "direct_boost", "weekday4", "chronos_joint_calendar"];
  const range = (n, from = 0) => Array.from({length: n}, (_, i) => i + from);
  const legend = (entries) => `<div class="research-keys">${entries.map(([name, color, variant]) => `<span><i class="${variant}" style="--line:${color}"></i>${name}</span>`).join("")}</div>`;
  const modelName = (m) => t(...styles[m].slice(0, 2));
  const modelKey = (m) => [modelName(m), styles[m][2], styles[m][3] ? "dashed" : ""];
  const numbers = (n) => new Intl.NumberFormat(t("zh-HK", "en-HK"), {maximumFractionDigits: 0}).format(n);
  const shortDate = (origin, offset) => {
    const d = new Date(`${origin}T00:00:00Z`);
    d.setUTCDate(d.getUTCDate() + offset);
    return d.toISOString().slice(5, 10);
  };
  const params = new URL(location.href).searchParams;
  const choice = (array, key, fallback) => array.includes(params.get(key)) ? params.get(key) : fallback;
  const requestedDay = Number(params.get("day"));
  const state = {
    origin: choice(data.origins, "origin", "2024-09-23"),
    port: choice(data.ports, "port", "Lo Wu"),
    group: choice(data.groups, "group", data.groups[0]),
    model: choice(modelChoices, "model", "learn_both"),
    day: Number.isInteger(requestedDay) && requestedDay >= 2 && requestedDay <= 15 ? requestedDay : 9,
  };
  const loaded = new Map();
  let current;
  let loading = false;

  function setSelect(name, choices) {
    const select = el(name);
    select.replaceChildren(...choices.map(([value, label]) => new Option(label, value)));
    select.value = state[name];
  }

  function controls() {
    setSelect("origin", data.origins.map((v) => [v, v]));
    setSelect("port", data.ports.map((v, i) => [v, t(portZh[i], v)]));
    setSelect("group", data.groups.map((v, i) => [v, t(["内地访客", "其他访客"][i], v)]));
    setSelect("model", modelChoices.filter((m) => !current || current.models[m]).map((m) => [m, modelName(m)]));
    el("day").value = state.day;
  }

  function shareState() {
    const url = new URL(location.href);
    for (const [key, value] of Object.entries(state)) url.searchParams.set(key, value);
    history.replaceState(null, "", url);
  }

  function selectDay(day) {
    state.day = Math.max(2,Math.min(15,day));
    el("day").value = state.day;
    shareState();
    if (!loading) drawReplay();
    drawSummary(false);
  }

  function fetchOrigin(origin) {
    if (!loaded.has(origin)) {
      const script = document.createElement("script");
      script.src = `research-data/${origin}.js`;
      loaded.set(origin, new Promise((resolve, reject) => {
        script.onload = () => window.forecastReplays?.[origin] ? resolve(window.forecastReplays[origin]) : reject();
        script.onerror = () => reject();
        document.head.append(script);
      }).catch(() => { loaded.delete(origin); script.remove(); throw Error("Archive could not be loaded"); }));
    }
    return loaded.get(origin);
  }

  async function chooseSeries() {
    const origin = state.origin;
    const exists = loaded.has(origin);
    if (!exists) {
      loading = true;
      el("replay-status").textContent = t("正在加载历史窗口……", "Loading the archived window…");
      el("replay").setAttribute("aria-busy", "true");
    }
    try {
      const fold = await fetchOrigin(origin);
      if (origin !== state.origin) return;
      current = fold[data.ports.indexOf(state.port) * data.groups.length + data.groups.indexOf(state.group)];
      const missing = !current.models[state.model];
      if (missing) state.model = "learn_both";
      el("replay-status").textContent = missing
        ? t("此截点无同期 Chronos‑2 结果，已切换至总量与份额。", "Chronos‑2 is unavailable at this origin. Showing total + shares.")
        : "";
      controls();
      shareState();
      drawReplay(true);
    } catch {
      if (origin !== state.origin) return;
      current = undefined;
      for (const k of ["replay", "values", "daily-table"]) el(k).replaceChildren();
      el("replay-status").textContent = t("历史窗口加载失败。请重新选择截点。", "The archive failed to load. Select an issue date to retry.");
    } finally {
      if (origin === state.origin) { loading = false; el("replay").removeAttribute("aria-busy"); }
    }
  }

  function chart(host, {xmin, xmax, ymin, ymax, yticks, xticks, label, height}, render) {
    const w = Math.max(245, Math.floor(host.clientWidth || 500));
    const h = height ?? (w < 460 ? 220 : 258);
    const left = 48, right = w - 15, top = 18, bottom = h - 34;
    const x = (v) => left + (v - xmin) / (xmax - xmin) * (right - left);
    const y = (v) => bottom - (v - ymin) / (ymax - ymin) * (bottom - top);
    const nodes = [];
    const add = (html) => nodes.push(html);
    const ln = (x1, y1, x2, y2, color, dash = "") => `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${color}" stroke-dasharray="${dash}"/>`;
    for (const [v, text] of yticks) {
      add(ln(left, y(v), right, y(v), "#e5e0eb"));
      add(`<text x="${left - 7}" y="${y(v) + 4}" text-anchor="end">${text}</text>`);
    }
    add(ln(left, bottom, right, bottom, "#afa6bb"));
    for (const [v, text] of xticks) add(`<text x="${x(v)}" y="${bottom + 19}" text-anchor="middle">${text}</text>`);
    const points = (pairs) => pairs.map(([a,b]) => `${x(a).toFixed(2)},${y(b).toFixed(2)}`).join(" ");
    const trace = (pairs, color, dash = "", width = 2) => add(`<polyline points="${points(pairs)}" fill="none" stroke="${color}" stroke-width="${width}" stroke-dasharray="${dash}" stroke-linecap="round" stroke-linejoin="round"/>`);
    render({x,y,top,bottom,left,right,trace,add,ln,points,width:w});
    host.innerHTML = `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${label}">${nodes.join("")}</svg>`;
    return {w, x};
  }

  function dataTable(host, heads, rows) {
    host.innerHTML = `<table><thead><tr>${heads.map((h) => `<th scope="col">${h}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr><th scope="row">${row[0]}</th>${row.slice(1).map((v) => `<td>${v}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
  }

  function drawReplay(updateTable = false) {
    if (!current) return;
    const {observed, history: past, holiday, models} = current;
    const host = el("replay");
    const days = range(14,1);
    const values = models[state.model];
    const compare = state.model === "weekday4" ? null : models.weekday4;
    const ymaxRaw = Math.max(...observed,...past,...values.map((r) => r[2]),...(compare ?? []).map((r) => r[0]));
    const roundTo = Math.pow(10, Math.floor(Math.log10(ymaxRaw || 1)) - 1);
    const step = Math.ceil(ymaxRaw / 4 / roundTo) * roundTo || 1;
    const series = (seq, offsets) => seq.map((value,i) => [offsets[i],value]);
    const selected = state.day - 1;
    const ticks = host.clientWidth < 520 ? [-7,0,7,14] : [-7,-4,0,4,8,12,14];
    const info = chart(host, {xmin:-7.4,xmax:14.45,ymin:0,ymax:step*4,
      yticks:range(5).map((i) => [i*step,numbers(i*step)]),xticks:ticks.map((i) => [i,shortDate(state.origin,i)]),
      height:host.clientWidth < 520 ? 220 : 300, label:t("逐日客流、预测和百分之七十区间", "Daily observed arrivals, forecasts and 70 percent prediction interval")},
    ({x,y,top,bottom,trace,add,ln,points}) => {
      for (const i of days.filter((_,j) => holiday[j])) add(`<rect x="${x(i-.48)}" y="${top}" width="${x(i+.43)-x(i-.48)}" height="${bottom-top}" fill="#f6b544" opacity=".14"/>`);
      add(ln(x(0),top,x(0),bottom,"#6f6681","3 4"));
      const upper = points(days.map((v,i) => [v,values[i][2]]));
      const lower = points(days.map((v,i) => [v,values[i][1]]).reverse());
      add(`<polygon points="${upper} ${lower}" fill="#c9c4ee" opacity=".70"/>`);
      trace(series(past,range(7,-7)),"#655d75","",1.5);
      if (compare) trace(series(compare.map((v) => v[0]),days),styles.weekday4[2],styles.weekday4[3],1.5);
      trace(series(values.map((v) => v[0]),days),styles[state.model][2],styles[state.model][3],2.4);
      trace(series(observed,days),"#241d34","",2.15);
      add(ln(x(selected),top,x(selected),bottom,"#766a90","2 3"));
      for (const [v,color] of [[observed[selected-1],"#241d34"],[values[selected-1][0],styles[state.model][2]]]) {
        add(`<circle cx="${x(selected)}" cy="${y(v)}" r="3.7" fill="${color}" stroke="#fff" stroke-width="1.2"/>`);
      }
    });
    const keys = [[t("实况", "Observed"),"#241d34",""],modelKey(state.model),[t("70% 区间", "70% interval"),"#c9c4ee","area"]];
    if (compare) keys.push(modelKey("weekday4"));
    keys.push([t("公共假日", "Public holiday"),"#faeed6","area"]);
    host.insertAdjacentHTML("afterbegin",legend(keys));
    host.querySelector("svg").addEventListener("pointerdown", (event) => {
      const box = event.currentTarget.getBoundingClientRect();
      const p = (event.clientX - box.left) * info.w / box.width;
      if (p < info.x(.5) || p > info.x(14.5)) return;
      selectDay(Math.round((p-info.x(0))/(info.x(1)-info.x(0))) + 1);
    });
    el("day-label").textContent = `${state.day} · ${shortDate(state.origin,selected)}`;
    const entry = values[selected-1];
    const facts = [[t("实况", "Observed"),numbers(observed[selected-1])], [t("点预测", "Point forecast"),numbers(entry[0])],
      [t("区间下界", "Lower bound"),numbers(entry[1])],[t("区间上界", "Upper bound"),numbers(entry[2])]];
    el("values").innerHTML = facts.map(([name,value]) => `<div><dt>${name}</dt><dd>${value}</dd></div>`).join("");
    if (updateTable) dataTable(el("daily-table"),[t("日期", "Date"),...facts.map((r) => r[0])],
      days.map((day,i) => [shortDate(state.origin,day), ...[observed[i],...values[i]].map(numbers)]));
  }

  function bindLead(host, geometry) {
    host.querySelector("svg").addEventListener("pointerdown", (event) => {
      const bounds = event.currentTarget.getBoundingClientRect();
      const position = (event.clientX-bounds.left) * geometry.w / bounds.width;
      if (position < geometry.x(2) || position > geometry.x(15)) return;
      selectDay(2+Math.round((position-geometry.x(2))/(geometry.x(3)-geometry.x(2))));
    });
  }

  function drawSummary(updateTables = true) {
    const models = Object.keys(data.lead);
    const leads = range(14,2);
    const ticks = [2,5,10,15].map((d) => [d,d]);
    const inspect = state.day-2;
    const ymax = Math.max(1.35,Math.ceil(Math.max(...Object.values(data.lead).flat())*10)/10);
    const marker = (x,y,color) => `<circle cx="${x}" cy="${y}" r="3.6" fill="${color}" stroke="#fff" stroke-width="1.1"/>`;
    const errorPlot = chart(el("error"),{xmin:2,xmax:15,ymin:.65,ymax,yticks:[.7,.9,1.1,1.3].filter((v) => v<=ymax).map((v) => [v,v.toFixed(1)]),xticks:ticks,label:t("各提前期的绝对缩放误差", "Mean absolute scaled error by lead")},
      ({trace,x,y,top,bottom,ln,add}) => {
        add(ln(x(state.day),top,x(state.day),bottom,"#9c94aa","3 4"));
        models.forEach((m) => {
          trace(data.lead[m].map((v,i) => [i+2,v]),styles[m][2],styles[m][3]);
          add(marker(x(state.day),y(data.lead[m][inspect]),styles[m][2]));
        });
      });
    el("error").insertAdjacentHTML("afterbegin",legend(models.map(modelKey)));
    bindLead(el("error"),errorPlot);
    const errorValue = models.map((m) => `${modelName(m)} ${data.lead[m][inspect].toFixed(3)}`).join(" · ");
    el("error").insertAdjacentHTML("beforeend",`<p class="research-caption">${t(`第 ${state.day} 天`, `Day ${state.day}`)} · ${errorValue}</p>`);
    if (updateTables) dataTable(el("error-table"),[t("提前期", "Lead"),...models.map(modelName)],leads.map((d,i) => [d,...models.map((m) => data.lead[m][i].toFixed(3))]));

    const coverPlot = chart(el("cover"),{xmin:2,xmax:15,ymin:0,ymax:100,yticks:[0,25,50,70,100].map((v) => [v,`${v}%`]),xticks:ticks,label:t("普通日与假日的区间覆盖率", "Prediction interval coverage on holidays and ordinary days")},
      ({trace,x,y,top,bottom,ln,add}) => {
        add(ln(x(2),y(70),x(15),y(70),"#776f85","3 3"));
        add(ln(x(state.day),top,x(state.day),bottom,"#9c94aa","3 4"));
        for (const type of ["Ordinary","Holiday"]) {
          const key = type.toLowerCase();
          trace(data.cover[type].map(([v],i) => [i+2,100*v]),styles[key][2],styles[key][3]);
          add(marker(x(state.day),y(data.cover[type][inspect][0]*100),styles[key][2]));
        }
      });
    el("cover").insertAdjacentHTML("afterbegin",legend([modelKey("ordinary"),modelKey("holiday"),[t("70% 目标", "70% target"),"#776f85","dashed"]]));
    bindLead(el("cover"),coverPlot);
    const coverValue = ["Ordinary","Holiday"].map((k) => `${modelName(k.toLowerCase())} ${(data.cover[k][inspect][0]*100).toFixed(1)}%`).join(" · ");
    el("cover").insertAdjacentHTML("beforeend",`<p class="research-caption">${t(`第 ${state.day} 天`, `Day ${state.day}`)} · ${coverValue}</p>`);
    if (updateTables) dataTable(el("cover-table"),[t("提前期", "Lead"),t("普通日（样本量）", "Ordinary days (n)"),t("假日（样本量）", "Holidays (n)")],
      leads.map((d,i) => [d,...["Ordinary","Holiday"].map((k) => `${(data.cover[k][i][0]*100).toFixed(1)}% (${data.cover[k][i][1]})`)]));
  }

  for (const name of ["origin","port","group","model"]) el(name).addEventListener("change", (event) => {
    state[name] = event.target.value;
    chooseSeries();
  });
  el("day").addEventListener("input", (event) => selectDay(Number(event.target.value)));
  document.addEventListener("site-language-change", () => { controls(); drawSummary(); drawReplay(true); });
  const sizes = new Map();
  const resize = new ResizeObserver((entries) => {
    if (!entries.some(({target,contentRect}) => sizes.get(target) !== Math.round(contentRect.width))) return;
    for (const {target,contentRect} of entries) sizes.set(target,Math.round(contentRect.width));
    drawSummary(false);
    if (!loading) drawReplay();
  });
  for (const name of ["replay","error","cover"]) resize.observe(el(name));
  controls();
  drawSummary();
  chooseSeries();
});
