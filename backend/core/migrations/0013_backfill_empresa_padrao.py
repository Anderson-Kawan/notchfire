from django.db import migrations


EMPRESA_PADRAO_SLUG = "empresa-padrao"
EMPRESA_PADRAO_NOME = "Empresa Padrao"

EMPRESA_SCOPED_MODELS = [
    "Predio",
    "Departamento",
    "Grupo",
    "Periodicidade",
    "TipoEquipamento",
    "TipoServico",
    "ServicoTipoEquipamento",
    "SecaoChecklist",
    "ItemChecklist",
    "Equipamento",
    "Inspecao",
    "Servico",
    "RespostaChecklist",
    "AcaoCorretiva",
    "RelatorioGerado",
]


def tipo_acesso_para_user(user):
    if user.is_superuser:
        return "admin"
    if user.is_staff:
        return "analista"
    return "usuario"


def forwards(apps, schema_editor):
    Empresa = apps.get_model("core", "Empresa")
    EmpresaUsuario = apps.get_model("core", "EmpresaUsuario")
    User = apps.get_model("auth", "User")

    empresa, _ = Empresa.objects.get_or_create(
        slug=EMPRESA_PADRAO_SLUG,
        defaults={
            "nome": EMPRESA_PADRAO_NOME,
            "ativa": True,
        },
    )

    for model_name in EMPRESA_SCOPED_MODELS:
        model = apps.get_model("core", model_name)
        model.objects.filter(empresa__isnull=True).update(empresa=empresa)

    for user in User.objects.all():
        EmpresaUsuario.objects.get_or_create(
            empresa=empresa,
            user=user,
            defaults={
                "tipo_acesso": tipo_acesso_para_user(user),
                "ativo": True,
            },
        )


def backwards(apps, schema_editor):
    Empresa = apps.get_model("core", "Empresa")
    EmpresaUsuario = apps.get_model("core", "EmpresaUsuario")

    empresa = Empresa.objects.filter(slug=EMPRESA_PADRAO_SLUG).first()
    if not empresa:
        return

    for model_name in EMPRESA_SCOPED_MODELS:
        model = apps.get_model("core", model_name)
        model.objects.filter(empresa=empresa).update(empresa=None)

    EmpresaUsuario.objects.filter(empresa=empresa).delete()
    empresa.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_empresa_empresausuario_alter_departamento_nome_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
