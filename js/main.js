// Global variables
let allFundings = [];
let filteredFundings = [];
let database = {};

// DOM elements
const searchInput = document.getElementById('searchInput');
const categoryFilter = document.getElementById('categoryFilter');
const careerStageFilter = document.getElementById('careerStageFilter');
const sortBy = document.getElementById('sortBy');
const fundingGrid = document.getElementById('fundingGrid');
const loading = document.getElementById('loading');
const noResults = document.getElementById('noResults');
const modal = document.getElementById('fundingModal');
const closeModal = document.getElementById('closeModal');
const modalContent = document.getElementById('modalContent');

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    loadData();
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    searchInput.addEventListener('input', debounce(filterFundings, 300));
    categoryFilter.addEventListener('change', filterFundings);
    careerStageFilter.addEventListener('change', filterFundings);
    sortBy.addEventListener('change', sortAndDisplayFundings);
    
    closeModal.addEventListener('click', closeModalHandler);
    window.addEventListener('click', function(event) {
        if (event.target === modal) {
            closeModalHandler();
        }
    });
}

// Load data from JSON files
async function loadData() {
    try {
        // Load main database
        const response = await fetch('data/funding_database.json');
        database = await response.json();
        
        // Use the fundings from the database instead of sample data
        allFundings = database.fundings || [];
        
        updateStats();
        filteredFundings = [...allFundings];
        sortAndDisplayFundings();
        
    } catch (error) {
        console.error('Error loading data:', error);
        showError('Failed to load funding data. Please try again later.');
    } finally {
        loading.style.display = 'none';
    }
}



// Update statistics
function updateStats() {
    const totalFundings = allFundings.length;
    const activeFundings = allFundings.filter(f => f.status === 'active').length;
    const closingSoon = allFundings.filter(f => {
        const deadline = new Date(f.application.deadline);
        const now = new Date();
        const diffTime = deadline - now;
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        return diffDays <= 30 && diffDays > 0;
    }).length;
    
    document.getElementById('totalFundings').textContent = totalFundings;
    document.getElementById('activeFundings').textContent = activeFundings;
    document.getElementById('closingSoon').textContent = closingSoon;
    document.getElementById('lastUpdated').textContent = new Date().toLocaleDateString();
    
    // Update dashboard
    updateDashboard();
}

// Update dashboard with comprehensive statistics
function updateDashboard() {
    updateCategoryStats();
    updateCareerStats();
    updateFundingRange();
    updateDeadlineStats();
    updateOrganizationStats();
    updateCompetitionStats();
}

// Update category distribution
function updateCategoryStats() {
    const categoryCount = {};
    allFundings.forEach(funding => {
        const category = funding.category || 'Other';
        categoryCount[category] = (categoryCount[category] || 0) + 1;
    });
    
    const total = allFundings.length;
    const categoryStatsEl = document.getElementById('categoryStats');
    
    categoryStatsEl.innerHTML = Object.entries(categoryCount)
        .sort((a, b) => b[1] - a[1])
        .map(([category, count]) => {
            const percentage = ((count / total) * 100).toFixed(1);
            return `
                <div class="stat-item">
                    <div class="stat-bar">
                        <span class="stat-label">${category}</span>
                        <div class="stat-progress">
                            <div class="stat-progress-fill" style="width: ${percentage}%"></div>
                        </div>
                        <span class="stat-value">${count} (${percentage}%)</span>
                    </div>
                </div>
            `;
        }).join('');
}

// Update career stage distribution
function updateCareerStats() {
    const careerCount = {};
    allFundings.forEach(funding => {
        const stage = funding.eligibility?.career_stage || 'All Stages';
        careerCount[stage] = (careerCount[stage] || 0) + 1;
    });
    
    const total = allFundings.length;
    const careerStatsEl = document.getElementById('careerStats');
    
    careerStatsEl.innerHTML = Object.entries(careerCount)
        .sort((a, b) => b[1] - a[1])
        .map(([stage, count]) => {
            const percentage = ((count / total) * 100).toFixed(1);
            return `
                <div class="stat-item">
                    <div class="stat-bar">
                        <span class="stat-label">${stage}</span>
                        <div class="stat-progress">
                            <div class="stat-progress-fill" style="width: ${percentage}%"></div>
                        </div>
                        <span class="stat-value">${count} (${percentage}%)</span>
                    </div>
                </div>
            `;
        }).join('');
}

