import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app, db
from app.models import Admin

app = create_app()
with app.app_context():
    a = Admin.query.filter_by(username='admin').first()
    a.set_password('password')
    db.session.commit()
    print('admin password set')