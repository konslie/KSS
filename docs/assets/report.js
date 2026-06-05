
const SOURCE_BADGES = [
  ["Naver Search News", "N", "naver", "Naver Search"],
  ["Naver Search", "N", "naver", "Naver Search"],
  ["DART", "D", "dart", "DART"],
  ["yfinance news", "y", "yfinance", "yfinance"],
  ["yfinance 뉴스", "y", "yfinance", "yfinance"],
  ["yfinance", "y", "yfinance", "yfinance"],
  ["CNBC Markets", "C", "cnbc", "CNBC"],
  ["CNBC", "C", "cnbc", "CNBC"],
].sort((a, b) => b[0].length - a[0].length);

const AUTO_BOLD_TERMS = [
  "오늘의 한줄 요약", "시장 위험도", "핵심 이벤트 3건",
  "하나금융지주", "우리금융지주", "DB손해보험", "현대차2우B",
  "삼성전자", "이수페타시스", "현대바이오", "금호석유화학",
  "SCHD", "Apple", "Nvidia", "Coupang", "Rocket Lab", "Resolve AI",
  "Intuitive Machines", "USD/KRW", "KOSPI", "KOSDAQ", "Nasdaq 100",
  "Nasdaq", "S&P 500", "SOXX", "VIX", "DART", "Naver Search",
  "yfinance", "CNBC", "주의", "확인 필요", "약세", "강세", "상승",
  "하락", "리스크",
].sort((a, b) => b.length - a.length);

const SPARK_VALUES = { "▁": 1, "▂": 2, "▃": 3, "▄": 4, "▅": 5, "▆": 6, "▇": 7, "█": 8 };

document.addEventListener("DOMContentLoaded", () => {
  const app = document.querySelector("#app");
  if (!app) return;
  loadReport(app).catch((error) => {
    app.innerHTML = `<section class="app-error">리포트를 불러오지 못했습니다: ${escapeHtml(error.message)}</section>`;
  });
});

async function loadReport(app) {
  const page = await readReportData(app);
  const report = page.report || page;
  const viewModel = page.view_model || null;
  const archives = JSON.parse(app.dataset.archiveDates || "[]");
  const inArchive = app.dataset.inArchive === "true";
  app.innerHTML = "";
  app.append(renderShell(report, app.dataset.currentDate, archives, inArchive, viewModel));
  document.title = report.title || "KO_데일리브리핑";
}

