# Generated manually for equipamento reports.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_relatoriogerado'),
    ]

    operations = [
        migrations.AddField(
            model_name='relatoriogerado',
            name='equipamento',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.equipamento'),
        ),
    ]
