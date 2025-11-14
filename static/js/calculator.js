// Страница экономического калькулятора
let crops = [];

// Загрузка культур
async function loadCrops() {
    try {
        const response = await fetch('/api/crops');
        crops = await response.json();
        loadCropsForSelect();
    } catch (error) {
        console.error('Ошибка загрузки культур:', error);
    }
}

// Загрузка культур для селекта
function loadCropsForSelect() {
    const select = document.getElementById('calc-crop-select');
    const prevSelect = document.getElementById('calc-previous-crop-select');
    
    const options = '<option value="">Выберите культуру</option>' +
        crops.map(crop => `<option value="${crop.id}">${escapeHtml(crop.name)}</option>`).join('');
    
    select.innerHTML = options;
    prevSelect.innerHTML = '<option value="">Предыдущая культура (необязательно)</option>' +
        crops.map(crop => `<option value="${crop.name}">${escapeHtml(crop.name)}</option>`).join('');
    
    // Загружаем информацию о культуре при выборе
    select.addEventListener('change', function() {
        const cropId = this.value;
        if (cropId) {
            const crop = crops.find(c => c.id == cropId);
            if (crop) {
                loadCropInfo(crop.name);
            }
        } else {
            document.getElementById('crop-info').style.display = 'none';
        }
    });
}

// Загрузка информации о культуре
async function loadCropInfo(cropName) {
    try {
        const response = await fetch(`/api/calculator/crops/${encodeURIComponent(cropName)}`);
        if (response.ok) {
            const data = await response.json();
            displayCropInfo(data);
        }
    } catch (error) {
        console.error('Ошибка загрузки информации о культуре:', error);
    }
}

// Отображение информации о культуре
function displayCropInfo(cropData) {
    const container = document.getElementById('crop-info-content');
    const infoDiv = document.getElementById('crop-info');
    
    container.innerHTML = `
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-top: 10px;">
            <div><strong>Базовая урожайность:</strong> ${cropData.base_yield} т/га</div>
            <div><strong>Рыночная цена:</strong> ${formatCurrency(cropData.market_price)} руб/т</div>
            <div><strong>Цена семян:</strong> ${formatCurrency(cropData.seed_price)} руб/кг</div>
            <div><strong>Норма высева:</strong> ${cropData.seed_rate} кг/га</div>
            <div><strong>Категория:</strong> ${cropData.category}</div>
            <div><strong>Стоимость удобрений:</strong> ${formatCurrency(cropData.fertilizer_cost_per_ha)} руб/га</div>
        </div>
    `;
    
    infoDiv.style.display = 'block';
}

// Расчет
document.getElementById('calculate-btn').addEventListener('click', async function() {
    const cropId = document.getElementById('calc-crop-select').value;
    const area = parseFloat(document.getElementById('calc-area').value);
    const previousCrop = document.getElementById('calc-previous-crop-select').value;
    
    if (!cropId || !area || area <= 0) {
        return;
    }
    
    try {
        const response = await fetch('/api/calculate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                crop_id: parseInt(cropId),
                area: area,
                previous_crop: previousCrop || null
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            displayCalculatorResult(result);
        }
    } catch (error) {
        console.error('Ошибка расчета:', error);
    }
});

// Отображение результатов калькулятора
function displayCalculatorResult(result) {
    const container = document.getElementById('calculator-result');
    
    let rotationInfo = '';
    if (result.previous_crop && result.calculation_details) {
        const details = result.calculation_details;
        rotationInfo = `
            <div class="calc-section" style="background: #f0f8ff; padding: 15px; border-radius: 5px; margin: 15px 0;">
                <h4>Влияние севооборота</h4>
                <p><strong>Предыдущая культура:</strong> ${escapeHtml(result.previous_crop)}</p>
                <p><strong>Базовая урожайность:</strong> ${details.base_yield} т/га</p>
                <p><strong>Скорректированная урожайность:</strong> ${details.adjusted_yield} т/га 
                   (коэффициент: ${details.yield_multiplier > 1 ? '+' : ''}${((details.yield_multiplier - 1) * 100).toFixed(1)}%)</p>
                <p><strong>Влияние на удобрения:</strong> ${details.fertilizer_multiplier > 1 ? '+' : ''}${((details.fertilizer_multiplier - 1) * 100).toFixed(1)}%</p>
            </div>
        `;
    }
    
    const html = `
        <h3>Расчет для: ${escapeHtml(result.crop_name)}</h3>
        <p><strong>Площадь:</strong> ${result.area} га</p>
        
        ${rotationInfo}
        
        <div class="calc-section">
            <h3>Расходы</h3>
            <div class="calc-row">
                <span>Стоимость семян:</span>
                <span>${formatCurrency(result.costs.seed_cost)} руб.</span>
            </div>
            <div class="calc-row">
                <span>Стоимость удобрений:</span>
                <span>${formatCurrency(result.costs.fertilizer_cost)} руб.</span>
            </div>
            <div class="calc-row">
                <span>Прочие расходы:</span>
                <span>${formatCurrency(result.costs.other_costs)} руб.</span>
            </div>
            <div class="calc-row">
                <span><strong>Итого расходов:</strong></span>
                <span><strong>${formatCurrency(result.costs.total_costs)} руб.</strong></span>
            </div>
        </div>
        
        <div class="calc-section">
            <h3>Доходы</h3>
            <div class="calc-row">
                <span>Урожайность:</span>
                <span>${result.revenue.yield_total.toFixed(2)} тонн</span>
            </div>
            <div class="calc-row">
                <span>Выручка:</span>
                <span>${formatCurrency(result.revenue.revenue)} руб.</span>
            </div>
        </div>
        
        <div class="calc-total" style="background: ${result.revenue.profit >= 0 ? '#d4edda' : '#f8d7da'}; padding: 20px; border-radius: 5px; margin-top: 20px;">
            <div style="font-size: 1.3em; font-weight: bold;">
                Прибыль: ${formatCurrency(result.revenue.profit)} руб.
            </div>
            ${result.profitability !== undefined ? `
                <div style="font-size: 1.1em; margin-top: 10px;">
                    Рентабельность: ${result.profitability.toFixed(2)}%
                </div>
            ` : ''}
            <div style="font-size: 0.9em; margin-top: 10px; color: #666;">
                Прибыль с гектара: ${formatCurrency(result.revenue.profit_per_ha)} руб.
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}

// Инициализация
document.addEventListener('DOMContentLoaded', function() {
    loadCrops();
});

