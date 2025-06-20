from django.shortcuts import get_object_or_404
from apps.service.rest_service import serializers as ytpl_serializers
from rest_framework import viewsets
from rest_framework.response import Response
from apps.peoples import models as people_models
from apps.onboarding import models as ob_models
from apps.activity import models as act_models
from apps.attendance.models import PeopleEventlog
from datetime import datetime


def get_queryset(model, request, related_fields=list):
    last_update = request.query_params.get("last_update")
    if last_update:
        last_update = datetime.strptime(last_update, "%Y-%m-%dT%H:%M:%S.%fZ")
        queryset = model.objects.filter(mdtz__gt=last_update)
    else:
        queryset = model.objects.all()
    return queryset


class PeopleViewset(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows People to be viewed.
    """

    def list(self, request):
        queryset = get_queryset(people_models.People, request)
        serializer = ytpl_serializers.PeopleSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        user = get_object_or_404(people_models.People, pk=kwargs["pk"])
        serializer = ytpl_serializers.PeopleSerializer(user)
        return Response(serializer.data)


class PELViewset(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows PeopleEventLog to be viewed.
    """

    def list(self, request):
        queryset = get_queryset(PeopleEventlog, request)
        serializer = ytpl_serializers.PeopleEventLogSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        event_log = get_object_or_404(PeopleEventlog, pk=kwargs["pk"])
        serializer = ytpl_serializers.PeopleEventLogSerializer(event_log)
        return Response(serializer.data)


class PgroupViewset(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows Pgroup to be viewed.
    """

    def list(self, request):
        queryset = get_queryset(people_models.Pgroup, request)
        serializer = ytpl_serializers.PgroupSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        pgroup = get_object_or_404(people_models.Pgroup, pk=kwargs["pk"])
        serializer = ytpl_serializers.PgroupSerializer(pgroup)
        return Response(serializer.data)


class BtViewset(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows Bt to be viewed.
    """

    def list(self, request):
        queryset = get_queryset(ob_models.Bt, request)
        serializer = ytpl_serializers.BtSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        bt = get_object_or_404(ob_models.Bt, pk=kwargs["pk"])
        serializer = ytpl_serializers.BtSerializer(bt)
        return Response(serializer.data)


class ShiftViewset(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows Shift to be viewed.
    """

    def list(self, request):
        queryset = get_queryset(ob_models.Shift, request)
        serializer = ytpl_serializers.ShiftSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        shift = get_object_or_404(ob_models.Shift, pk=kwargs["pk"])
        serializer = ytpl_serializers.ShiftSerializer(shift)
        return Response(serializer.data)


class TypeAssistViewset(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows TypeAssist to be viewed.
    """

    def list(self, request):
        queryset = get_queryset(ob_models.TypeAssist, request)
        serializer = ytpl_serializers.TypeAssistSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        type_assist = get_object_or_404(ob_models.TypeAssist, pk=kwargs["pk"])
        serializer = ytpl_serializers.TypeAssistSerializer(type_assist)
        return Response(serializer.data)


class PgbelongingViewset(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows Pgbelonging to be viewed.
    """

    def list(self, request):
        queryset = get_queryset(people_models.Pgbelonging, request)
        serializer = ytpl_serializers.PgbelongingSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        belonging = get_object_or_404(people_models.Pgbelonging, pk=kwargs["pk"])
        serializer = ytpl_serializers.PgbelongingSerializer(belonging)
        return Response(serializer.data)


class JobViewset(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows Job to be viewed.
    """

    def list(self, request):
        queryset = get_queryset(act_models.Job, request)
        serializer = ytpl_serializers.JobSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        job = get_object_or_404(act_models.Job, pk=kwargs["pk"])
        serializer = ytpl_serializers.JobSerializer(job)
        return Response(serializer.data)


class JobneedViewset(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows Jobneed to be viewed.
    """

    def list(self, request):
        queryset = get_queryset(act_models.Jobneed, request)
        serializer = ytpl_serializers.JobneedSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        jobneed = get_object_or_404(act_models.Jobneed, pk=kwargs["pk"])
        serializer = ytpl_serializers.JobneedSerializer(jobneed)
        return Response(serializer.data)
