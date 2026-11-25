from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from learning.models import Subject, Topic


class StudyPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="pupil", password="StrongPass123")
        self.client.force_login(self.user)

    def test_empty_topic_list(self):
        response = self.client.get(reverse("learning:start"))
        self.assertContains(response, "Тем пока нет")

    def test_topics_are_grouped_and_post_to_start_quiz(self):
        math = Subject.objects.create(name="Математика", slug="math")
        algebra = Topic.objects.create(subject=math, name="Алгебра", slug="algebra")
        response = self.client.get(reverse("learning:start"))
        self.assertContains(response, "Математика")
        self.assertContains(response, "Алгебра")
        self.assertContains(
            response,
            reverse("learning:start_quiz", args=[algebra.pk]),
        )
        self.assertContains(response, "Начать тест")
