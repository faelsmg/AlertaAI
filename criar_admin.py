from models import db, User
from app import app

with app.app_context():
    # Verifica se já existe
    if User.query.filter_by(email='admin@alertaai.com').first():
        print("Admin já existe.")
    else:
        admin = User(
            nome='Admin',
            email='admin@alertaai.com',
            tipo='admin'
        )
        admin.set_password('123')  # <- define a senha corretamente
        db.session.add(admin)
        db.session.commit()
        print("Admin criado com sucesso!")
