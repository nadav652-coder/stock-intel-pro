/**
 * Stock Intelligence Platform - Frontend Client Application
 * Features: Interactive Charts (Plotly), Live DCF Simulator, Hebrew RTL Rendering
 */

let currentAnalysisData = null;
let currentTicker = "AAPL";

document.addEventListener("DOMContentLoaded", () => {
    initViewSwitcher();
    initSectionTabs();
    initPortfolioManager();
    initSearch();
    initQuickPills();
    initDCFSliders();
    initReportsModal();
    
    // Determine initial ticker: URL hash > URL query param > localStorage > default AAPL
    const hashTicker = window.location.hash.replace("#", "").trim().toUpperCase();
    const queryTicker = new URLSearchParams(window.location.search).get("ticker")?.trim().toUpperCase();
    const savedTicker = localStorage.getItem("lastStockIntelTicker")?.trim().toUpperCase();
    
    const initialTicker = hashTicker || queryTicker || savedTicker || "AAPL";
    analyzeTicker(initialTicker);

    // Support browser back/forward buttons
    window.addEventListener("hashchange", () => {
        const newHash = window.location.hash.replace("#", "").trim().toUpperCase();
        if (newHash && newHash !== currentTicker) {
            analyzeTicker(newHash);
        }
    });
});

function initViewSwitcher() {
    const navStock = document.getElementById("navBtnStock");
    const navPort = document.getElementById("navBtnPortfolio");
    const stockView = document.getElementById("stockViewContainer");
    const portView = document.getElementById("portfolioViewContainer");
    const searchArea = document.getElementById("headerSearchArea");
    const pillsArea = document.getElementById("headerPillsArea");

    if (!navStock || !navPort) return;

    navStock.addEventListener("click", () => {
        navStock.classList.add("active");
        navPort.classList.remove("active");
        stockView.style.display = "block";
        portView.style.display = "none";
        if (searchArea) searchArea.style.display = "block";
        if (pillsArea) pillsArea.style.display = "flex";
    });

    navPort.addEventListener("click", () => {
        navPort.classList.add("active");
        navStock.classList.remove("active");
        stockView.style.display = "none";
        portView.style.display = "block";
        if (searchArea) searchArea.style.display = "none";
        if (pillsArea) pillsArea.style.display = "none";
        refreshPortfolio();
    });
}

function initSectionTabs() {
    document.querySelectorAll(".sec-tab-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".sec-tab-btn").forEach(b => b.classList.remove("active"));
            document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
            
            btn.classList.add("active");
            const targetId = btn.dataset.tab;
            const targetPane = document.getElementById(targetId);
            if (targetPane) {
                targetPane.classList.add("active");
                window.dispatchEvent(new Event('resize'));
            }
        });
    });
}

function initSearch() {
    const input = document.getElementById("tickerInput");
    const btn = document.getElementById("searchBtn");
    const dropdown = document.getElementById("searchDropdown");
    let debounceTimer = null;
    let selectedIndex = -1;
    let currentSuggestions = [];

    const hideDropdown = () => {
        if (dropdown) dropdown.style.display = "none";
        selectedIndex = -1;
    };

    const doSearch = (customVal) => {
        const val = (customVal || input.value).trim();
        hideDropdown();
        if (val) {
            analyzeTicker(val);
        }
    };

    if (btn) btn.addEventListener("click", () => doSearch());

    if (input) {
        input.addEventListener("input", () => {
            clearTimeout(debounceTimer);
            const q = input.value.trim();
            if (!q) {
                hideDropdown();
                return;
            }

            debounceTimer = setTimeout(async () => {
                try {
                    const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
                    const matches = await res.json();
                    currentSuggestions = matches || [];

                    if (!dropdown || currentSuggestions.length === 0) {
                        hideDropdown();
                        return;
                    }

                    dropdown.innerHTML = "";
                    currentSuggestions.forEach((item, idx) => {
                        const div = document.createElement("div");
                        div.className = "dropdown-item";
                        div.dataset.index = idx;
                        div.innerHTML = `
                            <div class="dropdown-info">
                                <span class="dropdown-name">${item.name}</span>
                                <span class="dropdown-desc">${item.desc || ''}</span>
                            </div>
                            <div class="dropdown-meta">
                                <span class="dropdown-type">${item.type || 'מניה'}</span>
                                <span class="dropdown-ticker">${item.ticker}</span>
                            </div>
                        `;
                        div.addEventListener("click", () => {
                            input.value = item.ticker;
                            doSearch(item.ticker);
                        });
                        dropdown.appendChild(div);
                    });

                    dropdown.style.display = "block";
                    selectedIndex = -1;
                } catch (e) {
                    console.error("Search fetch error:", e);
                }
            }, 180);
        });

        input.addEventListener("keydown", (e) => {
            const items = dropdown ? dropdown.querySelectorAll(".dropdown-item") : [];

            if (e.key === "ArrowDown") {
                e.preventDefault();
                if (items.length > 0) {
                    selectedIndex = (selectedIndex + 1) % items.length;
                    items.forEach((it, i) => it.classList.toggle("selected", i === selectedIndex));
                    items[selectedIndex].scrollIntoView({ block: "nearest" });
                }
            } else if (e.key === "ArrowUp") {
                e.preventDefault();
                if (items.length > 0) {
                    selectedIndex = (selectedIndex - 1 + items.length) % items.length;
                    items.forEach((it, i) => it.classList.toggle("selected", i === selectedIndex));
                    items[selectedIndex].scrollIntoView({ block: "nearest" });
                }
            } else if (e.key === "Enter") {
                e.preventDefault();
                if (selectedIndex >= 0 && selectedIndex < currentSuggestions.length) {
                    const chosen = currentSuggestions[selectedIndex];
                    input.value = chosen.ticker;
                    doSearch(chosen.ticker);
                } else {
                    doSearch();
                }
            } else if (e.key === "Escape") {
                hideDropdown();
            }
        });
    }

    // Close dropdown on click outside
    document.addEventListener("click", (e) => {
        if (!e.target.closest("#headerSearchArea")) {
            hideDropdown();
        }
    });
}

