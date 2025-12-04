# core/templatetags/form_tags.py
from django import template
from django.utils.safestring import mark_safe
import re

register = template.Library()

def _render_with_attrs(bound_or_html, extra_attrs: dict, merge_class: str | None = None):
    """
    Si recibe un BoundField, re-renderiza con attrs.
    Si recibe HTML (SafeString/str), inyecta attrs al primer tag <input|select|textarea>.
    merge_class: si viene, se mergea con la clase existente.
    """
    # Caso 1: BoundField (tiene .field)
    if hasattr(bound_or_html, "field"):
        attrs = bound_or_html.field.widget.attrs.copy()

        # merge de class
        if merge_class:
            current = attrs.get("class", "")
            if current:
                # agrega evitando duplicados simples
                new = current.split()
                for c in merge_class.split():
                    if c not in new:
                        new.append(c)
                attrs["class"] = " ".join(new)
            else:
                attrs["class"] = merge_class

        # otros attrs
        for k, v in extra_attrs.items():
            if k == "class":
                # también mergea si llega class desde extra_attrs
                current = attrs.get("class", "")
                if current:
                    acc = current.split()
                    for c in v.split():
                        if c not in acc:
                            acc.append(c)
                    attrs["class"] = " ".join(acc)
                else:
                    attrs["class"] = v
            else:
                attrs[k] = v

        return bound_or_html.as_widget(attrs=attrs)

    # Caso 2: ya es HTML; inyectar en el primer tag de formulario
    html = str(bound_or_html)

    # Si hay que mergear class, incorpóralo a extra_attrs
    if merge_class:
        if "class" in extra_attrs and extra_attrs["class"]:
            extra_attrs["class"] = extra_attrs["class"] + " " + merge_class
        else:
            extra_attrs["class"] = merge_class

    def repl(match):
        tag_open = match.group(0)

        # merge/append de class si ya existe
        if 'class="' in tag_open or "class='" in tag_open:
            # añade clases nuevas al atributo class existente
            def repl_class(m2):
                quote = m2.group(1)
                existing = m2.group(2)
                add = extra_attrs.pop("class", "")
                if add:
                    exist_set = existing.split()
                    for c in add.split():
                        if c not in exist_set:
                            exist_set.append(c)
                    merged = " ".join(exist_set)
                    return f'class={quote}{merged}{quote}'
                return m2.group(0)

            tag_open = re.sub(r'class=(["\'])(.*?)\1', repl_class, tag_open, count=1)
        elif "class" in extra_attrs:
            # no existe class: agrégalo
            cls = extra_attrs.pop("class", "")
            if cls:
                tag_open = tag_open[:-1] + f' class="{cls}">'

        # agrega el resto de attrs
        for k, v in list(extra_attrs.items()):
            if v == "":
                tag_open = tag_open[:-1] + f" {k}>"
            else:
                tag_open = tag_open[:-1] + f' {k}="{v}">'

        return tag_open

    # Solo el primer tag input/select/textarea
    html = re.sub(r'^<(input|select|textarea)\b[^>]*>', repl, html, count=1, flags=re.IGNORECASE)
    return mark_safe(html)

@register.filter(name="addclass")
def addclass(field, css):
    """
    Añade clases CSS al widget. Funciona con BoundField o HTML ya renderizado.
    Uso: {{ form.campo|addclass:"form-control is-invalid" }}
    """
    return _render_with_attrs(field, extra_attrs={}, merge_class=css)

@register.filter(name="attr")
def attr(field, arg):
    """
    Asigna un atributo al widget. Soporta "clave=valor" o solo "clave" (boolean-like).
    Uso: {{ form.email|attr:"autocomplete=email" }}
         {{ form.empresa_nombre|attr:"autofocus" }}
    """
    if "=" in arg:
        k, v = arg.split("=", 1)
        return _render_with_attrs(field, {k.strip(): v.strip()})
    else:
        return _render_with_attrs(field, {arg.strip(): ""})
