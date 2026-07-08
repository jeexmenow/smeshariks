from django.core.management.base import BaseCommand

from chat.models import ResponseTemplate
from chat.services.xlsx_templates import read_templates_from_xlsx


class Command(BaseCommand):
    help = "Import operator response templates from an .xlsx report."

    def add_arguments(self, parser):
        parser.add_argument('path', help='Path to report.xlsx')
        parser.add_argument('--replace', action='store_true', help='Delete existing templates before import')

    def handle(self, *args, **options):
        if options['replace']:
            ResponseTemplate.objects.all().delete()

        imported = 0
        for item in read_templates_from_xlsx(options['path']):
            ResponseTemplate.objects.update_or_create(
                title=item['title'],
                defaults={
                    'category': item['category'],
                    'keywords': item['keywords'],
                    'text': item['text'],
                    'html': item['html'],
                    'source': options['path'],
                },
            )
            imported += 1

        self.stdout.write(self.style.SUCCESS(f"Imported response templates: {imported}"))
