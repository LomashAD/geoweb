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


def get_secret_key() -> str:
	return os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')


def init_app_db(app):
	db.init_app(app)