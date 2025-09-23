# core/utils_pdf.py
import os
from io import BytesIO
from urllib.parse import urlparse
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.contrib.staticfiles import finders  # 👈 clave

def link_callback(uri, rel):
    """
    Convierte /static/... y /media/... en paths absolutos que xhtml2pdf pueda abrir.
    Funciona en dev (STATICFILES_DIRS) y en prod (STATIC_ROOT).
    """
    parsed = urlparse(uri)
    if parsed.scheme in ('http', 'https'):
        # Idealmente evita http(s) en xhtml2pdf; si necesitas, deja tal cual.
        return uri

    # Static
    static_url = getattr(settings, "STATIC_URL", "/static/")
    if uri.startswith(static_url):
        path = uri.replace(static_url, "", 1)

        # 1) Busca con staticfiles finders (dev/prod)
        absolute_path = finders.find(path)
        if absolute_path:
            return absolute_path

        # 2) Fallback a STATIC_ROOT si existe
        static_root = getattr(settings, "STATIC_ROOT", None)
        if static_root:
            candidate = os.path.join(static_root, path)
            if os.path.isfile(candidate):
                return candidate

        # 3) Fallback a STATICFILES_DIRS en dev
        for d in getattr(settings, "STATICFILES_DIRS", []):
            candidate = os.path.join(d, path)
            if os.path.isfile(candidate):
                return candidate

    # Media
    media_url = getattr(settings, "MEDIA_URL", "/media/")
    if uri.startswith(media_url):
        path = uri.replace(media_url, "", 1)
        media_root = getattr(settings, "MEDIA_ROOT", None)
        if media_root:
            candidate = os.path.join(media_root, path)
            if os.path.isfile(candidate):
                return candidate

    # Último recurso: si ya es ruta absoluta válida, úsala
    if os.path.isabs(uri) and os.path.isfile(uri):
        return uri

    return uri  # puede fallar, pero no explota con join(None, ...)
    

def render_to_pdf(template_src, context_dict=None, filename="reporte.pdf"):
    context_dict = context_dict or {}
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.CreatePDF(
        src=BytesIO(html.encode("utf-8")),
        dest=result,
        encoding='utf-8',
        link_callback=link_callback,  # 👈 importante
    )
    if not pdf.err:
        resp = HttpResponse(result.getvalue(), content_type='application/pdf')
        resp['Content-Disposition'] = f'attachment; filename="{filename}"'
        return resp
    return HttpResponse("Error generando el PDF", status=500)
