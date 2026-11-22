from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class AccountFlowTests(TestCase):
    def test_registration_logs_user_in(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "pupil",
                "password1": "StrongPass123",
                "password2": "StrongPass123",
            },
        )
        self.assertRedirects(response, reverse("home"))
        self.assertTrue(User.objects.filter(username="pupil").exists())
        self.assertIn("_auth_user_id", self.client.session)

    def test_results_require_login(self):
        response = self.client.get(reverse("learning:results"))
        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={reverse('learning:results')}",
        )

    def test_logged_in_user_opens_results(self):
        user = User.objects.create_user(username="pupil", password="StrongPass123")
        self.client.force_login(user)
        response = self.client.get(reverse("learning:results"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Мои результаты")
