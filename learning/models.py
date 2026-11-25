from django.db import models
from django.conf import settings

# Create your models here.


class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    class Meta:
        ordering = ['name']

class Topic(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=150)
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="topics"
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
            fields=['subject', 'slug'],
            name='unique_topic_slug_per_subject'
        )
]


class Skill(models.Model):
    name = models.CharField(max_length=150)
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name="skills"
    )
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name
    class Meta:
        ordering = ['order', 'name']


class Question(models.Model):
    skill = models.ForeignKey(
        Skill,
        on_delete = models.PROTECT,
        related_name="questions"
    )
    text = models.TextField()
    difficulty = models.PositiveSmallIntegerField(choices=[
        (1, 'Level 1'),
        (2, 'Level 2'),
        (3, 'Level 3'),
        (4, 'Level 4'),
        (5, 'Level 5')
    ], 
    default=1)
    explanation = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.text[:50]

class AnswerOption(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="options"
    )
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.text
    class Meta:
        ordering = ['order']

class QuizAttempt(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quiz_attempts"
    )
    topic = models.ForeignKey(
        Topic,
        on_delete=models.PROTECT,
        related_name="quiz_attempts"
    )
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(default=None, blank=True, null=True)
    is_completed = models.BooleanField(default=False)
    mode = models.CharField(choices=[('basic', 'Basic'), ('confidence', 'Confidence')], max_length=10, default='confidence')

    def __str__(self):
        return f'Attempt #{self.pk} by {self.user.get_username()}'

class StudentAnswer(models.Model):
    answer = models.ForeignKey(
        AnswerOption,
        on_delete=models.PROTECT,
        related_name="student_answers"
    )
    quiz_attempt = models.ForeignKey(
        QuizAttempt,
        on_delete=models.CASCADE,
        related_name="answers"
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.PROTECT,
        related_name="student_answers"
    )
    confidence = models.CharField(choices=[('low', 'Low'), ('medium', "Medium"), ('high', 'High')], max_length=10, null=True, blank=True)
    is_correct = models.BooleanField(default=False)
    answered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attempt #{self.quiz_attempt_id} | Question #{self.question_id} | {'Correct' if self.is_correct else 'Incorrect'}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['quiz_attempt', 'question'],
                name='unique_question_per_attempt'
            )
        ]


class AttemptQuestion(models.Model):
    attempt = models.ForeignKey(
        QuizAttempt,
        on_delete=models.CASCADE,
        related_name='assigned_questions'
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.PROTECT
    )
    order = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['attempt', 'question'],
                name='unique_assigned_question'
            ),
            models.UniqueConstraint(
                fields=['attempt', 'order'],
                name='unique_question_order_per_attempt'
            )
        ]

