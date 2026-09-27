import os
import sqlite3
from functools import wraps
from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-change-this-secret')
DATABASE = os.path.join(app.root_path, 'incidents.db')


def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view


def init_db():
    connection = get_db_connection()
    with open(os.path.join(app.root_path, 'schema.sql'), encoding='utf-8') as file:
        connection.executescript(file.read())
    user = connection.execute('SELECT id FROM users WHERE username = ?', ('admin',)).fetchone()
    if user is None:
        connection.execute(
            'INSERT INTO users (username, password_hash) VALUES (?, ?)',
            ('admin', generate_password_hash('CampusSafe123!')),
        )
    count = connection.execute('SELECT COUNT(*) FROM incidents').fetchone()[0]
    if count == 0:
        samples = [
            ('INC-0001', 'Suspicious Activity', 'North Campus Garage', '2026-09-26T20:30', 'Unattended backpack reported near the east entrance.', 'Medium', 'Open'),
            ('INC-0002', 'Safety Hazard', 'Science Building', '2026-09-25T14:10', 'Fictional wet-floor hazard reported near a laboratory hallway.', 'Low', 'Resolved'),
            ('INC-0003', 'Property Issue', 'Student Center East', '2026-09-24T18:45', 'Fictional damaged bicycle rack reported outside the entrance.', 'High', 'In Progress'),
        ]
        connection.executemany('''INSERT INTO incidents
            (incident_number, category, location, incident_date, description, priority, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)''', samples)
    connection.commit()
    connection.close()


def next_incident_number(connection):
    row = connection.execute('SELECT MAX(id) FROM incidents').fetchone()
    next_id = (row[0] or 0) + 1
    return f'INC-{next_id:04d}'


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        connection = get_db_connection()
        user = connection.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        connection.close()
        if user and check_password_hash(user['password_hash'], password):
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('home'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
@login_required
def home():
    connection = get_db_connection()
    incidents = connection.execute('SELECT * FROM incidents ORDER BY incident_date DESC LIMIT 5').fetchall()
    stats = {
        'total': connection.execute('SELECT COUNT(*) FROM incidents').fetchone()[0],
        'open': connection.execute("SELECT COUNT(*) FROM incidents WHERE status = 'Open'").fetchone()[0],
        'progress': connection.execute("SELECT COUNT(*) FROM incidents WHERE status = 'In Progress'").fetchone()[0],
        'resolved': connection.execute("SELECT COUNT(*) FROM incidents WHERE status = 'Resolved'").fetchone()[0],
    }
    connection.close()
    return render_template('index.html', incidents=incidents, stats=stats)


@app.route('/incidents')
@login_required
def incidents():
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    priority = request.args.get('priority', '').strip()
    status = request.args.get('status', '').strip()
    query = 'SELECT * FROM incidents WHERE 1=1'
    params = []
    if search:
        query += ' AND (incident_number LIKE ? OR location LIKE ? OR description LIKE ?)'
        term = f'%{search}%'
        params.extend([term, term, term])
    if category:
        query += ' AND category = ?'
        params.append(category)
    if priority:
        query += ' AND priority = ?'
        params.append(priority)
    if status:
        query += ' AND status = ?'
        params.append(status)
    query += ' ORDER BY incident_date DESC'
    connection = get_db_connection()
    rows = connection.execute(query, params).fetchall()
    connection.close()
    return render_template('incidents.html', incidents=rows, search=search, category=category, priority=priority, status=status)


@app.route('/incidents/new', methods=['GET', 'POST'])
@login_required
def create_incident():
    if request.method == 'POST':
        category = request.form.get('category', '').strip()
        location = request.form.get('location', '').strip()
        incident_date = request.form.get('incident_date', '').strip()
        description = request.form.get('description', '').strip()
        priority = request.form.get('priority', '').strip()
        status = request.form.get('status', 'Open').strip()
        allowed_priority = {'Low', 'Medium', 'High'}
        allowed_status = {'Open', 'In Progress', 'Resolved'}
        if not all([category, location, incident_date, description, priority, status]):
            flash('All fields are required.', 'error')
        elif priority not in allowed_priority or status not in allowed_status:
            flash('Invalid priority or status.', 'error')
        elif len(description) > 1000:
            flash('Description must be 1000 characters or fewer.', 'error')
        else:
            connection = get_db_connection()
            number = next_incident_number(connection)
            connection.execute('''INSERT INTO incidents
                (incident_number, category, location, incident_date, description, priority, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (number, category, location, incident_date, description, priority, status))
            connection.commit()
            connection.close()
            flash(f'{number} created successfully.', 'success')
            return redirect(url_for('incidents'))
    return render_template('incident_form.html', incident=None)


@app.route('/incidents/<int:incident_id>')
@login_required
def incident_detail(incident_id):
    connection = get_db_connection()
    incident = connection.execute('SELECT * FROM incidents WHERE id = ?', (incident_id,)).fetchone()
    connection.close()
    if incident is None:
        return ('Incident not found', 404)
    return render_template('incident_detail.html', incident=incident)


@app.route('/incidents/<int:incident_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_incident(incident_id):
    connection = get_db_connection()
    incident = connection.execute('SELECT * FROM incidents WHERE id = ?', (incident_id,)).fetchone()
    if incident is None:
        connection.close()
        return ('Incident not found', 404)
    if request.method == 'POST':
        values = [request.form.get(name, '').strip() for name in ['category', 'location', 'incident_date', 'description', 'priority', 'status']]
        if not all(values):
            flash('All fields are required.', 'error')
        elif values[4] not in {'Low', 'Medium', 'High'} or values[5] not in {'Open', 'In Progress', 'Resolved'}:
            flash('Invalid priority or status.', 'error')
        else:
            connection.execute('''UPDATE incidents SET category=?, location=?, incident_date=?, description=?, priority=?, status=? WHERE id=?''', (*values, incident_id))
            connection.commit()
            connection.close()
            flash('Incident updated successfully.', 'success')
            return redirect(url_for('incident_detail', incident_id=incident_id))
    connection.close()
    return render_template('incident_form.html', incident=incident)


@app.route('/incidents/<int:incident_id>/delete', methods=['POST'])
@login_required
def delete_incident(incident_id):
    connection = get_db_connection()
    connection.execute('DELETE FROM incidents WHERE id = ?', (incident_id,))
    connection.commit()
    connection.close()
    flash('Incident deleted.', 'success')
    return redirect(url_for('incidents'))


if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        init_db()
    app.run(debug=True)
