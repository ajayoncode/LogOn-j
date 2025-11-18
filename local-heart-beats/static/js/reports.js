let reportCharts = {};
let currentReportType = 'daily';
let filters = {
    startDate: null,
    endDate: null,
    project: null
};

// Initialize reports page
document.addEventListener('DOMContentLoaded', async () => {
    await loadFilters();
    setupEventListeners();
    await loadReportData('daily');
});

// Setup event listeners
function setupEventListeners() {
    document.getElementById('report-type').addEventListener('change', async (e) => {
        currentReportType = e.target.value;
        await loadReportData(currentReportType);
    });
    
    document.getElementById('apply-filters').addEventListener('click', async () => {
        filters.startDate = document.getElementById('start-date').value || null;
        filters.endDate = document.getElementById('end-date').value || null;
        filters.project = document.getElementById('project-filter').value || null;
        await loadReportData(currentReportType);
    });
    
    document.getElementById('reset-filters').addEventListener('click', async () => {
        document.getElementById('start-date').value = '';
        document.getElementById('end-date').value = '';
        document.getElementById('project-filter').value = '';
        filters = { startDate: null, endDate: null, project: null };
        await loadReportData(currentReportType);
    });
    
    document.getElementById('report-type').addEventListener('change', (e) => {
        const projectFilter = document.getElementById('project-filter');
        if (e.target.value === 'projects') {
            projectFilter.style.display = 'none';
        } else {
            projectFilter.style.display = 'block';
        }
    });
}

// Load available filters
async function loadFilters() {
    try {
        const response = await fetch('/api/reports/filters');
        const data = await response.json();
        
        // Populate project filter
        const projectSelect = document.getElementById('project-filter');
        projectSelect.innerHTML = '<option value="">All Projects</option>';
        data.projects.forEach(project => {
            const option = document.createElement('option');
            option.value = project;
            option.textContent = getProjectName(project);
            projectSelect.appendChild(option);
        });
        
        // Set date range
        if (data.date_range.min) {
            document.getElementById('start-date').min = data.date_range.min;
        }
        if (data.date_range.max) {
            document.getElementById('end-date').max = data.date_range.max;
            document.getElementById('end-date').value = data.date_range.max;
        }
    } catch (error) {
        console.error('Error loading filters:', error);
    }
}

// Load report data
async function loadReportData(type) {
    try {
        let endpoint = '';
        let params = new URLSearchParams();
        
        if (type === 'daily') {
            endpoint = '/api/reports/daily';
            if (filters.startDate) params.append('start_date', filters.startDate);
            if (filters.endDate) params.append('end_date', filters.endDate);
        } else if (type === 'monthly') {
            endpoint = '/api/reports/monthly';
        } else if (type === 'projects') {
            endpoint = '/api/reports/projects';
            if (filters.project) params.append('project', filters.project);
        }
        
        const url = params.toString() ? `${endpoint}?${params.toString()}` : endpoint;
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        console.log(`Reports API ${type}:`, {
            data_count: result.data ? result.data.length : 0,
            total: result.total_days || result.total_months || result.total_projects || 0
        });
        
        if (!result.data || result.data.length === 0) {
            console.warn(`No data available for ${type} reports`);
        }
        
        updateReportSummary(result);
        updateReportCharts(type, result.data || []);
        updateReportTable(type, result.data || []);
        
        // Update titles
        const titles = {
            daily: 'Daily Activity Report',
            monthly: 'Monthly Activity Report',
            projects: 'Project Activity Report'
        };
        const chartTitleEl = document.getElementById('report-chart-title');
        const tableTitleEl = document.getElementById('table-title');
        if (chartTitleEl) chartTitleEl.textContent = titles[type];
        if (tableTitleEl) tableTitleEl.textContent = `${titles[type]} - Data Table`;
        
    } catch (error) {
        console.error('Error loading report data:', error);
        const summaryDiv = document.getElementById('report-summary');
        if (summaryDiv) {
            summaryDiv.innerHTML = `<div class="summary-card"><h4>Error</h4><div class="value">${error.message}</div></div>`;
        }
    }
}

