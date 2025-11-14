// Страница управления полями
let map;
let drawControl;
let drawnItems;
let currentField = null;
let fields = [];

// Инициализация карты
function initMap() {
    // Центр карты - примерные координаты России
    map = L.map('map').setView([55.7558, 37.6173], 6);
    
    // Добавляем тайлы OpenStreetMap
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19
    }).addTo(map);
    
    // Инициализация рисования
    drawnItems = new L.FeatureGroup();
    map.addLayer(drawnItems);
    
    drawControl = new L.Control.Draw({
        draw: {
            polygon: {
                allowIntersection: false,
                showArea: true
            },
            rectangle: true,
            circle: false,
            marker: false,
            polyline: false,
            circlemarker: false
        },
        edit: {
            featureGroup: drawnItems,
            remove: true
        }
    });
    
    map.addControl(drawControl);
    
    // Функция расчета площади
    function calculateArea(latLngs) {
        if (!latLngs || latLngs.length < 3) return 0;
        
        let area = 0;
        const R = 6378137;
        const toRad = Math.PI / 180;
        
        for (let i = 0; i < latLngs.length; i++) {
            const j = (i + 1) % latLngs.length;
            const lat1 = latLngs[i].lat * toRad;
            const lat2 = latLngs[j].lat * toRad;
            const dLon = (latLngs[j].lng - latLngs[i].lng) * toRad;
            
            area += dLon * (2 + Math.sin(lat1) + Math.sin(lat2));
        }
        
        area = Math.abs(area) * R * R / 2;
        return area / 10000;
    }
    
    // Обработчики событий рисования
    map.on(L.Draw.Event.CREATED, function(event) {
        const layer = event.layer;
        drawnItems.addLayer(layer);
        
        const geometry = layer.toGeoJSON();
        let area = 0;
        
        if (layer instanceof L.Polygon) {
            const latLngs = layer.getLatLngs()[0];
            area = calculateArea(latLngs);
        } else if (layer instanceof L.Rectangle) {
            const bounds = layer.getBounds();
            const sw = bounds.getSouthWest();
            const ne = bounds.getNorthEast();
            const latLngs = [
                L.latLng(sw.lat, sw.lng),
                L.latLng(sw.lat, ne.lng),
                L.latLng(ne.lat, ne.lng),
                L.latLng(ne.lat, sw.lng)
            ];
            area = calculateArea(latLngs);
        }
        
        currentField = {
            geometry: JSON.stringify(geometry.geometry),
            area: area.toFixed(2)
        };
        
        document.getElementById('field-input').style.display = 'block';
        document.getElementById('save-field-btn').style.display = 'inline-block';
        document.getElementById('cancel-field-btn').style.display = 'inline-block';
    });
    
    map.on(L.Draw.Event.EDITED, function(event) {
        const layers = event.layers;
        layers.eachLayer(function(layer) {
            if (layer.toGeoJSON) {
                const geometry = layer.toGeoJSON();
                let area = 0;
                
                if (layer instanceof L.Polygon) {
                    const latLngs = layer.getLatLngs()[0];
                    area = calculateArea(latLngs);
                } else if (layer instanceof L.Rectangle) {
                    const bounds = layer.getBounds();
                    const sw = bounds.getSouthWest();
                    const ne = bounds.getNorthEast();
                    const latLngs = [
                        L.latLng(sw.lat, sw.lng),
                        L.latLng(sw.lat, ne.lng),
                        L.latLng(ne.lat, ne.lng),
                        L.latLng(ne.lat, sw.lng)
                    ];
                    area = calculateArea(latLngs);
                }
                
                currentField = {
                    geometry: JSON.stringify(geometry.geometry),
                    area: area.toFixed(2)
                };
            }
        });
    });
}

// Загрузка полей
async function loadFields() {
    try {
        const response = await fetch('/api/fields');
        fields = await response.json();
        displayFields();
        displayFieldsOnMap();
    } catch (error) {
        console.error('Ошибка загрузки полей:', error);
    }
}

