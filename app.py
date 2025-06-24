from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
import os
from datetime import datetime
from flask_migrate import Migrate
from model.detect_larva import verificar_imagem
import requests

from models import db, User, GrupoAgente, Denuncia, Armadilha, RotaGrupo

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///alertaai.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# ✅ Somente aqui deve estar o Migrate
migrate = Migrate(app, db)

from routes.admin_routes import admin_routes
app.register_blueprint(admin_routes)

from routes.agente_routes import agente_routes
app.register_blueprint(agente_routes)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def obter_latlon_por_endereco(endereco):
    try:
        url = f"https://nominatim.openstreetmap.org/search"
        params = {'q': endereco, 'format': 'json', 'limit': 1}
        headers = {'User-Agent': 'AlertaAiApp/1.0'}
        resposta = requests.get(url, params=params, headers=headers, timeout=10)
        if resposta.status_code == 200:
            data = resposta.json()
            if data and len(data) > 0:
                return data[0].get("lat"), data[0].get("lon")
    except Exception as e:
        print("Erro ao buscar lat/lon:", e)
    return None, None

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route("/admin/rotas")
@login_required
def admin_rotas():
    return "<h1>Página de Rotas (em construção)</h1>"
    
@app.context_processor
def inject_base_template():
    if current_user.is_authenticated:
        if current_user.tipo == 'admin':
            return dict(base_template='base_admin.html')
        elif current_user.tipo == 'agente':
            return dict(base_template='base_agente.html')
    return dict(base_template='base.html')

    
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(senha):
            login_user(user)
            flash('Login realizado com sucesso.', 'success')
            return redirect(url_for('painel'))
        flash('Credenciais inválidas.', 'danger')
    return render_template('login.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        tipo = request.form.get('tipo', 'cidadao')
        if User.query.filter_by(email=email).first():
            flash('E-mail já cadastrado.', 'warning')
        else:
            novo_user = User(nome=nome, email=email, tipo=tipo)
            novo_user.set_password(senha)
            db.session.add(novo_user)
            db.session.commit()
            flash('Cadastro realizado com sucesso.', 'success')
            return redirect(url_for('login'))
    return render_template('cadastro.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

def obter_bairro_por_lat_lng(lat, lng):
    GOOGLE_API_KEY = "AIzaSyClTfCYAfyVJ03aFc2KdxVOH1La3YUw8oM"
    url = f'https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&key={GOOGLE_API_KEY}&language=pt-BR'
    response = requests.get(url)
    data = response.json()

    for result in data.get('results', []):
        for comp in result['address_components']:
            if 'sublocality' in comp['types'] or 'administrative_area_level_2' in comp['types']:
                return comp['long_name']
    return "Bairro não encontrado"

@app.route('/nova_denuncia', methods=['GET', 'POST'])
@login_required
def nova_denuncia():
    if request.method == 'POST':
        foto = request.files['foto']
        endereco = request.form.get('endereco', '')
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        bairro = request.form.get('bairro') or "Desconhecido"  # ✅ Captura do campo oculto

        if foto:
            nome_arquivo = foto.filename
            path_imagem = os.path.join(UPLOAD_FOLDER, nome_arquivo)
            foto.save(path_imagem)

            # Recheca se é necessário buscar o endereço/bairro via API (fallback)
            if not endereco and latitude and longitude:
                try:
                    url = f"https://nominatim.openstreetmap.org/reverse?lat={latitude}&lon={longitude}&format=json&addressdetails=1"
                    headers = {'User-Agent': 'AlertaAiApp/1.0'}
                    resp = requests.get(url, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        endereco = data.get('display_name', 'Endereço não disponível')
                        address = data.get('address', {})
                        bairro = address.get('suburb') or address.get('neighbourhood') or address.get('city') or address.get('town') or "Desconhecido"
                except:
                    endereco = 'Endereço não disponível'

            resultado_ia, _ = verificar_imagem(path_imagem)
            resultado_texto = "Detectado" if resultado_ia else "Não detectado"

            nova = Denuncia(
                user_id=current_user.id,
                imagem=nome_arquivo,
                resultado_ia=resultado_ia,
                status="Pendente",
                comentario="",
                latitude=latitude or "",
                longitude=longitude or "",
                endereco=endereco,
                bairro=bairro  # ✅ Garantido que existe
            )
            db.session.add(nova)
            db.session.commit()
            flash(f'Denúncia registrada: {resultado_texto}', 'success')
            return redirect(url_for('painel'))

    return render_template('nova_denuncia.html')

@app.route('/painel')
@login_required
def painel():
    if current_user.tipo == "admin":
        denuncias = Denuncia.query.all()
    else:
        denuncias = Denuncia.query.filter_by(user_id=current_user.id).all()
    return render_template('painel.html', denuncias=denuncias)

@app.route('/mapa')
@login_required
def mapa():
    denuncias = Denuncia.query.all()
    armadilhas = Armadilha.query.all()
    rotas = RotaGrupo.query.all()

    # Transforma os objetos em dicionários serializáveis
    denuncias_dict = [{
        'latitude': float(d.latitude),
        'longitude': float(d.longitude),
        'status': d.status
    } for d in denuncias if d.latitude and d.longitude]

    armadilhas_dict = [{
        'latitude': float(a.latitude),
        'longitude': float(a.longitude)
    } for a in armadilhas if a.latitude and a.longitude]

    rotas_por_grupo = {}
    for rota in rotas:
        grupo_id = str(rota.grupo_id or "0")
        if grupo_id not in rotas_por_grupo:
            rotas_por_grupo[grupo_id] = []
        rotas_por_grupo[grupo_id].append({
            'rua': rota.rua,
            'numero_inicio': rota.numero_inicio,
            'numero_fim': rota.numero_fim,
            'cep': rota.cep
        })

    template_base = 'base_admin.html' if current_user.tipo == 'admin' else 'base.html'
    return render_template(
        'mapa.html',
        base_template=template_base,
        denuncias=denuncias_dict,
        armadilhas=armadilhas_dict,
        rotas_por_grupo=rotas_por_grupo
    )
    
@app.context_processor
def inject_user():
    return dict(current_user=current_user)

if __name__ == '__main__':
    app.run(debug=True)

