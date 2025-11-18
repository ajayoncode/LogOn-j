let charts = {};
let refreshInterval;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    loadDashboardData();
    
    // Auto-refresh every 10 seconds
    refreshInterval = setInterval(loadDashboardData, 10000);
    
    // Update last refresh time
    updateLastRefreshTime();
    setInterval(updateLastRefreshTime, 1000);
});

// Load dashboard data from API
async function loadDashboardData() {
    try {
        const response = await fetch('/api/data');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        
        console.log('API Data received:', {
            has_summary: !!data.summary,
            has_daily_stats: !!data.daily_stats && data.daily_stats.length > 0,
            has_hourly: !!data.hourly_activity && Object.keys(data.hourly_activity).length > 0,
            has_recent: !!data.recent_events && data.recent_events.length > 0
        });
        
        if (data.summary) {
            updateSummaryCards(data.summary, data.daily_stats);
            updateProjectsChart(data.summary.top_projects || {});
        }
        
        if (data.daily_stats && data.daily_stats.length > 0) {
            updateDailyChart(data.daily_stats);
        }
        
        if (data.hourly_activity && Object.keys(data.hourly_activity).length > 0) {
            updateHourlyChart(data.hourly_activity);
        }
        
        if (data.day_of_week_stats && data.day_of_week_stats.length > 0) {
            updateDayOfWeekChart(data.day_of_week_stats);
        }
        
        if (data.cumulative_time && data.cumulative_time.length > 0) {
            updateCumulativeChart(data.cumulative_time);
        }
        
        if (data.working_hours_analysis && data.working_hours_analysis.length > 0) {
            updateWorkingHoursChart(data.working_hours_analysis);
        }
        
        if (data.daily_project_breakdown && data.daily_project_breakdown.length > 0) {
            updateDailyProjectsChart(data.daily_project_breakdown);
        }
        
        updateRecentEventsTable(data.recent_events || []);
        
        updateLastRefreshTime();
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        const lastUpdateEl = document.getElementById('last-update-time');
        if (lastUpdateEl) {
            lastUpdateEl.textContent = 'Error loading data: ' + error.message;
        }
    }
}

// Update summary cards
function updateSummaryCards(summary, dailyStats) {
    if (!summary || Object.keys(summary).length === 0) {
        console.warn('No summary data available');
        return;
    }
    
    // Total coding time
    document.getElementById('total-duration').textContent = formatMinutes(summary.total_duration_minutes || 0);
    
    // Active days
    const activeDays = dailyStats ? dailyStats.length : 0;
    document.getElementById('total-days').textContent = activeDays;
    
    // Total projects
    document.getElementById('total-projects').textContent = formatNumber(summary.unique_projects || 0);
    
    // Average daily time
    const avgDaily = activeDays > 0 ? (summary.total_duration_minutes || 0) / activeDays : 0;
    document.getElementById('avg-daily').textContent = formatMinutes(avgDaily);
}

// Update daily activity chart
function updateDailyChart(dailyStats) {
    const ctx = document.getElementById('daily-chart');
    if (!ctx) return;
    
    if (!dailyStats || !Array.isArray(dailyStats) || dailyStats.length === 0) {
        console.warn('No daily stats data available');
        return;
    }
    
    const labels = dailyStats.map(d => {
        const date = new Date(d.date);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }).reverse();
    
    const durations = dailyStats.map(d => d.total_duration || 0).reverse();
    
    if (charts.daily) {
        charts.daily.destroy();
    }
    
    charts.daily = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Coding Time (minutes)',
                data: durations,
                borderColor: getChartColors().primary,
                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                tension: 0.4,
                fill: true,
                borderWidth: 2
            }]
        },
        options: {
            ...defaultChartOptions,
            scales: {
                ...defaultChartOptions.scales,
                y: {
                    ...defaultChartOptions.scales.y,
                    title: {
                        display: true,
                        text: 'Time (minutes)'
                    }
                }
            }
        }
    });
}

