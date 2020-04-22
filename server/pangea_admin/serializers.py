from django.contrib.auth.models import User, Group, Permission
from rest_framework import serializers
from pangea.settings import PANGEA_DB_URI, PANGEA_DB_URI_OGR_STYLE, PANGEA_IMPORTED_DATA_SCHEMA
from .utils.importers import import_csv_2_pg, import_ogr_2_pg
import copy

GENERIC_ERROR = "An error occurred while processing your request. Maybe, it can help you: %s"

from .models import LayerStatus, Column, LayerStatus, BasicTerritorialLevelLayer, ComposedTerritorialLevelLayer 
from .utils.database_information import get_geometry_column, get_geometry_type

import unidecode


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'url', 'name']


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['url', 'name']


class UserSerializer(serializers.ModelSerializer):
    user_permissions = PermissionSerializer(many=True, read_only=True)
    groups = GroupSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = ['id', 'url', 'username',
                  'email', 'groups', 'user_permissions']


class LayerStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = LayerStatus
        fields = ['id', 'url', 'layer', 'status', 'date']


class ColumnSerializer(serializers.ModelSerializer):
    class Meta:
        model = Column
        fields = ['id', 'layer', 'name', 'alias']



class BasicTerritorialLevelLayerSerializer(serializers.ModelSerializer):
    layerstatus_set = LayerStatusSerializer(many=True, read_only=True)
    column_set = ColumnSerializer(many=True, read_only=False, required=False)

    class Meta:
        model = BasicTerritorialLevelLayer
        fields = ['id', 'name', 'description', 'metadata', '_file',
                  'srid', 'geocod_column', 'dimension_column',
                  'encoding', 'zoom_min', 'zoom_max', 'column_set', 'layerstatus_set']

    def create(self, validated_data):
        ogr_params = {
            "encoding": validated_data['encoding'],
            "srid": validated_data['srid']
        }
        table_name = unidecode.unidecode('tb_{0}'.format(validated_data['name']))
        validated_data['table_name'] = table_name
        validated_data['schema_name'] = PANGEA_IMPORTED_DATA_SCHEMA

        try:
            layer = BasicTerritorialLevelLayer.objects.create(
                **validated_data)
            layer_status = {'layer': layer,
                           'status': LayerStatus.Status.IMPORTED}
            LayerStatus.objects.create(**layer_status)
            ok = import_ogr_2_pg(layer._file.path, PANGEA_DB_URI_OGR_STYLE,
                                 PANGEA_IMPORTED_DATA_SCHEMA, table_name, ogr_params)
            if ok:
                geometry_column = get_geometry_column(PANGEA_IMPORTED_DATA_SCHEMA, table_name)
                geometry_type = get_geometry_type(PANGEA_IMPORTED_DATA_SCHEMA, table_name, geometry_column)
                layer.geom_column = geometry_column
                layer.geom_type = geometry_type
                layer.save()

            else:
                raise Exception('Ocorreu um erro')


        except Exception as e:
            layer.delete()
            raise serializers.ValidationError(GENERIC_ERROR % e)

        return layer

    def update(self, instance, validated_data):
        if 'column_set' in validated_data:
            try:
                Column.objects.filter(layer=instance.id).delete()
                column_set = validated_data.pop('column_set')
                for column in column_set:
                    column["layer"] = instance
                    Column.objects.create(**column)
            except Exception as e:
                raise(e)
        return super(BasicTerritorialLevelLayerSerializer, self).update(instance, validated_data)


class ComposedTerritorialLevelLayerSerializer(serializers.ModelSerializer):
    layerstatus_set = LayerStatusSerializer(many=True, read_only=True)
    column_set = ColumnSerializer(many=True, read_only=False, required=False)

    class Meta:
        model = ComposedTerritorialLevelLayer
        fields = ['id', 'name', 'description', 'metadata', '_file',
                  'is_a_composition_of', 'geocod_column', 
                  'delimiter', 'quotechar', 'decimal','composition_column',
                  'encoding', 'zoom_min', 'zoom_max', 'column_set', 'layerstatus_set']

    def create(self, validated_data):
        
        table_name = unidecode.unidecode('tb_{0}'.format(validated_data['name']))
        validated_data['table_name'] = table_name
        validated_data['schema_name'] = PANGEA_IMPORTED_DATA_SCHEMA

        try:
            layer = ComposedTerritorialLevelLayer.objects.create(
                **validated_data)
            layer_status = {'layer': layer,
                           'status': LayerStatus.Status.IMPORTED}
            LayerStatus.objects.create(**layer_status)

            pandas_params = {
                "encoding": validated_data['encoding'],
                "delimiter": validated_data['delimiter'],
                "decimal": validated_data['decimal']
            }
            if 'quotechar' in validated_data['quotechar']:
                pandas_params["quotechar"] = validated_data['quotechar']
                pandas_params["quoting"] = 0  # QUOTE_MINIMAL

            import_csv_2_pg(layer._file.path, PANGEA_DB_URI,
                            PANGEA_IMPORTED_DATA_SCHEMA, table_name, pandas_params)

            
        except Exception as e:
            layer.delete()
            raise serializers.ValidationError(GENERIC_ERROR % e)

        return layer

    def update(self, instance, validated_data):
        if 'column_set' in validated_data:
            try:
                Column.objects.filter(layer=instance.id).delete()
                column_set = validated_data.pop('column_set')
                for column in column_set:
                    column["layer"] = instance
                    Column.objects.create(**column)
            except Exception as e:
                raise(e)
        return super(ComposedTerritorialLevelLayerSerializer, self).update(instance, validated_data)

'''class ImportedTabularDataSerializer(serializers.ModelSerializer):
    datastatus_set = DataStatusSerializer(many=True, read_only=True)

    class Meta:
        model = ImportedTabularData
        fields = ['id', 'url', 'file_path', 'table_name', 'description', 'metadata_url',
                  'encoding', 'delimiter', 'quotechar', 'decimal', 'datastatus_set']




class GeneralizationParamsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneralizationParams
        fields = ['zoom_level', 'url', 'factor']


class LayerMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = LayerMetadata
        fields = ['id', 'url', 'layer_name', 'data_imported', 'schema_name',
                  'table_name', 'geocod_column', 'dimension_column',
                  'topo_geom_column', 'is_a_composition_of',
                  'composition_column', 'zoom_min', 'zoom_max']'''
