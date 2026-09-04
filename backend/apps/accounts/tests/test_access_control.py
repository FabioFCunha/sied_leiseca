from django.http import JsonResponse
from django.test import RequestFactory, SimpleTestCase

from apps.accounts.access_control import (
    EDUCATION,
    INSPECTION,
    can_write_request,
    has_access_area,
)
from apps.accounts.middleware import UserAreaAccessMiddleware


class UserStub:
    is_authenticated = True
    is_superuser = False

    def __init__(self, areas, read_only=False):
        self.access_areas = areas
        self.is_read_only = read_only


class UserAreaAccessTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = UserAreaAccessMiddleware(
            lambda request: JsonResponse({"ok": True})
        )

    def test_education_user_does_not_have_inspection_area(self):
        user = UserStub([EDUCATION])
        self.assertTrue(has_access_area(user, EDUCATION))
        self.assertFalse(has_access_area(user, INSPECTION))

    def test_read_only_user_cannot_write(self):
        user = UserStub([EDUCATION, INSPECTION], read_only=True)
        self.assertFalse(can_write_request(user, "POST"))
        self.assertTrue(can_write_request(user, "GET"))

    def test_middleware_blocks_wrong_area(self):
        request = self.factory.get("/api/inspection/reports/")
        request.user = UserStub([EDUCATION])
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)

    def test_middleware_blocks_read_only_mutation(self):
        request = self.factory.post("/api/agendas/")
        request.user = UserStub([EDUCATION, INSPECTION], read_only=True)
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)