function initQuickPills() {
    document.querySelectorAll(".pill-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const ticker = btn.dataset.ticker;
            if (ticker) {
                document.querySelectorAll(".pill-btn").forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                document.getElementById("tickerInput").value = ticker;
                analyzeTicker(ticker);
            }
        });
    });
}

function showLoading(show, message = "מעבד נתונים ומריץ סימולציות...") {
    const overlay = document.getElementById("loadingOverlay");
    const textEl = document.getElementById("loadingSubtext");
    if (show) {
        overlay.style.display = "flex";
        textEl.textContent = message;
    } else {
        overlay.style.display = "none";
    }
}

async function analyzeTicker(ticker) {
    ticker = ticker.toUpperCase().trim();
    currentTicker = ticker;
    
    // Save to localStorage and update URL hash for state persistence across refreshes
    try {
        localStorage.setItem("lastStockIntelTicker", ticker);
        if (window.location.hash !== `#${ticker}`) {
            history.replaceState(null, "", `#${ticker}`);
        }
    } catch (e) {
        console.warn("Storage/history state update failed:", e);
    }

    // Sync input field and active pill state
    const input = document.getElementById("tickerInput");
    if (input) input.value = ticker;
    document.querySelectorAll(".pill-btn").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.ticker === ticker);
    });

    showLoading(true, `שולף דוחות כספיים ומריץ ניתוח עבור ${ticker}...`);

    try {
        const res = await fetch(`/api/stock/${encodeURIComponent(ticker)}`);
        const result = await res.json();

        if (!result.success || !result.data) {
            console.warn("Analysis response note:", result.error);
            showToast(`שגיאה: ${result.error || "לא ניתן היה לאחזר נתונים עבור סימול זה"}`, "error");
            showLoading(false);
            return;
        }

        currentAnalysisData = result.data;
        renderAnalysis(currentAnalysisData);
        showLoading(false);
    } catch (err) {
        console.warn("Fetch notice:", err);
        showLoading(false);
        // Ignore AbortError when user hits F5 (refresh) while request is in-flight
        if (err.name !== "AbortError") {
            showToast("מתחבר לשרת...", "info");
        }
    }
}

function showToast(message, type = "info") {
    let toast = document.getElementById("stockIntelToast");
    if (!toast) {
        toast = document.createElement("div");
        toast.id = "stockIntelToast";
        toast.style.cssText = "position: fixed; bottom: 24px; left: 24px; z-index: 2000; padding: 12px 20px; border-radius: 8px; font-size: 14px; font-weight: 600; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.5); transition: opacity 0.3s ease; opacity: 0; pointer-events: none;";
        document.body.appendChild(toast);
    }
    
    if (type === "error") {
        toast.style.background = "#7F1D1D";
        toast.style.color = "#FCA5A5";
        toast.style.border = "1px solid #EF4444";
    } else {
        toast.style.background = "#1E293B";
        toast.style.color = "#93C5FD";
        toast.style.border = "1px solid #3B82F6";
    }

    toast.textContent = message;
    toast.style.opacity = "1";
    setTimeout(() => {
        toast.style.opacity = "0";
    }, 3500);
}

