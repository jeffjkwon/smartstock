from datetime import datetime
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from pydantic import BaseModel
from typing import Optional, Union
# import os # might not be needed?
import random
import settings

app = Flask(__name__)
CORS(app)


USERNAME = settings.USERNAME
PASSWORD = settings.PASSWORD
DATABASE_NAME = settings.DATABASE_NAME


# app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql://{settings.USERNAME}:{settings.PASSWORD}@localhost/{settings.DATABASE_NAME}"
app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql://{USERNAME}:{PASSWORD}@localhost/{DATABASE_NAME}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

class Equipment(db.Model):
	#__tablename__ = "equipment"


	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String, nullable=False)
	category = db.Column(db.String)
	stats = db.relationship('EquipmentStats', backref='equipment')

	# def to_dict(self):
	# 	return {
	# 		"id": self.id,
	# 		"name": self.name,
	# 		"category": self.category,
	# 		"expiration_date": self.expiration_date,
	# 		"last_updated": self.last_updated.isoformat()
	# 	}

class EquipmentStats(db.Model):

	id = db.Column(db.Integer, primary_key=True)
	equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False)
	quantity = db.Column(db.Numeric, nullable=False)
	quantity_units = db.Column(db.String, nullable=False)
	expiration_date = db.Column(db.DateTime, default=None)
	# CHECK TO MAKESURE DATETIME IS COMPATIBLE
	last_updated = db.Column(db.DateTime, 
						  default=datetime.now())

	# def to_dict(self):
	# 	return {
	# 		"quantity": self.quantity,
	# 		"quantity_units": self.quantity_units,
	# 		"expiration_date": self.expiration_date,
	# 		"last_updated": self.last_updated.isoformat()
	# 	}



## PYDANTIC BASEMODELS
# Equipment categories: trauma, airway, vitals, misc.
class EquipmentBase(BaseModel):
	name: str
	category: str

class EquipmentStatsBase(BaseModel):
	quantity: Union[float, int]
	quantity_units: str
	expiration_date: Optional[datetime] = None
	# CHECK TO MAKESURE DATETIME IS COMPATIBLE
	last_updated: Optional[datetime] = datetime.now()
	

class EquipmentStatsOut(BaseModel):
	id: int
	equipment_id: int

	class Config:
		from_attributes = True

class EquipmentOut(BaseModel):
	id: int
	equipment_stats: list[EquipmentStatsOut]

	class Config:
		from_attributes = True



def mock_equipment():
	raise NotImplementedError

with app.app_context():
	db.create_all()



@app.route("/api/add_equipment", methods=["POST"])
def add_equipment():
	data = request.get_json()
	try:
		validated = EquipmentBase(**data)
	except Exception as e:
		return jsonify({"error": str(e)}), 400

	existing = Equipment.query.filter_by(name=validated.name)

	# If existing equipment
	if existing.first():
		if existing.count() > 1:
			return jsonify({"error": "MULTIPLE EQUIPMENT ENTRIES IN DATABASE. PLEASE FIX!"}), 400

		return jsonify({"error": "EQUIPMENT ALREADY IN DATABASE."}), 400


	new_equip = Equipment(**validated.model_dump())

	db.session.add(new_equip)
	db.session.commit()

	return jsonify({"message": f"Equipment {new_equip.name} added to database with ID: {new_equip.id}!"}), 201


@app.route("/api/add_equipment_stats/<equipment_id>", methods=["POST"])
def add_equipment_stats(equipment_id):
	data = request.get_json()
	try:
		validated = EquipmentStatsBase(**data)
	except Exception as e:
		return jsonify({"error": str(e)}), 400

	existing = Equipment.query.filter_by(id=equipment_id)

	# If existing equipment
	if not existing.first():
		return jsonify({"error": "EQUIPMENT IS NOT IN DATABASE."}), 400
	else:
		if existing.count() > 1:
			return jsonify({"error": "MULTIPLE EQUIPMENT ENTRIES IN DATABASE. PLEASE FIX!"}), 400
		else:
			equipment_name = existing.first().name


	new_stats = EquipmentStats(equipment_id=equipment_id, **validated.model_dump())

	db.session.add(new_stats)
	db.session.commit()

	return jsonify({"message": f"Stats added for equipment: {equipment_name}"}), 201


@app.route("/api/check_equipment_stats/<equipment_id>", methods=["GET"])
def get_equipment_stats(equipment_id):

	equipment = Equipment.query.get(equipment_id)
	if not equipment:
		return jsonify({"error": "EQUIPMENT IS NOT IN DATABASE."}), 404

	records = [
		EquipmentStats.query.filter_by(equipment_id=equipment_id).order_by(EquipmentStats.last_updated.desc()).limit(10).all()
	]
	
	# If existing equipment
	if not records:
		return jsonify({"error": "EQUIPMENT STATS NOT IN DATABASE."}), 400
	
	stats_schema = [EquipmentStatsOut.model_validate(equip) for equip in records]

	response = {
		"equipment_id": equipment.id,
		"equipment_name": equipment.name,
		"recent_stats": [schema.model_dump() for schema in stats_schema]
	}

	return jsonify(response)


@app.cli.command("reset-db")
def reset_db():
	db.drop_all()
	db.create_all()
	print("✅ All databases have been reset.")