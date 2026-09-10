"""呼出元が渡した上位ページを文書ヘッダーに表示する。"""
from html import escape
from urllib.parse import urlsplit


def validate_breadcrumbs(metadata):
    if not isinstance(metadata, dict) or 'breadcrumbs' not in metadata:
        return []
    items = metadata['breadcrumbs']
    if not isinstance(items, list):
        return ['metadata.breadcrumbs must be an array']
    errors = []
    for index, item in enumerate(items):
        if not isinstance(item, dict) or set(item) != {'label', 'href'}:
            errors.append(f'breadcrumb {index} requires label and href')
            continue
        label, href = item['label'], item['href']
        if not isinstance(label, str) or not label.strip():
            errors.append(f'breadcrumb {index} label must not be empty')
        if not isinstance(href, str) or not href or href != href.strip() or '\\' in href or any(ord(c) < 32 for c in href):
            errors.append(f'breadcrumb {index} href is invalid')
            continue
        try:
            url = urlsplit(href)
        except ValueError:
            errors.append(f'breadcrumb {index} href is invalid')
            continue
        if href.startswith('//') or url.scheme not in {'', 'http', 'https'} or (url.scheme and not url.netloc):
            errors.append(f'breadcrumb {index} href must be a relative or HTTP(S) URL')
    return errors


def render_breadcrumbs(metadata, title, lang='ja'):
    errors = validate_breadcrumbs(metadata)
    if errors:
        raise ValueError('; '.join(errors))
    items = metadata.get('breadcrumbs', [])
    if not items:
        return ''
    parts = []
    separator = '<span class="sep" aria-hidden="true">›</span>'
    for index, item in enumerate(items):
        prefix = separator if index else ''
        parts.append(f'<li>{prefix}<a href="{escape(item["href"], quote=True)}">{escape(item["label"])}</a></li>')
    parts.append(f'<li>{separator}<span aria-current="page">{escape(title)}</span></li>')
    label = 'パンくずリスト' if lang.startswith('ja') else 'Breadcrumb'
    return f'<nav class="doc-breadcrumb" aria-label="{label}"><ol>{"".join(parts)}</ol></nav>'