// Update report summary cards
function updateReportSummary(result) {
    const summaryDiv = document.getElementById('report-summary');
    
    if (currentReportType === 'daily') {
        const totalDays = result.total_days || 0;
        const totalDuration = result.data.reduce((sum, d) => sum + (d.total_duration || 0), 0);
        const totalEvents = result.data.reduce((sum, d) => sum + (d.event_count || 0), 0);
        const avgDuration = totalDays > 0 ? totalDuration / totalDays : 0;
        
        summaryDiv.innerHTML = `
            <div class="summary-card">
                <h4>Total Days</h4>
                <div class="value">${totalDays}</div>
            </div>
            <div class="summary-card">
                <h4>Total Duration</h4>
                <div class="value">${formatMinutes(totalDuration)}</div>
            </div>
            <div class="summary-card">
                <h4>Total Events</h4>
                <div class="value">${formatNumber(totalEvents)}</div>
            </div>
            <div class="summary-card">
                <h4>Avg Daily Duration</h4>
                <div class="value">${formatMinutes(avgDuration)}</div>
            </div>
        `;
    } else if (currentReportType === 'monthly') {
        const totalMonths = result.total_months || 0;
        const totalDuration = result.data.reduce((sum, d) => sum + (d.total_duration || 0), 0);
        const totalEvents = result.data.reduce((sum, d) => sum + (d.event_count || 0), 0);
        const avgDuration = totalMonths > 0 ? totalDuration / totalMonths : 0;
        
        summaryDiv.innerHTML = `
            <div class="summary-card">
                <h4>Total Months</h4>
                <div class="value">${totalMonths}</div>
            </div>
            <div class="summary-card">
                <h4>Total Duration</h4>
                <div class="value">${formatMinutes(totalDuration)}</div>
            </div>
            <div class="summary-card">
                <h4>Total Events</h4>
                <div class="value">${formatNumber(totalEvents)}</div>
            </div>
            <div class="summary-card">
                <h4>Avg Monthly Duration</h4>
                <div class="value">${formatMinutes(avgDuration)}</div>
            </div>
        `;
    } else if (currentReportType === 'projects') {
        const totalProjects = result.total_projects || 0;
        const totalDuration = result.data.reduce((sum, d) => sum + (d.total_duration || 0), 0);
        const totalEvents = result.data.reduce((sum, d) => sum + (d.event_count || 0), 0);
        
        summaryDiv.innerHTML = `
            <div class="summary-card">
                <h4>Total Projects</h4>
                <div class="value">${totalProjects}</div>
            </div>
            <div class="summary-card">
                <h4>Total Duration</h4>
                <div class="value">${formatMinutes(totalDuration)}</div>
            </div>
            <div class="summary-card">
                <h4>Total Events</h4>
                <div class="value">${formatNumber(totalEvents)}</div>
            </div>
            <div class="summary-card">
                <h4>Avg Files per Project</h4>
                <div class="value">${totalProjects > 0 ? Math.round(result.data.reduce((sum, d) => sum + (d.file_count || 0), 0) / totalProjects) : 0}</div>
            </div>
        `;
    }
}