function renderAnalysis(data) {
    const profile = data.profile;
    const synth = data.synthesis;
    const fund = data.fundamental;
    const val = data.valuation;
    const risk = data.risk;
    const fc = data.forecast;

    // 1. Hero Card
    document.getElementById("heroTicker").textContent = profile.ticker;
    document.getElementById("heroName").textContent = profile.name;
    document.getElementById("heroSector").textContent = profile.sector;
    document.getElementById("heroIndustry").textContent = profile.industry;
    document.getElementById("heroExchange").textContent = profile.exchange || "US";
    document.getElementById("heroPrice").textContent = profile.current_price ? `$${Number(profile.current_price).toFixed(2)}` : "N/A";
    
    // Market cap / AUM formatted
    const mcap = profile.market_cap;
    let mcapStr = "N/A";
    if (mcap) {
        if (mcap >= 1e12) mcapStr = `$${(mcap / 1e12).toFixed(2)}T`;
        else if (mcap >= 1e9) mcapStr = `$${(mcap / 1e9).toFixed(2)}B`;
        else mcapStr = `$${(mcap / 1e6).toFixed(0)}M`;
    }
    document.getElementById("heroMarketCap").textContent = mcapStr;

    // ETF Specific Handling
    const etfSection = document.getElementById("etfSpecificSection");
    const heroTypeBadge = document.getElementById("heroTypeBadge");
    if (profile.is_etf && profile.etf_data) {
        if (heroTypeBadge) {
            heroTypeBadge.textContent = "קרן סל מחקה מדד (ETF)";
            heroTypeBadge.style.background = "rgba(16, 185, 129, 0.2)";
            heroTypeBadge.style.color = "#34D399";
        }
        if (etfSection) {
            etfSection.style.display = "block";
            const ed = profile.etf_data;
            document.getElementById("etfCategoryChip").textContent = `קטגוריה: ${ed.category || 'כללי'}`;
            document.getElementById("etfExpenseRatio").textContent = ed.expense_ratio !== null ? `${ed.expense_ratio}%` : "—";
            
            let aumStr = "—";
            if (ed.aum) {
                if (ed.aum >= 1e12) aumStr = `$${(ed.aum / 1e12).toFixed(2)}T`;
                else if (ed.aum >= 1e9) aumStr = `$${(ed.aum / 1e9).toFixed(1)}B`;
                else aumStr = `$${(ed.aum / 1e6).toFixed(0)}M`;
            }
            document.getElementById("etfAUM").textContent = aumStr;
            document.getElementById("etfYield").textContent = ed.yield !== null ? `${ed.yield}%` : "—";
            document.getElementById("etfBeta").textContent = profile.beta ? Number(profile.beta).toFixed(2) : "1.00";

            // Holdings table
            const hBody = document.getElementById("etfHoldingsTableBody");
            hBody.innerHTML = "";
            (ed.top_holdings || []).forEach(h => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td class="latin" style="font-weight:700;"><a href="#${h.symbol}" class="etf-hold-link" style="color:#93C5FD; text-decoration:none;">${h.symbol}</a></td>
                    <td>${h.name}</td>
                    <td class="latin" style="font-weight:700; color:#34D399;">${h.percent}%</td>
                `;
                tr.style.cursor = "pointer";
                tr.querySelector(".etf-hold-link").addEventListener("click", (e) => {
                    e.preventDefault();
                    analyzeTicker(h.symbol);
                });
                hBody.appendChild(tr);
            });

            // Sector list
            const sList = document.getElementById("etfSectorList");
            sList.innerHTML = "";
            for (const [sec, pct] of Object.entries(ed.sector_weightings || {})) {
                const div = document.createElement("div");
                div.style.cssText = "display:flex; justify-content:space-between; font-size:13px; padding:6px 10px; background:var(--bg-subtle); border-radius:4px;";
                div.innerHTML = `<span>${sec}</span><span class="latin" style="font-weight:700;">${pct}%</span>`;
                sList.appendChild(div);
            }
        }
    } else {
        if (heroTypeBadge) {
            heroTypeBadge.textContent = "מניה רגילה";
            heroTypeBadge.style.background = "rgba(59, 130, 246, 0.2)";
            heroTypeBadge.style.color = "#93C5FD";
        }
        if (etfSection) etfSection.style.display = "none";
    }

    // 2. Score Cards (0-100)
    try { renderScores(synth); } catch (e) { console.error("renderScores error:", e); }

    // 3. Quality vs Valuation Insight Alert
    const qAlert = document.getElementById("qualityValuationAlert");
    if (qAlert && synth) {
        qAlert.innerHTML = `<strong>אבחנה אסטרטגית:</strong> ${synth.quality_vs_valuation_insight || 'ניתוח פונדמנטלי זמין בכרטיסיות מטה.'}`;
    }

    // 4. Fundamental Metrics Grid
    try { renderFundamentalGrid(fund ? fund.metrics : []); } catch (e) { console.error("renderFundamentalGrid error:", e); }

    // 5. Piotroski F-Score & Altman Z-Score
    try { renderQualityScores(fund); } catch (e) { console.error("renderQualityScores error:", e); }

    // 6. Valuation & DCF Model
    try { renderValuationSection(val); } catch (e) { console.error("renderValuationSection error:", e); }

    // 7. Risk & Technical Indicators
    try { renderRiskSection(risk); } catch (e) { console.error("renderRiskSection error:", e); }

    // 8. Performance Comparison (Stock vs S&P 500)
    try { renderPerformanceTable(risk ? risk.performance_comparison : []); } catch (e) { console.error("renderPerformanceTable error:", e); }

    // 9. Probabilistic Forecasting (3M, 6M, 1Y, 3Y)
    try { renderForecastSection(fc); } catch (e) { console.error("renderForecastSection error:", e); }

    // 10. Qualitative Analysis & Moat
    try { renderQualitative(synth ? synth.qualitative_analysis : null); } catch (e) { console.error("renderQualitative error:", e); }

    // 11. Investor Suitability & Checklist
    try { renderSuitabilityAndChecklist(synth ? synth.investor_suitability : null, synth ? synth.pre_investment_checklist : null); } catch (e) { console.error("renderSuitabilityAndChecklist error:", e); }

    // 12. SEC Link
    const secBtn = document.getElementById("secFilingBtn");
    if (secBtn && data.sec_info) {
        secBtn.href = data.sec_info.filings_url;
    }

    // 13. Interactive Charts (Plotly)
    try { renderCharts(data); } catch (e) { console.error("renderCharts error:", e); }
}

function renderScores(synth) {
    const formatScore = (elId, barId, score, colorClass) => {
        const el = document.getElementById(elId);
        const bar = document.getElementById(barId);
        if (el) el.textContent = score;
        if (bar) {
            bar.style.width = `${score}%`;
            bar.className = `score-bar-fill ${colorClass}`;
        }
    };

    const getColor = (s) => s >= 75 ? "bg-emerald" : (s >= 55 ? "bg-blue" : (s >= 40 ? "bg-amber" : "bg-rose"));

    formatScore("scoreComposite", "barComposite", synth.composite_score, getColor(synth.composite_score));
    formatScore("scoreQuality", "barQuality", synth.quality_score, getColor(synth.quality_score));
    formatScore("scoreValuation", "barValuation", synth.valuation_score, getColor(synth.valuation_score));
    formatScore("scoreGrowth", "barGrowth", synth.growth_score, getColor(synth.growth_score));
    formatScore("scoreRisk", "barRisk", synth.risk_score, getColor(synth.risk_score));

    // Verdict Badge
    const verdictEl = document.getElementById("compositeVerdict");
    if (verdictEl && synth.score_verdict) {
        verdictEl.textContent = synth.score_verdict.grade;
    }
}

function renderFundamentalGrid(metrics) {
    const container = document.getElementById("metricsGrid");
    container.innerHTML = "";

    metrics.forEach(m => {
        const card = document.createElement("div");
        card.className = "metric-card";
        
        const badgeClass = m.status === "positive" ? "positive" : (m.status === "negative" ? "negative" : "neutral");
        const badgeLabel = m.status === "positive" ? "חיובי" : (m.status === "negative" ? "שלילי" : "ניטרלי");

        card.innerHTML = `
            <div class="metric-top">
                <span class="metric-name">${m.name}</span>
                <span class="metric-badge ${badgeClass}">${badgeLabel}</span>
            </div>
            <div class="metric-value latin">${m.formatted}</div>
            <div class="metric-benchmark">הקשר שוק: ${m.benchmark}</div>
            <div class="metric-verdict">${m.verdict}</div>
        `;
        container.appendChild(card);
    });
}

function renderQualityScores(fund) {
    // Piotroski
    const p = fund.piotroski_f_score;
    document.getElementById("piotroskiScore").textContent = `${p.score}/9`;
    document.getElementById("piotroskiVerdict").textContent = p.interpretation;
    
    const pList = document.getElementById("piotroskiList");
    pList.innerHTML = "";
    p.details.forEach(item => {
        const li = document.createElement("div");
        li.className = "checklist-item";
        li.innerHTML = `
            <span class="checklist-icon" style="color: ${item.passed ? 'var(--color-positive)' : 'var(--color-negative)'}">
                ${item.passed ? '✓' : '✗'}
            </span>
            <span class="checklist-text" style="color: ${item.passed ? 'var(--text-primary)' : 'var(--text-muted)'}">
                ${item.criterion}
            </span>
        `;
        pList.appendChild(li);
    });

    // Altman Z-Score
    const z = fund.altman_z_score;
    document.getElementById("altmanScore").textContent = z.score;
    document.getElementById("altmanZone").textContent = z.zone;
    document.getElementById("altmanExplanation").textContent = z.explanation;
}

function renderValuationSection(val) {
    document.getElementById("dcfFairValue").textContent = `$${val.dcf_fair_value}`;
    document.getElementById("peFairValue").textContent = `$${val.pe_fair_value}`;
    document.getElementById("blendedFairValue").textContent = `$${val.blended_fair_value}`;
    
    const mosEl = document.getElementById("marginOfSafety");
    mosEl.textContent = `${val.margin_of_safety_percent > 0 ? '+' : ''}${val.margin_of_safety_percent}%`;
    mosEl.style.color = val.margin_of_safety_percent > 10 ? "var(--color-positive)" : (val.margin_of_safety_percent < -10 ? "var(--color-negative)" : "var(--color-neutral)");
    
    document.getElementById("valuationSummaryHebrew").textContent = val.summary_hebrew;

    // Set Slider Defaults from assumptions
    document.getElementById("sliderWacc").value = val.assumptions.wacc;
    document.getElementById("valWacc").textContent = `${val.assumptions.wacc}%`;
    
    document.getElementById("sliderGrowth").value = val.assumptions.growth_rate_5y;
    document.getElementById("valGrowth").textContent = `${val.assumptions.growth_rate_5y}%`;

    // Render Sensitivity Matrix
    renderSensitivityMatrix(val.sensitivity);
}

function renderSensitivityMatrix(sens) {
    const tableHead = document.getElementById("sensitivityHead");
    const tableBody = document.getElementById("sensitivityBody");
    if (!tableHead || !tableBody) return;

    tableHead.innerHTML = `<tr><th>קצב צמיחה \\ WACC</th>` + sens.wacc_headers.map(w => `<th class="latin">${w}</th>`).join("") + `</tr>`;
    
    tableBody.innerHTML = "";
    sens.matrix.forEach(row => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td style="font-weight:700;" class="latin">${row.growth}%</td>` + row.values.map(v => {
            return `<td class="latin">${v !== null ? `$${v}` : '—'}</td>`;
        }).join("");
        tableBody.appendChild(tr);
    });
}

function initDCFSliders() {
    const sliderWacc = document.getElementById("sliderWacc");
    const sliderGrowth = document.getElementById("sliderGrowth");
    const valWacc = document.getElementById("valWacc");
    const valGrowth = document.getElementById("valGrowth");

    const updateSimulation = async () => {
        valWacc.textContent = `${sliderWacc.value}%`;
        valGrowth.textContent = `${sliderGrowth.value}%`;

        try {
            const res = await fetch("/api/valuation/dcf", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    ticker: currentTicker,
                    wacc: parseFloat(sliderWacc.value) / 100.0,
                    growth_rate: parseFloat(sliderGrowth.value) / 100.0
                })
            });
            const result = await res.json();
            if (result.success && result.data) {
                renderValuationSection(result.data);
            }
        } catch (e) {
            console.error("DCF simulation error:", e);
        }
    };

    sliderWacc.addEventListener("input", updateSimulation);
    sliderGrowth.addEventListener("input", updateSimulation);
}

