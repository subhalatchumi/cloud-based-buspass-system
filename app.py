from flask import Flask, render_template, request, jsonify
import sqlite3
import uuid

app = Flask(__name__)

DATABASE = "buspass.db"


def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def create_database():
    connection = get_db()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS bus_passes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pass_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            source TEXT NOT NULL,
            destination TEXT NOT NULL,
            pass_type TEXT NOT NULL,
            fare REAL NOT NULL
        )
    """)

    connection.commit()
    connection.close()


# ---------------- FARE CALCULATION ----------------

ROUTES = {
    ("Trichy", "Lalgudi"): 30,
    ("Trichy", "Thanjavur"): 50,
    ("Trichy", "Kumbakonam"): 70,

    ("Lalgudi", "Trichy"): 30,

    ("Thanjavur", "Trichy"): 50,

    ("Kumbakonam", "Trichy"): 70
}


def calculate_fare(source, destination, pass_type):

    base_fare = ROUTES.get(
        (source, destination),
        40
    )

    if pass_type == "Daily":
        return base_fare

    if pass_type == "Weekly":
        return base_fare * 6

    if pass_type == "Monthly":
        return base_fare * 20

    return base_fare


# ---------------- HOME ----------------

@app.route("/")
def home():
    return render_template("index.html")


# ---------------- FARE API ----------------

@app.route("/calculate", methods=["POST"])
def calculate():

    data = request.get_json()

    source = data.get("source")
    destination = data.get("destination")
    pass_type = data.get("pass_type")

    if not source or not destination or not pass_type:
        return jsonify({
            "success": False,
            "message": "Please select all travel details."
        })

    if source == destination:
        return jsonify({
            "success": False,
            "message": "Your destination must be different from your source."
        })

    fare = calculate_fare(
        source,
        destination,
        pass_type
    )

    return jsonify({
        "success": True,
        "fare": fare
    })


# ---------------- BOOK PASS ----------------

@app.route("/book", methods=["POST"])
def book():

    data = request.get_json()

    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()
    source = data.get("source")
    destination = data.get("destination")
    pass_type = data.get("pass_type")

    # Basic validation
    if not name or not phone:
        return jsonify({
            "success": False,
            "message": "Please enter your name and phone number."
        })

    if len(phone) != 10 or not phone.isdigit():
        return jsonify({
            "success": False,
            "message": "Please enter a valid 10-digit phone number."
        })

    if source == destination:
        return jsonify({
            "success": False,
            "message": "Source and destination cannot be the same."
        })

    fare = calculate_fare(
        source,
        destination,
        pass_type
    )

    connection = get_db()

    # Prevent duplicate active booking
    existing = connection.execute("""
        SELECT pass_id
        FROM bus_passes
        WHERE phone = ?
        AND source = ?
        AND destination = ?
    """, (
        phone,
        source,
        destination
    )).fetchone()

    if existing:

        connection.close()

        return jsonify({
            "success": False,
            "message": "You already have a pass for this route."
        })

    # Generate unique pass number
    pass_id = (
        "BUS-" +
        uuid.uuid4().hex[:8].upper()
    )

    connection.execute("""
        INSERT INTO bus_passes
        (
            pass_id,
            name,
            phone,
            source,
            destination,
            pass_type,
            fare
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        pass_id,
        name,
        phone,
        source,
        destination,
        pass_type,
        fare
    ))

    connection.commit()
    connection.close()

    return jsonify({
        "success": True,
        "pass_id": pass_id,
        "name": name,
        "source": source,
        "destination": destination,
        "pass_type": pass_type,
        "fare": fare
    })


# ---------------- RUN ----------------

if __name__ == "__main__":
    create_database()

    app.run(
        debug=True
    )
