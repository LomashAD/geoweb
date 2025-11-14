from flask import Flask, render_template, request, jsonify
from config import get_database_url, get_secret_key, db, init_app_db
from models import Field, Crop, CropHistory
from neural_network_recommender import recommender
from calculator_api import calculate_profit_with_rotation
from utils import seed_initial_crops
from datetime import datetime

app = Flask(__name__)

# Конфигурация приложения
app.config['SQLALCHEMY_DATABASE_URI'] = get_database_url()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = get_secret_key()

# Инициализация базы данных
init_app_db(app)

# Маршруты
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/fields')
def fields_page():
    return render_template('fields.html')

@app.route('/history')
def history_page():
    return render_template('history.html')

@app.route('/calculator')
def calculator_page():
    return render_template('calculator.html')


@app.route('/api/fields', methods=['GET'])
def get_fields():
    fields = Field.query.all()
    return jsonify([field.to_dict() for field in fields])


@app.route('/api/fields', methods=['POST'])
def create_field():
    data = request.json
    try:
        field = Field(
            name=data['name'],
            geometry=data['geometry'],
            area=data.get('area', 0)
        )
        db.session.add(field)
        db.session.commit()
        return jsonify(field.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@app.route('/api/fields/<int:field_id>', methods=['PUT'])
def update_field(field_id):
    field = Field.query.get_or_404(field_id)
    data = request.json
    try:
        if 'name' in data:
            field.name = data['name']
        if 'geometry' in data:
            field.geometry = data['geometry']
        if 'area' in data:
            field.area = data['area']
        db.session.commit()
        return jsonify(field.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@app.route('/api/fields/<int:field_id>', methods=['DELETE'])
def delete_field(field_id):
    field = Field.query.get_or_404(field_id)
    try:
        db.session.delete(field)
        db.session.commit()
        return jsonify({'message': 'Поле удалено'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@app.route('/api/crops', methods=['GET'])
def get_crops():
    crops = Crop.query.all()
    return jsonify([crop.to_dict() for crop in crops])


@app.route('/api/crop-history', methods=['GET'])
def get_crop_history():
    field_id = request.args.get('field_id', type=int)
    query = CropHistory.query
    if field_id:
        query = query.filter_by(field_id=field_id)
    history = query.order_by(CropHistory.year.desc(), CropHistory.id.desc()).all()
    return jsonify([h.to_dict() for h in history])


@app.route('/api/crop-history', methods=['POST'])
def create_crop_history():
    data = request.json
    try:
        history = CropHistory(
            field_id=data['field_id'],
            crop_id=data['crop_id'],
            year=data['year'],
            season=data.get('season', 'весна-лето'),
            notes=data.get('notes', '')
        )
        db.session.add(history)
        db.session.commit()
        return jsonify(history.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@app.route('/api/crop-history/<int:history_id>', methods=['DELETE'])
def delete_crop_history(history_id):
    history = CropHistory.query.get_or_404(history_id)
    try:
        db.session.delete(history)
        db.session.commit()
        return jsonify({'message': 'Запись удалена'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@app.route('/api/field-recommendation', methods=['GET'])
def get_field_recommendation():
    # Получение рекомендации
    field_id = request.args.get('field_id', type=int)
    
    if not field_id:
        return jsonify({'error': 'Не указано поле'}), 400
    
    try:
        field = Field.query.get_or_404(field_id) # берём поле
        
        history = CropHistory.query.filter_by(field_id=field_id).order_by( #Смотрим историю посева
            CropHistory.year.desc()
        ).all()
        
        crop_history = [h.to_dict() for h in history] # история для нейронки
        
        recommendation = recommender.generate_field_recommendation( # генерация
            field_name=field.name,
            field_geometry=field.geometry,
            crop_history=crop_history
        )
        
        return jsonify(recommendation)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/calculate', methods=['POST'])
def calculate_economics():
    data = request.json
    crop_id = data.get('crop_id')
    area = data.get('area', 0)
    previous_crop_name = data.get('previous_crop')
    
    if not crop_id or area <= 0:
        return jsonify({'error': 'Не указана культура или площадь'}), 400
    
    crop = Crop.query.get_or_404(crop_id)
    previous_crop = None
    if previous_crop_name:
        previous_crop = Crop.query.filter_by(name=previous_crop_name).first()
    
    try:
        result = calculate_profit_with_rotation(
            crop=crop,
            area=area,
            previous_crop=previous_crop
        )
        
        result['costs'] = {
            'seed_cost': result['cost_breakdown']['seed_cost'],
            'fertilizer_cost': result['cost_breakdown']['fertilizer_cost'],
            'other_costs': result['cost_breakdown']['other_costs'],
            'total_costs': result['total_costs']
        }
        result['revenue'] = {
            'yield_total': result['total_harvest'],
            'revenue': result['revenue'],
            'profit': result['net_profit'],
            'profit_per_ha': round(result['net_profit'] / area if area > 0 else 0, 2)
        }
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Ошибка расчета: {str(e)}'}), 500


@app.route('/api/calculator/prices/crops', methods=['GET'])
def get_current_crop_prices():
    crops = Crop.query.all()
    prices = {crop.name: crop.market_price_per_ton for crop in crops}
    
    return jsonify({
        'prices': prices,
        'currency': 'RUB/тонна',
        'last_updated': datetime.now().isoformat()
    })


@app.route('/api/calculator/crops/<crop_name>', methods=['GET'])
def get_crop_details_for_calculator(crop_name: str):
    crop = Crop.query.filter_by(name=crop_name).first_or_404()
    
    seed_rate = 200 if crop.category == "Зерновые" else (120 if crop.category == "Бобовые" else 100) # Норма высева (приблизительно)
    
    return jsonify({
        'name': crop.name,
        'base_yield': crop.yield_per_ha,
        'market_price': crop.market_price_per_ton,
        'seed_price': crop.seed_price_per_kg,
        'seed_rate': seed_rate,
        'fertilizer_cost_per_ha': crop.fertilizer_cost_per_ha,
        'category': crop.category
    })


# Инициализация базы данных
def init_db():
    with app.app_context():
        db.create_all()
        # Обучаем нейронну
        try:
            recommender.train()
            print("Нейронная сеть успешно обучена")
        except Exception as e:
            print(f"Предупреждение: не удалось обучить нейронную сеть: {e}")
        seed_initial_crops()


if __name__ == '__main__':
    app.run(debug=True, port=5000)