// Update funding range statistics
function updateFundingRange() {
    const amounts = allFundings
        .map(funding => {
            const amount = funding.funding_details?.amount;
            if (!amount) return null;
            return {
                min: amount.min || amount.max || 0,
                max: amount.max || amount.min || 0
            };
        })
        .filter(amount => amount && amount.min > 0);
    
    if (amounts.length === 0) {
        document.getElementById('fundingRange').innerHTML = '<p>No funding amount data available</p>';
        return;
    }
    
    const minAmount = Math.min(...amounts.map(a => a.min));
    const maxAmount = Math.max(...amounts.map(a => a.max));
    const avgMin = amounts.reduce((sum, a) => sum + a.min, 0) / amounts.length;
    const avgMax = amounts.reduce((sum, a) => sum + a.max, 0) / amounts.length;
    
    document.getElementById('fundingRange').innerHTML = `
        <div class="range-item">
            <div class="range-label">Minimum Available</div>
            <div class="range-value">£${formatNumber(minAmount)}</div>
        </div>
        <div class="range-item">
            <div class="range-label">Maximum Available</div>
            <div class="range-value">£${formatNumber(maxAmount)}</div>
        </div>
        <div class="range-item">
            <div class="range-label">Average Range</div>
            <div class="range-value">£${formatNumber(avgMin)} - £${formatNumber(avgMax)}</div>
        </div>
    `;
}

// Update deadline analysis
function updateDeadlineStats() {
    const now = new Date();
    let openNow = 0;
    let closingSoon = 0;
    let closedCount = 0;
    let noDeadline = 0;
    
    allFundings.forEach(funding => {
        if (!funding.application?.deadline) {
            noDeadline++;
            return;
        }
        
        const deadline = new Date(funding.application.deadline);
        const diffTime = deadline - now;
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        
        if (diffDays < 0) {
            closedCount++;
        } else if (diffDays <= 30) {
            closingSoon++;
        } else {
            openNow++;
        }
    });
    
    document.getElementById('deadlineStats').innerHTML = `
        <div class="deadline-item">
            <span class="deadline-number">${openNow}</span>
            <span class="deadline-label">Open Now</span>
        </div>
        <div class="deadline-item">
            <span class="deadline-number">${closingSoon}</span>
            <span class="deadline-label">Closing Soon</span>
        </div>
        <div class="deadline-item">
            <span class="deadline-number">${closedCount}</span>
            <span class="deadline-label">Closed</span>
        </div>
        <div class="deadline-item">
            <span class="deadline-number">${noDeadline}</span>
            <span class="deadline-label">No Deadline</span>
        </div>
    `;
}

// Update top organizations
function updateOrganizationStats() {
    const orgCount = {};
    allFundings.forEach(funding => {
        const org = funding.organization || 'Unknown';
        orgCount[org] = (orgCount[org] || 0) + 1;
    });
    
    const topOrgs = Object.entries(orgCount)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5);
    
    document.getElementById('organizationStats').innerHTML = topOrgs
        .map(([org, count]) => `
            <div class="stat-item">
                <span class="stat-label">${org}</span>
                <span class="stat-value">${count}</span>
            </div>
        `).join('');
}

// Update competition level analysis
function updateCompetitionStats() {
    const amounts = allFundings
        .map(funding => funding.funding_details?.amount?.max || funding.funding_details?.amount?.min || 0)
        .filter(amount => amount > 0);
    
    const avgAmount = amounts.length > 0 ? amounts.reduce((sum, a) => sum + a, 0) / amounts.length : 0;
    const highValueCount = amounts.filter(a => a > avgAmount * 2).length;
    const mediumValueCount = amounts.filter(a => a > avgAmount && a <= avgAmount * 2).length;
    const lowValueCount = amounts.filter(a => a <= avgAmount).length;
    
    let competitionLevel = 'Low';
    let competitionClass = 'competition-low';
    let description = 'Generally accessible opportunities';
    
    if (highValueCount > amounts.length * 0.3) {
        competitionLevel = 'High';
        competitionClass = 'competition-high';
        description = 'Many high-value, competitive opportunities';
    } else if (mediumValueCount > amounts.length * 0.4) {
        competitionLevel = 'Medium';
        competitionClass = 'competition-medium';
        description = 'Mix of competitive and accessible opportunities';
    }
    
    document.getElementById('competitionStats').innerHTML = `
        <div class="competition-item ${competitionClass}">
            <div class="competition-level">${competitionLevel} Competition</div>
            <div class="competition-desc">${description}</div>
        </div>
        <div style="margin-top: 1rem; font-size: 0.9rem; color: #666;">
            High Value: ${highValueCount} | Medium: ${mediumValueCount} | Accessible: ${lowValueCount}
        </div>
    `;
}

