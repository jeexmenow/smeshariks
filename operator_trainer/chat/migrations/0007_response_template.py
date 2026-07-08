from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0006_ai_training_refactor'),
    ]

    operations = [
        migrations.CreateModel(
            name='ResponseTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255, verbose_name='Название')),
                ('category', models.CharField(blank=True, max_length=120, verbose_name='Категория')),
                ('keywords', models.TextField(blank=True, verbose_name='Ключевые слова')),
                ('text', models.TextField(verbose_name='Текст шаблона')),
                ('html', models.TextField(blank=True, verbose_name='HTML шаблон')),
                ('source', models.CharField(blank=True, max_length=255, verbose_name='Источник')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Шаблон ответа',
                'verbose_name_plural': 'Шаблоны ответов',
                'ordering': ['category', 'title'],
            },
        ),
    ]
