from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from learning.models import (
    AnswerOption,
    AttemptQuestion,
    Question,
    QuizAttempt,
    Skill,
    StudentAnswer,
    Subject,
    Topic,
)


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

    def test_unfinished_attempt_offers_continue_without_new_quiz(self):
        math = Subject.objects.create(name="Математика", slug="math-open")
        topic = Topic.objects.create(subject=math, name="Линейная алгебра", slug="linear")
        attempt = QuizAttempt.objects.create(user=self.user, topic=topic, is_completed=False)
        response = self.client.get(reverse("learning:start"))
        self.assertContains(response, "Продолжить тест")
        self.assertContains(response, reverse("learning:quiz_detail", args=[attempt.pk]))
        self.assertNotContains(response, reverse("learning:start_quiz", args=[topic.pk]))

    def test_completed_attempt_offers_a_new_quiz(self):
        math = Subject.objects.create(name="Математика", slug="math-done")
        topic = Topic.objects.create(subject=math, name="Дроби", slug="fractions")
        QuizAttempt.objects.create(user=self.user, topic=topic, is_completed=True)
        response = self.client.get(reverse("learning:start"))
        self.assertContains(response, "Начать тест")
        self.assertContains(response, reverse("learning:start_quiz", args=[topic.pk]))
        self.assertNotContains(response, "Продолжить тест")


class QuizDetailTemplateTests(TestCase):
    def test_quiz_form_lists_assigned_questions_without_answers(self):
        user = User.objects.create_user(username="pupil2", password="StrongPass123")
        subject = Subject.objects.create(name="Математика", slug="math-quiz")
        topic = Topic.objects.create(subject=subject, name="Уравнения", slug="equations")
        skill = Skill.objects.create(topic=topic, name="Линейные уравнения")
        first = Question.objects.create(
            skill=skill,
            text="Первый вопрос",
            explanation="Секретное объяснение",
        )
        second = Question.objects.create(skill=skill, text="Второй вопрос")
        AnswerOption.objects.create(question=first, text="Верный вариант", is_correct=True, order=1)
        AnswerOption.objects.create(question=first, text="Другой вариант", order=2)
        attempt = QuizAttempt.objects.create(user=user, topic=topic, mode="confidence")
        AttemptQuestion.objects.create(attempt=attempt, question=second, order=1)
        AttemptQuestion.objects.create(attempt=attempt, question=first, order=2)

        self.client.force_login(user)
        response = self.client.get(reverse("learning:quiz_detail", args=[attempt.pk]))
        content = response.content.decode()

        self.assertContains(response, "Первый вопрос")
        self.assertContains(response, "Верный вариант")
        self.assertContains(response, f'name="answer_{first.pk}"')
        self.assertContains(response, f'name="confidence_{first.pk}"')
        self.assertContains(response, 'value="low"')
        self.assertContains(response, 'value="medium"')
        self.assertContains(response, 'value="high"')
        self.assertContains(response, "Уверен")
        self.assertContains(response, "Сомневаюсь")
        self.assertContains(response, "Угадываю")
        self.assertContains(response, "Здесь нет правильного выбора")
        self.assertNotContains(response, "checked")
        self.assertLess(content.index("Второй вопрос"), content.index("Первый вопрос"))
        self.assertNotContains(response, "Секретное объяснение")
        self.assertNotContains(response, "is_correct")
        self.assertContains(response, reverse("learning:submit_quiz", args=[attempt.pk]))
        self.assertNotContains(response, "disabled")


class QuizResultsTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="StrongPass123")
        self.other = User.objects.create_user(username="other", password="StrongPass123")
        subject = Subject.objects.create(name="Математика", slug="math-results")
        self.topic = Topic.objects.create(subject=subject, name="Линейная алгебра", slug="linear-results")
        skill = Skill.objects.create(topic=self.topic, name="Уравнения")
        self.question = Question.objects.create(skill=skill, text="Сколько будет 2 + 2?")
        self.correct = AnswerOption.objects.create(question=self.question, text="4", is_correct=True)
        self.wrong = AnswerOption.objects.create(question=self.question, text="5", is_correct=False)
        QuizAttempt.objects.create(
            user=self.other,
            topic=self.topic,
            is_completed=True,
            completed_at=timezone.now(),
        )
        self.attempt = QuizAttempt.objects.create(
            user=self.owner,
            topic=self.topic,
            is_completed=True,
        )
        AttemptQuestion.objects.create(attempt=self.attempt, question=self.question, order=1)
        StudentAnswer.objects.create(
            quiz_attempt=self.attempt,
            question=self.question,
            answer=self.wrong,
            confidence="low",
            is_correct=False,
        )

    def test_owner_sees_saved_result_without_recalculation(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("learning:quiz_results", args=[self.attempt.pk]))
        self.assertContains(response, "Тест 1")
        self.assertNotContains(response, f"Тест {self.attempt.pk}")
        self.assertContains(response, "owner")
        self.assertContains(response, "Линейная алгебра")
        self.assertContains(response, "0%")
        self.assertContains(response, "Правильных ответов: 0 из 1")
        self.assertNotContains(response, "Навыки")
        self.assertContains(response, "Сколько будет 2 + 2?")
        self.assertContains(response, "Твой ответ:")
        self.assertContains(response, "answer-mine")
        self.assertContains(response, "5")
        self.assertContains(response, "Правильный ответ:")
        self.assertContains(response, "answer-right")
        self.assertContains(response, "4")
        self.assertContains(response, "Неверно")
        self.assertContains(response, "is-wrong")
        self.assertContains(response, "Как ты отвечал:")
        self.assertContains(response, "Выбирал наугад")
        self.assertContains(response, "Объяснить ошибку")
        self.assertNotContains(response, "AI")
        self.assertContains(response, "К моим результатам")
        self.assertContains(response, reverse("learning:results") + "\"")
        self.assertContains(response, reverse("learning:start"))
        self.assertNotContains(response, "Ошибка")

    def test_correct_answer_is_not_repeated(self):
        self.attempt.answers.update(answer=self.correct, is_correct=True)
        self.client.force_login(self.owner)
        response = self.client.get(reverse("learning:quiz_results", args=[self.attempt.pk]))
        self.assertContains(response, "Верно")
        self.assertContains(response, "is-correct")
        self.assertContains(response, "Твой ответ:")
        self.assertContains(response, "answer-right")
        self.assertNotContains(response, "Правильный ответ")
        self.assertNotContains(response, "answer-mine")
        self.assertEqual(response.content.decode().count(">4<"), 1)

    def test_previous_result_is_the_last_attempt_on_the_same_topic(self):
        other_topic = Topic.objects.create(
            subject=self.topic.subject,
            name="Дроби",
            slug="fractions-results",
        )
        QuizAttempt.objects.create(
            user=self.owner,
            topic=other_topic,
            is_completed=True,
            completed_at=timezone.now() - timedelta(hours=1),
        )
        earlier = QuizAttempt.objects.create(
            user=self.owner,
            topic=self.topic,
            is_completed=True,
            completed_at=timezone.now() - timedelta(days=1),
        )
        StudentAnswer.objects.create(
            quiz_attempt=earlier,
            question=self.question,
            answer=self.correct,
            confidence="high",
            is_correct=True,
        )
        self.attempt.completed_at = timezone.now()
        self.attempt.save(update_fields=["completed_at"])
        self.client.force_login(self.owner)
        response = self.client.get(reverse("learning:quiz_results", args=[self.attempt.pk]))
        self.assertContains(response, "Предыдущий тест №1:")
        self.assertContains(response, "1 из 1 · 100%")
        self.assertNotContains(response, "Навыки")

    def test_several_skills_are_listed_against_the_same_previous_test(self):
        second_skill = Skill.objects.create(topic=self.topic, name="Перенос слагаемых")
        second_question = Question.objects.create(skill=second_skill, text="Перенеси слагаемое")
        second_option = AnswerOption.objects.create(
            question=second_question,
            text="Готово",
            is_correct=True,
        )
        StudentAnswer.objects.create(
            quiz_attempt=self.attempt,
            question=second_question,
            answer=second_option,
            confidence="medium",
            is_correct=True,
        )
        earlier = QuizAttempt.objects.create(
            user=self.owner,
            topic=self.topic,
            is_completed=True,
            completed_at=timezone.now() - timedelta(days=1),
        )
        StudentAnswer.objects.create(
            quiz_attempt=earlier,
            question=self.question,
            answer=self.correct,
            confidence="high",
            is_correct=True,
        )
        self.attempt.completed_at = timezone.now()
        self.attempt.save(update_fields=["completed_at"])
        self.client.force_login(self.owner)
        response = self.client.get(reverse("learning:quiz_results", args=[self.attempt.pk]))
        self.assertContains(response, "Навыки")
        self.assertContains(response, "Уравнения — 0 из 1")
        self.assertContains(response, "прошлый результат: 1 из 1")
        self.assertContains(response, "Перенос слагаемых — 1 из 1")
        self.assertEqual(response.content.decode().count("прошлый результат"), 1)

    def test_other_user_cannot_open_results(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse("learning:quiz_results", args=[self.attempt.pk]))
        self.assertEqual(response.status_code, 404)

    def test_unfinished_attempt_does_not_reveal_the_correct_answer(self):
        self.attempt.is_completed = False
        self.attempt.save(update_fields=["is_completed"])
        self.client.force_login(self.owner)
        response = self.client.get(reverse("learning:quiz_results", args=[self.attempt.pk]))
        self.assertRedirects(response, reverse("learning:quiz_detail", args=[self.attempt.pk]))


class ResultsHistoryTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="StrongPass123")
        self.other = User.objects.create_user(username="other", password="StrongPass123")
        subject = Subject.objects.create(name="Математика", slug="math-history")
        self.topic = Topic.objects.create(subject=subject, name="Линейные уравнения", slug="equations-history")
        self.hidden = Topic.objects.create(subject=subject, name="Чужая тема", slug="hidden-history")
        skill = Skill.objects.create(topic=self.topic, name="Уравнения")
        question = Question.objects.create(skill=skill, text="Сколько будет 2 + 2?")
        wrong = AnswerOption.objects.create(question=question, text="5", is_correct=False)
        now = timezone.now()
        self.newest = self._attempt(self.owner, self.topic, now, wrong, False)
        self.older = self._attempt(self.owner, self.topic, now - timedelta(hours=2), wrong, False)
        self.foreign = self._attempt(self.other, self.hidden, now, wrong, False)
        self.open_attempt = QuizAttempt.objects.create(
            user=self.owner,
            topic=self.topic,
            is_completed=False,
        )

    def _attempt(self, user, topic, completed_at, option, is_correct):
        attempt = QuizAttempt.objects.create(
            user=user,
            topic=topic,
            is_completed=True,
            completed_at=completed_at,
        )
        StudentAnswer.objects.create(
            quiz_attempt=attempt,
            question=option.question,
            answer=option,
            confidence="high",
            is_correct=is_correct,
        )
        return attempt

    def test_history_lists_only_own_completed_attempts_newest_first(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("learning:results"))
        content = response.content.decode()
        newest_url = reverse("learning:quiz_results", args=[self.newest.pk])
        older_url = reverse("learning:quiz_results", args=[self.older.pk])
        self.assertContains(response, "Линейные уравнения")
        self.assertContains(response, "0 из 1 · 0%")
        self.assertContains(response, "Подробнее")
        self.assertLess(content.index(newest_url), content.index(older_url))
        self.assertNotContains(response, "Чужая тема")
        self.assertNotContains(response, reverse("learning:quiz_results", args=[self.foreign.pk]))
        self.assertNotContains(response, reverse("learning:quiz_detail", args=[self.open_attempt.pk]))

    def test_history_pages_ten_attempts(self):
        now = timezone.now()
        oldest = None
        for offset in range(9):
            oldest = self._attempt(
                self.owner,
                self.topic,
                now - timedelta(days=offset + 1),
                self.newest.answers.get().answer,
                False,
            )
        self.client.force_login(self.owner)
        first = self.client.get(reverse("learning:results"))
        second = self.client.get(reverse("learning:results") + "?page=2")
        self.assertEqual(first.content.decode().count("Подробнее"), 10)
        self.assertContains(second, reverse("learning:quiz_results", args=[oldest.pk]) + "?page=2")
        self.assertNotContains(second, reverse("learning:quiz_results", args=[self.newest.pk]))
        self.assertContains(second, "2 из 2")

    def test_results_link_returns_to_the_same_history_page(self):
        self.client.force_login(self.owner)
        response = self.client.get(
            reverse("learning:quiz_results", args=[self.older.pk]) + "?page=2"
        )
        self.assertContains(response, "← К моим результатам")
        self.assertContains(response, reverse("learning:results") + "?page=2")

    def test_empty_history_offers_to_start(self):
        user = User.objects.create_user(username="newcomer", password="StrongPass123")
        self.client.force_login(user)
        response = self.client.get(reverse("learning:results"))
        self.assertContains(response, "Ты ещё не прошёл ни одного теста")
        self.assertContains(response, reverse("learning:start"))
        self.assertContains(response, "Начать обучение")
