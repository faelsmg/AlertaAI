from flask import Blueprint, request, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, User, GrupoAgente, RotaGrupo, Denuncia, Armadilha, Agente, PushMessage
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

admin_routes = Blueprint('admin_routes', __name__)

# ------------------ Agentes ------------------

@admin_routes.route('/admin/agentes')
@login_required
def admin_agentes():
    if current_user.tipo != 'admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('painel'))

    termo = request.args.get('search', '')
    agentes = User.query.filter(
        User.tipo == 'agente',
        User.nome.ilike(f'%{termo}%')
    ).all()
    grupos = GrupoAgente.query.all()
    return render_template('admin/agentes.html', agentes=agentes, grupos=grupos, search=termo)

@admin_routes.route("/admin/agentes/criar", methods=["POST"])
@login_required
def criar_agente():
    nome = request.form['nome']
    email = request.form['email']
    senha = request.form['senha']
    grupo_id = request.form.get('grupo_id') or None
    if User.query.filter_by(email=email).first():
        flash("Email já cadastrado", "warning")
    else:
        novo = User(
            nome=nome,
            email=email,
            tipo='agente',
            grupo_id=grupo_id
        )
        novo.set_password(senha)
        db.session.add(novo)
        db.session.commit()
        flash("Agente criado com sucesso", "success")
    return redirect(url_for('admin_routes.admin_agentes'))

@admin_routes.route('/admin/grupos/editar/<int:id>', methods=['POST'])
@login_required
def editar_grupo(id):
    if current_user.tipo != 'admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('painel'))

    grupo = GrupoAgente.query.get(id)
    if grupo:
        novo_nome = request.form['novo_nome']
        grupo.nome = novo_nome
        db.session.commit()
        flash("Grupo atualizado com sucesso", "success")
    else:
        flash("Grupo não encontrado", "warning")

    return redirect(url_for('admin_routes.admin_agentes_grupos'))

@admin_routes.route("/admin/agentes/deletar/<int:id>", methods=["POST"])
@login_required
def deletar_agente(id):
    agente = User.query.get(id)
    if agente:
        db.session.delete(agente)
        db.session.commit()
        flash("Agente excluído", "info")
    return redirect(url_for('admin_routes.admin_agentes'))


# ------------------ Grupos ------------------

@admin_routes.route('/admin/agentes-grupos', methods=['GET'])
@login_required
def admin_agentes_grupos():
    if current_user.tipo != 'admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('painel'))

    termo = request.args.get('search', '')
    grupos = GrupoAgente.query.filter(GrupoAgente.nome.ilike(f'%{termo}%')).all()
    return render_template('admin/agentes_grupos.html', grupos=grupos, search=termo)


@admin_routes.route("/admin/grupos/criar", methods=["POST"])
@login_required
def criar_grupo():
    nome = request.form['nome_grupo']
    if GrupoAgente.query.filter_by(nome=nome).first():
        flash("Grupo já existe", "warning")
    else:
        grupo = GrupoAgente(nome=nome)
        db.session.add(grupo)
        db.session.commit()
        flash("Grupo criado com sucesso", "success")
    return redirect(url_for('admin_routes.admin_agentes_grupos'))

@admin_routes.route('/admin/grupos/deletar/<int:id>', methods=["POST"])
@login_required
def deletar_grupo(id):
    grupo = GrupoAgente.query.get(id)
    if grupo:
        db.session.delete(grupo)
        db.session.commit()
        flash("Grupo excluído com sucesso", "success")
    return redirect(url_for('admin_routes.admin_agentes_grupos'))

