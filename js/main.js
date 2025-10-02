const STATE = {
    fundings: [],
    filtered: [],
    summary: null,
};

const WINDOW_DAYS = 90;

const elements = {
    searchInput: document.getElementById('searchInput'),
    sourceFilters: document.querySelectorAll('#sourceFilters input[type="checkbox"]'),
    careerStageFilter: document.getElementById('careerStageFilter'),
    sortSelect: document.getElementById('sortSelect'),
    fundingGrid: document.getElementById('fundingGrid'),
    loading: document.getElementById('loading'),
    noResults: document.getElementById('noResults'),
    totalFundings: document.getElementById('totalFundings'),
    closingSoon: document.getElementById('closingSoon'),
    lastUpdated: document.getElementById('lastUpdated'),
    resultSummary: document.getElementById('resultSummary'),
    heroHighlight: document.getElementById('heroHighlight'),
    aiSummarySection: document.getElementById('aiSummarySection'),
    aiSummaryOverview: document.getElementById('aiSummaryOverview'),
    aiSummaryTimestamp: document.getElementById('aiSummaryTimestamp'),
    aiHighlights: document.getElementById('aiHighlights'),
    aiUpcoming: document.getElementById('aiUpcoming'),
    aiTopBodies: document.getElementById('aiTopBodies'),
    aiCareerFocus: document.getElementById('aiCareerFocus'),
    aiHighValue: document.getElementById('aiHighValue'),
    aiCoverageWindow: document.getElementById('aiCoverageWindow'),
    qualityNotes: document.getElementById('qualityNotes'),
    resetFilters: document.getElementById('resetFilters'),
    modal: document.getElementById('fundingModal'),
    closeModal: document.getElementById('closeModal'),
    modalContent: document.getElementById('modalContent'),
};

document.addEventListener('DOMContentLoaded', () => {
    bindEvents();
    loadData();
});

function bindEvents() {
    const debouncedFilter = debounce(applyFilters, 200);
    elements.searchInput.addEventListener('input', debouncedFilter);
    elements.careerStageFilter.addEventListener('change', applyFilters);
    elements.sortSelect.addEventListener('change', () => {
        sortFundings();
        renderFundings();
    });
    elements.sourceFilters.forEach((checkbox) => {
        checkbox.addEventListener('change', applyFilters);
    });
    if (elements.resetFilters) {
        elements.resetFilters.addEventListener('click', resetFilters);
    }
    if (elements.closeModal) {
        elements.closeModal.addEventListener('click', closeModal);
    }
    window.addEventListener('click', (event) => {
        if (event.target === elements.modal) {
            closeModal();
        }
    });
}

async function loadData() {
    try {
        const [databaseResponse, summaryResponse] = await Promise.all([
            fetch('data/funding_database.json'),
            fetch('data/ai_summary.json'),
        ]);

        if (!databaseResponse.ok) {
            throw new Error('Unable to load funding database');
        }

        const database = await databaseResponse.json();
        const fundings = enforceWindow(database.fundings || []);
        STATE.fundings = fundings;
        STATE.filtered = [...fundings];

        updateHeadlineMetrics(fundings, database.last_updated);
        updateInsights(fundings);
        sortFundings();
        renderFundings();

        if (summaryResponse.ok) {
            const summary = await summaryResponse.json();
            STATE.summary = summary;
            updateAISummary(summary);
        } else {
            showAISummaryFallback('AI summary is not available yet.');
        }
    } catch (error) {
        console.error(error);
        showErrorState('We could not load the latest funding data. Please try again later.');
        showAISummaryFallback('Unable to fetch AI summary at this time.');
    } finally {
        if (elements.loading) {
            elements.loading.hidden = true;
        }
    }
}

function enforceWindow(fundings) {
    const now = new Date();
    const windowStart = new Date(now.getTime() - WINDOW_DAYS * 24 * 60 * 60 * 1000);
    const windowEnd = new Date(now.getTime() + WINDOW_DAYS * 24 * 60 * 60 * 1000);

    return fundings.filter((funding) => {
        const deadline = parseDeadline(funding?.application?.deadline);
        if (!deadline) {
            return false;
        }
        return deadline >= windowStart && deadline <= windowEnd;
    });
}

function updateHeadlineMetrics(fundings, lastUpdated) {
    if (!elements.totalFundings || !elements.closingSoon || !elements.lastUpdated) {
        return;
    }

    elements.totalFundings.textContent = fundings.length.toString();

    const closingSoon = fundings.filter((funding) => {
        const deadline = parseDeadline(funding?.application?.deadline);
        if (!deadline) return false;
        const diff = deadline.getTime() - Date.now();
        const days = Math.ceil(diff / (1000 * 60 * 60 * 24));
        return days > 0 && days <= 30;
    }).length;
    elements.closingSoon.textContent = closingSoon.toString();

    if (lastUpdated) {
        elements.lastUpdated.textContent = new Date(lastUpdated).toLocaleString();
    } else {
        elements.lastUpdated.textContent = new Date().toLocaleString();
    }
}

