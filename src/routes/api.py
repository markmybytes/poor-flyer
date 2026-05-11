import uuid
from datetime import date, datetime, timezone

from flask import Blueprint, jsonify, request

from src.database import Flight, FlightFareSnapshot, SessionLocal
from src.services.scraper import scrape_prices

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/entries", methods=["POST"])
def create_entry():
    db = SessionLocal()
    try:
        data = request.get_json(silent=True) or request.form.to_dict()

        deadline_str = data.get("deadline")
        deadline = (
            datetime.strptime(deadline_str, "%Y-%m-%d").date() if deadline_str else None
        )

        entry = Flight(
            id=str(uuid.uuid4()),
            origin=data.get("origin").upper(),
            destination=data.get("destination").upper(),
            flight_date=datetime.strptime(data.get("flight_date"), "%Y-%m-%d").date(),
            deadline=deadline,
            is_active=True,
        )

        db.add(entry)
        db.commit()
        return jsonify(
            {
                "success": True,
                "message": "Entry created",
                "data": entry,
            }
        )
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "message": str(e)}), 400
    finally:
        db.close()


@api_bp.route("/entries/<entry_id>", methods=["GET"])
def get_entry(entry_id):
    db = SessionLocal()
    try:
        entry = db.query(Flight).filter(Flight.id == entry_id).first()
        if not entry:
            return jsonify({"success": False, "message": "Entry not found"}), 404

        return jsonify(
            {
                "success": True,
                "message": "Entry retrieved",
                "data": entry,
            }
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400
    finally:
        db.close()


@api_bp.route("/entries/<entry_id>", methods=["PATCH"])
def update_entry(entry_id):
    db = SessionLocal()
    try:
        entry = db.query(Flight).filter(Flight.id == entry_id).first()
        if not entry:
            return jsonify({"success": False, "message": "Entry not found"}), 404

        data = request.get_json(silent=True) or request.form.to_dict()

        if "is_active" in data:
            entry.is_active = data["is_active"]

        db.commit()
        return jsonify(
            {
                "success": True,
                "message": "Entry updated",
                "data": entry,
            }
        )
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "message": str(e)}), 400
    finally:
        db.close()


@api_bp.route("/entries/<entry_id>", methods=["DELETE"])
def delete_entry(entry_id):
    db = SessionLocal()
    try:
        entry = db.query(Flight).filter(Flight.id == entry_id).first()
        if not entry:
            return jsonify({"success": False, "message": "Entry not found"}), 404

        db.delete(entry)
        db.commit()
        return jsonify({"success": True, "message": "Entry deleted", "data": None})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "message": str(e)}), 400
    finally:
        db.close()


@api_bp.route("/entries/<entry_id>/scrape", methods=["POST"])
def scrape_now(entry_id):
    db = SessionLocal()
    try:
        entry = db.query(Flight).filter(Flight.id == entry_id).first()
        if not entry:
            return jsonify({"success": False, "message": "Entry not found"}), 404

        if entry.flight_date < date.today():
            return jsonify(
                {"success": False, "message": "Cannot scrape: flight date has passed"}
            ), 400

        results = scrape_prices(
            origin=entry.origin,
            destination=entry.destination,
            flight_date=entry.flight_date,
        )

        for result in results.results:
            snapshot = FlightFareSnapshot(
                flight_id=entry_id,
                created_at=datetime.now(timezone.utc),
                fare=result.fare,
                flight_number=result.flight_number,
                departure_at=result.departure_at,
                arrival_at=result.arrival_at,
                scrape_status="success" if results.success else "error",
                error_message=results.error_message,
            )

            db.add(snapshot)
            db.commit()

        return jsonify(
            {
                "success": True,
                "message": "Scrape completed",
                "data": entry,
            }
        )
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "message": str(e)}), 400
    finally:
        db.close()