// Отображение полей в списке
function displayFields() {
    const container = document.getElementById('fields-list');
    const summaryContainer = document.getElementById('fields-summary');
    
    if (fields.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #6b7280; padding: 40px;">Поля пока не добавлены. Нажмите "Добавить новое поле" и нарисуйте поле на карте.</p>';
        if (summaryContainer) summaryContainer.innerHTML = '';
        return;
    }
    
    // Вычисляем общую площадь
    const totalArea = fields.reduce((sum, field) => sum + (parseFloat(field.area) || 0), 0);
    if (summaryContainer) {
        summaryContainer.innerHTML = `${fields.length} полей · ${totalArea.toFixed(2)} га`;
    }
    
    container.innerHTML = fields.map(field => {
        const createdDate = field.created_at ? new Date(field.created_at).toLocaleDateString('ru-RU') : 'Не указана';
        return `
            <div class="field-card" data-field-id="${field.id}">
                <div class="field-name-container">
                    <h3 class="field-name-display" data-field-id="${field.id}">${escapeHtml(field.name)}</h3>
                    <input type="text" class="field-name-edit input" data-field-id="${field.id}" value="${escapeHtml(field.name)}" style="display: none;">
                    <button class="btn-icon" onclick="startEditFieldName(${field.id})" title="Редактировать название">
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M11.5 2.5a2.121 2.121 0 0 1 3 3L6.5 12.5 2.5 13.5 3.5 9.5 11.5 2.5z"/>
                        </svg>
                    </button>
                </div>
                <p style="margin: 10px 0;"><strong>Площадь:</strong> ${field.area || '0'} га</p>
                <p style="margin: 10px 0;"><strong>Создано:</strong> ${createdDate}</p>
                <div class="field-actions">
                    <button class="btn btn-success" onclick="viewField(${field.id})">Просмотр</button>
                    <button class="btn btn-danger" onclick="deleteField(${field.id})">Удалить</button>
                </div>
            </div>
        `;
    }).join('');
}

// Отображение полей на карте
function displayFieldsOnMap() {
    drawnItems.clearLayers();
    
    fields.forEach(field => {
        try {
            const geometry = JSON.parse(field.geometry);
            const layer = L.geoJSON(geometry, {
                style: {
                    color: '#ef4444',
                    fillColor: '#ef4444',
                    fillOpacity: 0.3,
                    weight: 2
                }
            }).bindPopup(`<b>${escapeHtml(field.name)}</b><br>Площадь: ${field.area || 'Не указана'} га<br><button class="btn btn-success" onclick="viewField(${field.id})" style="margin-top: 5px; width: 100%;">Просмотр поля</button>`);
            drawnItems.addLayer(layer);
        } catch (error) {
            console.error('Ошибка отображения поля на карте:', error);
        }
    });
    
    if (fields.length > 0) {
        map.fitBounds(drawnItems.getBounds());
    }
}

// Просмотр поля
function viewField(fieldId) {
    // Можно перейти на отдельную страницу или показать детали поля
    // Пока просто центрируем карту на поле
    const field = fields.find(f => f.id === fieldId);
    if (field) {
        try {
            const geometry = JSON.parse(field.geometry);
            const layer = L.geoJSON(geometry);
            map.fitBounds(layer.getBounds());
            
            // Открываем popup
            drawnItems.eachLayer(function(l) {
                if (l.feature && l.feature.id === fieldId) {
                    l.openPopup();
                }
            });
        } catch (error) {
            console.error('Ошибка просмотра поля:', error);
        }
    }
}

// Добавление нового поля
document.getElementById('add-field-btn').addEventListener('click', function() {
    document.getElementById('field-name').value = '';
    document.getElementById('field-input').style.display = 'none';
    document.getElementById('save-field-btn').style.display = 'none';
    document.getElementById('cancel-field-btn').style.display = 'none';
    currentField = null;
    drawnItems.clearLayers();
    map.removeControl(drawControl);
    map.addControl(drawControl);
});

