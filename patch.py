# -*- coding: utf-8 -*-
import re

with open('backend/apps/schedules/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add _block_visitor_write
block_code = '''
    def _block_visitor_write(self):
        if self.request.user and self.request.user.is_authenticated and self.request.user.role == User.Role.VISITOR:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("O perfil Visitante possui apenas permissão de consulta no módulo Relatório Técnico.")
'''
content = re.sub(
    r'(class EducationReportViewSet\(viewsets\.ModelViewSet\):\n    serializer_class = EducationReportSerializer\n    permission_classes = \[IsAuthenticated\]\n)',
    r'\g<1>' + block_code,
    content
)

# 2. Add _block_visitor_write call to create, update, partial_update, destroy, process_statistics, submit_for_review, approve, return_for_correction
methods = ['create', 'update', 'partial_update', 'destroy', 'process_statistics', 'submit_for_review', 'approve', 'return_for_correction']

for method in methods:
    if method == 'destroy':
        # Check if destroy is explicitly defined in EducationReportViewSet
        if 'def destroy(' not in content:
            # Need to add destroy method
            destroy_code = '''
    def destroy(self, request, *args, **kwargs):
        self._block_visitor_write()
        return super().destroy(request, *args, **kwargs)
'''
            # Add before get_queryset
            content = content.replace('    def get_queryset(self):', destroy_code + '\n    def get_queryset(self):')
        else:
            content = re.sub(
                r'(def ' + method + r'\(self, request(?:, [^)]*)?\):\n(?:        [^\n]+\n)?)',
                r'\g<1>        self._block_visitor_write()\n',
                content
            )
    else:
        # For other methods, add self._block_visitor_write() right after def ...: or decorators
        content = re.sub(
            r'(def ' + method + r'\(self, request(?:, [^)]*)?\):\n)',
            r'\g<1>        self._block_visitor_write()\n',
            content
        )

# 3. Add to retrieve:
retrieve_add = '''        if request.user.role == User.Role.VISITOR:
            instance = self.get_object()
            if instance.status != EducationReport.ReportStatus.APPROVED:
                from django.http import Http404
                raise Http404("Relatório não encontrado.")
'''
content = re.sub(
    r'(def retrieve\(self, request, \*args, \*\*kwargs\):\n)',
    r'\g<1>' + retrieve_add,
    content
)

# 4. Modify get_queryset for visitor
get_queryset_mod = '''
        # VISITOR: acesso somente-leitura de relatórios aprovados (caminho independente)
        if user.role == User.Role.VISITOR:
            from django.db.models import Q
            scoped = queryset.filter(status=EducationReport.ReportStatus.APPROVED)
            params = self.request.query_params
            if params.get("protocol"):
                scoped = scoped.filter(agenda_id=params["protocol"])
            if params.get("team"):
                scoped = scoped.filter(team__icontains=params["team"].strip())
            if params.get("source"):
                scoped = scoped.filter(source=params["source"])
            if params.get("date"):
                scoped = scoped.filter(operation_date=params["date"])
            if params.get("date_from"):
                scoped = scoped.filter(operation_date__gte=params["date_from"])
            if params.get("date_to"):
                scoped = scoped.filter(operation_date__lte=params["date_to"])
            if params.get("q"):
                term = params["q"].strip()
                search_filter = (
                    Q(team__icontains=term)
                    | Q(agenda__source_id__icontains=term)
                    | Q(agenda__title__icontains=term)
                    | Q(management_name__icontains=term)
                )
                scoped = scoped.filter(search_filter)
            return scoped.order_by("-operation_date", "-created_at").distinct()
'''
content = re.sub(
    r'(        if user\.is_admin_role:\n            queryset = queryset\.filter\(agenda__date__gte="2026-07-01"\))',
    get_queryset_mod + r'\n\g<1>',
    content
)

# 5. allowed_visitors logic in _validate_agenda_access
validate_agenda_mod = '''        allowed_visitors = ["OLS/CooAdm", "Subsecretaria"]
        is_allowed_visitor = request.user.role == User.Role.VISITOR and request.user.sector and request.user.sector.name in allowed_visitors
        if not (request.user.is_admin_role or request.user.role == User.Role.SUPERVISOR or is_allowed_visitor):'''
content = content.replace('        if not (request.user.is_admin_role or request.user.role == User.Role.SUPERVISOR):', validate_agenda_mod)

with open('backend/apps/schedules/views.py', 'w', encoding='utf-8') as f:
    f.write(content)
