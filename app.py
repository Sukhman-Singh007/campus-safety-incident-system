from flask import Flask, render_template
import sqlite3

app = Flask(__name__)


def get_db_connection():
    connection = sqlite3.connect("incidents.db")
    connection.row_factory = sqlite3.Row
    return connection


@app.route("/")
def home():
    connection = get_db_connection()

    incidents = connection.execute(
        "SELECT * FROM incidents ORDER BY id DESC"
    ).fetchall()

    total_incidents = connection.execute(
        "SELECT COUNT(*) FROM incidents"
    ).fetchone()[0]

    open_incidents = connection.execute(
        "SELECT COUNT(*) FROM incidents WHERE status = 'Open'"
    ).fetchone()[0]

    in_progress_incidents = connection.execute(
        "SELECT COUNT(*) FROM incidents WHERE status = 'In Progress'"
    ).fetchone()[0]

    resolved_incidents = connection.execute(
        "SELECT COUNT(*) FROM incidents WHERE status = 'Resolved'"
    ).fetchone()[0]

    connection.close()

    return render_template(
        "index.html",
        incidents=incidents,
        total_incidents=total_incidents,
        open_incidents=open_incidents,
        in_progress_incidents=in_progress_incidents,
        resolved_incidents=resolved_incidents
    )


if __name__ == "__main__":
    app.run(debug=True)