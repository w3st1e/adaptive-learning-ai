from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, F, OuterRef, Q, Subquery
from django.views.decorators.http import require_POST
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from django.http import HttpResponse
from .models import Subject, Topic, QuizAttempt, Question, AttemptQuestion, AnswerOption, StudentAnswer



@login_required
def study(request):
    subjects = Subject.objects.prefetch_related("topics").order_by("name")
    has_topics = Topic.objects.exists()
    open_attempts = {}
    unfinished = QuizAttempt.objects.filter(
        user=request.user,
        is_completed=False,
    ).order_by("-started_at")
    for attempt in unfinished:
        open_attempts.setdefault(attempt.topic_id, attempt)
    return render(
        request,
        "learning/study.html",
        {
            "subjects": subjects,
            "has_topics": has_topics,
            "open_attempts": open_attempts,
        },
    )


@login_required
def results(request):
    attempts = (
        QuizAttempt.objects.filter(user=request.user, is_completed=True)
        .select_related("topic", "topic__subject")
        .annotate(
            correct_count=Count("answers", filter=Q(answers__is_correct=True)),
            total_count=Count("answers"),
        )
        .order_by("-completed_at", "-pk")
    )
    page = Paginator(attempts, 10).get_page(request.GET.get("page"))
    for attempt in page.object_list:
        total = attempt.total_count or 0
        attempt.percent = round(100 * attempt.correct_count / total) if total else 0
    return render(request, "learning/results.html", {"page_obj": page})

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

    assigned = (
        attempt.assigned_questions
        .select_related("question", "question__skill")
        .prefetch_related("question__options")
        .order_by("order")
    )
    try:
        submit_url = reverse("learning:submit_quiz", args=[attempt.pk])
    except NoReverseMatch:
        submit_url = ""

    return render(
        request,
        "learning/quiz_detail.html",
        {
            "attempt": attempt,
            "assigned": assigned,
            "submit_url": submit_url,
            "form_errors": [],
            "question_errors": {},
        },
    )

@login_required
@require_POST
def submit_quiz(request, attempt_id):
    attempt = get_object_or_404(
        QuizAttempt,
        user=request.user,
        pk=attempt_id
    )

    if attempt.is_completed:
        return HttpResponse('Тест уже завершен', status=409)

    assigned_questions = attempt.assigned_questions.select_related('question').order_by('order')

    answers_data = []
    for question in assigned_questions:
        question_id = question.question_id
        answer = request.POST.get(f'answer_{question_id}')
        confidence = request.POST.get(f'confidence_{question_id}')
        answers_data.append(
            {
                'id': question_id,
                'answer': answer,
                'confidence': confidence
            }
        )

    # validation 
    validated_answers = []

    if len(answers_data) != 5:
        return HttpResponse('Invalid quiz', status=400)

    for data in answers_data:
        # Everything answered
        if not all([data['id'], data['answer'], data['confidence']]):
            return HttpResponse('Not all questions were answered', status=400)

        # Confidence selected
        if data['confidence'] not in ('low', 'medium', 'high'):
            return HttpResponse('Invalid data for "Confidence" option', status=400)

        # Answer belongs to right question
        try:
            answer_id = int(data['answer'])
        except (ValueError, TypeError):
            return HttpResponse('Invalid answer ID', status=400)

        if answer_id <= 0:
            return HttpResponse('Invalid answer ID', status=400)

        option = AnswerOption.objects.filter(
            pk=answer_id,
            question__id=data['id']
        ).first()

        if option is None:
            return HttpResponse('Invalid data', status=400)
        validated_answers.append(
            {
                'question_id': data['id'],
                'option': option,
                'confidence': data['confidence']
            }
        )
    with transaction.atomic():
        for data in validated_answers:
            StudentAnswer.objects.create(
                answer=data['option'],
                quiz_attempt=attempt,
                question_id=data['question_id'],
                confidence=data['confidence'],
                is_correct=data['option'].is_correct
            )
        attempt.is_completed = True
        attempt.completed_at = timezone.now()
        attempt.save()

    return redirect("learning:quiz_results", attempt_id=attempt.pk)


CONFIDENCE_LABELS = {
    "high": "Был уверен",
    "medium": "Сомневался",
    "low": "Выбирал наугад",
}


