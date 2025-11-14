from datetime import datetime
from config import db


class Field(db.Model):
	__tablename__ = 'fields'
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(100), nullable=False)
	geometry = db.Column(db.Text, nullable=False)
	area = db.Column(db.Float)
	created_at = db.Column(db.DateTime, default=datetime.utcnow)

	crop_history = db.relationship('CropHistory', backref='field', lazy=True, cascade='all, delete-orphan')

	def to_dict(self):
		return {
			'id': self.id,
			'name': self.name,
			'geometry': self.geometry,
			'area': self.area,
			'created_at': self.created_at.isoformat() if self.created_at else None
		}


class Crop(db.Model):
	__tablename__ = 'crops'
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(100), nullable=False, unique=True)
	category = db.Column(db.String(50))
	seed_price_per_kg = db.Column(db.Float, default=0)
	fertilizer_cost_per_ha = db.Column(db.Float, default=0)
	yield_per_ha = db.Column(db.Float, default=0)
	market_price_per_ton = db.Column(db.Float, default=0)
	other_costs_per_ha = db.Column(db.Float, default=0)

	def to_dict(self):
		return {
			'id': self.id,
			'name': self.name,
			'category': self.category,
			'seed_price_per_kg': self.seed_price_per_kg,
			'fertilizer_cost_per_ha': self.fertilizer_cost_per_ha,
			'yield_per_ha': self.yield_per_ha,
			'market_price_per_ton': self.market_price_per_ton,
			'other_costs_per_ha': self.other_costs_per_ha
		}


class CropHistory(db.Model):
	__tablename__ = 'crop_history'
	id = db.Column(db.Integer, primary_key=True)
	field_id = db.Column(db.Integer, db.ForeignKey('fields.id'), nullable=False)
	crop_id = db.Column(db.Integer, db.ForeignKey('crops.id'), nullable=False)
	year = db.Column(db.Integer, nullable=False)
	season = db.Column(db.String(20), default='весна-лето')
	notes = db.Column(db.Text)
	created_at = db.Column(db.DateTime, default=datetime.utcnow)

	crop = db.relationship('Crop', backref='history')

	def to_dict(self):
		return {
			'id': self.id,
			'field_id': self.field_id,
			'field_name': self.field.name if self.field else None,
			'crop_id': self.crop_id,
			'crop_name': self.crop.name if self.crop else None,
			'year': self.year,
			'season': self.season,
			'notes': self.notes,
			'created_at': self.created_at.isoformat() if self.created_at else None
		}


