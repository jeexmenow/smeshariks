from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0005_dialogstep'),
    ]

    operations = [
        migrations.CreateModel(
            name='Scenario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=180, verbose_name='Название кейса')),
                ('client_name', models.CharField(default='Клиент', max_length=120, verbose_name='Имя клиента')),
                ('client_status', models.CharField(default='online', max_length=120, verbose_name='Статус клиента')),
                ('client_avatar', models.URLField(blank=True, verbose_name='Аватар клиента')),
                ('situation', models.TextField(blank=True, verbose_name='Ситуация клиента')),
                ('goal', models.TextField(blank=True, verbose_name='Цель оператора')),
                ('initial_message', models.TextField(verbose_name='Первое сообщение клиента')),
                ('hints', models.TextField(blank=True, help_text='Каждая подсказка с новой строки', verbose_name='Подсказки')),
                ('knowledge_base_url', models.URLField(blank=True, verbose_name='Ссылка на базу знаний')),
                ('difficulty', models.CharField(choices=[('easy', 'Легкий'), ('medium', 'Средний'), ('hard', 'Сложный')], default='medium', max_length=20, verbose_name='Сложность')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активен')),
                ('stop_words', models.CharField(blank=True, help_text='Через запятую', max_length=255, verbose_name='Стоп-слова')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Сценарий',
                'verbose_name_plural': 'Сценарии',
                'ordering': ['title'],
            },
        ),
        migrations.CreateModel(
            name='ScenarioStep',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('step_number', models.PositiveIntegerField(verbose_name='Номер шага')),
                ('client_message', models.TextField(verbose_name='Ответ клиента')),
                ('expected_operator_response', models.TextField(blank=True, verbose_name='Ожидаемое действие оператора')),
                ('evaluation_criteria', models.TextField(blank=True, help_text='Каждый критерий с новой строки: приветствие, уточнение проблемы, решение', verbose_name='Критерии оценки')),
                ('keywords', models.TextField(blank=True, help_text='Через запятую', verbose_name='Ключевые слова')),
                ('hint', models.TextField(blank=True, verbose_name='Подсказка к шагу')),
                ('is_final', models.BooleanField(default=False, verbose_name='Финальный шаг')),
                ('scenario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='steps', to='chat.scenario')),
            ],
            options={
                'verbose_name': 'Шаг сценария',
                'verbose_name_plural': 'Шаги сценария',
                'ordering': ['step_number'],
                'unique_together': {('scenario', 'step_number')},
            },
        ),
        migrations.AddField(
            model_name='dialog',
            name='ai_mode',
            field=models.CharField(default='scenario', help_text='Зарезервировано для будущей AI-интеграции', max_length=40),
        ),
        migrations.AddField(
            model_name='dialog',
            name='client_name',
            field=models.CharField(default='Клиент', max_length=120),
        ),
        migrations.AddField(
            model_name='dialog',
            name='scenario',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='dialogs', to='chat.scenario'),
        ),
        migrations.AddField(
            model_name='dialog',
            name='score',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='dialog',
            name='status',
            field=models.CharField(choices=[('active', 'Активен'), ('completed', 'Завершен'), ('closed', 'Закрыт')], default='active', max_length=20),
        ),
        migrations.AddField(
            model_name='message',
            name='metadata',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='message',
            name='role',
            field=models.CharField(choices=[('client', 'Клиент'), ('operator', 'Оператор'), ('system', 'Система'), ('ai', 'AI-клиент')], default='client', max_length=20),
        ),
        migrations.AddField(
            model_name='message',
            name='score',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='userresponse',
            name='dialog',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='chat.dialog', verbose_name='Диалог'),
        ),
        migrations.AddField(
            model_name='userresponse',
            name='scenario',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='chat.scenario', verbose_name='Сценарий'),
        ),
        migrations.CreateModel(
            name='Evaluation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('score', models.PositiveIntegerField(default=0, verbose_name='Оценка')),
                ('max_score', models.PositiveIntegerField(default=100, verbose_name='Максимум')),
                ('matched_keywords', models.JSONField(blank=True, default=list, verbose_name='Найденные критерии')),
                ('missed_keywords', models.JSONField(blank=True, default=list, verbose_name='Пропущенные критерии')),
                ('feedback', models.TextField(blank=True, verbose_name='Обратная связь')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('dialog', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='evaluations', to='chat.dialog')),
                ('message', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='evaluation', to='chat.message')),
                ('scenario_step', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='chat.scenariostep')),
            ],
            options={
                'verbose_name': 'Оценка ответа',
                'verbose_name_plural': 'Оценки ответов',
                'ordering': ['-created_at'],
            },
        ),
    ]