# ------------------ Rotas ------------------
@admin_routes.route('/admin/rotas')
@login_required
def admin_rotas():
    if current_user.tipo != 'admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('painel'))

    grupos = GrupoAgente.query.all()
    rotas = RotaGrupo.query.all()

    # Organiza rotas por grupo
    rotas_por_grupo = {}
    for rota in rotas:
        grupo_id = rota.grupo_id
        if grupo_id not in rotas_por_grupo:
            rotas_por_grupo[grupo_id] = []
        rotas_por_grupo[grupo_id].append({
            "rua": rota.rua,
            "cep": rota.cep,
            "numero_inicio": rota.numero_inicio,
            "numero_fim": rota.numero_fim
        })

    return render_template('admin/rotas.html', grupos=grupos, rotas_por_grupo=rotas_por_grupo)
    

@admin_routes.route("/admin/rotas/criar", methods=["POST"])
@login_required
def criar_rota():
    if current_user.tipo != 'admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('painel'))

    grupo_id = request.form['grupo_id']
    rua = request.form['rua']
    cep = request.form['cep']
    numero_inicio = request.form.get('numero_inicio') or None
    numero_fim = request.form.get('numero_fim') or None

    nova_rota = RotaGrupo(
        grupo_id=grupo_id,
        rua=rua,
        cep=cep,
        numero_inicio=int(numero_inicio) if numero_inicio else None,
        numero_fim=int(numero_fim) if numero_fim else None
    )
    db.session.add(nova_rota)
    db.session.commit()
    flash("Rota criada com sucesso", "success")
    return redirect(url_for('admin_routes.admin_rotas'))

@admin_routes.route("/api/endereco-por-cep/<cep>")
def endereco_por_cep(cep):
    import requests
    try:
        url = f"https://viacep.com.br/ws/{cep}/json/"
        resp = requests.get(url)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "rua": data.get("logradouro"),
                "bairro": data.get("bairro"),
                "cidade": data.get("localidade"),
                "estado": data.get("uf")
            }
    except Exception as e:
        print("Erro ao consultar CEP:", e)
    return {}, 400


# ------------------ Outras páginas ------------------

@admin_routes.route('/admin/mapa')
@login_required
def admin_mapa():
    if current_user.tipo != 'admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('painel'))

    denuncias = [{
        "id": d.id,
        "resultado": d.resultado_ia,
        "status": d.status,
        "data": d.data.strftime("%d/%m/%Y") if d.data else "",
        "endereco": d.endereco,
        "latitude": d.latitude,
        "longitude": d.longitude
    } for d in Denuncia.query.all()]

    armadilhas = [{
        "id": a.id,
        "descricao": a.descricao,
        "latitude": a.latitude,
        "longitude": a.longitude
    } for a in Armadilha.query.all()]

    grupos = GrupoAgente.query.all()
    rotas_por_grupo = {}
    for grupo in grupos:
        rotas_por_grupo[grupo.id] = [{
            "rua": rota.rua,
            "cep": rota.cep,
            "numero_inicio": rota.numero_inicio,
            "numero_fim": rota.numero_fim
        } for rota in grupo.rotas_grupo]

    base_template = (
        "base_admin.html" if current_user.tipo == "admin"
        else "base_agente.html" if current_user.tipo == "agente"
        else "base.html"
    )

    return render_template(
        'mapa.html',
        base_template=base_template,
        denuncias=denuncias,
        armadilhas=armadilhas,
        rotas_por_grupo=rotas_por_grupo
    )

