from django.contrib import admin

from quiz.models import Question, Quiz, QuizAnswer


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "question_text", "answer_text")
    search_fields = ("question_text",)


@admin.register(QuizAnswer)
class QuizAnswerAdmin(admin.ModelAdmin):
    list_display = ("id", "question", "submitted_answer")
    # Without this the changelist issues one query per row to render the FK.
    list_select_related = ("question",)


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("id", "submitted_by", "evaluated_by", "score", "submitted_at")
    list_filter = ("submitted_at",)
    search_fields = ("submitted_by", "evaluated_by")
    # A ManyToMany rendered as a multi-select widget loads every row in the
    # table; raw_id_fields keeps the change form O(1) in the answer count.
    raw_id_fields = ("question_response",)
