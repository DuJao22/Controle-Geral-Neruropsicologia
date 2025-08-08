// Dashboard JavaScript Functions

// Global chart instances
let faturamentoChart = null;
let tiposChart = null;
let timelineChart = null;

// Initialize all charts
function initializeCharts(data) {
    if (data.faturamento) {
        initializeFaturamentoChart(data.faturamento);
    }
    if (data.tipos) {
        initializeTiposChart(data.tipos);
    }
    // Initialize timeline chart with API data
    loadTimelineData();
}

// Revenue by Doctor Chart
function initializeFaturamentoChart(data) {
    const ctx = document.getElementById('faturamentoChart');
    if (!ctx) return;

    const labels = data.map(item => item.nome);
    const values = data.map(item => item.total);

    faturamentoChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Faturamento (R$)',
                data: values,
                backgroundColor: [
                    '#28a745',
                    '#20c997',
                    '#17a2b8',
                    '#ffc107',
                    '#fd7e14',
                    '#e83e8c',
                    '#6f42c1',
                    '#007bff'
                ],
                borderColor: '#28a745',
                borderWidth: 1,
                borderRadius: 5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return 'R$ ' + context.parsed.y.toFixed(2);
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return 'R$ ' + value.toFixed(0);
                        }
                    }
                },
                x: {
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45
                    }
                }
            }
        }
    });
}

// Password Types Pie Chart
function initializeTiposChart(data) {
    const ctx = document.getElementById('tiposChart');
    if (!ctx) return;

    const labels = data.map(item => item.tipo === 'consulta' ? 'Consultas' : 'Testes');
    const values = data.map(item => item.count);

    tiposChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: [
                    '#28a745',
                    '#20c997'
                ],
                borderColor: '#ffffff',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.parsed / total) * 100).toFixed(1);
                            return context.label + ': ' + context.parsed + ' (' + percentage + '%)';
                        }
                    }
                }
            }
        }
    });
}

// Load and initialize timeline chart
function loadTimelineData() {
    fetch('/api/dashboard_data')
        .then(response => response.json())
        .then(data => {
            if (data.timeline) {
                initializeTimelineChart(data.timeline);
            }
        })
        .catch(error => {
            console.error('Error loading timeline data:', error);
        });
}

// Sessions Timeline Chart
function initializeTimelineChart(data) {
    const ctx = document.getElementById('timelineChart');
    if (!ctx) return;

    const labels = data.map(item => {
        const date = new Date(item.data);
        return date.toLocaleDateString('pt-BR');
    });
    const values = data.map(item => item.count);

    timelineChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Sessões Realizadas',
                data: values,
                borderColor: '#28a745',
                backgroundColor: 'rgba(40, 167, 69, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#28a745',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                },
                x: {
                    ticks: {
                        maxTicksLimit: 10,
                        maxRotation: 45
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    });
}

// Utility Functions

// Format currency
function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
}

// Format date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('pt-BR');
}

// Show loading state
function showLoading(element) {
    if (element) {
        element.classList.add('loading');
    }
}

// Hide loading state
function hideLoading(element) {
    if (element) {
        element.classList.remove('loading');
    }
}

// Confirm dialog for important actions
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// Auto-refresh data every 5 minutes
function startAutoRefresh() {
    setInterval(function() {
        if (typeof loadTimelineData === 'function') {
            loadTimelineData();
        }
    }, 300000); // 5 minutes
}

// Initialize auto-refresh when page loads
document.addEventListener('DOMContentLoaded', function() {
    startAutoRefresh();
    
    // Add smooth scrolling to anchor links (only if they exist)
    const anchorLinks = document.querySelectorAll('a[href^="#"]');
    if (anchorLinks.length > 0) {
        anchorLinks.forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const targetId = this.getAttribute('href');
                if (targetId && targetId !== '#') {
                    const target = document.querySelector(targetId);
                    if (target) {
                        target.scrollIntoView({
                            behavior: 'smooth',
                            block: 'start'
                        });
                    }
                }
            });
        });
    }
    
    // Add tooltips to elements with data-bs-toggle="tooltip"
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

// Mobile menu handler
function toggleMobileMenu() {
    const navbar = document.querySelector('.navbar-collapse');
    if (navbar) {
        navbar.classList.toggle('show');
    }
}

// Form validation helpers
function validateForm(formElement) {
    const inputs = formElement.querySelectorAll('input[required], select[required], textarea[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.classList.add('is-invalid');
            isValid = false;
        } else {
            input.classList.remove('is-invalid');
        }
    });
    
    return isValid;
}

// File upload helpers
function setupFileUpload() {
    const fileInputs = document.querySelectorAll('input[type="file"]');
    
    fileInputs.forEach(input => {
        input.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                validateFile(file, e.target);
            }
        });
    });
}

function validateFile(file, input) {
    const maxSize = 50 * 1024 * 1024; // 50MB - increased size limit
    
    if (file.size > maxSize) {
        alert('Arquivo muito grande. Tamanho máximo: 50MB');
        input.value = '';
        return false;
    }
    
    // Allow all file types - no type restriction
    return true;
}

// Initialize file upload when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    setupFileUpload();
});