function setSafeText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = (text !== undefined && text !== null) ? text : '—';
}

function renderRiskSection(risk) {
    if (!risk) return;
    setSafeText("riskVol", `${risk.annual_volatility}%`);
    setSafeText("riskBeta", risk.beta);
    setSafeText("riskDrawdown", `${risk.max_drawdown}%`);
    setSafeText("riskSharpe", risk.sharpe_ratio);
    setSafeText("riskSortino", risk.sortino_ratio);
    setSafeText("riskVaR", `${risk.var_95_annual}%`);
    
    setSafeText("techTrend", risk.trend_status);
    setSafeText("techRsi", risk.rsi_14);
    setSafeText("techSma50", `$${risk.sma_50}`);
    setSafeText("techSma200", `$${risk.sma_200}`);
}

function renderPerformanceTable(perfList) {
    const tbody = document.getElementById("performanceTableBody");
    if (!tbody) return;
    tbody.innerHTML = "";
    if (!Array.isArray(perfList) || perfList.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 16px;">מידע היסטורי חלקי עבור נכס זה</td></tr>';
        return;
    }
    perfList.forEach(p => {
        const tr = document.createElement("tr");
        const diffColor = p.beating_benchmark ? "var(--color-positive)" : "var(--color-negative)";
        const icon = p.beating_benchmark ? "🏆 מכה" : "מפגר";
        tr.innerHTML = `
            <td style="font-weight:700;" class="latin">${p.period}</td>
            <td class="latin">${p.stock_return > 0 ? '+' : ''}${p.stock_return}%</td>
            <td class="latin">${p.benchmark_return > 0 ? '+' : ''}${p.benchmark_return}%</td>
            <td class="latin" style="color: ${diffColor}; font-weight:700;">${p.alpha_diff > 0 ? '+' : ''}${p.alpha_diff}%</td>
            <td style="color: ${diffColor};">${icon}</td>
        `;
        tbody.appendChild(tr);
    });
}

