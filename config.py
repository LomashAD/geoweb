import os
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

db = SQLAlchemy()


def get_database_url() -> str:
	# SQLite URL в файле проекта
	basedir = os.path.abspath(os.path.dirname(__file__))
	sqlite_path = os.path.join(basedir, 'geoweb.db')
	return f"sqlite:///{sqlite_path}"


def get_users_database_url() -> str:
	# Отдельная база данных для пользователей
	basedir = os.path.abspath(os.path.dirname(__file__))
	sqlite_path = os.path.join(basedir, 'users.db')
	return f"sqlite:///{sqlite_path}"


def get_secret_key() -> str:
	return os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')


def init_app_db(app):
	# Основная база данных
	app.config['SQLALCHEMY_DATABASE_URI'] = get_database_url()
	# Настройка отдельной базы данных для пользователей через binds
	app.config['SQLALCHEMY_BINDS'] = {
		'users': get_users_database_url()
	}
	db.init_app(app)