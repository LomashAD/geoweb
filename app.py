from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from functools import wraps
from config import get_database_url, get_secret_key, db, init_app_db
from models import Field, Crop, CropHistory, User
from neural_network_recommender import recommender
from calculator_api import calculate_profit_with_rotation
from utils import seed_initial_crops
from price_updater import update_all_crop_prices, get_price_update_status
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit

app = Flask(__name__)


def login_required(f):
    """Декоратор для проверки авторизации пользователя"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('account', form='login'))
        return f(*args, **kwargs)
    return decorated_function


def api_login_required(f):
    """Декоратор для проверки авторизации в API маршрутах"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Требуется авторизация'}), 401
        return f(*args, **kwargs)
    return decorated_function

# Конфигурация приложения
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = get_secret_key()

# Инициализация базы данных
init_app_db(app)

# Автоматическое создание таблиц при запуске
with app.app_context():
    try:
        db.create_all()
        db.create_all(bind_key='users')
        print("Таблицы базы данных успешно созданы")
        
        # Миграция: добавление колонки last_price_update, если её нет
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('crops')]
            
            if 'last_price_update' not in columns:
                print("Добавление колонки last_price_update в таблицу crops...")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE crops ADD COLUMN last_price_update DATETIME"))
                    conn.commit()
                print("Колонка last_price_update успешно добавлена")
                
                # Устанавливаем старую дату (25 часов назад) для существующих записей
                # Это позволит системе сразу обновить цены при первом запуске
                with db.engine.connect() as conn:
                    # Обновляем все записи, у которых дата NULL или очень свежая (вероятно, из предыдущей миграции)
                    conn.execute(text("""
                        UPDATE crops 
                        SET last_price_update = datetime('now', '-25 hours') 
                        WHERE last_price_update IS NULL 
                           OR datetime(last_price_update) > datetime('now', '-1 hour')
                    """))
                    conn.commit()
                print("Установлена дата обновления для существующих записей (25 часов назад для немедленного обновления)")
        except Exception as migration_error:
            print(f"Предупреждение при миграции: {migration_error}")
            
    except Exception as e:
        print(f"Предупреждение при создании таблиц: {e}")

# Настройка планировщика для автоматического обновления цен
scheduler = BackgroundScheduler()
scheduler.start()

def scheduled_price_update():
    """Функция для автоматического обновления цен каждые 24 часа"""
    with app.app_context():
        try:
            print("\n[ПЛАНИРОВЩИК] Запуск автоматического обновления цен...")
            update_all_crop_prices(force=False)
            print("[ПЛАНИРОВЩИК] Обновление цен завершено\n")
        except Exception as e:
            print(f"[ПЛАНИРОВЩИК] Ошибка при обновлении цен: {e}\n")

# Планируем обновление цен каждые 24 часа
scheduler.add_job(
    func=scheduled_price_update,
    trigger=IntervalTrigger(hours=24),
    id='update_crop_prices',
    name='Обновление цен на культуры каждые 24 часа',
    replace_existing=True
)

# Выполняем первое обновление при запуске
# Проверяем, нужно ли принудительное обновление (если все даты одинаковые - значит была миграция)
with app.app_context():
    try:
        from models import Crop
        from datetime import timedelta
        
        # Проверяем, есть ли культуры, которые никогда не обновлялись или обновлялись недавно
        crops = Crop.query.all()
        need_force_update = False
        
        if crops:
            # Если все культуры имеют одинаковую дату обновления (вероятно, из миграции)
            # или если прошло менее 24 часов - делаем принудительное обновление
            first_update = crops[0].last_price_update if crops[0].last_price_update else None
            if first_update:
                time_since = datetime.utcnow() - first_update
                if time_since < timedelta(hours=24):
                    # Все культуры обновлены недавно - вероятно, это результат миграции
                    # Делаем принудительное обновление при первом запуске
                    need_force_update = True
                    print("\n[ИНИЦИАЛИЗАЦИЯ] Обнаружены недавно обновленные культуры (миграция).")
                    print("[ИНИЦИАЛИЗАЦИЯ] Выполняется принудительное обновление цен...")
        
        print("\n[ИНИЦИАЛИЗАЦИЯ] Первичное обновление цен...")
        update_all_crop_prices(force=need_force_update)
        print("[ИНИЦИАЛИЗАЦИЯ] Первичное обновление завершено\n")
    except Exception as e:
        print(f"[ИНИЦИАЛИЗАЦИЯ] Ошибка при первичном обновлении цен: {e}\n")

# Остановка планировщика при выходе из приложения
atexit.register(lambda: scheduler.shutdown())

# Маршруты
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('account', form='login'))
    return render_template('index.html')

@app.route('/fields')
@login_required
def fields_page():
    return render_template('fields.html')

@app.route('/history')
@login_required
def history_page():
    return render_template('history.html')