// Update hourly activity chart
function updateHourlyChart(hourlyData) {
    const ctx = document.getElementById('hourly-chart');
    if (!ctx) return;
    
    if (!hourlyData || !hourlyData.hours || !hourlyData.duration) {
        console.warn('No hourly activity data available');
        return;
    }
    
    const hours = Array.from({ length: 24 }, (_, i) => i);
    const durations = hours.map(h => {
        const index = hourlyData.hours.indexOf(h);
        return index !== -1 ? (hourlyData.duration[index] || 0) : 0;
    });
    
    if (charts.hourly) {
        charts.hourly.destroy();
    }
    
    charts.hourly = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: hours.map(h => `${h}:00`),
            datasets: [{
                label: 'Activity (minutes)',
                data: durations,
                backgroundColor: getChartColors().gradient[0],
                borderColor: getChartColors().primary,
                borderWidth: 1
            }]
        },
        options: defaultChartOptions
    });
}

// Update day of week chart
function updateDayOfWeekChart(dayStats) {
    const ctx = document.getElementById('day-of-week-chart');
    if (!ctx) return;
    
    if (!dayStats || !Array.isArray(dayStats) || dayStats.length === 0) {
        console.warn('No day of week data available');
        return;
    }
    
    const labels = dayStats.map(d => d.day.substring(0, 3)); // Mon, Tue, etc.
    const durations = dayStats.map(d => d.total_duration || 0);
    
    if (charts.dayOfWeek) {
        charts.dayOfWeek.destroy();
    }
    
    charts.dayOfWeek = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Coding Time (minutes)',
                data: durations,
                backgroundColor: getChartColors().primary,
                borderColor: getChartColors().secondary,
                borderWidth: 2
            }]
        },
        options: {
            ...defaultChartOptions,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Time (minutes)'
                    }
                }
            }
        }
    });
}

// Update cumulative time chart
function updateCumulativeChart(cumulativeData) {
    const ctx = document.getElementById('cumulative-chart');
    if (!ctx) return;
    
    if (!cumulativeData || !Array.isArray(cumulativeData) || cumulativeData.length === 0) {
        console.warn('No cumulative time data available');
        return;
    }
    
    const labels = cumulativeData.map(d => {
        const date = new Date(d.date);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
    
    const dailyMinutes = cumulativeData.map(d => d.daily_minutes || 0);
    const cumulativeMinutes = cumulativeData.map(d => d.cumulative_minutes || 0);
    
    if (charts.cumulative) {
        charts.cumulative.destroy();
    }
    
    charts.cumulative = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Cumulative Time (minutes)',
                data: cumulativeMinutes,
                borderColor: getChartColors().primary,
                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                tension: 0.4,
                fill: true,
                yAxisID: 'y'
            }, {
                label: 'Daily Time (minutes)',
                data: dailyMinutes,
                borderColor: getChartColors().warning,
                backgroundColor: 'rgba(245, 158, 11, 0.1)',
                tension: 0.4,
                fill: true,
                yAxisID: 'y1',
                type: 'bar'
            }]
        },
        options: {
            ...defaultChartOptions,
            scales: {
                y: {
                    beginAtZero: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Cumulative (minutes)'
                    }
                },
                y1: {
                    beginAtZero: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Daily (minutes)'
                    },
                    grid: {
                        drawOnChartArea: false
                    }
                }
            }
        }
    });
}

