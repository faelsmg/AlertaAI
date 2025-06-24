from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import Denuncia, Armadilha, GrupoAgente, db
from datetime import datetime

agente_routes = Blueprint('agente_routes', __name__)

@agente_routes.route('/agente/painel')
@login_required
def painel_agente():
    if current_user.tipo != 'agente':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('painel'))

    grupo_id = current_user.grupo_id

    total_chamados = Denuncia.query.filter_by(grupo_id=grupo_id).count()
    pendentes = Denuncia.query.filter_by(grupo_id=grupo_id, status='Pendente').count()
    armadilhas = Armadilha.query.filter_by(grupo_id=grupo_id).count()

    return render_template(
        'agentes/painel.html',
        total_chamados=total_chamados,
        pendentes=pendentes,
        armadilhas=armadilhas
    )

@agente_routes.route('/agente/chamados')
@login_required
def chamados_agente():
    if current_user.tipo != 'agente':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('painel'))

    grupo_id = current_user.grupo_id
    chamados = Denuncia.query.filter_by(grupo_id=grupo_id).order_by(Denuncia.data.desc()).all()

    return render_template('agentes/chamados.html', chamados=chamados)
    
@agente_routes.route('/agente/chamados/<int:id>')
@login_required
def detalhar_chamado_agente(id):
    if current_user.tipo != 'agente':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('painel'))

    chamado = Denuncia.query.get_or_404(id)

    # Garante que o agente só veja chamados do seu grupo
    if chamado.grupo_id != current_user.grupo_id:
        flash('Chamado não pertence ao seu grupo.', 'danger')
        return redirect(url_for('agente_routes.chamados_agente'))

    return render_template('agentes/chamado_detalhe.html', chamado=chamado)
    
@agente_routes.route('/agente/chamados/<int:id>/encerrar', methods=['POST'])
@login_required
def encerrar_chamado_agente(id):
    if current_user.tipo != 'agente':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('painel'))

    chamado = Denuncia.query.get_or_404(id)

    if chamado.grupo_id != current_user.grupo_id:
        flash('Chamado não pertence ao seu grupo.', 'danger')
        return redirect(url_for('agente_routes.chamados_agente'))

    comentario = request.form.get('comentario')
    chamado.comentario = comentario
    chamado.status = 'Encerrado'
    chamado.data_encerramento = datetime.utcnow()
    db.session.commit()
    flash('Chamado encerrado com sucesso!', 'success')
    return redirect(url_for('agente_routes.chamados_agente'))
    
@agente_routes.route('/agente/mapa')
@login_required
def agente_mapa():
    denuncias = [{
        "id": d.id,
        "latitude": float(d.latitude) if d.latitude else None,
        "longitude": float(d.longitude) if d.longitude else None,
        "status": d.status
    } for d in Denuncia.query.filter_by(grupo_id=current_user.grupo_id).all()]

    armadilhas = [{
        "id": a.id,
        "latitude": float(a.latitude),
        "longitude": float(a.longitude)
    } for a in Armadilha.query.filter_by(grupo_id=current_user.grupo_id).all()]

    grupo = GrupoAgente.query.get(current_user.grupo_id)
    rotas_por_grupo = {}

    if grupo:
        rotas_por_grupo[str(grupo.id)] = [{
            "rua": rota.rua,
            "cep": rota.cep,
            "numero_inicio": rota.numero_inicio,
            "numero_fim": rota.numero_fim
        } for rota in grupo.rotas_grupo]

    return render_template(
        'agentes/mapa.html',
        base_template='base_agente.html',
        denuncias=denuncias,
        armadilhas=armadilhas,
        rotas_por_grupo=rotas_por_grupo
    )

    
@agente_routes.route('/agente/denuncias')
@login_required
def agente_denuncias():
    if current_user.tipo != 'agente':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('painel'))

    denuncias = Denuncia.query.filter_by(grupo_id=current_user.grupo_id).all()
    return render_template('agentes/denuncias.html', denuncias=denuncias)
    
@agente_routes.route('/agente/denuncias/<int:id>')
@login_required
def ver_denuncia(id):
    denuncia = Denuncia.query.get_or_404(id)
    return render_template('agentes/ver_denuncia.html', denuncia=denuncia)
    
@agente_routes.route('/agente/denuncias/<int:id>/encerrar', methods=['POST'])
@login_required
def encerrar_denuncia(id):
    denuncia = Denuncia.query.get_or_404(id)
    if denuncia.status != 'Encerrado':
        comentario = request.form.get('comentario', '')
        denuncia.status = 'Encerrado'
        denuncia.comentario = comentario
        denuncia.data_encerramento = datetime.utcnow()
        db.session.commit()
        flash("Denúncia encerrada com sucesso!", "success")
    return redirect(url_for('agente_routes.ver_denuncia', id=id))
    
@agente_routes.route('/agente/armadilhas')
@login_required
def armadilhas_agente():
    if current_user.tipo != 'agente':
        flash("Acesso negado", "danger")
        return redirect(url_for('painel'))
    
    armadilhas = Armadilha.query.filter_by(grupo_id=current_user.grupo_id).all()
    return render_template("agentes/armadilhas.html", armadilhas=armadilhas)

@agente_routes.route('/agente/armadilha/nova', methods=['POST'])
@login_required
def criar_armadilha_agente():
    from datetime import datetime
    latitude = request.form.get('latitude')
    longitude = request.form.get('longitude')
    endereco = request.form.get('endereco')
    tipo = request.form.get('tipo')

    nova = Armadilha(
        latitude=latitude,
        longitude=longitude,
        endereco=endereco,
        tipo=tipo,
        grupo_id=current_user.grupo_id,
        data_instalacao=datetime.utcnow()
    )
    db.session.add(nova)
    db.session.commit()
    flash('Armadilha criada com sucesso.')
    return redirect(url_for('agente_routes.armadilhas_agente'))

@agente_routes.route('/agente/perfil', methods=['GET', 'POST'])
@login_required
def perfil_agente():
    if current_user.tipo != 'agente':
        flash("Acesso negado", "danger")
        return redirect(url_for('painel'))

    if request.method == 'POST':
        current_user.nome = request.form.get('nome')
        current_user.telefone = request.form.get('telefone')
        db.session.commit()
        flash("Perfil atualizado com sucesso!", "success")
        return redirect(url_for('agente_routes.perfil_agente'))

    return render_template('agentes/perfil.html')
    
