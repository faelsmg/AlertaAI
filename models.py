from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, current_user
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(128), nullable=False)
    telefone = db.Column(db.String(20), nullable=True)
    tipo = db.Column(db.String(20), default='cidadao')
    grupo_id = db.Column(db.Integer, db.ForeignKey('grupo_agente.id'))
    denuncias = db.relationship('Denuncia', backref='usuario', lazy=True)
    ativo = db.Column(db.Boolean, default=True)

    def set_password(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_password(self, senha):
        return check_password_hash(self.senha_hash, senha)

class GrupoAgente(db.Model):
    __tablename__ = 'grupo_agente'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    agentes = db.relationship('User', backref='grupo', lazy=True)

class Denuncia(db.Model):
    __tablename__ = 'denuncia'
    id = db.Column(db.Integer, primary_key=True)
    imagem = db.Column(db.String(200), nullable=False)
    comentario = db.Column(db.Text)
    latitude = db.Column(db.String(50))
    longitude = db.Column(db.String(50))
    resultado_ia = db.Column(db.Boolean)
    status = db.Column(db.String(50), default='Em análise')  # ou 'Vistoriado', 'Resolvido'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    grupo_id = db.Column(db.Integer, db.ForeignKey('grupo_agente.id'), nullable=True)
    endereco = db.Column(db.String(255))  
    data = db.Column(db.DateTime, default=datetime.utcnow)  
    data_encerramento = db.Column(db.DateTime, nullable=True)
    bairro = db.Column(db.String(100), nullable=True)


class Armadilha(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    endereco = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)
    data_instalacao = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    grupo_id = db.Column(db.Integer, db.ForeignKey('grupo_agente.id'))
    grupo = db.relationship('GrupoAgente', backref='armadilhas')
    descricao = db.Column(db.String(200))  

    
class RotaGrupo(db.Model):
    __tablename__ = 'rota_grupo'
    id = db.Column(db.Integer, primary_key=True)
    grupo_id = db.Column(db.Integer, db.ForeignKey('grupo_agente.id'), nullable=False)
    rua = db.Column(db.String(100), nullable=False)
    cep = db.Column(db.String(20), nullable=False)
    numero_inicio = db.Column(db.Integer, nullable=True)
    numero_fim = db.Column(db.Integer, nullable=True)

    grupo = db.relationship('GrupoAgente', backref='rotas_grupo')

class Agente(db.Model):
    __tablename__ = 'agente'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    ativo = db.Column(db.Boolean, default=True)
    
class PushMessage(db.Model):
    __tablename__ = 'push_message'
    id = db.Column(db.Integer, primary_key=True)
    mensagem = db.Column(db.Text, nullable=False)
    data_agendada = db.Column(db.DateTime, nullable=True)
    bairro = db.Column(db.String(100), nullable=True)
    cep = db.Column(db.String(20), nullable=True)
    grupo_id = db.Column(db.Integer, db.ForeignKey('grupo_agente.id'), nullable=True)
    status = db.Column(db.String(20), default='Agendado')
    data_envio = db.Column(db.DateTime, default=datetime.utcnow)
    