@login_required
def quiz_results(request, attempt_id):
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related("topic", "topic__subject", "user"),
        pk=attempt_id,
        user=request.user,
    )
    if not attempt.is_completed:
        return redirect("learning:quiz_detail", attempt_id=attempt.pk)

    question_order = AttemptQuestion.objects.filter(
        attempt=attempt,
        question_id=OuterRef("question_id"),
    ).values("order")[:1]
    answers = list(
        StudentAnswer.objects.filter(quiz_attempt=attempt)
        .select_related("question", "question__skill", "answer")
        .annotate(question_order=Subquery(question_order))
        .order_by("question_order", "pk")
    )
    correct_options = {
        option.question_id: option
        for option in AnswerOption.objects.filter(
            question_id__in=[answer.question_id for answer in answers],
            is_correct=True,
        ).order_by("order", "pk")
    }
    rows = [
        {
            "order": answer.question_order,
            "question": answer.question,
            "selected": answer.answer,
            "correct": correct_options.get(answer.question_id),
            "is_correct": answer.is_correct,
            "confidence": CONFIDENCE_LABELS.get(answer.confidence, "Не указано"),
            "confidence_level": answer.confidence if answer.confidence in CONFIDENCE_LABELS else "unknown",
        }
        for answer in answers
    ]
    correct_count = sum(row["is_correct"] for row in rows)
    total_count = len(rows)
    percent = round(100 * correct_count / total_count) if total_count else 0
    skills = _skill_summaries(rows)
    numbers = _user_test_numbers(attempt.user_id)
    previous_result = _previous_result(attempt, numbers)
    if len(skills) > 1 and previous_result is not None:
        _attach_previous_skills(skills, previous_result["id"])
    return render(
        request,
        "learning/quiz_results.html",
        {
            "attempt": attempt,
            "test_number": numbers.get(attempt.pk),
            "rows": rows,
            "skills": skills if len(skills) > 1 else [],
            "previous_result": previous_result,
            "correct_count": correct_count,
            "total_count": total_count,
            "percent": percent,
            "history_page": _history_page(request),
        },
    )


def _history_page(request):
    raw = request.GET.get("page", "")
    if raw.isdigit() and int(raw) > 0:
        return int(raw)
    return None


def _skill_summaries(rows):
    summaries = []
    index = {}
    for row in rows:
        skill = row["question"].skill
        item = index.get(skill.pk)
        if item is None:
            item = {"id": skill.pk, "name": skill.name, "correct": 0, "total": 0, "previous": None}
            index[skill.pk] = item
            summaries.append(item)
        item["total"] += 1
        item["correct"] += int(bool(row["is_correct"]))
    return summaries


def _attach_previous_skills(summaries, previous_attempt_id):
    index = {item["id"]: item for item in summaries}
    prior = StudentAnswer.objects.filter(
        quiz_attempt_id=previous_attempt_id,
        question__skill_id__in=index,
    ).select_related("question")
    for answer in prior:
        item = index[answer.question.skill_id]
        bucket = item["previous"]
        if bucket is None:
            bucket = {"correct": 0, "total": 0}
            item["previous"] = bucket
        bucket["total"] += 1
        bucket["correct"] += int(answer.is_correct)


def _user_test_numbers(user_id):
    attempt_ids = (
        QuizAttempt.objects.filter(user_id=user_id, is_completed=True)
        .order_by(F("completed_at").asc(nulls_last=True), "pk")
        .values_list("pk", flat=True)
    )
    return {pk: number for number, pk in enumerate(attempt_ids, start=1)}


def _previous_result(attempt, numbers):
    if attempt.completed_at is None:
        return None
    previous = (
        QuizAttempt.objects.filter(
            user_id=attempt.user_id,
            topic_id=attempt.topic_id,
            is_completed=True,
            completed_at__lt=attempt.completed_at,
        )
        .annotate(
            correct_count=Count("answers", filter=Q(answers__is_correct=True)),
            answer_count=Count("answers"),
        )
        .order_by("-completed_at", "-pk")
        .first()
    )
    if previous is None or not previous.answer_count:
        return None
    return {
        "id": previous.pk,
        "number": numbers.get(previous.pk),
        "correct": previous.correct_count,
        "total": previous.answer_count,
        "percent": round(100 * previous.correct_count / previous.answer_count),
    }






        

