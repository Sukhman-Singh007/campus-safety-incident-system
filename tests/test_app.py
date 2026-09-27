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
