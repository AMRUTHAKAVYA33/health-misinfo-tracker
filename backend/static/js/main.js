document.addEventListener("DOMContentLoaded", function () {
    // 🔥 Get data from HTML attributes (SAFE)
    const appDataEl = document.getElementById('app-data');
    const healthResult = appDataEl ? appDataEl.dataset.result : null;
    const modelAccuracy = parseFloat(appDataEl ? appDataEl.dataset.modelAccuracy : 86.4);
    
    console.log('Health Result:', healthResult);
    console.log('Model Accuracy:', modelAccuracy);

    // Model Accuracy Chart
    initModelCharts(modelAccuracy);

    // Live prediction tracking
    handlePredictions(healthResult);

    // Initialize counters and recent list
    updateLiveStats();
    updateRecentList();
});

function initModelCharts(accuracy) {
    const accuracyCanvas = document.getElementById('modelAccuracyChart');
    if (accuracyCanvas) {
        const ctx = accuracyCanvas.getContext('2d');
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [accuracy, 100 - accuracy],
                    backgroundColor: ['#10b981', 'rgba(148, 163, 184, 0.2)'],
                    borderWidth: 0
                }]
            },
            options: {
                cutout: '75%',
                responsive: false,
                plugins: { legend: false },
                animation: { animateRotate: true, duration: 2000 }
            }
        });
    }
}

function handlePredictions(result) {
    if (!result) return;

    let predictions = JSON.parse(localStorage.getItem('predictions') || '[]');
    
    // Add current prediction
    predictions.unshift({
        label: result.label,
        confidence: result.confidence_percent || result.confidence || 0,
        text: result.text_preview || result.text?.substring(0, 100) || 'Health statement analyzed'
    });
    
    // Keep only last 10
    predictions = predictions.slice(0, 10);
    localStorage.setItem('predictions', JSON.stringify(predictions));
    
    updateRecentList();
    updateLiveStats();
}

function updateRecentList() {
    const container = document.getElementById('recentPredictionsList');
    if (!container) return;
    
    const predictions = JSON.parse(localStorage.getItem('predictions') || '[]');
    
    if (predictions.length === 0) {
        container.innerHTML = '<div class="recent-empty text-muted">No predictions yet</div>';
        return;
    }
    
    container.innerHTML = predictions.map(function(prediction) {
        const labelClass = prediction.label === 'misinfo' ? 'misinfo' : 'true-info';
        return `
            <div class="recent-item ${labelClass}">
                <div class="recent-content">
                    <span class="label">${prediction.label.toUpperCase()}</span>
                    <span class="confidence">${prediction.confidence}%</span>
                </div>
                <div class="text-preview">${prediction.text}</div>
            </div>
        `;
    }).join('');
}

function updateLiveStats() {
    const predictions = JSON.parse(localStorage.getItem('predictions') || '[]');
    const total = predictions.length;
    const misinfo = predictions.filter(function(p) { return p.label === 'misinfo'; }).length;
    const trueInfo = predictions.filter(function(p) { return p.label === 'true-info'; }).length;
    
    // Update counters safely
    const totalEl = document.getElementById('totalAnalyzed');
    const misinfoEl = document.getElementById('misinfoCount');
    const trueEl = document.getElementById('trueCount');
    
    if (totalEl) totalEl.textContent = total;
    if (misinfoEl) misinfoEl.textContent = misinfo;
    if (trueEl) trueEl.textContent = trueInfo;
}