// Update working hours chart
function updateWorkingHoursChart(workingHoursData) {
    const ctx = document.getElementById('working-hours-chart');
    if (!ctx) return;
    
    if (!workingHoursData || !Array.isArray(workingHoursData) || workingHoursData.length === 0) {
        console.warn('No working hours data available');
        return;
    }
    
    const labels = workingHoursData.map(d => {
        const date = new Date(d.date);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
    
    const workingHours = workingHoursData.map(d => d.working_hours || 0);
    const productivity = workingHoursData.map(d => d.productivity || 0);
    const durationMinutes = workingHoursData.map(d => d.duration_minutes || 0);
    
    if (charts.workingHours) {
        charts.workingHours.destroy();
    }
    
    charts.workingHours = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Working Hours',
                data: workingHours,
                backgroundColor: getChartColors().info,
                borderColor: getChartColors().info,
                borderWidth: 1,
                yAxisID: 'y'
            }, {
                label: 'Productivity %',
                data: productivity,
                borderColor: getChartColors().success,
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                tension: 0.4,
                type: 'line',
                yAxisID: 'y1'
            }, {
                label: 'Duration (minutes)',
                data: durationMinutes,
                backgroundColor: getChartColors().warning,
                borderColor: getChartColors().warning,
                borderWidth: 1,
                yAxisID: 'y2',
                type: 'bar',
                hidden: true
            }]
        },
        options: {
            ...defaultChartOptions,
            scales: {
                y: {
                    beginAtZero: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Working Hours'
                    }
                },
                y1: {
                    beginAtZero: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Productivity %'
                    },
                    grid: {
                        drawOnChartArea: false
                    },
                    max: 100
                },
                y2: {
                    beginAtZero: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Duration (minutes)'
                    },
                    grid: {
                        drawOnChartArea: false
                    },
                    display: false
                }
            }
        }
    });
}

// Update daily projects breakdown chart
function updateDailyProjectsChart(dailyProjectsData) {
    const ctx = document.getElementById('daily-projects-chart');
    if (!ctx) return;
    
    if (!dailyProjectsData || !Array.isArray(dailyProjectsData) || dailyProjectsData.length === 0) {
        console.warn('No daily projects data available');
        return;
    }
    
    // Get all project keys (excluding 'date')
    const projectKeys = Object.keys(dailyProjectsData[0]).filter(key => key !== 'date');
    
    const labels = dailyProjectsData.map(d => {
        const date = new Date(d.date);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
    
    const colors = getChartColors().gradient;
    const datasets = projectKeys.map((project, index) => ({
        label: getProjectName(project),
        data: dailyProjectsData.map(d => d[project] || 0),
        backgroundColor: colors[index % colors.length],
        borderColor: colors[index % colors.length],
        borderWidth: 1
    }));
    
    if (charts.dailyProjects) {
        charts.dailyProjects.destroy();
    }
    
    charts.dailyProjects = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            ...defaultChartOptions,
            scales: {
                x: {
                    stacked: true,
                    grid: {
                        display: false
                    }
                },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Duration (minutes)'
                    }
                }
            },
            plugins: {
                tooltip: {
                    mode: 'index',
                    intersect: false
                },
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// Update projects chart
function updateProjectsChart(projects) {
    const ctx = document.getElementById('projects-chart');
    if (!ctx) return;
    
    if (!projects || Object.keys(projects).length === 0) {
        console.warn('No projects data available');
        return;
    }
    
    const sortedProjects = Object.entries(projects)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10);
    
    const labels = sortedProjects.map(([name]) => getProjectName(name));
    const durations = sortedProjects.map(([, duration]) => duration || 0);
    
    if (charts.projects) {
        charts.projects.destroy();
    }
    
    charts.projects = new Chart(ctx, {
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
                    grid: {
                        color: '#e2e8f0'
                    }
                },
                y: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

// Update recent events table (only shows coding sessions with duration)
function updateRecentEventsTable(events) {
    const tbody = document.getElementById('recent-events-tbody');
    if (!tbody) return;
    
    // Filter to only show typing events with actual duration (coding sessions)
    const codingSessions = events.filter(e => 
        (e.event === 'typing' || e.event === 'typing_start') && 
        e.durationMs && 
        e.durationMs > 0
    ).slice(0, 50);
    
    if (codingSessions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="loading-text">No coding sessions found</td></tr>';
        return;
    }
    
    tbody.innerHTML = codingSessions.map(event => `
        <tr>
            <td>${formatDate(event.timestamp)}</td>
            <td title="${event.file || '-'}">${truncateText(getFileName(event.file), 30)}</td>
            <td>${event.language || '-'}</td>
            <td title="${event.workspace || '-'}">${truncateText(getProjectName(event.workspace), 25)}</td>
            <td>${formatDuration(event.durationMs)}</td>
            <td>${event.gitBranch || '-'}</td>
        </tr>
    `).join('');
}

// Update last refresh time
function updateLastRefreshTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    document.getElementById('last-update-time').textContent = `Last updated: ${timeString}`;
}