function updateInsights(fundings) {
    updateCategoryStats(fundings);
    updateCareerStats(fundings);
    updateFundingRange(fundings);
    updateDeadlineStats(fundings);
    updateOrganizationStats(fundings);
    updateCompetitionStats(fundings);
}

function applyFilters() {
    const query = elements.searchInput.value.trim().toLowerCase();
    const selectedStages = elements.careerStageFilter.value;
    const activeSources = Array.from(elements.sourceFilters)
        .filter((checkbox) => checkbox.checked)
        .map((checkbox) => checkbox.value);

    let filtered = STATE.fundings.filter((funding) => {
        const matchesSource = activeSources.includes((funding.category || '').toLowerCase());
        if (!matchesSource) return false;

        const matchesStage = !selectedStages || funding?.eligibility?.career_stage === selectedStages;
        if (!matchesStage) return false;

        if (!query) return true;
        const haystack = [
            funding.title,
            funding.organization,
            funding.description,
            funding?.eligibility?.career_stage,
        ]
            .join(' ')
            .toLowerCase();
        return haystack.includes(query);
    });

    STATE.filtered = filtered;
    sortFundings();
    renderFundings();
}

function sortFundings() {
    const mode = elements.sortSelect.value;
    STATE.filtered.sort((a, b) => {
        if (mode === 'title') {
            return a.title.localeCompare(b.title);
        }

        if (mode === 'amount') {
            const amountA = getAmountValue(a);
            const amountB = getAmountValue(b);
            return amountB - amountA;
        }

        const deadlineA = parseDeadline(a?.application?.deadline) || new Date(8640000000000000);
        const deadlineB = parseDeadline(b?.application?.deadline) || new Date(8640000000000000);
        return deadlineA - deadlineB;
    });
}

function renderFundings() {
    if (!elements.fundingGrid) return;

    const hasResults = STATE.filtered.length > 0;
    elements.noResults.hidden = hasResults;
    elements.fundingGrid.innerHTML = '';

    if (!hasResults) {
        elements.resultSummary.textContent = 'Showing 0 opportunities';
        return;
    }

    elements.resultSummary.textContent = `Showing ${STATE.filtered.length} opportunities`;

    const fragment = document.createDocumentFragment();

    STATE.filtered.forEach((funding) => {
        const card = document.createElement('article');
        card.className = 'funding-card';
        card.innerHTML = createFundingCardMarkup(funding);
        const button = card.querySelector('button[data-id]');
        if (button) {
            button.addEventListener('click', () => openModal(funding));
        }
        fragment.appendChild(card);
    });

    elements.fundingGrid.appendChild(fragment);
}

function createFundingCardMarkup(funding) {
    const deadline = formatDate(funding?.application?.deadline) || 'Date TBC';
    const amount = formatCurrencyDisplay(getAmountValue(funding));
    const category = (funding.category || 'Other').toUpperCase();
    const organization = funding.organization || 'Unknown organisation';
    const description = (funding.description || '').slice(0, 180);

    return `
        <span class="funding-card__badge"><i class="fas fa-layer-group"></i> ${category}</span>
        <h3 class="funding-card__title">${funding.title}</h3>
        <div class="funding-card__meta">
            <span><i class="fas fa-building"></i> ${organization}</span>
            <span><i class="fas fa-pound-sign"></i> ${amount}</span>
        </div>
        <p class="funding-card__description">${description}${description.length === 180 ? '…' : ''}</p>
        <div class="funding-card__footer">
            <span class="funding-card__deadline"><i class="fas fa-calendar"></i> ${deadline}</span>
            <button class="funding-card__button" data-id="${funding.id}"><span>View details</span> <i class="fas fa-arrow-right"></i></button>
        </div>
    `;
}