function renderForecastSection(fc) {
    const tbody = document.getElementById("forecastTableBody");
    tbody.innerHTML = "";
    
    fc.horizons.forEach(h => {
        const tr = document.createElement("tr");
        const probPosColor = h.prob_positive >= 60 ? "var(--color-positive)" : (h.prob_positive < 45 ? "var(--color-negative)" : "var(--color-neutral)");
        const probSpColor = h.prob_beat_sp500 >= 55 ? "var(--color-positive)" : "var(--color-neutral)";

        tr.innerHTML = `
            <td style="font-weight:700;">${h.label}</td>
            <td class="latin" style="color:${probPosColor}; font-weight:700;">${h.prob_positive}%</td>
            <td class="latin" style="color:${probSpColor}; font-weight:700;">${h.prob_beat_sp500}%</td>
            <td class="latin" style="color:var(--color-negative);">$${h.bear_case_p10.price} (${h.bear_case_p10.return_percent > 0 ? '+' : ''}${h.bear_case_p10.return_percent}%)</td>
            <td class="latin" style="color:var(--text-primary); font-weight:700;">$${h.base_case_p50.price} (${h.base_case_p50.return_percent > 0 ? '+' : ''}${h.base_case_p50.return_percent}%)</td>
            <td class="latin" style="color:var(--color-positive); font-weight:700;">$${h.bull_case_p90.price} (${h.bull_case_p90.return_percent > 0 ? '+' : ''}${h.bull_case_p90.return_percent}%)</td>
            <td><span class="meta-chip">${h.confidence_level}</span></td>
        `;
        tbody.appendChild(tr);
    });

    document.getElementById("forecastDisclaimer").textContent = fc.disclaimer_hebrew;
}

function renderQualitative(qual) {
    document.getElementById("moatText").textContent = qual.competitive_moat;
    document.getElementById("managementText").textContent = qual.management_quality;
    document.getElementById("threatsText").textContent = qual.market_threats;
    document.getElementById("catalystsText").textContent = qual.upside_catalysts;
}

function renderSuitabilityAndChecklist(suitList, checkList) {
    const suitContainer = document.getElementById("suitabilityList");
    suitContainer.innerHTML = "";
    suitList.forEach(s => {
        const div = document.createElement("div");
        div.className = "checklist-item";
        div.innerHTML = `
            <span class="checklist-icon" style="color: ${s.suitable ? 'var(--color-positive)' : 'var(--text-muted)'}">
                ${s.suitable ? '★ מתאים' : '○ פחות מתאים'}
            </span>
            <div>
                <strong style="color: var(--text-primary);">${s.type}</strong>
                <div style="font-size: 13px; color: var(--text-secondary);">${s.explanation}</div>
            </div>
        `;
        suitContainer.appendChild(div);
    });

    const checkContainer = document.getElementById("preChecklist");
    checkContainer.innerHTML = "";
    checkList.forEach((c, idx) => {
        const div = document.createElement("div");
        div.className = "checklist-item";
        div.innerHTML = `
            <span class="checklist-icon">📌</span>
            <span class="checklist-text">${c}</span>
        `;
        checkContainer.appendChild(div);
    });
}

function renderCharts(data) {
    if (typeof Plotly === "undefined") return;

    // 1. Stock vs Benchmark Return Chart
    if (data.price_chart_data && data.price_chart_data.length > 0) {
        const dates = data.price_chart_data.map(d => d.date);
        const stockPct = data.price_chart_data.map(d => d.stock_pct);
        const benchPct = data.price_chart_data.map(d => d.benchmark_pct);

        const traceStock = {
            x: dates,
            y: stockPct,
            type: 'scatter',
            mode: 'lines',
            name: `${data.profile.ticker} (%)`,
            line: { color: '#3B82F6', width: 2.5 }
        };

        const traceBench = {
            x: dates,
            y: benchPct,
            type: 'scatter',
            mode: 'lines',
            name: 'S&P 500 (%)',
            line: { color: '#94A3B8', width: 1.5, dash: 'dot' }
        };

        const layoutReturn = {
            autosize: true,
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            margin: { t: 30, r: 15, l: 35, b: 35 },
            showlegend: true,
            legend: { orientation: 'h', y: 1.15, font: { color: '#94A3B8' } },
            xaxis: { gridcolor: '#1E293B', color: '#94A3B8' },
            yaxis: { gridcolor: '#1E293B', color: '#94A3B8', ticksuffix: '%' }
        };

        Plotly.newPlot('chartPriceComparison', [traceStock, traceBench], layoutReturn, { responsive: true, displayModeBar: false });
    }

    // 2. Monte Carlo Fan Chart
    if (data.forecast.fan_chart_data && data.forecast.fan_chart_data.length > 0) {
        const days = data.forecast.fan_chart_data.map(d => `יום ${d.day}`);
        const p10 = data.forecast.fan_chart_data.map(d => d.p10);
        const p50 = data.forecast.fan_chart_data.map(d => d.p50);
        const p90 = data.forecast.fan_chart_data.map(d => d.p90);

        const traceP90 = {
            x: days,
            y: p90,
            type: 'scatter',
            mode: 'lines',
            name: 'אופטימי (P90)',
            line: { color: 'rgba(16, 185, 129, 0.8)', width: 2 }
        };

        const traceP50 = {
            x: days,
            y: p50,
            type: 'scatter',
            mode: 'lines',
            name: 'בסיס (חציון P50)',
            line: { color: '#3B82F6', width: 2.5 }
        };

        const traceP10 = {
            x: days,
            y: p10,
            type: 'scatter',
            mode: 'lines',
            name: 'פסימי (P10)',
            line: { color: 'rgba(239, 68, 68, 0.8)', width: 2 }
        };

        const layoutFan = {
            autosize: true,
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            margin: { t: 30, r: 15, l: 35, b: 35 },
            showlegend: true,
            legend: { orientation: 'h', y: 1.15, font: { color: '#94A3B8' } },
            xaxis: { gridcolor: '#1E293B', color: '#94A3B8' },
            yaxis: { gridcolor: '#1E293B', color: '#94A3B8', tickprefix: '$' }
        };

        Plotly.newPlot('chartMonteCarlo', [traceP10, traceP50, traceP90], layoutFan, { responsive: true, displayModeBar: false });
    }
}