// Filter fundings based on search and filters
function filterFundings() {
    const searchTerm = searchInput.value.toLowerCase();
    const categoryValue = categoryFilter.value;
    const careerStageValue = careerStageFilter.value;
    
    filteredFundings = allFundings.filter(funding => {
        const matchesSearch = !searchTerm || 
            funding.title.toLowerCase().includes(searchTerm) ||
            funding.organization.toLowerCase().includes(searchTerm) ||
            funding.description.toLowerCase().includes(searchTerm) ||
            funding.tags.some(tag => tag.toLowerCase().includes(searchTerm));
            
        const matchesCategory = !categoryValue || funding.category === categoryValue;
        const matchesCareerStage = !careerStageValue || funding.eligibility.career_stage === careerStageValue;
        
        return matchesSearch && matchesCategory && matchesCareerStage;
    });
    
    sortAndDisplayFundings();
}

// Sort and display fundings
function sortAndDisplayFundings() {
    const sortValue = sortBy.value;
    
    filteredFundings.sort((a, b) => {
        switch (sortValue) {
            case 'deadline':
                return new Date(a.application.deadline) - new Date(b.application.deadline);
            case 'amount':
                return b.funding_details.amount.max - a.funding_details.amount.max;
            case 'title':
                return a.title.localeCompare(b.title);
            default:
                return 0;
        }
    });
    
    displayFundings();
}

// Display fundings in the grid
function displayFundings() {
    if (filteredFundings.length === 0) {
        fundingGrid.style.display = 'none';
        noResults.style.display = 'block';
        return;
    }
    
    fundingGrid.style.display = 'grid';
    noResults.style.display = 'none';
    
    fundingGrid.innerHTML = filteredFundings.map(funding => createFundingCard(funding)).join('');
    
    // Add click listeners to cards
    document.querySelectorAll('.funding-card').forEach(card => {
        card.addEventListener('click', function() {
            const fundingId = this.dataset.fundingId;
            const funding = allFundings.find(f => f.id === fundingId);
            showFundingDetails(funding);
        });
    });
}

// Create funding card HTML
function createFundingCard(funding) {
    const deadline = new Date(funding.application.deadline);
    const now = new Date();
    const diffTime = deadline - now;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    let deadlineClass = 'safe';
    let cardClass = '';
    if (diffDays <= 7) {
        deadlineClass = 'urgent';
        cardClass = 'urgent';
    } else if (diffDays <= 30) {
        deadlineClass = 'warning';
        cardClass = 'closing-soon';
    }
    
    const amount = funding.funding_details.amount;
    const amountText = amount.min === amount.max ? 
        `£${formatNumber(amount.max)}` : 
        `£${formatNumber(amount.min)} - £${formatNumber(amount.max)}`;
    
    return `
        <div class="funding-card ${cardClass}" data-funding-id="${funding.id}">
            <div class="card-header">
                <div>
                    <h3 class="card-title">${funding.title}</h3>
                    <div class="card-organization">${funding.organization}</div>
                </div>
                <div class="card-amount">${amountText}</div>
            </div>
            
            <p class="card-description">${funding.description}</p>
            
            <div class="card-details">
                <div class="detail-item">
                    <i class="fas fa-user-graduate"></i>
                    <span>${funding.eligibility.career_stage}</span>
                </div>
                <div class="detail-item">
                    <i class="fas fa-clock"></i>
                    <span>${funding.funding_details.amount.duration_years} years</span>
                </div>
                <div class="detail-item">
                    <i class="fas fa-chart-line"></i>
                    <span>${funding.key_info.success_rate || 'N/A'}</span>
                </div>
                <div class="detail-item">
                    <i class="fas fa-calendar"></i>
                    <span>${funding.application.frequency}</span>
                </div>
            </div>
            
            <div class="card-tags">
                ${funding.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
            </div>
            
            <div class="card-footer">
                <div class="deadline ${deadlineClass}">
                    <i class="fas fa-calendar-alt"></i>
                    Deadline: ${formatDate(deadline)}
                    ${diffDays > 0 ? `(${diffDays} days)` : '(Closed)'}
                </div>
                <button class="view-details">View Details</button>
            </div>
        </div>
    `;
}

