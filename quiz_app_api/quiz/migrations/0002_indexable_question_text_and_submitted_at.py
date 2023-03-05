"""Make the question catalogue indexable and timestamp submissions.

- ``question_text`` becomes a CharField so its uniqueness constraint is backed
  by a portable b-tree index (several backends refuse to index unbounded TEXT).
- ``Quiz.submitted_at`` is added and indexed so the newest-first ordering the
  admin uses does not degrade into a filesort as the table grows.
- Text fields gain explicit blank/default rather than relying on Django's
  implicit empty-string fallback.
"""


from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('quiz', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='question',
            options={'ordering': ['id']},
        ),
        migrations.AlterModelOptions(
            name='quiz',
            options={'ordering': ['-submitted_at', '-id'], 'verbose_name_plural': 'quizzes'},
        ),
        migrations.AlterModelOptions(
            name='quizanswer',
            options={'ordering': ['id']},
        ),
        migrations.AddField(
            model_name='quiz',
            name='submitted_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='question',
            name='answer_text',
            field=models.TextField(blank=True, default='', max_length=800),
        ),
        migrations.AlterField(
            model_name='question',
            name='question_text',
            field=models.CharField(max_length=500, unique=True),
        ),
        migrations.AlterField(
            model_name='quiz',
            name='evaluated_by',
            field=models.CharField(blank=True, default='', max_length=150),
        ),
        migrations.AlterField(
            model_name='quiz',
            name='question_response',
            field=models.ManyToManyField(blank=True, related_name='quizzes', to='quiz.quizanswer'),
        ),
        migrations.AlterField(
            model_name='quiz',
            name='score',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='quiz',
            name='submitted_by',
            field=models.CharField(blank=True, default='', max_length=150),
        ),
        migrations.AlterField(
            model_name='quizanswer',
            name='question',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='answers', to='quiz.question'),
        ),
        migrations.AlterField(
            model_name='quizanswer',
            name='submitted_answer',
            field=models.TextField(blank=True, default='', max_length=800),
        ),
    ]