/* ==========================================================================
   Translated Financial Statements & SEC Key Sections Modal
   ========================================================================== */

let currentReportsData = null;
let currentReportsTab = "income";
let currentReportsPeriod = "annual";

function initReportsModal() {
    const modal = document.getElementById("reportsModal");
    const openBtn = document.getElementById("openReportsModalBtn");
    const closeBtn = document.getElementById("closeReportsModalBtn");
    const searchInput = document.getElementById("statementSearchInput");

    if (!modal || !openBtn) return;

    const openModal = async () => {
        modal.style.display = "flex";
        document.body.style.overflow = "hidden"; // Prevent background scroll
        
        // If reports data already exists in currentAnalysisData, use it, else fetch
        if (currentAnalysisData && currentAnalysisData.translated_reports) {
            currentReportsData = currentAnalysisData.translated_reports;
            renderReportsModalContent();
        } else {
            const tableContainer = document.getElementById("statementTableContainer");
            if (tableContainer) {
                tableContainer.innerHTML = '<div style="padding:40px; text-align:center;">טוען דוחות כספיים מתורגמים...</div>';
            }
            try {
                const res = await fetch(`/api/stock/${currentTicker}/reports`);
                const json = await res.json();
                if (json.success && json.data) {
                    currentReportsData = json.data;
                    renderReportsModalContent();
                }
            } catch (err) {
                console.error("Error loading reports:", err);
            }
        }
    };

    const closeModal = () => {
        modal.style.display = "none";
        document.body.style.overflow = "auto";
    };

    openBtn.addEventListener("click", openModal);
    if (closeBtn) closeBtn.addEventListener("click", closeModal);

    // Close when clicking outside container
    modal.addEventListener("click", (e) => {
        if (e.target === modal) closeModal();
    });

    // Close on Escape key
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && modal.style.display === "flex") {
            closeModal();
        }
    });

    // Tab buttons
    document.querySelectorAll(".modal-tab-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".modal-tab-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            currentReportsTab = btn.dataset.tab;
            renderReportsModalContent();
        });
    });

    // Period toggle buttons
    document.querySelectorAll(".toggle-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".toggle-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            currentReportsPeriod = btn.dataset.period;
            renderReportsModalContent();
        });
    });

    // Real-time search filter
    if (searchInput) {
        searchInput.addEventListener("input", () => {
            renderReportsModalContent();
        });
    }
}

function renderReportsModalContent() {
    if (!currentReportsData) return;

    // Subtitle
    const subEl = document.getElementById("modalSubtitle");
    if (subEl) {
        subEl.textContent = `חברת ${currentReportsData.company_name} (${currentReportsData.ticker}) | מטבע דיווח: ${currentReportsData.currency}`;
    }

    const tableContainer = document.getElementById("statementTableContainer");
    const secContainer = document.getElementById("secSectionsContainer");
    const periodToggleWrapper = document.getElementById("periodToggleWrapper");
    const searchWrapper = document.querySelector(".statement-search-wrapper");
    const searchInput = document.getElementById("statementSearchInput");
    const filterQuery = (searchInput ? searchInput.value : "").trim().toLowerCase();

    // If SEC Key Sections Tab
    if (currentReportsTab === "sec_sections") {
        tableContainer.style.display = "none";
        secContainer.style.display = "grid";
        if (periodToggleWrapper) periodToggleWrapper.style.display = "none";
        if (searchWrapper) searchWrapper.style.display = "none";

        secContainer.innerHTML = "";
        const sections = currentReportsData.sec_key_sections || [];
        sections.forEach(sec => {
            const card = document.createElement("div");
            card.className = "sec-card";
            
            const bulletsHtml = sec.content_he.map(b => {
                const formatted = b.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                return `<div class="sec-bullet">${formatted}</div>`;
            }).join("");

            card.innerHTML = `
                <div class="sec-card-header">
                    <div>
                        <div class="sec-card-title">${sec.title_he}</div>
                        <div class="sec-card-title-en">${sec.title_en}</div>
                    </div>
                    <span class="sec-badge">${sec.badge}</span>
                </div>
                <div class="sec-card-body">
                    ${bulletsHtml}
                </div>
            `;
            secContainer.appendChild(card);
        });
        return;
    }

    // Otherwise, render financial statement table (Income, Balance, Cashflow)
    tableContainer.style.display = "block";
    secContainer.style.display = "none";
    if (periodToggleWrapper) periodToggleWrapper.style.display = "flex";
    if (searchWrapper) searchWrapper.style.display = "block";

    const periodData = currentReportsData[currentReportsPeriod] || {};
    let statementKey = "income_statement";
    if (currentReportsTab === "balance") statementKey = "balance_sheet";
    else if (currentReportsTab === "cashflow") statementKey = "cashflow";

    const statement = periodData[statementKey] || { years: [], rows: [] };
    const years = statement.years || [];
    let rows = statement.rows || [];

    // Filter rows if search query exists
    if (filterQuery) {
        rows = rows.filter(r => 
            r.hebrew_name.toLowerCase().includes(filterQuery) || 
            r.english_key.toLowerCase().includes(filterQuery)
        );
    }

    if (rows.length === 0) {
        tableContainer.innerHTML = '<div style="padding: 30px; text-align: center; color: var(--text-muted);">לא נמצאו שורות מתאימות לחיפוש.</div>';
        return;
    }

    let theadHtml = `<thead><tr><th>סעיף חשבונאי (מתורגם לעברית)</th>`;
    years.forEach(y => {
        theadHtml += `<th class="latin" style="text-align: left;">${y}</th>`;
    });
    theadHtml += `</tr></thead>`;

    let tbodyHtml = `<tbody>`;
    rows.forEach(r => {
        const highlightClass = r.is_important ? "highlight-row" : "";
        tbodyHtml += `<tr class="${highlightClass}">`;
        tbodyHtml += `<td>
            <div>${r.hebrew_name}</div>
            <span class="row-eng-hint latin">${r.english_key}</span>
        </td>`;
        r.formatted_values.forEach(v => {
            const isNegative = v.startsWith("-");
            const valColor = isNegative ? 'color: var(--color-negative);' : '';
            tbodyHtml += `<td class="latin" style="text-align: left; font-weight: 600; ${valColor}">${v}</td>`;
        });
        tbodyHtml += `</tr>`;
    });
    tbodyHtml += `</tbody>`;

    tableContainer.innerHTML = `<table class="data-table">${theadHtml}${tbodyHtml}</table>`;
}

