# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2021 Gemeente Amsterdam
from datapunt_api.pagination import HALPagination
from datapunt_api.rest import _DisabledHTMLFilterBackend, DEFAULT_RENDERERS
from rest_framework import viewsets, mixins
from rest_framework_extensions.mixins import DetailSerializerMixin


class HALViewSetRetrieve(DetailSerializerMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    renderer_classes = DEFAULT_RENDERERS
    pagination_class = HALPagination
    filter_backends = (_DisabledHTMLFilterBackend,)

    detailed_keyword = 'detailed'


class HALViewSetRetrieveCreateUpdate(DetailSerializerMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                                  mixins.UpdateModelMixin, viewsets.GenericViewSet):
    renderer_classes = DEFAULT_RENDERERS
    pagination_class = HALPagination
    filter_backends = (_DisabledHTMLFilterBackend,)

    detailed_keyword = 'detailed'
