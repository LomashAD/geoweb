// Страница истории культур
let crops = [];

// Загрузка культур
async function loadCrops() {
    try {
        const response = await fetch('/api/crops');
        crops = await response.json();
    } catch (error) {
        console.error('Ошибка загрузки культур:', error);
    }
}

// Загрузка полей для селекта
async function loadFieldsForSelect() {
    try {
        const response = await fetch('/api/fields');
        const fieldsData = await response.json();
        const select = document.getElementById('history-field-select');
        select.innerHTML = '<option value="">Выберите поле</option>' +
            fieldsData.map(field => `<option value="${field.id}">${escapeHtml(field.name)}</option>`).join('');
    } catch (error) {
        console.error('Ошибка загрузки полей:', error);
    }
}

// Загрузка культур для селекта
function loadCropsForSelect() {
    const select = document.getElementById('history-crop-select');
    select.innerHTML = '<option value="">Выберите культуру</option>' +
        crops.map(crop => `<option value="${crop.id}">${escapeHtml(crop.name)}</option>`).join('');
}

// Добавление записи истории
document.getElementById('add-history-btn').addEventListener('click', function() {
    const fieldId = document.getElementById('history-field-select').value;
    if (!fieldId) {
        return;
    }
    document.getElementById('history-form').style.display = 'block';
    loadCropsForSelect();
    document.getElementById('history-year').value = new Date().getFullYear();
});

// Отмена добавления
document.getElementById('cancel-history-btn').addEventListener('click', function() {
    document.getElementById('history-form').style.display = 'none';
    document.getElementById('history-crop-select').value = '';
    document.getElementById('history-year').value = '';
    document.getElementById('history-notes').value = '';
});

// Сохранение записи истории
document.getElementById('save-history-btn').addEventListener('click', async function() {
    const fieldId = document.getElementById('history-field-select').value;
    const cropId = document.getElementById('history-crop-select').value;
    const year = document.getElementById('history-year').value;
    const season = document.getElementById('history-season').value;
    const notes = document.getElementById('history-notes').value;
    
    if (!fieldId || !cropId || !year) {
        return;
    }
    
    try {
        const response = await fetch('/api/crop-history', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                field_id: parseInt(fieldId),
                crop_id: parseInt(cropId),
                year: parseInt(year),
                season: season,
                notes: notes
            })
        });
        
        if (response.ok) {
            document.getElementById('history-form').style.display = 'none';
            document.getElementById('history-crop-select').value = '';
            document.getElementById('history-year').value = '';
            document.getElementById('history-notes').value = '';
            loadHistory();
        }
    } catch (error) {
        console.error('Ошибка сохранения истории:', error);
    }
});

// Загрузка истории
async function loadHistory() {
    const fieldId = document.getElementById('history-field-select').value;
    if (!fieldId) {
        document.getElementById('history-table').innerHTML = '';
        return;
    }
    
    try {
        const response = await fetch(`/api/crop-history?field_id=${fieldId}`);
        const history = await response.json();
        displayHistory(history);
    } catch (error) {
        console.error('Ошибка загрузки истории:', error);
    }
}

// Отображение истории
function displayHistory(history) {
    const container = document.getElementById('history-table');
    if (history.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #6b7280; padding: 40px;">История по этому полю отсутствует.</p>';
        return;
    }
    
    container.innerHTML = `
        <table>
            <thead>
                <tr>
                    <th>Год</th>
                    <th>Сезон</th>
                    <th>Культура</th>
                    <th>Примечания</th>
                    <th>Действия</th>
                </tr>
            </thead>
            <tbody>
                ${history.map(h => `
                    <tr>
                        <td>${h.year}</td>
                        <td>${escapeHtml(h.season)}</td>
                        <td>${escapeHtml(h.crop_name)}</td>
                        <td>${escapeHtml(h.notes || '-')}</td>
                        <td>
                            <button class="btn btn-danger" onclick="deleteHistory(${h.id})">Удалить</button>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

// Удаление записи истории
async function deleteHistory(historyId) {
    try {
        const response = await fetch(`/api/crop-history/${historyId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            loadHistory();
        }
    } catch (error) {
        console.error('Ошибка удаления истории:', error);
    }
}

// Инициализация
document.getElementById('history-field-select').addEventListener('change', loadHistory);

document.addEventListener('DOMContentLoaded', function() {
    loadCrops();
    loadFieldsForSelect();
});

