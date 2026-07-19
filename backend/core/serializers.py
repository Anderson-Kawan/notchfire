from rest_framework import serializers
from .models import Equipamento


class EquipamentoSerializer(serializers.ModelSerializer):
    tipo_equipamento_nome = serializers.SerializerMethodField()
    grupo_nome = serializers.SerializerMethodField()
    predio_nome = serializers.SerializerMethodField()
    departamento_nome = serializers.SerializerMethodField()
    codigo = serializers.SerializerMethodField()
    foto_url = serializers.SerializerMethodField()
    qr_code_url = serializers.SerializerMethodField()
    is_extintor = serializers.SerializerMethodField()

    class Meta:
        model = Equipamento
        fields = '__all__'
        read_only_fields = ('empresa',)

    def get_tipo_equipamento_nome(self, obj):
        return obj.tipo_equipamento.nome if obj.tipo_equipamento else ''

    def get_grupo_nome(self, obj):
        return obj.grupo.nome if obj.grupo else ''

    def get_predio_nome(self, obj):
        return obj.predio.nome if obj.predio else ''

    def get_departamento_nome(self, obj):
        return obj.departamento.nome if obj.departamento else ''

    def get_codigo(self, obj):
        return obj.numero_serie or obj.numero_extintor or obj.numero_cilindro or ''

    def get_is_extintor(self, obj):
        return obj.is_extintor()

    def get_absolute_file_url(self, obj, field_name):
        field = getattr(obj, field_name, None)
        if not field:
            return ''

        try:
            url = field.url
        except ValueError:
            return ''

        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(url)
        return url

    def get_foto_url(self, obj):
        return self.get_absolute_file_url(obj, 'foto')

    def get_qr_code_url(self, obj):
        return self.get_absolute_file_url(obj, 'qr_code')