@admin_routes.route('/admin/dashboard')
@login_required
def admin_dashboard():
    hoje = datetime.utcnow()

    # Total de denúncias
    total_denuncias = Denuncia.query.count()

    # Denúncias por bairro
    denuncias_por_bairro = db.session.query(
        Denuncia.bairro, db.func.count(Denuncia.id)
    ).group_by(Denuncia.bairro).all()

    agentes_em_campo = 5

    bairros_labels = []
    bairros_counts = []
    for bairro, count in denuncias_por_bairro:
        bairros_labels.append(bairro or "Desconhecido")
        bairros_counts.append(count)

    # Armadilhas e vencidas
    total_armadilhas = Armadilha.query.count()
    vencidas = 0
    for a in Armadilha.query.all():
        if a.data_instalacao and (hoje - a.data_instalacao).days > 5:
            vencidas += 1

    # SLA médio (tempo entre data e data_encerramento)
    sla_query = db.session.query(
        (Denuncia.data_encerramento - Denuncia.data)
    ).filter(Denuncia.data_encerramento != None).all()

    sla_medio = round(
        sum([(d[0].days if d[0] else 0) for d in sla_query]) / len(sla_query), 2
    ) if sla_query else 0

    # Agentes ativos
    agentes_ativos = User.query.filter_by(tipo='agente', ativo=True).count()

    # Chamados encerrados no mês atual
    encerrados_mes = Denuncia.query.filter(
        db.extract('month', Denuncia.data_encerramento) == hoje.month,
        db.extract('year', Denuncia.data_encerramento) == hoje.year
    ).count()

    # Top 5 bairros com mais focos detectados
    top_bairros = db.session.query(
        Denuncia.bairro, db.func.count(Denuncia.id)
    ).group_by(Denuncia.bairro).order_by(
        db.func.count(Denuncia.id).desc()
    ).limit(5).all()

    top_bairros_focos_labels = []
    top_bairros_focos_counts = []
    for bairro, count in top_bairros:
        top_bairros_focos_labels.append(bairro or "Desconhecido")
        top_bairros_focos_counts.append(count)

    # Últimas 5 denúncias recebidas
    ultimas_denuncias = Denuncia.query.order_by(Denuncia.data.desc()).limit(5).all()

    return render_template(
        'admin/dashboard.html',
        total_denuncias=total_denuncias,
        denuncias_por_bairro=denuncias_por_bairro,
        total_armadilhas=total_armadilhas,
        vencidas=vencidas,
        sla_medio=sla_medio,
        agentes_ativos=agentes_ativos,
        encerrados_mes=encerrados_mes,
        top_bairros=top_bairros,
        ultimas_denuncias=ultimas_denuncias,
        bairros_labels=bairros_labels,
        bairros_counts=bairros_counts,
        top_bairros_focos_labels=top_bairros_focos_labels,
        top_bairros_focos_counts=top_bairros_focos_counts,
        agentes_em_campo=agentes_em_campo
    )

@admin_routes.route('/admin/sla')
@login_required
def admin_sla():
    return render_template('admin/sla.html')

@admin_routes.route('/admin/monitoramento')
@login_required
def admin_monitoramento():
    hoje = datetime.utcnow()
    denuncias = Denuncia.query.filter(Denuncia.status != 'Encerrado').all()
    armadilhas = Armadilha.query.all()
    agentes_em_campo = Agente.query.filter(Agente.ativo == True).all()

    total_denuncias_abertas = len(denuncias)
    total_chamados_resolvidos_hoje = Denuncia.query.filter(
        Denuncia.status == 'Encerrado',
        Denuncia.data_encerramento >= hoje.date()
    ).count()
    total_armadilhas_vencidas = sum(
        1 for a in armadilhas if a.data_instalacao and (hoje - a.data_instalacao).days > 5
    )

    for a in armadilhas:
        a.vencida = a.data_instalacao and (hoje - a.data_instalacao).days > 5

    return render_template(
        'admin/monitoramento.html',
        denuncias=denuncias,
        armadilhas=armadilhas,
        agentes_em_campo=agentes_em_campo,
        total_denuncias_abertas=total_denuncias_abertas,
        total_chamados_resolvidos_hoje=total_chamados_resolvidos_hoje,
        total_armadilhas_vencidas=total_armadilhas_vencidas
    )

@admin_routes.route('/admin/push', methods=['GET', 'POST'])
@login_required
def admin_push():
    if request.method == 'POST':
        mensagem = request.form['mensagem']
        data_agendada = datetime.strptime(request.form['data_agendada'], "%Y-%m-%dT%H:%M")
        bairro = request.form.get('bairro')
        cep = request.form.get('cep')
        grupo_id = request.form.get('grupo_id') or None

        nova_msg = PushMessage(
            mensagem=mensagem,
            data_agendada=data_agendada,
            bairro=bairro if bairro else None,
            cep=cep if cep else None,
            grupo_id=grupo_id if grupo_id else None
        )
        db.session.add(nova_msg)
        db.session.commit()
        flash('Mensagem agendada com sucesso!', 'success')
        return redirect(url_for('admin_routes.admin_push'))

    mensagens = PushMessage.query.order_by(PushMessage.data_agendada.desc()).all()
    grupos = GrupoAgente.query.all()
    return render_template('admin/push.html', mensagens=mensagens, grupos=grupos)