// Update report charts
function updateReportCharts(type, data) {
    const ctx = document.getElementById('report-chart');
    const distCtx = document.getElementById('report-distribution-chart');
    
    if (!ctx || !distCtx) {
        console.warn('Chart canvases not found');
        return;
    }
    
    if (!data || !Array.isArray(data) || data.length === 0) {
        console.warn(`No data available for ${type} charts`);
        return;
    }
    
    // Main chart
    if (reportCharts.main) {
        reportCharts.main.destroy();
    }
    
    if (type === 'daily' || type === 'monthly') {
        const labels = data.map(d => {
            if (type === 'daily') {
                const date = new Date(d.date);
                return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            } else {
                return d.month;
            }
        });
        
        const durations = data.map(d => d.total_duration || 0);
        const eventCounts = data.map(d => d.event_count || 0);
        
        reportCharts.main = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Duration (minutes)',
                    data: durations,
                    borderColor: getChartColors().primary,
                    backgroundColor: 'rgba(99, 102, 241, 0.1)',
                    tension: 0.4,
                    fill: true
                }, {
                    label: 'Event Count',
                    data: eventCounts,
                    borderColor: getChartColors().success,
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.4,
                    fill: true,
                    yAxisID: 'y1'
                }]
            },
            options: {
                ...defaultChartOptions,
                scales: {
                    ...defaultChartOptions.scales,
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        beginAtZero: true,
                        grid: {
                            drawOnChartArea: false
                        }
                    }
                }
            }
        });
        
        // Distribution chart (bar chart)
        reportCharts.distribution = new Chart(distCtx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Duration (minutes)',
                    data: durations,
                    backgroundColor: getChartColors().gradient[0],
                    borderColor: getChartColors().primary,
                    borderWidth: 1
                }]
            },
            options: defaultChartOptions
        });
        
    } else if (type === 'projects') {
        const sorted = [...data].sort((a, b) => (b.total_duration || 0) - (a.total_duration || 0)).slice(0, 15);
        const labels = sorted.map(d => getProjectName(d.workspace));
        const durations = sorted.map(d => d.total_duration || 0);
        
        reportCharts.main = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Duration (minutes)',
                    data: durations,
                    backgroundColor: getChartColors().primary,
                    borderColor: getChartColors().secondary,
                    borderWidth: 1
                }]
            },
            options: {
                ...defaultChartOptions,
                indexAxis: 'y',
                scales: {
                    x: {
                        beginAtZero: true,
                        grid: { color: '#e2e8f0' }
                    },
                    y: {
                        grid: { display: false }
                    }
                }
            }
        });
        
        // Distribution chart (doughnut)
        const eventCounts = sorted.map(d => d.event_count || 0);
        reportCharts.distribution = new Chart(distCtx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: eventCounts,
                    backgroundColor: getChartColors().gradient,
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }
}

// Update report table
function updateReportTable(type, data) {
    const thead = document.getElementById('report-table-head');
    const tbody = document.getElementById('report-table-body');
    
    if (!thead || !tbody) {
        console.warn('Table elements not found');
        return;
    }
    
    if (!data || !Array.isArray(data) || data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" class="loading-text">No data available</td></tr>';
        return;
    }
    
    if (type === 'daily') {
        thead.innerHTML = `
            <tr>
                <th>Date</th>
                <th>Total Duration (min)</th>
                <th>Event Count</th>
                <th>Projects</th>
                <th>Files</th>
            </tr>
        `;
        tbody.innerHTML = data.map(d => `
            <tr>
                <td>${new Date(d.date).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}</td>
                <td>${formatMinutes(d.total_duration || 0)}</td>
                <td>${formatNumber(d.event_count || 0)}</td>
                <td>${formatNumber(d.project_count || 0)}</td>
                <td>${formatNumber(d.file_count || 0)}</td>
            </tr>
        `).join('');
    } else if (type === 'monthly') {
        thead.innerHTML = `
            <tr>
                <th>Month</th>
                <th>Total Duration (min)</th>
                <th>Event Count</th>
                <th>Projects</th>
                <th>Files</th>
            </tr>
        `;
        tbody.innerHTML = data.map(d => `
            <tr>
                <td>${d.month}</td>
                <td>${formatMinutes(d.total_duration || 0)}</td>
                <td>${formatNumber(d.event_count || 0)}</td>
                <td>${formatNumber(d.project_count || 0)}</td>
                <td>${formatNumber(d.file_count || 0)}</td>
            </tr>
        `).join('');
    } else if (type === 'projects') {
        thead.innerHTML = `
            <tr>
                <th>Project</th>
                <th>Total Duration (min)</th>
                <th>Event Count</th>
                <th>Avg Duration (sec)</th>
                <th>Files</th>
                <th>First Seen</th>
                <th>Last Seen</th>
            </tr>
        `;
        const sorted = [...data].sort((a, b) => (b.total_duration || 0) - (a.total_duration || 0));
        tbody.innerHTML = sorted.map(d => `
            <tr>
                <td title="${d.workspace}">${truncateText(getProjectName(d.workspace), 30)}</td>
                <td>${formatMinutes(d.total_duration || 0)}</td>
                <td>${formatNumber(d.event_count || 0)}</td>
                <td>${(d.avg_duration || 0).toFixed(1)}s</td>
                <td>${formatNumber(d.file_count || 0)}</td>
                <td>${d.first_seen || '-'}</td>
                <td>${d.last_seen || '-'}</td>
            </tr>
        `).join('');
    }
}