function openModal(funding) {
    if (!elements.modal || !elements.modalContent) return;

    const deadline = formatDate(funding?.application?.deadline) || 'Date TBC';
    const nextDeadline = formatDate(funding?.application?.next_deadline);
    const amount = formatCurrencyDisplay(getAmountValue(funding));
    const coverage = funding?.funding_details?.covers || [];
    const requirements = funding?.eligibility?.requirements || [];

    elements.modalContent.innerHTML = `
        <h2 id="modalTitle">${funding.title}</h2>
        <p><strong>Organisation:</strong> ${funding.organization || 'Unknown organisation'}</p>
        <p><strong>Category:</strong> ${(funding.category || 'Other').toUpperCase()}</p>
        <p><strong>Funding amount:</strong> ${amount}</p>
        <p><strong>Deadline:</strong> ${deadline}</p>
        ${nextDeadline ? `<p><strong>Next cycle:</strong> ${nextDeadline}</p>` : ''}
        <p>${funding.description || ''}</p>
        ${renderListBlock('Covers', coverage)}
        ${renderListBlock('Eligibility requirements', requirements)}
        ${funding?.application?.application_url ? `<a class="button" href="${funding.application.application_url}" target="_blank" rel="noopener">Apply on website</a>` : ''}
    `;

    elements.modal.hidden = false;
    document.body.style.overflow = 'hidden';
}

function renderListBlock(title, items) {
    if (!items || items.length === 0) {
        return '';
    }
    const list = items
        .map((item) => `<li>${item}</li>`)
        .join('');
    return `
        <div>
            <h3>${title}</h3>
            <ul>${list}</ul>
        </div>
    `;
}

function closeModal() {
    if (!elements.modal) return;
    elements.modal.hidden = true;
    document.body.style.overflow = '';
}

function updateAISummary(summary) {
    if (!summary || !elements.aiSummarySection) {
        showAISummaryFallback('AI summary is not available yet.');
        return;
    }

    elements.aiSummaryOverview.textContent = summary.overall_summary || 'Automated briefing ready.';
    elements.aiSummaryTimestamp.textContent = summary.generated_at
        ? `Generated ${new Date(summary.generated_at).toLocaleString()}`
        : 'Generated recently';

    if (summary.coverage_window?.label) {
        elements.aiCoverageWindow.textContent = `Window: ${summary.coverage_window.label}`;
    }

    renderSimpleList(elements.aiHighlights, summary.highlights, (item) => `<li>${item}</li>`);
    renderSimpleList(
        elements.aiUpcoming,
        summary.upcoming_deadlines,
        (item) => `
            <li>
                <strong>${item.title}</strong>
                <span>${item.organization} · ${item.deadline} (${item.days_remaining} days left)</span>
            </li>
        `
    );
    renderSimpleList(
        elements.aiTopBodies,
        summary.top_funding_bodies,
        (item) => `
            <li>
                <strong>${item.organization}</strong>
                <span>${item.opportunity_count} opportunities</span>
            </li>
        `
    );
    renderSimpleList(
        elements.aiCareerFocus,
        summary.career_stage_focus,
        (item) => `
            <li>
                <strong>${item.stage}</strong>
                <span>${item.opportunity_count} opportunities</span>
            </li>
        `
    );
    renderSimpleList(
        elements.aiHighValue,
        summary.high_value_awards,
        (item) => `
            <li>
                <strong>${item.title}</strong>
                <span>${item.organization} · ${item.amount} · Deadline: ${item.deadline}</span>
            </li>
        `
    );

    updateHeroHighlight(summary);
    updateQualityNotes(summary.quality_notes || []);
}

function updateHeroHighlight(summary) {
    if (!elements.heroHighlight) return;
    const firstHighlight = summary.highlights?.[0];
    const heroText = firstHighlight || summary.overall_summary || 'Daily briefing ready.';
    elements.heroHighlight.innerHTML = `<p class="hero__snapshot-text">${heroText}</p>`;
}

function updateQualityNotes(notes) {
    if (!elements.qualityNotes) return;
    if (!notes.length) {
        elements.qualityNotes.innerHTML = '';
        return;
    }
    elements.qualityNotes.innerHTML = notes.map((note) => `<span>${note}</span>`).join('');
}

function showAISummaryFallback(message) {
    elements.aiSummaryOverview.textContent = message;
    elements.aiSummaryTimestamp.textContent = '—';
    elements.aiCoverageWindow.textContent = 'Window: —';
    ['aiHighlights', 'aiUpcoming', 'aiTopBodies', 'aiCareerFocus', 'aiHighValue'].forEach((key) => {
        const container = elements[key];
        if (container) {
            container.innerHTML = '<li>No data available.</li>';
        }
    });
    updateQualityNotes([]);
}

function renderSimpleList(container, items, templateFn) {
    if (!container) return;
    if (!items || !items.length) {
        container.innerHTML = '<li>No data available.</li>';
        return;
    }
    container.innerHTML = items.map(templateFn).join('');
}

function showErrorState(message) {
    if (!elements.noResults) return;
    elements.noResults.hidden = false;
    elements.noResults.querySelector('h3').textContent = 'Unable to load data';
    elements.noResults.querySelector('p').textContent = message;
}

