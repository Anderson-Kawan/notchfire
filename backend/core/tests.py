import json

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from rest_framework.authtoken.models import Token

from .models import (
    AlertaChecklist,
    Departamento,
    Empresa,
    EmpresaUsuario,
    Equipamento,
    Grupo,
    ItemChecklist,
    Notificacao,
    Periodicidade,
    Predio,
    RespostaChecklist,
    SecaoChecklist,
    Servico,
    ServicoTipoEquipamento,
    TipoEquipamento,
    TipoServico,
    UsuarioPerfil,
)
from .tenant_context import reset_current_empresa, set_current_empresa
from .tenancy import activate_empresa, deactivate_empresa, resolve_empresa_ativa, resolve_empresa_por_host


class PermissoesUsuarioComumTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(username='vistoriador', password='123')
        self.gestor = User.objects.create_user(username='gestor', password='123', is_staff=True)
        self.outro_usuario = User.objects.create_user(username='outro', password='123')

        self.grupo = Grupo.objects.create(nome='Extintores')
        self.periodicidade = Periodicidade.objects.create(nome='Mensal', valor=1, tipo='meses')
        self.tipo_servico = TipoServico.objects.create(nome='Vistoria')
        self.tipo_equipamento = TipoEquipamento.objects.create(
            nome='Extintor CO2',
            grupo=self.grupo,
            periodicidade=self.periodicidade,
        )
        self.equipamento = Equipamento.objects.create(
            nome='Extintor Recepcao',
            numero_serie='EXT-001',
            tipo_equipamento=self.tipo_equipamento,
        )
        self.servico_config = ServicoTipoEquipamento.objects.create(
            tipo_equipamento=self.tipo_equipamento,
            tipo_servico=self.tipo_servico,
            periodicidade=self.periodicidade,
        )
        self.secao = SecaoChecklist.objects.create(
            servico_tipo_equipamento=self.servico_config,
            nome='Geral',
        )
        self.item = ItemChecklist.objects.create(
            secao=self.secao,
            pergunta='Lacre em bom estado?',
        )

    def test_usuario_comum_nao_cria_predio(self):
        self.client.force_login(self.usuario)

        response = self.client.post(
            reverse('api_predios_criar'),
            data=json.dumps({'nome': 'Predio Administrativo'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Predio.objects.filter(nome='Predio Administrativo').exists())

    def test_gestor_cria_predio(self):
        self.client.force_login(self.gestor)

        response = self.client.post(
            reverse('api_predios_criar'),
            data=json.dumps({'nome': 'Predio Administrativo'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Predio.objects.filter(nome='Predio Administrativo').exists())

    def test_usuario_comum_acessa_apenas_areas_permitidas(self):
        self.client.force_login(self.usuario)

        rotas_permitidas = [
            'equipamentos',
            'predios',
            'calendario',
            'servicos',
            'rascunhos',
            'minha_conta',
        ]
        for rota in rotas_permitidas:
            with self.subTest(rota=rota):
                response = self.client.get(reverse(rota))
                self.assertEqual(response.status_code, 200)

        rotas_admin = [
            'usuarios',
            'criar_usuario',
            'departamentos',
            'grupos',
            'tipos_servico',
            'periodicidades',
            'tipos_equipamento',
            'relatorios',
        ]
        for rota in rotas_admin:
            with self.subTest(rota=rota):
                response = self.client.get(reverse(rota))
                self.assertEqual(response.status_code, 302)

    def test_usuario_comum_nao_acessa_apis_administrativas(self):
        self.client.force_login(self.usuario)

        response = self.client.get(
            reverse('api_departamentos_listar'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 403)

        response = self.client.get(
            reverse('api_usuarios_listar'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 403)

    def test_usuario_comum_nao_altera_login_ou_email_na_minha_conta(self):
        self.client.force_login(self.usuario)

        response = self.client.post(
            reverse('minha_conta'),
            {
                'nome_completo': 'Vistoriador Atualizado',
                'username': 'novo-login',
                'email': 'novo-email@example.com',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Usuário simples não pode alterar o nome de usuário usado no login.')
        self.assertContains(response, 'Usuário simples não pode alterar o e-mail de acesso.')
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.username, 'vistoriador')
        self.assertNotEqual(self.usuario.email, 'novo-email@example.com')

    def test_usuario_comum_nao_cria_servico_de_vistoria(self):
        self.client.force_login(self.usuario)

        response = self.client.post(
            reverse('api_servicos_criar'),
            data=json.dumps({
                'equipamento_id': self.equipamento.id,
                'tipo_servico_id': self.tipo_servico.id,
                'status': 'concluido',
                'respostas': [
                    {'item_id': self.item.id, 'opcao': 'atende', 'observacao': ''}
                ],
                'observacoes': 'Vistoria realizada.',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Servico.objects.filter(realizado_por=self.usuario).exists())

    def test_gestor_cria_servico_de_vistoria(self):
        self.client.force_login(self.gestor)

        response = self.client.post(
            reverse('api_servicos_criar'),
            data=json.dumps({
                'equipamento_id': self.equipamento.id,
                'tipo_servico_id': self.tipo_servico.id,
                'status': 'concluido',
                'respostas': [
                    {'item_id': self.item.id, 'opcao': 'atende', 'observacao': ''}
                ],
                'observacoes': 'Vistoria realizada.',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        servico = Servico.objects.get(realizado_por=self.gestor)
        self.assertEqual(servico.status, 'concluido')
        self.assertEqual(RespostaChecklist.objects.filter(servico=servico).count(), 1)

    def test_notifica_admins_e_analistas_quando_item_nao_atende(self):
        admin = User.objects.create_user(username='admin_resp', password='123')
        supervisor = User.objects.create_user(username='supervisor_resp', password='123')
        analista = User.objects.create_user(username='analista_resp', password='123')
        usuario_comum = User.objects.create_user(username='usuario_resp', password='123')
        UsuarioPerfil.objects.create(user=admin, tipo_acesso='admin', status='ativo')
        UsuarioPerfil.objects.create(user=supervisor, tipo_acesso='supervisor', status='ativo')
        UsuarioPerfil.objects.create(user=analista, tipo_acesso='analista', status='ativo')
        UsuarioPerfil.objects.create(user=usuario_comum, tipo_acesso='usuario', status='ativo')
        self.client.force_login(self.gestor)

        response = self.client.post(
            reverse('api_servicos_criar'),
            data=json.dumps({
                'equipamento_id': self.equipamento.id,
                'tipo_servico_id': self.tipo_servico.id,
                'status': 'concluido',
                'respostas': [
                    {
                        'item_id': self.item.id,
                        'opcao': 'nao_atende',
                        'observacao': 'Lacre rompido',
                    }
                ],
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        notificacoes = Notificacao.objects.order_by('destinatario__username')
        self.assertEqual(notificacoes.count(), 3)
        self.assertEqual(
            list(notificacoes.values_list('destinatario__username', flat=True)),
            ['admin_resp', 'analista_resp', 'supervisor_resp'],
        )
        mensagem = notificacoes.first().mensagem
        self.assertIn(self.equipamento.nome, mensagem)
        self.assertIn(self.item.pergunta, mensagem)
        self.assertIn(self.gestor.username, mensagem)
        self.assertIn('Lacre rompido', mensagem)
        self.assertEqual(AlertaChecklist.objects.count(), 1)
        alerta = AlertaChecklist.objects.get()
        self.assertEqual(alerta.equipamento, self.equipamento)
        self.assertEqual(alerta.servico.realizado_por, self.gestor)
        self.assertEqual(alerta.resposta_checklist.item_checklist, self.item)
        self.assertEqual(alerta.status, 'pendente')

        token, _ = Token.objects.get_or_create(user=admin)
        api_response = self.client.get(
            reverse('api-notificacoes'),
            HTTP_AUTHORIZATION=f'Token {token.key}',
        )

        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(api_response.json()['nao_lidas'], 1)
        self.assertEqual(api_response.json()['notificacoes'][0]['equipamento_nome'], self.equipamento.nome)

    def test_mobile_usuario_comum_envia_checklist_e_cria_alerta(self):
        token, _ = Token.objects.get_or_create(user=self.usuario)

        response = self.client.post(
            reverse('api-mobile-servicos-criar'),
            data=json.dumps({
                'equipamento_id': self.equipamento.id,
                'tipo_servico_id': self.tipo_servico.id,
                'status': 'concluido',
                'respostas': [
                    {
                        'item_id': self.item.id,
                        'opcao': 'nao_atende',
                        'observacao': 'Mangueira obstruída',
                    }
                ],
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Token {token.key}',
        )

        self.assertEqual(response.status_code, 200)
        servico = Servico.objects.get(realizado_por=self.usuario)
        alerta = AlertaChecklist.objects.get(servico=servico)
        self.assertEqual(alerta.criado_por, self.usuario)
        self.assertEqual(alerta.status, 'pendente')
        self.assertEqual(alerta.resposta_checklist.observacao, 'Mangueira obstruída')

    def test_mobile_lista_apenas_alertas_do_proprio_usuario(self):
        outro_item = ItemChecklist.objects.create(
            secao=self.secao,
            pergunta='Sinalização visível?',
        )
        servico_usuario = Servico.objects.create(
            equipamento=self.equipamento,
            tipo_servico=self.tipo_servico,
            status='concluido',
            realizado_por=self.usuario,
        )
        resposta_usuario = RespostaChecklist.objects.create(
            servico=servico_usuario,
            item_checklist=self.item,
            opcao='nao_atende',
            observacao='Lacre rompido',
        )
        alerta_usuario = AlertaChecklist.objects.create(
            equipamento=self.equipamento,
            servico=servico_usuario,
            resposta_checklist=resposta_usuario,
            criado_por=self.usuario,
            status='pendente',
        )
        servico_outro = Servico.objects.create(
            equipamento=self.equipamento,
            tipo_servico=self.tipo_servico,
            status='concluido',
            realizado_por=self.outro_usuario,
        )
        resposta_outro = RespostaChecklist.objects.create(
            servico=servico_outro,
            item_checklist=outro_item,
            opcao='nao_atende',
        )
        AlertaChecklist.objects.create(
            equipamento=self.equipamento,
            servico=servico_outro,
            resposta_checklist=resposta_outro,
            criado_por=self.outro_usuario,
            status='pendente',
        )

        token, _ = Token.objects.get_or_create(user=self.usuario)
        response = self.client.get(
            reverse('api-mobile-alertas-checklist'),
            HTTP_AUTHORIZATION=f'Token {token.key}',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['pendentes'], 1)
        self.assertEqual(len(payload['alertas']), 1)
        self.assertEqual(payload['alertas'][0]['id'], alerta_usuario.id)
        self.assertEqual(payload['alertas'][0]['item_pergunta'], self.item.pergunta)

    def test_alerta_salva_dados_da_tratativa(self):
        supervisor = User.objects.create_user(username='supervisor', password='123', is_staff=True)
        servico = Servico.objects.create(
            equipamento=self.equipamento,
            tipo_servico=self.tipo_servico,
            status='concluido',
            realizado_por=self.usuario,
        )
        resposta = RespostaChecklist.objects.create(
            servico=servico,
            item_checklist=self.item,
            opcao='nao_atende',
        )
        alerta = AlertaChecklist.objects.create(
            equipamento=self.equipamento,
            servico=servico,
            resposta_checklist=resposta,
            criado_por=self.usuario,
        )

        alerta.marcar_resolvido(supervisor, 'Extintor substituído e área sinalizada.')
        alerta.refresh_from_db()

        self.assertEqual(alerta.status, 'resolvido')
        self.assertEqual(alerta.resolvido_por, supervisor)
        self.assertIsNotNone(alerta.resolvido_em)
        self.assertEqual(alerta.tratativa, 'Extintor substituído e área sinalizada.')

    def test_api_predios_e_filtro_equipamentos_por_departamento(self):
        predio = Predio.objects.create(nome='Prédio Administrativo', endereco='Rua 1')
        departamento = Departamento.objects.create(nome='Recepção', predio=predio)
        self.equipamento.predio = predio
        self.equipamento.departamento = departamento
        self.equipamento.save()
        token, _ = Token.objects.get_or_create(user=self.usuario)

        predios_response = self.client.get(
            reverse('api-mobile-predios'),
            HTTP_AUTHORIZATION=f'Token {token.key}',
        )

        self.assertEqual(predios_response.status_code, 200)
        predio_payload = predios_response.json()['predios'][0]
        self.assertEqual(predio_payload['nome'], predio.nome)
        self.assertEqual(predio_payload['departamentos'][0]['nome'], departamento.nome)
        self.assertEqual(predio_payload['equipamentos_count'], 1)
        self.assertEqual(predio_payload['departamentos'][0]['equipamentos_count'], 1)

        equipamentos_response = self.client.get(
            reverse('api-mobile-equipamentos'),
            {
                'predio_id': predio.id,
                'departamento_id': departamento.id,
            },
            HTTP_AUTHORIZATION=f'Token {token.key}',
        )

        self.assertEqual(equipamentos_response.status_code, 200)
        self.assertEqual(len(equipamentos_response.json()), 1)
        self.assertEqual(equipamentos_response.json()[0]['id'], self.equipamento.id)

    def test_fluxo_web_navegacao_predio_departamento_e_equipamento(self):
        predio = Predio.objects.create(nome='Predio Administrativo', endereco='Rua 1')
        departamento = Departamento.objects.create(nome='Recepcao', predio=predio)
        outro_departamento = Departamento.objects.create(nome='Arquivo', predio=predio)
        self.equipamento.predio = predio
        self.equipamento.departamento = departamento
        self.equipamento.local = 'Entrada principal'
        self.equipamento.ponto_referencia = 'Ao lado da porta'
        self.equipamento.save()
        Equipamento.objects.create(
            nome='Extintor Inativo',
            numero_serie='EXT-INATIVO',
            tipo_equipamento=self.tipo_equipamento,
            predio=predio,
            departamento=departamento,
            ativo=False,
        )
        Equipamento.objects.create(
            nome='Extintor Arquivo',
            numero_serie='EXT-ARQ',
            tipo_equipamento=self.tipo_equipamento,
            predio=predio,
            departamento=outro_departamento,
        )
        self.client.force_login(self.usuario)

        predios_response = self.client.get(reverse('api_navegacao_predios'))
        self.assertEqual(predios_response.status_code, 200)
        predio_payload = predios_response.json()['predios'][0]
        self.assertEqual(predio_payload['id'], predio.id)
        self.assertEqual(predio_payload['departamentos_count'], 2)
        self.assertEqual(predio_payload['equipamentos_count'], 2)

        departamentos_response = self.client.get(
            reverse('api_navegacao_departamentos_por_predio', args=[predio.id])
        )
        self.assertEqual(departamentos_response.status_code, 200)
        departamentos_payload = departamentos_response.json()['departamentos']
        self.assertEqual([item['nome'] for item in departamentos_payload], ['Arquivo', 'Recepcao'])
        recepcao_payload = next(item for item in departamentos_payload if item['id'] == departamento.id)
        self.assertEqual(recepcao_payload['equipamentos_count'], 1)

        equipamentos_response = self.client.get(
            reverse('api_navegacao_equipamentos_por_departamento', args=[predio.id, departamento.id])
        )
        self.assertEqual(equipamentos_response.status_code, 200)
        equipamentos_payload = equipamentos_response.json()['equipamentos']
        self.assertEqual(len(equipamentos_payload), 1)
        self.assertEqual(equipamentos_payload[0]['id'], self.equipamento.id)
        self.assertEqual(equipamentos_payload[0]['predio_id'], predio.id)
        self.assertEqual(equipamentos_payload[0]['departamento_id'], departamento.id)

        detalhe_response = self.client.get(
            reverse('api_navegacao_equipamento_detalhe', args=[self.equipamento.id])
        )
        self.assertEqual(detalhe_response.status_code, 200)
        detalhe_payload = detalhe_response.json()['equipamento']
        self.assertEqual(detalhe_payload['id'], self.equipamento.id)
        self.assertEqual(detalhe_payload['local'], 'Entrada principal')
        self.assertEqual(detalhe_payload['ponto_referencia'], 'Ao lado da porta')

    def test_endpoints_aninhados_predio_departamento_e_equipamentos(self):
        predio = Predio.objects.create(nome='Predio Administrativo', endereco='Rua 1')
        outro_predio = Predio.objects.create(nome='Predio Operacional')
        departamento = Departamento.objects.create(nome='Manutencao', predio=predio)
        outro_departamento = Departamento.objects.create(nome='Arquivo', predio=outro_predio)
        self.equipamento.predio = predio
        self.equipamento.departamento = departamento
        self.equipamento.save()
        Equipamento.objects.create(
            nome='Extintor Arquivo',
            numero_serie='EXT-ARQ',
            tipo_equipamento=self.tipo_equipamento,
            predio=outro_predio,
            departamento=outro_departamento,
        )
        self.client.force_login(self.usuario)

        departamentos_response = self.client.get(
            reverse('api_predio_departamentos', args=[predio.id])
        )
        self.assertEqual(departamentos_response.status_code, 200)
        departamentos_payload = departamentos_response.json()
        self.assertEqual(departamentos_payload, [
            {
                'id': departamento.id,
                'nome': departamento.nome,
                'predio_id': predio.id,
                'predio_nome': predio.nome,
            }
        ])

        equipamentos_response = self.client.get(
            reverse('api_departamento_equipamentos', args=[departamento.id])
        )
        self.assertEqual(equipamentos_response.status_code, 200)
        equipamentos_payload = equipamentos_response.json()
        self.assertEqual(len(equipamentos_payload), 1)
        self.assertEqual(equipamentos_payload[0]['id'], self.equipamento.id)
        self.assertEqual(equipamentos_payload[0]['codigo'], self.equipamento.numero_serie)
        self.assertEqual(equipamentos_payload[0]['departamento_id'], departamento.id)
        self.assertEqual(equipamentos_payload[0]['departamento_nome'], departamento.nome)
        self.assertEqual(equipamentos_payload[0]['predio_id'], predio.id)
        self.assertEqual(equipamentos_payload[0]['predio_nome'], predio.nome)
        self.assertEqual(equipamentos_payload[0]['status'], 'ativo')

    def test_endpoints_aninhados_retornam_404_para_vinculos_inexistentes(self):
        self.client.force_login(self.usuario)

        departamentos_response = self.client.get(
            reverse('api_predio_departamentos', args=[999])
        )
        equipamentos_response = self.client.get(
            reverse('api_departamento_equipamentos', args=[999])
        )

        self.assertEqual(departamentos_response.status_code, 404)
        self.assertEqual(equipamentos_response.status_code, 404)

    def test_api_equipamentos_web_filtra_por_predio_e_departamento(self):
        predio = Predio.objects.create(nome='Predio Operacional')
        departamento = Departamento.objects.create(nome='Manutencao', predio=predio)
        outro_departamento = Departamento.objects.create(nome='Estoque', predio=predio)
        self.equipamento.predio = predio
        self.equipamento.departamento = departamento
        self.equipamento.save()
        Equipamento.objects.create(
            nome='Equipamento Estoque',
            numero_serie='EST-001',
            tipo_equipamento=self.tipo_equipamento,
            predio=predio,
            departamento=outro_departamento,
        )
        self.client.force_login(self.usuario)

        response = self.client.get(
            reverse('api_equipamentos_listar'),
            {
                'predio_id': predio.id,
                'departamento_id': departamento.id,
                'rows': 50,
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['total'], 1)
        self.assertEqual(payload['data'][0]['id'], self.equipamento.id)
        self.assertEqual(payload['data'][0]['predio_id'], predio.id)
        self.assertEqual(payload['data'][0]['departamento_id'], departamento.id)

    def test_usuario_comum_nao_atualiza_servico_de_outra_pessoa(self):
        servico = Servico.objects.create(
            equipamento=self.equipamento,
            tipo_servico=self.tipo_servico,
            status='rascunho',
            realizado_por=self.outro_usuario,
        )
        self.client.force_login(self.usuario)

        response = self.client.put(
            reverse('api_servicos_atualizar', args=[servico.id]),
            data=json.dumps({'status': 'rascunho', 'observacoes': 'Alterado'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 403)
        servico.refresh_from_db()
        self.assertNotEqual(servico.observacoes, 'Alterado')


class EditorTipoEquipamentoChecklistTests(TestCase):
    def setUp(self):
        self.gestor = User.objects.create_user(username='gestor_editor', password='123', is_staff=True)
        self.grupo = Grupo.objects.create(nome='Extintores')
        self.periodicidade = Periodicidade.objects.create(nome='Mensal', valor=1, tipo='meses')
        self.periodicidade_anual = Periodicidade.objects.create(nome='Anual', valor=1, tipo='anos')
        self.tipo_servico = TipoServico.objects.create(nome='Vistoria')
        self.tipo_equipamento = TipoEquipamento.objects.create(
            nome='Extintor ABC',
            grupo=self.grupo,
            periodicidade=self.periodicidade,
        )
        self.client.force_login(self.gestor)

    def test_cria_checklist_com_secoes_e_perguntas_no_mesmo_payload(self):
        response = self.client.post(
            reverse('api_editor_servico_criar'),
            data=json.dumps({
                'tipo_equipamento_id': self.tipo_equipamento.id,
                'tipo_servico_id': self.tipo_servico.id,
                'periodicidade_id': self.periodicidade.id,
                'obrigatorio': True,
                'secoes': [
                    {
                        'nome': 'Itens de verificação',
                        'descricao': 'Avaliação visual',
                        'ordem': 0,
                        'itens': [
                            {
                                'pergunta': 'Manômetro está no verde?',
                                'tipo_resposta': 'sim_nao',
                                'ordem': 0,
                                'obrigatorio': True,
                            },
                            {
                                'pergunta': 'Lacre está íntegro?',
                                'tipo_resposta': 'sim_nao',
                                'ordem': 1,
                                'obrigatorio': True,
                            },
                        ],
                    },
                ],
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['message'], 'Checklist criado com sucesso.')
        servico = ServicoTipoEquipamento.objects.get(tipo_equipamento=self.tipo_equipamento)
        self.assertEqual(servico.secoes_checklist.count(), 1)
        self.assertEqual(ItemChecklist.objects.filter(secao__servico_tipo_equipamento=servico).count(), 2)

    def test_edita_checklist_sincronizando_secoes_e_perguntas(self):
        servico = ServicoTipoEquipamento.objects.create(
            tipo_equipamento=self.tipo_equipamento,
            tipo_servico=self.tipo_servico,
            periodicidade=self.periodicidade,
        )
        secao_mantida = SecaoChecklist.objects.create(
            servico_tipo_equipamento=servico,
            nome='Geral',
        )
        item_mantido = ItemChecklist.objects.create(
            secao=secao_mantida,
            pergunta='Pergunta antiga',
        )
        secao_removida = SecaoChecklist.objects.create(
            servico_tipo_equipamento=servico,
            nome='Remover',
        )
        ItemChecklist.objects.create(secao=secao_removida, pergunta='Remover também')

        response = self.client.put(
            reverse('api_editor_servico_editar', args=[servico.id]),
            data=json.dumps({
                'tipo_servico_id': self.tipo_servico.id,
                'periodicidade_id': self.periodicidade_anual.id,
                'obrigatorio': False,
                'secoes': [
                    {
                        'id': secao_mantida.id,
                        'nome': 'Geral atualizada',
                        'descricao': '',
                        'ordem': 0,
                        'itens': [
                            {
                                'id': item_mantido.id,
                                'pergunta': 'Pergunta atualizada',
                                'tipo_resposta': 'texto',
                                'ordem': 0,
                                'obrigatorio': False,
                            },
                            {
                                'pergunta': 'Nova pergunta',
                                'tipo_resposta': 'numero',
                                'ordem': 1,
                                'obrigatorio': True,
                            },
                        ],
                    },
                ],
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        servico.refresh_from_db()
        self.assertFalse(servico.obrigatorio)
        self.assertEqual(servico.periodicidade, self.periodicidade_anual)
        self.assertFalse(SecaoChecklist.objects.filter(id=secao_removida.id).exists())
        secao_mantida.refresh_from_db()
        item_mantido.refresh_from_db()
        self.assertEqual(secao_mantida.nome, 'Geral atualizada')
        self.assertEqual(item_mantido.pergunta, 'Pergunta atualizada')
        self.assertEqual(item_mantido.tipo_resposta, 'texto')
        self.assertEqual(ItemChecklist.objects.filter(secao=secao_mantida).count(), 2)

    def test_validacao_de_secao_usa_nomenclatura_checklist(self):
        response = self.client.post(
            reverse('api_editor_secao_criar'),
            data=json.dumps({'nome': 'Geral'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Checklist e nome da seção são obrigatórios.')

    def test_checklist_duplicado_nao_expoe_erro_do_banco(self):
        ServicoTipoEquipamento.objects.create(
            tipo_equipamento=self.tipo_equipamento,
            tipo_servico=self.tipo_servico,
            periodicidade=self.periodicidade,
        )

        with self.assertLogs('core.views', level='ERROR') as logs:
            response = self.client.post(
                reverse('api_editor_servico_criar'),
                data=json.dumps({
                    'tipo_equipamento_id': self.tipo_equipamento.id,
                    'tipo_servico_id': self.tipo_servico.id,
                    'periodicidade_id': self.periodicidade.id,
                }),
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 400)
        erro = response.json()['error']
        self.assertEqual(
            erro,
            'Já existe um checklist com esta periodicidade para este tipo de equipamento.',
        )
        self.assertNotIn('duplicate key', erro.lower())
        self.assertNotIn('constraint', erro.lower())
        self.assertTrue(any('Erro de integridade no banco de dados' in linha for linha in logs.output))


class MultiempresaBaseTests(TestCase):
    def setUp(self):
        self.empresa_a = Empresa.objects.create(nome='Empresa A', slug='empresa-a')
        self.empresa_b = Empresa.objects.create(nome='Empresa B', slug='empresa-b')
        self.usuario = User.objects.create_user(username='usuario', password='123')
        self.factory = RequestFactory()

    def test_usuario_pode_pertencer_a_duas_empresas(self):
        EmpresaUsuario.objects.create(empresa=self.empresa_a, user=self.usuario)
        EmpresaUsuario.objects.create(empresa=self.empresa_b, user=self.usuario)

        self.assertEqual(EmpresaUsuario.objects.filter(user=self.usuario).count(), 2)

    def test_vinculo_duplicado_e_bloqueado(self):
        EmpresaUsuario.objects.create(empresa=self.empresa_a, user=self.usuario)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                EmpresaUsuario.objects.create(empresa=self.empresa_a, user=self.usuario)

    def test_manager_filtra_pela_empresa_ativa(self):
        Grupo.all_objects.create(empresa=self.empresa_a, nome='EXTINTORES')
        Grupo.all_objects.create(empresa=self.empresa_b, nome='HIDRANTES')

        token = set_current_empresa(self.empresa_a)
        try:
            self.assertEqual(list(Grupo.objects.values_list('nome', flat=True)), ['EXTINTORES'])
        finally:
            reset_current_empresa(token)

    def test_save_preenche_empresa_ativa(self):
        token = set_current_empresa(self.empresa_b)
        try:
            grupo = Grupo.objects.create(nome='BOMBAS')
        finally:
            reset_current_empresa(token)

        grupo.refresh_from_db()
        self.assertEqual(grupo.empresa, self.empresa_b)

    def test_endpoints_aninhados_respeitam_empresa_ativa(self):
        EmpresaUsuario.objects.create(empresa=self.empresa_a, user=self.usuario)
        predio_a = Predio.all_objects.create(empresa=self.empresa_a, nome='Predio A')
        predio_b = Predio.all_objects.create(empresa=self.empresa_b, nome='Predio B')
        departamento_a = Departamento.all_objects.create(
            empresa=self.empresa_a,
            nome='Manutencao A',
            predio=predio_a,
        )
        departamento_b = Departamento.all_objects.create(
            empresa=self.empresa_b,
            nome='Manutencao B',
            predio=predio_b,
        )
        equipamento_a = Equipamento.all_objects.create(
            empresa=self.empresa_a,
            nome='Extintor A',
            numero_serie='EXT-A',
            predio=predio_a,
            departamento=departamento_a,
        )
        Equipamento.all_objects.create(
            empresa=self.empresa_b,
            nome='Extintor B',
            numero_serie='EXT-B',
            predio=predio_b,
            departamento=departamento_b,
        )
        self.client.force_login(self.usuario)

        departamentos_response = self.client.get(
            reverse('api_predio_departamentos', args=[predio_a.id])
        )
        self.assertEqual(departamentos_response.status_code, 200)
        self.assertEqual(departamentos_response.json()[0]['id'], departamento_a.id)

        equipamentos_response = self.client.get(
            reverse('api_departamento_equipamentos', args=[departamento_a.id])
        )
        self.assertEqual(equipamentos_response.status_code, 200)
        self.assertEqual(equipamentos_response.json()[0]['id'], equipamento_a.id)

        outro_predio_response = self.client.get(
            reverse('api_predio_departamentos', args=[predio_b.id])
        )
        outro_departamento_response = self.client.get(
            reverse('api_departamento_equipamentos', args=[departamento_b.id])
        )
        self.assertEqual(outro_predio_response.status_code, 404)
        self.assertEqual(outro_departamento_response.status_code, 404)

    def test_nomes_iguais_sao_permitidos_em_empresas_diferentes(self):
        Grupo.all_objects.create(empresa=self.empresa_a, nome='EXTINTORES')
        Grupo.all_objects.create(empresa=self.empresa_b, nome='EXTINTORES')

        self.assertEqual(Grupo.all_objects.filter(nome='EXTINTORES').count(), 2)

    @override_settings(ALLOWED_HOSTS=['mercadolivre.saas.test'])
    def test_resolve_empresa_por_dominio_exato(self):
        self.empresa_a.dominio = 'mercadolivre.saas.test'
        self.empresa_a.save()

        request = self.factory.get('/', HTTP_HOST='mercadolivre.saas.test')

        self.assertEqual(resolve_empresa_por_host(request), self.empresa_a)

    @override_settings(
        ALLOWED_HOSTS=['.saas.test'],
        TENANT_BASE_DOMAINS=['saas.test'],
    )
    def test_resolve_empresa_ativa_pelo_subdominio_slug(self):
        self.empresa_a.slug = 'mercado-livre'
        self.empresa_a.save()
        self.empresa_b.slug = 'brightlux'
        self.empresa_b.save()
        EmpresaUsuario.objects.create(empresa=self.empresa_a, user=self.usuario)
        EmpresaUsuario.objects.create(empresa=self.empresa_b, user=self.usuario)
        Grupo.all_objects.create(empresa=self.empresa_a, nome='EXTINTORES ML')
        Grupo.all_objects.create(empresa=self.empresa_b, nome='EXTINTORES BR')

        request = self.factory.get('/', HTTP_HOST='mercado-livre.saas.test')
        request.user = self.usuario
        token = activate_empresa(request)
        try:
            self.assertEqual(resolve_empresa_ativa(request), self.empresa_a)
            self.assertEqual(list(Grupo.objects.values_list('nome', flat=True)), ['EXTINTORES ML'])
        finally:
            deactivate_empresa(token)

    @override_settings(
        ALLOWED_HOSTS=['.saas.test'],
        TENANT_BASE_DOMAINS=['saas.test'],
    )
    def test_bloqueia_usuario_sem_vinculo_no_subdominio(self):
        self.empresa_a.slug = 'mercado-livre'
        self.empresa_a.save()
        self.empresa_b.slug = 'brightlux'
        self.empresa_b.save()
        EmpresaUsuario.objects.create(empresa=self.empresa_b, user=self.usuario)

        request = self.factory.get('/', HTTP_HOST='mercado-livre.saas.test')
        request.user = self.usuario

        with self.assertRaises(PermissionDenied):
            activate_empresa(request)

    @override_settings(
        ALLOWED_HOSTS=['.saas.test'],
        TENANT_BASE_DOMAINS=['saas.test'],
    )
    def test_login_api_resolve_empresa_pelo_subdominio(self):
        self.empresa_a.slug = 'mercado-livre'
        self.empresa_a.save()
        EmpresaUsuario.objects.create(empresa=self.empresa_a, user=self.usuario)

        response = self.client.post(
            '/api/login/',
            {'username': 'usuario', 'password': '123'},
            HTTP_HOST='mercado-livre.saas.test',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['empresa']['slug'], 'mercado-livre')

    @override_settings(
        ALLOWED_HOSTS=['.saas.test'],
        TENANT_BASE_DOMAINS=['saas.test'],
    )
    def test_login_api_bloqueia_usuario_sem_vinculo_no_subdominio(self):
        self.empresa_a.slug = 'mercado-livre'
        self.empresa_a.save()
        self.empresa_b.slug = 'brightlux'
        self.empresa_b.save()
        EmpresaUsuario.objects.create(empresa=self.empresa_b, user=self.usuario)

        response = self.client.post(
            '/api/login/',
            {'username': 'usuario', 'password': '123'},
            HTTP_HOST='mercado-livre.saas.test',
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['detail'], 'Usuário sem acesso a esta empresa.')
