import os
import tempfile
import app as application


def test_login_page():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    old_db = application.DATABASE
    application.DATABASE = path
    application.app.config.update(TESTING=True)
    application.init_db()
    client = application.app.test_client()
    response = client.get('/login')
    assert response.status_code == 200
    assert b'Authorized Login' in response.data
    application.DATABASE = old_db
    os.unlink(path)


def _new_incident_form():
    return {
        'category': 'Suspicious Activity',
        'location': 'Library',
        'incident_date': '2026-09-27T10:00',
        'description': 'Test incident.',
        'priority': 'Low',
        'status': 'Open',
    }


def test_incident_number_not_reused_after_delete():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    old_db = application.DATABASE
    application.DATABASE = path
    application.app.config.update(TESTING=True)
    try:
        application.init_db()
        client = application.app.test_client()
        client.post('/login', data={'username': 'admin', 'password': 'CampusSafe123!'})

        created = client.post('/incidents/new', data=_new_incident_form(), follow_redirects=True)
        assert b'INC-0004 created successfully.' in created.data

        # The new incident is the seeded rows (ids 1-3) plus this one (id 4).
        client.post('/incidents/4/delete', follow_redirects=True)

        recreated = client.post('/incidents/new', data=_new_incident_form(), follow_redirects=True)
        assert b'INC-0005 created successfully.' in recreated.data
        assert b'INC-0004 created successfully.' not in recreated.data
    finally:
        application.DATABASE = old_db
        os.unlink(path)