function parseDeadline(value) {
    if (!value) return null;
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function formatDate(value) {
    const date = parseDeadline(value);
    if (!date) return null;
    return new Intl.DateTimeFormat('en-GB', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
    }).format(date);
}

function getAmountValue(funding) {
    const amount = funding?.funding_details?.amount || {};
    return amount.max || amount.min || 0;
}

function formatCurrencyDisplay(value) {
    if (!value) return 'Unknown';
    if (value >= 1_000_000_000) {
        return `£${(value / 1_000_000_000).toFixed(2)}bn`;
    }
    if (value >= 1_000_000) {
        return `£${(value / 1_000_000).toFixed(1)}m`;
    }
    if (value >= 1_000) {
        return `£${Math.round(value / 1_000)}k`;
    }
    return `£${value.toLocaleString()}`;
}

function debounce(fn, wait = 150) {
    let timeout;
    return (...args) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => fn.apply(null, args), wait);
    };
}

function resetFilters() {
    elements.searchInput.value = '';
    elements.careerStageFilter.value = '';
    elements.sourceFilters.forEach((checkbox) => {
        checkbox.checked = true;
    });
    elements.sortSelect.value = 'deadline';
    applyFilters();
}

function updateCategoryStats(fundings) {
    const container = document.getElementById('categoryStats');
    if (!container) return;
    const counts = countBy(fundings, (funding) => funding.category || 'Other');
    renderStatList(container, counts, fundings.length);
}

function updateCareerStats(fundings) {
    const container = document.getElementById('careerStats');
    if (!container) return;
    const counts = countBy(fundings, (funding) => funding?.eligibility?.career_stage || 'All');
    renderStatList(container, counts, fundings.length);
}

function updateFundingRange(fundings) {
    const container = document.getElementById('fundingRange');
    if (!container) return;
    if (!fundings.length) {
        container.innerHTML = '<p>No funding data available.</p>';
        return;
    }
    const amounts = fundings.map(getAmountValue);
    const max = Math.max(...amounts);
    const min = Math.min(...amounts.filter((value) => value > 0));
    container.innerHTML = `
        <div class="stat-item">
            <span class="stat-label">Largest award</span>
            <span>${formatCurrencyDisplay(max)}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Smallest award</span>
            <span>${min === Infinity ? 'Unknown' : formatCurrencyDisplay(min)}</span>
        </div>
    `;
}

function updateDeadlineStats(fundings) {
    const container = document.getElementById('deadlineStats');
    if (!container) return;
    if (!fundings.length) {
        container.innerHTML = '<p>No deadlines available.</p>';
        return;
    }
    const buckets = {
        '0-14 days': 0,
        '15-30 days': 0,
        '31-60 days': 0,
        '61-90 days': 0,
    };
    const now = Date.now();
    fundings.forEach((funding) => {
        const deadline = parseDeadline(funding?.application?.deadline);
        if (!deadline) return;
        const diff = deadline.getTime() - now;
        const days = Math.ceil(diff / (1000 * 60 * 60 * 24));
        if (days <= 14) buckets['0-14 days'] += 1;
        else if (days <= 30) buckets['15-30 days'] += 1;
        else if (days <= 60) buckets['31-60 days'] += 1;
        else buckets['61-90 days'] += 1;
    });
    renderStatList(container, buckets, fundings.length);
}

function updateOrganizationStats(fundings) {
    const container = document.getElementById('organizationStats');
    if (!container) return;
    const counts = countBy(fundings, (funding) => funding.organization || 'Unknown');
    const entries = Object.entries(counts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 6);
    renderStatList(container, Object.fromEntries(entries), fundings.length);
}

function updateCompetitionStats(fundings) {
    const container = document.getElementById('competitionStats');
    if (!container) return;
    const counts = countBy(fundings, (funding) => funding?.key_info?.competition_level || 'Not stated');
    renderStatList(container, counts, fundings.length);
}

function countBy(items, keyFn) {
    return items.reduce((acc, item) => {
        const key = keyFn(item);
        acc[key] = (acc[key] || 0) + 1;
        return acc;
    }, {});
}

function renderStatList(container, counts, total) {
    if (!total) {
        container.innerHTML = '<p>No data available.</p>';
        return;
    }
    const markup = Object.entries(counts)
        .sort((a, b) => b[1] - a[1])
        .map(([label, count]) => {
            const percentage = Math.round((count / total) * 100);
            return `
                <div class="stat-item">
                    <div class="stat-label">${label}</div>
                    <div class="stat-progress">
                        <div class="stat-progress-fill" style="width: ${percentage}%"></div>
                    </div>
                    <div>${count} (${percentage}%)</div>
                </div>
            `;
        })
        .join('');
    container.innerHTML = markup || '<p>No data available.</p>';
}
