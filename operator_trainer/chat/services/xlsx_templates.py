import re
import zipfile
import xml.etree.ElementTree as ET


SPREADSHEET_NS = {'a': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def _column_index(cell_ref: str) -> int:
    letters = ''.join(ch for ch in cell_ref if ch.isalpha())
    index = 0
    for letter in letters:
        index = index * 26 + (ord(letter.upper()) - ord('A') + 1)
    return index - 1


def _clean_text(value: str) -> str:
    value = re.sub(r'\[\{/?b\}\]', '', value or '')
    value = re.sub(r'\[\{url=([^}]+)\}\](.*?)\[\{/url\}\]', r'\2 (\1)', value)
    value = re.sub(r'\s+', ' ', value).strip()
    return value


def read_templates_from_xlsx(path: str) -> list[dict]:
    with zipfile.ZipFile(path) as archive:
        shared_strings = []
        if 'xl/sharedStrings.xml' in archive.namelist():
            root = ET.fromstring(archive.read('xl/sharedStrings.xml'))
            for item in root.findall('a:si', SPREADSHEET_NS):
                shared_strings.append(''.join(text.text or '' for text in item.findall('.//a:t', SPREADSHEET_NS)))

        sheet_name = next(name for name in archive.namelist() if name.startswith('xl/worksheets/sheet'))
        sheet = ET.fromstring(archive.read(sheet_name))

        rows = []
        for row in sheet.findall('.//a:row', SPREADSHEET_NS):
            values = []
            for cell in row.findall('a:c', SPREADSHEET_NS):
                index = _column_index(cell.attrib.get('r', 'A1'))
                while len(values) <= index:
                    values.append('')

                value = cell.find('a:v', SPREADSHEET_NS)
                if value is None:
                    inline = ''.join(text.text or '' for text in cell.findall('.//a:t', SPREADSHEET_NS))
                    values[index] = inline
                elif cell.attrib.get('t') == 's':
                    values[index] = shared_strings[int(value.text)]
                else:
                    values[index] = value.text or ''
            rows.append(values)

    templates = []
    for row in rows[1:]:
        row += [''] * max(0, 6 - len(row))
        title, category, keywords, text, html, _attachments = row[:6]
        title = _clean_text(title)
        text = _clean_text(text)
        if not title or not text:
            continue

        templates.append({
            'title': title,
            'category': _clean_text(category),
            'keywords': _clean_text(keywords),
            'text': text,
            'html': html or '',
        })
    return templates