// Show funding details in modal
function showFundingDetails(funding) {
    const amount = funding.funding_details.amount;
    const amountText = amount.min === amount.max ? 
        `£${formatNumber(amount.max)}` : 
        `£${formatNumber(amount.min)} - £${formatNumber(amount.max)}`;
    
    modalContent.innerHTML = `
        <h2>${funding.title}</h2>
        <h3 style="color: #667eea; margin-bottom: 2rem;">${funding.organization}</h3>
        
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 2rem;">
            <div>
                <h4><i class="fas fa-info-circle"></i> Overview</h4>
                <p style="margin-bottom: 1rem;">${funding.description}</p>
                
                <h4><i class="fas fa-pound-sign"></i> Funding Details</h4>
                <ul style="margin-bottom: 1rem;">
                    <li><strong>Amount:</strong> ${amountText}</li>
                    <li><strong>Duration:</strong> ${funding.funding_details.amount.duration_years} years</li>
                    <li><strong>Covers:</strong> ${funding.funding_details.covers.join(', ')}</li>
                </ul>
                
                <h4><i class="fas fa-calendar"></i> Application</h4>
                <ul style="margin-bottom: 1rem;">
                    <li><strong>Deadline:</strong> ${formatDate(new Date(funding.application.deadline))}</li>
                    <li><strong>Next Deadline:</strong> ${formatDate(new Date(funding.application.next_deadline))}</li>
                    <li><strong>Frequency:</strong> ${funding.application.frequency}</li>
                </ul>
            </div>
            
            <div>
                <h4><i class="fas fa-user-check"></i> Eligibility</h4>
                <ul style="margin-bottom: 1rem;">
                    <li><strong>Career Stage:</strong> ${funding.eligibility.career_stage}</li>
                    <li><strong>Disciplines:</strong> ${funding.eligibility.disciplines.join(', ')}</li>
                </ul>
                <div style="margin-bottom: 1rem;">
                    <strong>Requirements:</strong>
                    <ul style="margin-left: 1rem;">
                        ${funding.eligibility.requirements.map(req => `<li>${req}</li>`).join('')}
                    </ul>
                </div>
                
                <h4><i class="fas fa-chart-bar"></i> Key Information</h4>
                <ul style="margin-bottom: 1rem;">
                    <li><strong>Priority Level:</strong> ${funding.key_info.priority_level}</li>
                    <li><strong>Competition Level:</strong> ${funding.key_info.competition_level}</li>
                    <li><strong>Success Rate:</strong> ${funding.key_info.success_rate || 'N/A'}</li>
                </ul>
                
                <div style="margin-top: 2rem;">
                    <a href="${funding.scraped_from || funding.application.application_url}" target="_blank" 
                       style="background: #667eea; color: white; padding: 0.75rem 1.5rem; 
                              border-radius: 6px; text-decoration: none; display: inline-block;">
                        <i class="fas fa-external-link-alt"></i> Apply Now
                    </a>
                </div>
            </div>
        </div>
        
        <div style="margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #eee;">
            <div style="display: flex; flex-wrap: wrap; gap: 0.5rem;">
                ${funding.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
            </div>
        </div>
    `;
    
    modal.style.display = 'block';
}

// Close modal
function closeModalHandler() {
    modal.style.display = 'none';
}

// Utility functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function formatNumber(num) {
    // Convert from pence to pounds if the number is very large (likely in pence)
    if (num > 1000000) {
        num = num / 100;
    }
    return new Intl.NumberFormat('en-GB').format(num);
}

function formatDate(date) {
    return date.toLocaleDateString('en-GB', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function showError(message) {
    fundingGrid.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 2rem; color: #e74c3c;">
            <i class="fas fa-exclamation-triangle" style="font-size: 2rem; margin-bottom: 1rem;"></i>
            <h3>Error</h3>
            <p>${message}</p>
        </div>
    `;
}