// Отмена добавления поля
document.getElementById('cancel-field-btn').addEventListener('click', function() {
    document.getElementById('field-input').style.display = 'none';
    document.getElementById('save-field-btn').style.display = 'none';
    document.getElementById('cancel-field-btn').style.display = 'none';
    document.getElementById('field-name').value = '';
    currentField = null;
    drawnItems.clearLayers();
});

// Сохранение поля
document.getElementById('save-field-btn').addEventListener('click', async function() {
    const name = document.getElementById('field-name').value.trim();
    if (!name) {
        return;
    }
    
    if (!currentField) {
        return;
    }
    
    try {
        const response = await fetch('/api/fields', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: name,
                geometry: currentField.geometry,
                area: parseFloat(currentField.area)
            })
        });
        
        if (response.ok) {
            document.getElementById('field-input').style.display = 'none';
            document.getElementById('save-field-btn').style.display = 'none';
            document.getElementById('cancel-field-btn').style.display = 'none';
            document.getElementById('field-name').value = '';
            currentField = null;
            loadFields();
        }
    } catch (error) {
        console.error('Ошибка сохранения поля:', error);
    }
});

// Начало редактирования названия поля
function startEditFieldName(fieldId) {
    const display = document.querySelector(`.field-name-display[data-field-id="${fieldId}"]`);
    const edit = document.querySelector(`.field-name-edit[data-field-id="${fieldId}"]`);
    const btn = event.target.closest('.btn-icon');
    
    if (display && edit) {
        display.style.display = 'none';
        edit.style.display = 'block';
        edit.focus();
        edit.select();
        btn.style.display = 'none';
        
        // Сохранение при потере фокуса или Enter
        edit.addEventListener('blur', function() {
            saveFieldName(fieldId);
        }, { once: true });
        
        edit.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                edit.blur();
            } else if (e.key === 'Escape') {
                e.preventDefault();
                cancelEditFieldName(fieldId);
            }
        });
    }
}

// Сохранение названия поля
async function saveFieldName(fieldId) {
    const edit = document.querySelector(`.field-name-edit[data-field-id="${fieldId}"]`);
    const display = document.querySelector(`.field-name-display[data-field-id="${fieldId}"]`);
    const btn = document.querySelector(`.btn-icon[onclick="startEditFieldName(${fieldId})"]`);
    const field = fields.find(f => f.id === fieldId);
    
    if (!edit || !field) return;
    
    const newName = edit.value.trim();
    if (!newName || newName === field.name) {
        cancelEditFieldName(fieldId);
        return;
    }
    
    try {
        const response = await fetch(`/api/fields/${fieldId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: newName
            })
        });
        
        if (response.ok) {
            field.name = newName;
            display.textContent = escapeHtml(newName);
            edit.style.display = 'none';
            display.style.display = 'block';
            if (btn) btn.style.display = 'inline-block';
        } else {
            cancelEditFieldName(fieldId);
        }
    } catch (error) {
        console.error('Ошибка обновления поля:', error);
        cancelEditFieldName(fieldId);
    }
}

// Отмена редактирования названия поля
function cancelEditFieldName(fieldId) {
    const display = document.querySelector(`.field-name-display[data-field-id="${fieldId}"]`);
    const edit = document.querySelector(`.field-name-edit[data-field-id="${fieldId}"]`);
    const btn = document.querySelector(`.btn-icon[onclick="startEditFieldName(${fieldId})"]`);
    const field = fields.find(f => f.id === fieldId);
    
    if (display && edit && field) {
        edit.value = field.name;
        edit.style.display = 'none';
        display.style.display = 'block';
        if (btn) btn.style.display = 'inline-block';
    }
}

// Удаление поля
async function deleteField(fieldId) {
    try {
        const response = await fetch(`/api/fields/${fieldId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            loadFields();
        }
    } catch (error) {
        console.error('Ошибка удаления поля:', error);
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    initMap();
    loadFields();
});