/* ==========================================================================
   Portfolio Tracker & Allocator
   ========================================================================== */

let myPortfolioHoldings = [
    { ticker: "AAPL", shares: 15, buy_price: 220 },
    { ticker: "NVDA", shares: 20, buy_price: 110 },
    { ticker: "QQQ", shares: 25, buy_price: 470 },
    { ticker: "MSFT", shares: 10, buy_price: 410 },
    { ticker: "SCHD", shares: 30, buy_price: 82 }
];

function initPortfolioManager() {
    const saved = localStorage.getItem("stockIntelPortfolio");
    if (saved) {
        try {
            myPortfolioHoldings = JSON.parse(saved);
        } catch (e) {
            console.warn("Error parsing saved portfolio:", e);
        }
    }

    const addBtn = document.getElementById("btnAddAssetBtn");
    const tickerInput = document.getElementById("addPortTicker");
    const sharesInput = document.getElementById("addPortShares");
    const buyPriceInput = document.getElementById("addPortBuyPrice");
    const loadDemoBtn = document.getElementById("btnLoadDemoPortfolio");
    const clearBtn = document.getElementById("btnClearPortfolio");

    if (addBtn) {
        addBtn.addEventListener("click", () => {
            const sym = tickerInput.value.trim().toUpperCase();
            const sh = parseFloat(sharesInput.value);
            const pr = parseFloat(buyPriceInput.value);

            if (!sym || isNaN(sh) || sh <= 0 || isNaN(pr) || pr <= 0) {
                showToast("אנא הזן סימול תקין, כמות מניות חיובית ומחיר קנייה ממוצע.", "warning");
                return;
            }

            const existing = myPortfolioHoldings.find(h => h.ticker === sym);
            if (existing) {
                const totalCost = (existing.shares * existing.buy_price) + (sh * pr);
                existing.shares += sh;
                existing.buy_price = Number((totalCost / existing.shares).toFixed(2));
            } else {
                myPortfolioHoldings.push({ ticker: sym, shares: sh, buy_price: pr });
            }

            saveAndRefreshPortfolio();
            tickerInput.value = "";
            sharesInput.value = "";
            buyPriceInput.value = "";
        });
    }

    if (loadDemoBtn) {
        loadDemoBtn.addEventListener("click", () => {
            myPortfolioHoldings = [
                { ticker: "AAPL", shares: 15, buy_price: 220 },
                { ticker: "NVDA", shares: 20, buy_price: 110 },
                { ticker: "QQQ", shares: 25, buy_price: 470 },
                { ticker: "MSFT", shares: 10, buy_price: 410 },
                { ticker: "SCHD", shares: 30, buy_price: 82 }
            ];
            saveAndRefreshPortfolio();
        });
    }

    if (clearBtn) {
        clearBtn.addEventListener("click", () => {
            if (confirm("האם לאפס את כל הנכסים בתיק?")) {
                myPortfolioHoldings = [];
                saveAndRefreshPortfolio();
            }
        });
    }
}

function saveAndRefreshPortfolio() {
    localStorage.setItem("stockIntelPortfolio", JSON.stringify(myPortfolioHoldings));
    refreshPortfolio();
}

async function refreshPortfolio() {
    const tbody = document.getElementById("portfolioTableBody");
    if (!tbody) return;

    if (myPortfolioHoldings.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" style="text-align: center; color: var(--text-muted); padding: 24px;">עדיין לא נוספו נכסים לתיק. הוסף נכס ראשון או לחץ על "טען תיק הדגמה".</td></tr>';
        document.getElementById("portTotalValue").textContent = "$0.00";
        document.getElementById("portTotalCost").textContent = "$0.00";
        document.getElementById("portTotalPnL").textContent = "$0.00";
        document.getElementById("portTotalPnLPct").textContent = "+0.0%";
        document.getElementById("portWeightedBeta").textContent = "1.00";
        document.getElementById("portQualityScore").textContent = "0 / 100";
        return;
    }

    showLoading(true, "מחשב שווי וביצועי תיק בזמן אמת...");

    try {
        const res = await fetch("/api/portfolio/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ holdings: myPortfolioHoldings })
        });
        const json = await res.json();
        showLoading(false);

        if (!json.success || !json.data) {
            showToast(`שגיאה בניתוח התיק: ${json.error || 'שגיאה כללית'}`, "error");
            return;
        }

        renderPortfolioView(json.data);
    } catch (e) {
        showLoading(false);
        console.error("Portfolio refresh error:", e);
    }
}

