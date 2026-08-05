# -*- coding: utf-8 -*-
with open('backend/apps/schedules/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

destroy_code = '''
    def destroy(self, request, *args, **kwargs):
        self._block_visitor_write()
        return super().destroy(request, *args, **kwargs)
'''

# We will inject destroy right before get_queryset in EducationReportViewSet
content = content.replace('    def get_queryset(self):\n        user = self.request.user\n        queryset = EducationReport.objects.select_related("agenda"', destroy_code + '\n    def get_queryset(self):\n        user = self.request.user\n        queryset = EducationReport.objects.select_related("agenda"')

with open('backend/apps/schedules/views.py', 'w', encoding='utf-8') as f:
    f.write(content)
