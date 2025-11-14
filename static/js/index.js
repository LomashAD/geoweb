// Главная страница - статистика, последние поля и рекомендации
let fields = [];
let crops = [];
let historyRecords = [];

// Загрузка статистики
async function loadStats() {
    try {
        // Загружаем поля
        const fieldsResponse = await fetch('/api/fields');
        fields = await fieldsResponse.json();
        
        // Загружаем культуры
        const cropsResponse = await fetch('/api/crops');
        crops = await cropsResponse.json();
        
        // Загружаем историю
        const historyResponse = await fetch('/api/crop-history');
        historyRecords = await historyResponse.json();
        
        // Обновляем статистику
        updateStats();
        
        // Отображаем последние поля
        displayLastFields();
        
        // Загружаем рекомендации
        loadAllRecommendations();
    } catch (error) {
        console.error('Ошибка загрузки данных:', error);
    }
}

// Обновление статистики
function updateStats() {
    document.getElementById('stat-fields').textContent = fields.length;
    document.getElementById('stat-crops').textContent = crops.length;
    document.getElementById('stat-history').textContent = historyRecords.length;
    
    // Количество рекомендаций будет обновлено после загрузки рекомендаций
}

// Отображение последних полей
function displayLastFields() {
    const container = document.getElementById('last-fields-list');
    
    if (fields.length === 0) {
        container.innerHTML = '<p class="no-data">Поля пока не добавлены. Перейдите в раздел "Мои поля" для добавления.</p>';
        return;
    }
    
    // Сортируем поля по дате создания (последние первыми)
    const sortedFields = [...fields].sort((a, b) => {
        const dateA = new Date(a.created_at || 0);
        const dateB = new Date(b.created_at || 0);
        return dateB - dateA;
    });
    
    // Берем последние 2 поля
    const lastFields = sortedFields.slice(0, 2);
    
    let html = '';
    lastFields.forEach(field => {
        const createdDate = field.created_at ? new Date(field.created_at).toLocaleDateString('ru-RU') : 'Не указана';
        html += `
            <div class="field-item">
                <div class="field-item-name">${escapeHtml(field.name)}</div>
                <div class="field-item-info">
                    <span class="field-item-label">Площадь:</span>
                    <span class="field-item-value">${field.area || '0'} га.</span>
                </div>
                <div class="field-item-info">
                    <span class="field-item-label">Создано:</span>
                    <span class="field-item-value">${createdDate}</span>
                </div>
                <div style="margin-top: 10px;">
                    <a href="/fields" class="btn btn-secondary" style="text-decoration: none; display: inline-block;">Просмотр</a>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// Загрузка рекомендаций для всех полей
async function loadAllRecommendations() {
    const container = document.getElementById('all-recommendations');
    
    if (fields.length === 0) {
        container.innerHTML = '<p class="no-data">Поля пока не добавлены. Перейдите в раздел "Мои поля" для добавления.</p>';
        document.getElementById('stat-recommendations').textContent = '0';
        return;
    }
    
    container.innerHTML = '<p class="loading-text">Загрузка рекомендаций...</p>';
    
    try {
        const recommendations = [];
        
        // Загружаем рекомендации для каждого поля
        for (const field of fields) {
            try {
                const response = await fetch(`/api/field-recommendation?field_id=${field.id}`);
                if (response.ok) {
                    const recommendation = await response.json();
                    recommendations.push({
                        field: field,
                        recommendation: recommendation
                    });
                }
            } catch (error) {
                console.error(`Ошибка загрузки рекомендации для поля ${field.id}:`, error);
            }
        }
        
        document.getElementById('stat-recommendations').textContent = recommendations.length;
        displayAllRecommendations(recommendations);
    } catch (error) {
        console.error('Ошибка загрузки рекомендаций:', error);
        container.innerHTML = '<p class="error-text">Не удалось загрузить рекомендации</p>';
        document.getElementById('stat-recommendations').textContent = '0';
    }
}

// Отображение всех рекомендаций в формате карточек
function displayAllRecommendations(recommendations) {
    const container = document.getElementById('all-recommendations');
    
    if (recommendations.length === 0) {
        container.innerHTML = '<p class="no-data">Рекомендации отсутствуют</p>';
        return;
    }
    
    let html = `<p style="color: #6b7280; margin-bottom: 15px; font-size: 0.9em;">${recommendations.length} рекомендаций</p>`;
    
    recommendations.forEach(item => {
        const field = item.field;
        const rec = item.recommendation;
        
        // Форматируем рекомендуемые культуры
        const recommendedCrops = rec.recommended_crop ? rec.recommended_crop.split(',').map(c => c.trim()).join(', ') : '';
        
        // Берем рекомендацию 
        let recommendation = rec.message || rec.justification || 'Рекомендация по севообороту';
        
        // Формируем текст рекомендации 
        const recommendationText = `${escapeHtml(recommendation)}`;
        
        html += `
            <div class="recommendation-card">
                <div class="recommendation-justification">${recommendationText}</div>
                ${recommendedCrops ? `<div class="recommendation-crops-small">${escapeHtml(recommendedCrops)}</div>` : ''}
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    loadStats();
});