function renderPortfolioView(data) {
    // 1. Summary Cards
    document.getElementById("portTotalValue").textContent = `$${Number(data.total_value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    document.getElementById("portTotalCost").textContent = `$${Number(data.total_cost).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    
    const pnlSign = data.total_pnl >= 0 ? "+" : "";
    const pnlColor = data.total_pnl >= 0 ? "#34D399" : "#EF4444";
    const pnlEl = document.getElementById("portTotalPnL");
    const pnlPctEl = document.getElementById("portTotalPnLPct");
    
    pnlEl.textContent = `${pnlSign}$${Number(data.total_pnl).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    pnlEl.style.color = pnlColor;
    
    pnlPctEl.textContent = `${pnlSign}${data.total_pnl_percent}%`;
    pnlPctEl.style.color = pnlColor;

    document.getElementById("portWeightedBeta").textContent = data.weighted_beta;
    document.getElementById("portRiskProfile").textContent = `רמת סיכון: ${data.risk_profile}`;
    document.getElementById("portQualityScore").textContent = `${data.weighted_quality_score} / 100`;
    document.getElementById("portValuationScore").textContent = data.weighted_valuation_score;

    // 2. Holdings Table
    const tbody = document.getElementById("portfolioTableBody");
    tbody.innerHTML = "";

    data.positions.forEach((pos, idx) => {
        const tr = document.createElement("tr");
        const rowPnlColor = pos.pnl_amount >= 0 ? "var(--color-positive)" : "var(--color-negative)";
        const rowSign = pos.pnl_amount >= 0 ? "+" : "";

        tr.innerHTML = `
            <td class="latin" style="font-weight:700;"><a href="#${pos.ticker}" class="stock-link" style="color:#93C5FD; text-decoration:none;">${pos.ticker}</a></td>
            <td>${pos.sector}</td>
            <td class="latin">${pos.shares}</td>
            <td class="latin">$${pos.buy_price}</td>
            <td class="latin">$${pos.current_price}</td>
            <td class="latin" style="font-weight:700;">$${pos.position_value.toLocaleString()}</td>
            <td class="latin" style="color: ${rowPnlColor}; font-weight:700;">${rowSign}$${pos.pnl_amount.toLocaleString()}</td>
            <td class="latin" style="color: ${rowPnlColor}; font-weight:700;">${rowSign}${pos.pnl_percent}%</td>
            <td class="latin" style="font-weight:700;">${pos.weight_percent}%</td>
            <td>
                <button class="pill-btn delete-pos-btn" data-index="${idx}" style="color:#F87171; border-color:rgba(239,68,68,0.3); padding:2px 8px; font-size:12px;">מחק</button>
            </td>
        `;

        tr.querySelector(".stock-link").addEventListener("click", (e) => {
            e.preventDefault();
            document.getElementById("navBtnStock").click();
            analyzeTicker(pos.ticker);
        });

        tr.querySelector(".delete-pos-btn").addEventListener("click", () => {
            myPortfolioHoldings.splice(idx, 1);
            saveAndRefreshPortfolio();
        });

        tbody.appendChild(tr);
    });

    // 3. Sector Allocation Donut Chart (Plotly)
    if (data.sector_allocation && data.sector_allocation.length > 0 && typeof Plotly !== "undefined") {
        const labels = data.sector_allocation.map(s => s.sector);
        const values = data.sector_allocation.map(s => s.value);

        const donutTrace = [{
            labels: labels,
            values: values,
            type: 'pie',
            hole: 0.55,
            textinfo: 'label+percent',
            textposition: 'inside',
            marker: {
                colors: ['#3B82F6', '#10B981', '#F59E0B', '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16']
            }
        }];

        const donutLayout = {
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            margin: { t: 20, r: 20, l: 20, b: 20 },
            showlegend: false
        };

        Plotly.newPlot('chartPortfolioSectors', donutTrace, donutLayout, { responsive: true, displayModeBar: false });
    }

    // 4. Correlation Matrix Table
    const corrContainer = document.getElementById("portCorrelationContainer");
    if (data.correlation_matrix && data.correlation_matrix.matrix.length > 0) {
        const cm = data.correlation_matrix;
        let thead = `<tr><th>מתאם (Correlation)</th>` + cm.tickers.map(t => `<th class="latin">${t}</th>`).join("") + `</tr>`;
        let tbodyStr = "";
        cm.matrix.forEach((row, i) => {
            tbodyStr += `<tr><td class="latin" style="font-weight:700;">${cm.tickers[i]}</td>`;
            row.forEach(val => {
                let cellColor = "#FFFFFF";
                if (val > 0.7) cellColor = "rgba(239, 68, 68, 0.9)";
                else if (val < 0.3) cellColor = "rgba(16, 185, 129, 0.9)";
                tbodyStr += `<td class="latin" style="color:${cellColor}; font-weight:600;">${val}</td>`;
            });
            tbodyStr += `</tr>`;
        });
        corrContainer.innerHTML = `<table class="data-table"><thead>${thead}</thead><tbody>${tbodyStr}</tbody></table>`;
    } else {
        corrContainer.innerHTML = '<div style="padding: 30px; text-align: center; color: var(--text-muted);">נדרשים לפחות 2 נכסים להצגת מטריצת מתאם.</div>';
    }
}

// Auto-resize Plotly charts on window resize / mobile orientation change
window.addEventListener("resize", () => {
    const plots = document.querySelectorAll(".js-plotly-plot");
    plots.forEach(p => {
        if (typeof Plotly !== "undefined") {
            try { Plotly.Plots.resize(p); } catch (e) {}
        }
    });
});
