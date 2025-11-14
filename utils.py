from flask import Flask
from config import get_database_url, db, init_app_db
from models import Field, Crop, CropHistory

def ensure_database_exists(db_url: str):
	pass


def seed_initial_crops():
	if Crop.query.count() > 0:
		return
	
	initial_crops = [
		Crop(name='Пшеница', category='Зерновые', seed_price_per_kg=25, 
		     fertilizer_cost_per_ha=15000, yield_per_ha=4.5, market_price_per_ton=18000, 
		     other_costs_per_ha=8000),
		Crop(name='Ячмень', category='Зерновые', seed_price_per_kg=20, 
		     fertilizer_cost_per_ha=12000, yield_per_ha=4.0, market_price_per_ton=15000, 
		     other_costs_per_ha=7000),
		Crop(name='Горох', category='Бобовые', seed_price_per_kg=50, 
		     fertilizer_cost_per_ha=8000, yield_per_ha=3.0, market_price_per_ton=25000, 
		     other_costs_per_ha=6000),
		Crop(name='Фасоль', category='Бобовые', seed_price_per_kg=60, 
		     fertilizer_cost_per_ha=9000, yield_per_ha=2.5, market_price_per_ton=30000, 
		     other_costs_per_ha=7000),
		Crop(name='Кукуруза', category='Зерновые', seed_price_per_kg=120, 
		     fertilizer_cost_per_ha=18000, yield_per_ha=8.0, market_price_per_ton=14000, 
		     other_costs_per_ha=10000),
		Crop(name='Картофель', category='Овощные', seed_price_per_kg=30, 
		     fertilizer_cost_per_ha=20000, yield_per_ha=25.0, market_price_per_ton=15000, 
		     other_costs_per_ha=15000),
		Crop(name='Люцерна', category='Бобовые', seed_price_per_kg=200, 
		     fertilizer_cost_per_ha=5000, yield_per_ha=8.0, market_price_per_ton=8000, 
		     other_costs_per_ha=4000),
		Crop(name='Клевер', category='Бобовые', seed_price_per_kg=150, 
		     fertilizer_cost_per_ha=4000, yield_per_ha=6.0, market_price_per_ton=7000, 
		     other_costs_per_ha=3000),
		Crop(name='Овес', category='Зерновые', seed_price_per_kg=22, 
		     fertilizer_cost_per_ha=11000, yield_per_ha=3.5, market_price_per_ton=14000, 
		     other_costs_per_ha=6500),
		Crop(name='Свекла', category='Овощные', seed_price_per_kg=35, 
		     fertilizer_cost_per_ha=16000, yield_per_ha=40.0, market_price_per_ton=12000, 
		     other_costs_per_ha=12000),
	]
	
	for crop in initial_crops:
		db.session.add(crop)
	db.session.commit()
	print(f"[OK] Добавлено {len(initial_crops)} культур")


def init_database():
	db_url = get_database_url()
	ensure_database_exists(db_url)
	
	app = Flask(__name__)
	app.config['SQLALCHEMY_DATABASE_URI'] = db_url
	app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
	init_app_db(app)
	
	with app.app_context():
		db.create_all()
		seed_initial_crops()
		print("[SUCCESS] Таблицы созданы, данные загружены")


def check_database():
	# Проверка состояния бд
	app = Flask(__name__)
	app.config['SQLALCHEMY_DATABASE_URI'] = get_database_url()
	app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
	init_app_db(app)
	
	with app.app_context():
		fields_cnt = db.session.query(Field).count()
		crops_cnt = db.session.query(Crop).count()
		hist_cnt = db.session.query(CropHistory).count()
		print(f"OK: fields={fields_cnt}, crops={crops_cnt}, crop_history={hist_cnt}")


if __name__ == "__main__":
	import sys
	if len(sys.argv) > 1 and sys.argv[1] == 'check':
		check_database()
	else:
		init_database()