@admin_routes.route('/admin/recomendacoes')
@login_required
def admin_recomendacoes():
    return render_template('admin/recomendacoes.html')

@admin_routes.route('/admin/chamados')
@login_required
def admin_chamados():
    if current_user.tipo != 'admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('painel'))

    filtro_status = request.args.get('status')

    query = Denuncia.query.filter(Denuncia.resultado_ia == True)
    if filtro_status:
        query = query.filter(Denuncia.status == filtro_status)

    chamados = query.order_by(Denuncia.data.desc()).all()
    grupos = GrupoAgente.query.all()

    now = datetime.utcnow()

    return render_template(
        'admin/chamados.html',
        chamados=chamados,
        grupos=grupos,
        filtro_status=filtro_status,
        now=now
    )

@admin_routes.route('/admin/chamados/<int:id>/atribuir-grupo', methods=['POST'])
@login_required
def atribuir_grupo_chamado(id):
    if current_user.tipo != 'admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('painel'))

    denuncia = Denuncia.query.get(id)
    grupo_id = request.form.get('grupo_id')

    if denuncia:
        denuncia.grupo_id = grupo_id if grupo_id else None
        db.session.commit()
        flash("Grupo atribuído com sucesso!", "success")
    else:
        flash("Chamado não encontrado", "warning")

    return redirect(url_for('admin_routes.admin_chamados'))

@admin_routes.route('/admin/chamados/<int:id>')
@login_required
def ver_chamado(id):
    if current_user.tipo != 'admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('painel'))

    chamado = Denuncia.query.get_or_404(id)
    return render_template('admin/chamado_detalhe.html', chamado=chamado)


@admin_routes.route('/admin/armadilhas')
@login_required
def admin_armadilhas():
    armadilhas = Armadilha.query.order_by(Armadilha.data_instalacao.desc()).all()
    grupos = GrupoAgente.query.all()
    hoje = datetime.utcnow()

    for a in armadilhas:
        if a.data_instalacao:
            a.dias_instalado = (hoje - a.data_instalacao).days
        else:
            a.dias_instalado = '-'

    return render_template('admin/armadilhas.html', armadilhas=armadilhas, grupos=grupos, current_time=hoje)



@admin_routes.route('/admin/armadilha/nova', methods=['POST'])
@login_required
def nova_armadilha():
    latitude = request.form.get('latitude')
    longitude = request.form.get('longitude')
    endereco = request.form.get('endereco')
    tipo = request.form.get('tipo')
    grupo_id = request.form.get('grupo_id')

    nova = Armadilha(
        latitude=latitude,
        longitude=longitude,
        endereco=endereco,
        tipo=tipo,
        grupo_id=grupo_id,
        data_instalacao=datetime.utcnow()
    )
    db.session.add(nova)
    db.session.commit()
    flash('Armadilha criada com sucesso.')
    return redirect(url_for('admin_routes.admin_armadilhas'))

@admin_routes.route('/admin/chamados/<int:id>/encerrar', methods=['POST'])
@login_required
def encerrar_chamado(id):
    if current_user.tipo != 'admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('painel'))

    chamado = Denuncia.query.get_or_404(id)
    comentario = request.form.get('comentario')

    chamado.status = 'Encerrado'
    chamado.comentario = comentario
    chamado.data_encerramento = datetime.utcnow()

    db.session.commit()
    flash("Chamado encerrado com sucesso!", "success")
    return redirect(url_for('admin_routes.ver_chamado', id=id))

