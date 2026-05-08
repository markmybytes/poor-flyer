import uuid
from datetime import date, datetime

from flask import Blueprint, jsonify, redirect, request, url_for

from src.database import PriceSnapshot, SessionLocal, TrackingEntry
from src.scraper import scrape_prices

api_bp = Blueprint("api", __name__)


@api_bp.route("/entries", methods=["POST"])
def create_entry():
    db = SessionLocal()
    try:
        data = request.get_json(silent=True) or request.form.to_dict()

        deadline_str = data.get("deadline")
        deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date() if deadline_str else None

        entry = TrackingEntry(
            id=str(uuid.uuid4()),
            name=data.get("name") or None,
            origin=data.get("origin").upper(),
            destination=data.get("destination").upper(),
            flight_date=datetime.strptime(data.get("flight_date"), "%Y-%m-%d").date(),
            adult_count=int(data.get("adult_count", 1)),
            child_count=int(data.get("child_count", 0)),
            infant_count=int(data.get("infant_count", 0)),
            deadline=deadline,
            is_active=True,
        )

        db.add(entry)
        db.commit()
        return redirect(url_for("pages.list_entries"))
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        db.close()


@api_bp.route("/entries/<entry_id>/toggle", methods=["POST"])
def toggle_entry(entry_id):
    db = SessionLocal()
    try:
        entry = db.query(TrackingEntry).filter(TrackingEntry.id == entry_id).first()
        if not entry:
            return jsonify({"error": "Entry not found"}), 404

        entry.is_active = not entry.is_active
        db.commit()
        return redirect(url_for("pages.list_entries"))
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        db.close()


@api_bp.route("/entries/<entry_id>/delete", methods=["POST"])
def delete_entry(entry_id):
    db = SessionLocal()
    try:
        entry = db.query(TrackingEntry).filter(TrackingEntry.id == entry_id).first()
        if not entry:
            return jsonify({"error": "Entry not found"}), 404

        db.delete(entry)
        db.commit()
        return redirect(url_for("pages.list_entries"))
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        db.close()


@api_bp.route("/entries/<entry_id>/scrape", methods=["POST"])
def scrape_now(entry_id):
    db = SessionLocal()
    try:
        entry = db.query(TrackingEntry).filter(TrackingEntry.id == entry_id).first()
        if not entry:
            return jsonify({"error": "Entry not found"}), 404

        if entry.flight_date < date.today():
            return jsonify({"error": "Cannot scrape: flight date has passed"}), 400

        result = scrape_prices(
            origin=entry.origin,
            destination=entry.destination,
            flight_date=entry.flight_date,
            adult_count=entry.adult_count,
            child_count=entry.child_count,
            infant_count=entry.infant_count,
        )

        snapshot = PriceSnapshot(
            id=str(uuid.uuid4()),
            entry_id=entry_id,
            scraped_at=datetime.utcnow(),
            fare=result.fare,
            flight_number=result.flight_number,
            departure_time=result.departure_time,
            arrival_time=result.arrival_time,
            scrape_status="success" if result.success else "error",
            error_message=result.error_message,
        )

        db.add(snapshot)
        db.commit()
        return redirect(url_for("pages.detail_entry", entry_id=entry_id))
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        db.close()
