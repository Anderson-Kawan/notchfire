# Generated manually for relatório history.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0009_usuarioperfil_foto_usuarioperfil_predio'),
    ]

    operations = [
        migrations.CreateModel(
            name='RelatorioGerado',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('condensado', 'Relatório Condensado')], default='condensado', max_length=30)),
                ('data_inicio', models.DateField(blank=True, null=True)),
                ('data_fim', models.DateField(blank=True, null=True)),
                ('total_servicos', models.IntegerField(default=0)),
                ('total_equipamentos', models.IntegerField(default=0)),
                ('total_nao_conformes', models.IntegerField(default=0)),
                ('media_pontuacao', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('arquivo_nome', models.CharField(blank=True, max_length=160)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('criado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='relatorios_gerados', to=settings.AUTH_USER_MODEL)),
                ('predio', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.predio')),
                ('tipo_equipamento', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.tipoequipamento')),
                ('tipo_servico', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.tiposervico')),
            ],
            options={
                'verbose_name': 'Relatório Gerado',
                'verbose_name_plural': 'Relatórios Gerados',
                'ordering': ['-criado_em'],
            },
        ),
    ]