@app.route('/calculator')
@login_required
def calculator_page():
    return render_template('calculator.html')

@app.route('/account')
def account():
    # Если пользователь уже авторизован, перенаправляем на главную
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('account.html')


@app.route('/register', methods=['POST'])
def register():
    # Если пользователь уже авторизован, перенаправляем на главную
    if 'user_id' in session:
        return redirect(url_for('index'))
    
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    confirm_password = request.form.get('confirm_password', '')
    
    # Валидация
    errors = []
    if not username or len(username) < 3:
        errors.append('Имя пользователя должно быть не менее 3 символов')
    if not email or '@' not in email:
        errors.append('Введите корректный email')
    if not password or len(password) < 6:
        errors.append('Пароль должен быть не менее 6 символов')
    if password != confirm_password:
        errors.append('Пароли не совпадают')
    
    if errors:
        return redirect(url_for('account', form='register', error=errors[0]))
    
    # Проверка существующего пользователя
    if User.query.filter_by(username=username).first():
        return redirect(url_for('account', form='register', error='Пользователь с таким именем уже существует'))
    
    if User.query.filter_by(email=email).first():
        return redirect(url_for('account', form='register', error='Пользователь с таким email уже существует'))
    
    # Создание нового пользователя
    try:
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        # Автоматический вход после регистрации
        session['user_id'] = new_user.id
        session['username'] = new_user.username
        session['email'] = new_user.email
        
        return redirect(url_for('index'))
    except Exception as e:
        db.session.rollback()
        return redirect(url_for('account', form='register', error=f'Ошибка при регистрации: {str(e)}'))


@app.route('/login', methods=['POST'])
def login():
    # Если пользователь уже авторизован, перенаправляем на главную
    if 'user_id' in session:
        return redirect(url_for('index'))
    
    username_or_email = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    
    if not username_or_email or not password:
        return redirect(url_for('account', form='login', error='Заполните все поля'))
    
    # Поиск пользователя по username или email
    user = User.query.filter(
        (User.username == username_or_email) | (User.email == username_or_email)
    ).first()
    
    if user and user.check_password(password):
        # Успешный вход - сохраняем в сессии
        session['user_id'] = user.id
        session['username'] = user.username
        session['email'] = user.email
        return redirect(url_for('index'))
    else:
        return redirect(url_for('account', form='login', error='Неверное имя пользователя или пароль'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/api/fields', methods=['GET'])
@api_login_required
def get_fields():
    fields = Field.query.all()
    return jsonify([field.to_dict() for field in fields])


@app.route('/api/fields', methods=['POST'])
@api_login_required
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
@api_login_required
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
@api_login_required
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
@api_login_required
def get_crops():
    crops = Crop.query.all()
    return jsonify([crop.to_dict() for crop in crops])


@app.route('/api/crop-history', methods=['GET'])
@api_login_required
def get_crop_history():
    field_id = request.args.get('field_id', type=int)
    query = CropHistory.query
    if field_id:
        query = query.filter_by(field_id=field_id)
    history = query.order_by(CropHistory.year.desc(), CropHistory.id.desc()).all()
    return jsonify([h.to_dict() for h in history])


@app.route('/api/crop-history', methods=['POST'])
@api_login_required
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
@api_login_required
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
@api_login_required
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
@api_login_required
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
@api_login_required
def get_current_crop_prices():
    crops = Crop.query.all()
    prices = {crop.name: crop.market_price_per_ton for crop in crops}
    
    # Получаем статус обновления цен
    status = get_price_update_status()
    
    return jsonify({
        'prices': prices,
        'currency': 'RUB/тонна',
        'last_updated': datetime.now().isoformat(),
        'update_status': status
    })


@app.route('/api/admin/update-prices', methods=['POST'])
@api_login_required
def manual_update_prices():
    """Ручное обновление цен (для администратора)"""
    try:
        force = request.json.get('force', False) if request.is_json else False
        result = update_all_crop_prices(force=force)
        return jsonify({
            'success': True,
            'message': 'Цены успешно обновлены',
            'stats': result
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/admin/price-status', methods=['GET'])
@api_login_required
def get_price_status():
    """Получение статуса обновления цен"""
    try:
        status = get_price_update_status()
        return jsonify(status), 200
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500


@app.route('/api/calculator/crops/<crop_name>', methods=['GET'])
@api_login_required
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
        # Создание таблиц для основной базы данных
        db.create_all()
        # Создание таблиц для базы данных пользователей (с указанием bind)
        db.create_all(bind_key='users')
        # Обучаем нейронну
        try:
            recommender.train()
            print("Нейронная сеть успешно обучена")
        except Exception as e:
            print(f"Предупреждение: не удалось обучить нейронную сеть: {e}")
        seed_initial_crops()


if __name__ == '__main__':
    app.run(debug=True, port=5000)

