from django.contrib import admin

from .models import (
    AnswerOption,
    Question,
    QuizAttempt,
    Skill,
    StudentAnswer,
    Subject,
    Topic,
)

admin.site.site_header = "Адаптивное обучение"
admin.site.site_title = "Адаптивное обучение"
admin.site.index_title = "Содержание"


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("name", "subject", "slug")
    list_filter = ("subject",)
    search_fields = ("name", "slug", "subject__name")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("subject",)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "topic", "order")
    list_filter = ("topic__subject", "topic")
    search_fields = ("name", "topic__name")
    autocomplete_fields = ("topic",)


class AnswerOptionInline(admin.TabularInline):
    model = AnswerOption
    extra = 4
    fields = ("order", "text", "is_correct")
    ordering = ("order",)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("short_text", "skill", "difficulty", "created_at")
    list_filter = ("difficulty", "skill__topic__subject", "skill__topic")
    search_fields = ("text", "skill__name")
    autocomplete_fields = ("skill",)
    inlines = (AnswerOptionInline,)

    @admin.display(description="Текст")
    def short_text(self, obj):
        return obj.text[:80]


@admin.register(AnswerOption)
class AnswerOptionAdmin(admin.ModelAdmin):
    list_display = ("text", "question", "is_correct", "order")
    list_filter = ("is_correct",)
    search_fields = ("text", "question__text")
    autocomplete_fields = ("question",)


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "topic", "mode", "is_completed", "started_at")
    list_filter = ("mode", "is_completed", "topic")
    search_fields = ("user__username", "topic__name")
    autocomplete_fields = ("user", "topic")
    date_hierarchy = "started_at"


@admin.register(StudentAnswer)
class StudentAnswerAdmin(admin.ModelAdmin):
    list_display = ("quiz_attempt", "question", "is_correct", "confidence", "answered_at")
    list_filter = ("is_correct", "confidence")
    search_fields = ("quiz_attempt__user__username", "question__text")
    autocomplete_fields = ("quiz_attempt", "question", "answer")
