from django.urls import path
from rest_framework.routers import DefaultRouter
from .views_api import AlertasChecklistMobileAPI, ChecklistItensAPI, DashboardAPI, EquipamentoDetalheMobileAPI, EquipamentoTiposServicoAPI, EquipamentosMobileAPI, EquipamentoViewSet, LoginAPI, NotificacoesAPI, PerfilAPI, PrediosAPI, QRCodeEquipamentoAPI, ServicoCriarAPI, ServicoDetalheAPI

router = DefaultRouter()
router.register(r'equipamentos', EquipamentoViewSet, basename='api-equipamentos')

urlpatterns = [
    path('login/', LoginAPI.as_view(), name='api-login'),
    path('dashboard/', DashboardAPI.as_view(), name='api-dashboard'),
    path('me/', PerfilAPI.as_view(), name='api-me'),
    path('notificacoes/', NotificacoesAPI.as_view(), name='api-notificacoes'),
    path('mobile/alertas-checklist/', AlertasChecklistMobileAPI.as_view(), name='api-mobile-alertas-checklist'),
    path('mobile/predios/', PrediosAPI.as_view(), name='api-mobile-predios'),
    path('mobile/equipamentos/', EquipamentosMobileAPI.as_view(), name='api-mobile-equipamentos'),
    path('mobile/equipamentos/<int:id>/', EquipamentoDetalheMobileAPI.as_view(), name='api-mobile-equipamento-detalhe'),
    path('mobile/servicos/criar/', ServicoCriarAPI.as_view(), name='api-mobile-servicos-criar'),
    path('mobile/servicos/<int:id>/', ServicoDetalheAPI.as_view(), name='api-mobile-servicos-detalhe'),
    path('mobile/checklist-itens/', ChecklistItensAPI.as_view(), name='api-mobile-checklist-itens'),
    path('mobile/equipamentos/<int:id>/tipos-servico/', EquipamentoTiposServicoAPI.as_view(), name='api-mobile-equipamento-tipos-servico'),
    path('mobile/qr/equipamento/', QRCodeEquipamentoAPI.as_view(), name='api-mobile-qr-equipamento'),
    path('servicos/criar/', ServicoCriarAPI.as_view(), name='api-servicos-criar'),
    path('checklist-itens/', ChecklistItensAPI.as_view(), name='api-checklist-itens'),
    path('equipamentos/<int:id>/tipos-servico/', EquipamentoTiposServicoAPI.as_view(), name='api-equipamento-tipos-servico'),
    path('qr/equipamento/', QRCodeEquipamentoAPI.as_view(), name='api-qr-equipamento'),
]

urlpatterns += router.urls