async function readReportData(app) {
  const embedded = document.querySelector("#report-data");
  if (embedded && embedded.textContent.trim()) {
    return JSON.parse(embedded.textContent);
  }
  const response = await fetch(app.dataset.reportJson, { cache: "no-store" });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

function renderShell(report, currentDate, archives, inArchive, viewModel) {
  const shell = document.createElement("article");
  shell.className = "report-shell";
  shell.append(renderHeader(currentDate, archives, inArchive));
  if (viewModel) shell.append(renderDataDashboard(viewModel, report));
  const content = document.createElement("section");
  content.className = "report-content";
  const elements = viewModel ? reportBodyElements(report.elements || []) : report.elements || [];
  for (const element of elements) {
    content.append(renderElement(element));
  }
  shell.append(content);
  return shell;
}

function reportBodyElements(elements) {
  const visible = [];
  let skipSection = null;
  for (const element of elements) {
    if (element.type === "heading" && element.level === 1) continue;
    if (element.type === "heading" && element.level === 2) {
      const text = element.text || "";
      if (text.includes("주요 거시지표") || text.includes("포트폴리오 영향도")) {
        skipSection = text;
        continue;
      }
      skipSection = null;
    }
    if (skipSection) {
      if (element.type === "table" || element.type === "metrics-meta") continue;
    }
    visible.push(element);
  }
  return visible;
}

function renderHeader(currentDate, archives, inArchive) {
  const header = document.createElement("section");
  header.className = "brief-header";
  if (inArchive) {
    const back = document.createElement("a");
    back.className = "back-link";
    back.href = "../index.html";
    back.textContent = "돌아가기";
    header.append(back);
  }
  const title = document.createElement("p");
  title.className = "brief-title";
  title.textContent = `Latest: ${currentDate} KST`;
  header.append(title);
  const label = document.createElement("span");
  label.textContent = "최근 5일";
  header.append(label);
  const links = document.createElement("div");
  links.className = "brief-links";
  const prefix = inArchive ? "" : "reports/";
  for (const date of archives.slice(0, 5)) {
    const link = document.createElement("a");
    link.href = `${prefix}${date}.html`;
    link.textContent = date;
    links.append(link);
  }
  header.append(links);
  return header;
}

function renderDataDashboard(viewModel, report) {
  const section = document.createElement("section");
  section.className = "data-dashboard";
  section.append(renderHero(report, viewModel));
  section.append(renderSectionHeader("주요 지표", marketDateMeta(viewModel.market_indicators || [], viewModel.date || report.date || ""), "violet"));
  section.append(renderMarketCards(viewModel.market_indicators || []));
  section.append(renderSectionHeader("포트폴리오 현황", "", "gold", sourceLegend()));
  section.append(renderHoldingMatrix(viewModel.holdings || []));
  return section;
}

function marketDateMeta(indicators, fallbackDate) {
  const domestic = indicators.filter((item) => ["KOSPI", "KOSDAQ"].includes(item.name));
  const global = indicators.filter((item) => !["KOSPI", "KOSDAQ"].includes(item.name));
  const domesticDate = groupedDateLabel(domestic, fallbackDate);
  const globalDate = groupedDateLabel(global, fallbackDate);
  return `한국 지표: ${domesticDate} 장 마감 · 미국/글로벌 지표: ${globalDate} 장 마감`;
}

function groupedDateLabel(items, fallbackDate) {
  const dates = uniqueValues(items.map((item) => normalizeDisplayDate(item.as_of_date)));
  if (dates.length === 1) return dates[0];
  if (dates.length > 1) return dates.join(", ");
  return normalizeDisplayDate(fallbackDate);
}

function uniqueValues(values) {
  return [...new Set(values.filter(Boolean))];
}

function normalizeDisplayDate(value) {
  const text = String(value || "").trim();
  const digits = text.replace(/\D/g, "");
  if (digits.length >= 8) return `${digits.slice(0, 4)}-${digits.slice(4, 6)}-${digits.slice(6, 8)}`;
  return text;
}

function renderHero(report, viewModel) {
  const hero = document.createElement("section");
  hero.className = "dashboard-hero";
  const date = viewModel.date || report.date || "";
  const status = viewModel.market_status || {};
  const statusTone = marketStatusTone(status.label);
  hero.innerHTML = `
    <p class="eyebrow">개인 포트폴리오 관련 브리핑</p>
    <h1>${escapeHtml(report.title || "KO_데일리브리핑")}</h1>
    <p>${escapeHtml(date)} · 국내외 시장 & 포트폴리오 요약</p>
    <div class="market-status status-${statusTone}">
      <span>${escapeHtml(status.label || "상태 확인")}</span>
      <strong>${escapeHtml(status.reason || "시장 상태 산정 정보 부족")}</strong>
    </div>
  `;
  return hero;
}

function renderSectionHeader(title, meta = "", accent = "violet", addon = null) {
  const head = document.createElement("div");
  head.className = `dashboard-section-head section-${accent}`;
  head.innerHTML = `
    <div>
      <h2>${escapeHtml(title)}</h2>
      ${meta ? `<p>${meta}</p>` : ""}
    </div>
  `;
  if (addon) head.append(addon);
  return head;
}

function renderMarketCards(indicators) {
  const grid = document.createElement("div");
  grid.className = "market-card-grid";
  for (const indicator of indicators) {
    const price = indicator.price || {};
    const tone = toneFromNumber(price.change_pct);
    const card = document.createElement("article");
    card.className = `market-card market-${tone}`;
    card.innerHTML = `
      <div class="market-copy">
        <p>${escapeHtml(indicator.name || indicator.symbol || "")}</p>
        <span class="prev-value">이전 ${formatPlainNumber(price.previous_close)}</span>
        <strong>${formatPlainNumber(price.latest_close)}</strong>
        <span class="metric-pills"><b>${formatSignedPercent(price.change_pct)}</b><em>${formatSignedNumber(price.change)}</em></span>
        <span class="market-comment">${escapeHtml(indicator.short_comment || "")}</span>
        ${tagList(indicator.risk_tags || [])}
      </div>
      <div class="market-spark">${numericSparkline(price.recent_closes || [], tone)}</div>
    `;
    grid.append(card);
  }
  return grid;
}

function renderHoldingMatrix(holdings) {
  const wrap = document.createElement("section");
  wrap.className = "holding-matrix";

  const table = document.createElement("table");
  table.className = "holding-data-table";
  table.innerHTML = `
    <thead>
      <tr>
        <th>종목</th>
        <th>최신 가격</th>
        <th>등락</th>
        <th>추이 (7일)</th>
        <th>수급</th>
        <th>영향</th>
        <th>핵심 이슈</th>
        <th>한줄 요약</th>
      </tr>
    </thead>
  `;
  const tbody = document.createElement("tbody");
  for (const holding of holdings) {
    const price = holding.price || {};
    const flow = holding.flow || {};
    const latest = flow.latest || {};
    const seven = flow.seven_day_total || {};
    const tone = toneFromNumber(price.change_pct);
    const hasDomesticFlow = holding.market === "KR";
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>
        <strong>${escapeHtml(holding.name || "")}</strong>
        <span>${escapeHtml(holding.symbol || "")} · ${escapeHtml(holding.market || "")}</span>
      </td>
      <td>${formatHoldingPrice(price.latest_close, holding.market)}</td>
      <td>
        <span class="change-pill change-${tone}">${formatSignedPercent(price.change_pct)}</span>
        <span class="change-detail">${formatSignedNumber(price.change, holding.market)}</span>
      </td>
      <td>${numericSparkline(price.recent_closes || [], tone)}</td>
      <td>${hasDomesticFlow ? compactFlowBlock(latest, seven) : `<span class="muted-cell">국내 종목만</span>`}</td>
      <td><span class="impact-pill impact-${impactTone(holding.impact?.label)}">${escapeHtml(holding.impact?.label || "중립")}</span></td>
      <td>
        <div class="issue-cell">
          <strong>${escapeHtml(holding.primary_issue || "특이 신호 제한")}</strong>
          ${tagList((holding.impact?.reasons || []).slice(0, 2))}
          ${dataStatusFlags(holding.data_status || {})}
        </div>
      </td>
      <td><p class="brief-summary">${escapeHtml(holdingBriefSummary(holding))}</p></td>
    `;
    tbody.append(tr);
  }
  table.append(tbody);
  wrap.append(table);
  return wrap;
}

function holdingBriefSummary(holding) {
  const news = holding.news || [];
  const article = news.find((item) => item.title || item.summary);
  if (article) {
    return truncateText(`뉴스: ${article.title || article.summary}`, 74);
  }
  return "확인된 뉴스 없음";
}

function truncateText(text, limit) {
  const normalized = String(text || "").replace(/\s+/g, " ").trim();
  if (normalized.length <= limit) return normalized;
  return `${normalized.slice(0, limit - 1)}…`;
}

function tagList(tags) {
  const clean = (tags || []).filter(Boolean).slice(0, 3);
  if (!clean.length) return "";
  return `<span class="tag-list">${clean.map((tag) => `<i>${escapeHtml(tag)}</i>`).join("")}</span>`;
}

function dataStatusFlags(status) {
  const labels = [];
  if (status.price === "missing") labels.push("가격 확인 필요");
  if (status.flow === "missing") labels.push("수급 확인 필요");
  if (status.news === "empty") labels.push("뉴스 없음");
  if (!labels.length) return "";
  return `<span class="status-flags">${labels.map((label) => `<i>${escapeHtml(label)}</i>`).join("")}</span>`;
}

function impactTone(label) {
  const text = String(label || "");
  if (text.includes("긍정")) return "up";
  if (text.includes("부정")) return "down";
  return "neutral";
}

function marketStatusTone(label) {
  if (label === "위험") return "danger";
  if (label === "주의") return "warning";
  return "neutral";
}

function compactFlowBlock(latest, seven) {
  const foreign = latest.foreign;
  const institution = latest.institution;
  const sevenForeign = seven?.available ? seven.foreign : null;
  return `
    <div class="compact-flow">
      <span class="flow-${toneFromNumber(foreign)}"><b>외인</b>${formatFlow(foreign)}</span>
      <span class="flow-${toneFromNumber(institution)}"><b>기관</b>${formatFlow(institution)}</span>
      ${Number.isFinite(Number(sevenForeign)) ? `<small>7일 외인 ${formatFlow(sevenForeign)}</small>` : ""}
    </div>
  `;
}

function flowBlock(flow) {
  const items = [
    ["기관", flow.institution],
    ["외인", flow.foreign],
    ["개인", flow.individual],
  ];
  return `<div class="flow-stack">${items.map(([label, value]) => {
    const tone = toneFromNumber(value);
    return `<span class="flow-item flow-${tone}"><b>${label}</b>${formatFlow(value)}</span>`;
  }).join("")}</div>`;
}

function renderElement(element) {
  if (element.type === "heading") {
    const heading = document.createElement(`h${element.level}`);
    heading.innerHTML = inlineHtml(element.text, { autoBold: false, sourceBadges: false });
    return heading;
  }
  if (element.type === "metrics-meta") {
    const meta = document.createElement("p");
    meta.className = "metrics-meta";
    meta.textContent = element.text;
    return meta;
  }
  if (element.type === "paragraph") {
    const paragraph = document.createElement("p");
    paragraph.innerHTML = inlineHtml(element.text, { autoBold: element.autoBold, sourceBadges: false });
    return paragraph;
  }
  if (element.type === "list") {
    const list = document.createElement("ul");
    for (const item of element.items || []) {
      const li = document.createElement("li");
      li.innerHTML = inlineHtml(item, { autoBold: element.autoBold, sourceBadges: false });
      list.append(li);
    }
    return list;
  }
  if (element.type === "table") {
    return renderTable(element);
  }
  return document.createTextNode("");
}

function renderTable(element) {
  if (element.className === "portfolio-table") {
    const panel = document.createElement("section");
    panel.className = "portfolio-panel";
    panel.append(sourceLegend());
    panel.append(tableNode(element));
    panel.append(impactLegend());
    return panel;
  }
  return tableNode(element);
}

function tableNode(element) {
  const table = document.createElement("table");
  table.className = `data-table ${element.className}`.trim();
  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  for (const cell of element.header || []) {
    const th = document.createElement("th");
    th.textContent = cell;
    headRow.append(th);
  }
  thead.append(headRow);
  table.append(thead);
  const tbody = document.createElement("tbody");
  for (const row of element.rows || []) {
    const tr = document.createElement("tr");
    row.forEach((cell, index) => {
      const td = document.createElement("td");
      const classes = cellClasses(cell);
      const tableClasses = classes.filter((name) => !name.startsWith("tone-"));
      if (tableClasses.length) td.className = tableClasses.join(" ");
      const isPortfolioRationale = element.className === "portfolio-table" && index > 0;
      const header = element.header[index] || "";
      if (element.className === "portfolio-table" && header === "가격") {
        td.append(renderPriceCell(cell));
      } else if (classes.includes("spark")) {
        td.append(renderSparkline(cell, sparklineTone(row)));
      } else {
        td.innerHTML = wrapTone(
          inlineHtml(cell, { autoBold: false, sourceBadges: isPortfolioRationale }),
          classes,
        );
      }
      tr.append(td);
    });
    tbody.append(tr);
  }
  table.append(tbody);
  return table;
}

function renderPriceCell(text) {
  const raw = String(text || "");
  const [close, detail = ""] = raw.split(/\n|<br\s*\/?>/i, 2);
  const tone = detail.trim().startsWith("-") ? "down" : detail.trim().startsWith("+") ? "up" : "neutral";
  const wrap = document.createElement("div");
  wrap.className = `price-stack price-${tone}`;
  const closeNode = document.createElement("span");
  closeNode.className = "price-close";
  closeNode.textContent = close.trim();
  const detailNode = document.createElement("span");
  detailNode.className = "price-change";
  detailNode.textContent = detail.trim();
  wrap.append(closeNode);
  if (detail.trim()) wrap.append(detailNode);
  return wrap;
}

function inlineHtml(text, { autoBold, sourceBadges }) {
  let result = escapeHtml(text || "");
  result = result.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  if (autoBold) result = autoBoldKeywords(result);
  if (sourceBadges) result = sourceBadgeHtml(result);
  return result;
}

function autoBoldKeywords(text) {
  const protectedStrong = [];
  let result = text.replace(/<strong>.*?<\/strong>/g, (match) => {
    protectedStrong.push(match);
    return `@@STRONG_${protectedStrong.length - 1}@@`;
  });
  AUTO_BOLD_TERMS.forEach((term, index) => {
    result = result.split(escapeHtml(term)).join(`@@AUTO_BOLD_${index}@@`);
  });
  AUTO_BOLD_TERMS.forEach((term, index) => {
    result = result.split(`@@AUTO_BOLD_${index}@@`).join(`<strong>${escapeHtml(term)}</strong>`);
  });
  protectedStrong.forEach((value, index) => {
    result = result.split(`@@STRONG_${index}@@`).join(value);
  });
  return result;
}

function sourceBadgeHtml(text) {
  let result = text;
  const replacements = [];
  SOURCE_BADGES.forEach(([label, initial, sourceClass, title], index) => {
    const token = `@@SOURCE_BADGE_${index}@@`;
    result = result.split(escapeHtml(label)).join(token);
    replacements.push([
      token,
      `<span class="source-badge source-${sourceClass}" title="${escapeHtml(title)}">${escapeHtml(initial)}</span>`,
    ]);
  });
  for (const [token, badge] of replacements) {
    result = result.split(token).join(badge);
  }
  return result;
}

function cellClasses(text) {
  const classes = [];
  if (/[▁▂▃▄▅▆▇█]{3,}/.test(text)) classes.push("spark");
  if (/^\+|\+\d/.test(text)) classes.push("value-up");
  else if (/^-|-\d/.test(text)) classes.push("value-down");
  if (text === "긍정") classes.push("tone-up");
  else if (text === "부정") classes.push("tone-down");
  else if ((text || "").startsWith("중립")) classes.push("tone-neutral");
  return classes;
}

function wrapTone(cell, classes) {
  for (const tone of ["tone-up", "tone-down", "tone-neutral"]) {
    if (classes.includes(tone)) return `<span class="${tone}">${cell}</span>`;
  }
  return cell;
}

function sparklineTone(row) {
  for (const cell of row) {
    const trimmed = String(cell || "").trim();
    if (trimmed.startsWith("+")) return "up";
    if (trimmed.startsWith("-")) return "down";
  }
  return "up";
}

function renderSparkline(text, tone) {
  const values = [...String(text || "")].filter((char) => SPARK_VALUES[char]).map((char) => SPARK_VALUES[char]);
  if (!values.length) {
    const span = document.createElement("span");
    span.textContent = text;
    return span;
  }
  const width = 116;
  const height = 46;
  const padX = 7;
  const padY = 7;
  const usableW = width - padX * 2;
  const usableH = height - padY * 2;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = Math.max(max - min, 1);
  const step = usableW / Math.max(values.length - 1, 1);
  const points = values.map((value, index) => {
    const x = padX + step * index;
    const normalized = (value - min) / span;
    const y = padY + usableH - normalized * usableH;
    return [x, y];
  });
  const path = points.map(([x, y], index) => `${index === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
  const fillPoints = [
    `${points[0][0].toFixed(1)},${(height - padY).toFixed(1)}`,
    ...points.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`),
    `${points[points.length - 1][0].toFixed(1)},${(height - padY).toFixed(1)}`,
  ].join(" ");
  const [lastX, lastY] = points[points.length - 1];
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", `sparkline sparkline-${tone || (values[values.length - 1] >= values[0] ? "up" : "down")}`);
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "7일 추이");
  svg.innerHTML = `
    <line class="sparkline-baseline" x1="${padX}" y1="${height - padY}" x2="${width - padX}" y2="${height - padY}"></line>
    <polygon class="sparkline-fill" points="${fillPoints}"></polygon>
    <path class="sparkline-path" d="${path}"></path>
    <circle class="sparkline-dot" cx="${lastX.toFixed(1)}" cy="${lastY.toFixed(1)}" r="4"></circle>
  `;
  return svg;
}

function numericSparkline(values, tone = "neutral") {
  const nums = values.map((value) => Number(value)).filter((value) => Number.isFinite(value));
  if (!nums.length) return `<span class="muted-cell">미수집</span>`;
  const width = 122;
  const height = 46;
  const padX = 8;
  const padY = 8;
  const min = Math.min(...nums);
  const max = Math.max(...nums);
  const span = Math.max(max - min, 1);
  const usableW = width - padX * 2;
  const usableH = height - padY * 2;
  const step = usableW / Math.max(nums.length - 1, 1);
  const coords = nums.map((value, index) => {
    const x = padX + step * index;
    const y = padY + usableH - ((value - min) / span) * usableH;
    return [x, y];
  });
  const path = coords.map(([x, y], index) => `${index === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
  const [lastX, lastY] = coords[coords.length - 1];
  return `
    <svg class="numeric-spark spark-${tone}" viewBox="0 0 ${width} ${height}" aria-hidden="true">
      <path class="numeric-baseline" d="M${padX} ${(height - padY).toFixed(1)} H${(width - padX).toFixed(1)}"></path>
      <path class="numeric-path numeric-path-shadow" d="${path}"></path>
      <path class="numeric-path" d="${path}"></path>
      <circle class="numeric-dot" cx="${lastX.toFixed(1)}" cy="${lastY.toFixed(1)}" r="2.8"></circle>
    </svg>
  `;
}

function toneFromNumber(value) {
  const number = Number(value);
  if (!Number.isFinite(number) || number === 0) return "neutral";
  return number > 0 ? "up" : "down";
}

function formatPlainNumber(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "확인 필요";
  return number.toLocaleString("ko-KR", { maximumFractionDigits: 2 });
}

function formatHoldingPrice(value, market) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "확인 필요";
  if (market === "US") return `$${number.toLocaleString("en-US", { maximumFractionDigits: 2 })}`;
  return `${number.toLocaleString("ko-KR", { maximumFractionDigits: 0 })}원`;
}

function formatSignedNumber(value, market) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "확인 필요";
  const sign = number > 0 ? "+" : "";
  if (market === "US") return `${sign}$${number.toLocaleString("en-US", { maximumFractionDigits: 2 })}`;
  return `${sign}${number.toLocaleString("ko-KR", { maximumFractionDigits: 0 })}`;
}

function formatSignedPercent(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "확인 필요";
  const sign = number > 0 ? "+" : "";
  return `${sign}${number.toLocaleString("ko-KR", { maximumFractionDigits: 2 })}%`;
}

function formatFlow(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "미수집";
  const direction = number > 0 ? "순매수" : number < 0 ? "순매도" : "중립";
  const abs = Math.abs(number);
  if (abs >= 1000000000000) {
    return `${direction} ${(abs / 1000000000000).toLocaleString("ko-KR", { maximumFractionDigits: 1 })}조`;
  }
  return `${direction} ${Math.round(abs / 100000000).toLocaleString("ko-KR")}억`;
}

function sourceLegend() {
  const legend = document.createElement("div");
  legend.className = "source-legend";
  legend.setAttribute("aria-label", "뉴스 출처 범례");
  for (const [initial, sourceClass, label] of [
    ["N", "naver", "Naver Search"],
    ["D", "dart", "DART"],
    ["y", "yfinance", "yfinance"],
    ["C", "cnbc", "CNBC"],
  ]) {
    const item = document.createElement("span");
    item.innerHTML = `<span class="source-badge source-${sourceClass}">${initial}</span>${escapeHtml(label)}`;
    legend.append(item);
  }
  return legend;
}

function impactLegend() {
  const legend = document.createElement("div");
  legend.className = "impact-legend";
  legend.setAttribute("aria-label", "영향도 기준");
  legend.innerHTML = `
    <span><strong>긍정</strong> 가격/공시/뉴스 흐름이 보유 종목에 우호적</span>
    <span><strong>중립</strong> 방향성이 제한적이거나 확인 필요</span>
    <span><strong>부정</strong> 가격 약세나 리스크 뉴스가 우세</span>
  `;
  return legend;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
