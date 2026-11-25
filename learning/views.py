from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.views.decorators.http import require_POST
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.http import HttpResponse
from .models import Subject, Topic, QuizAttempt, Question, AttemptQuestion



@login_required
def study(request):
    subjects = Subject.objects.prefetch_related("topics").order_by("name")
    has_topics = Topic.objects.exists()
    return render(
        request,
        "learning/study.html",
        {"subjects": subjects, "has_topics": has_topics},
    )


@login_required
def results(request):
    return render(request, "learning/results.html")

@login_required
@require_POST
def start_quiz(request, topic_id):
    topic = get_object_or_404(Topic, pk=topic_id)

    questions = list(
    Question.objects.filter(
        skill__topic=topic,
        difficulty=1
    ).order_by('?')[:5]
)

    if len(questions) < 5:
        return HttpResponse('Недостаточно вопросов в теме')
    else:
        with transaction.atomic():
            new_quiz = QuizAttempt.objects.create(
                user=request.user,
                topic=topic,
                mode='confidence'
            )
            for order, question in enumerate(questions, start=1):
                AttemptQuestion.objects.create(
                    attempt=new_quiz,
                    question=question,
                    order=order
                )

            return redirect('learning:quiz_detail', attempt_id=new_quiz.pk)

@login_required
def quiz_detail(request, attempt_id):
    attempt = get_object_or_404(
        QuizAttempt,
        pk=attempt_id,
        user=request.user
    )

    assigned = attempt.assigned_questions.all().order_by('order').select_related('question')

    question_texts = [
        item.question.text for item in assigned
    ]

    return HttpResponse('\n'.join(question_texts))
