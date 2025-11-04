from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.contrib import messages
from django.conf import settings
from django.utils import timezone

from .decorators import require_billing_role
from .models import SuscripcionEmpresa, EstadoSub, CicloFact, MercadoPagoEvent
from .services.mercadopago import (
    create_plan_and_get_initpoint,
    create_preapproval,                # opcional si lo usas en alguna prueba
    get_preapproval,
    search_preapprovals_by_plan,
    search_preapprovals_all,
)


@login_required
@require_billing_role
def billing_overview(request):
    sub, _ = SuscripcionEmpresa.objects.get_or_create(empresa=request.user.empresa)
    return render(request, "core/billing/overview.html", {"sub": sub})


@login_required
@require_billing_role
def billing_checkout(request):
    """
    Flujo estable: crear un PLAN y redirigir al init_point del plan.
    Mercado Pago pedirá la tarjeta y creará la suscripción (preapproval) automáticamente.
    """
    sub = get_object_or_404(SuscripcionEmpresa, empresa=request.user.empresa)

    if request.method == "POST":
        # 1) Ciclo y monto
        ciclo = (request.POST.get("ciclo") or sub.ciclo or CicloFact.MENSUAL).upper()
        if ciclo not in (CicloFact.MENSUAL, CicloFact.ANUAL):
            ciclo = CicloFact.MENSUAL
        if sub.ciclo != ciclo:
            sub.ciclo = ciclo
            sub.save(update_fields=["ciclo"])

        amount = sub.amount_for_cycle(ciclo)  # CLP => entero
        reason = f"Trackify {sub.plan} ({ciclo}) - {request.user.empresa.nombre}"

        # 2) Crear plan y tomar su init_point
        plan = create_plan_and_get_initpoint(
            amount=amount,
            currency=sub.currency,                     # "CLP"
            cycle=ciclo,                               # "MENSUAL" | "ANUAL"
            reason=reason,
            back_url=settings.MERCADOPAGO_SUCCESS_URL  # HTTPS público (ngrok/domino)
        )
        status = plan.get("status")
        resp   = plan.get("response", {}) or {}

        # Logs
        try:
            from pprint import pformat
            print("PLAN_STATUS:", status)
            print("PLAN_RESPONSE:", pformat(resp))
        except Exception:
            pass

        if status in (200, 201):
            init_point = resp.get("init_point")
            plan_id    = resp.get("id")
            # guarda el plan para facilitar los refresh
            if plan_id:
                if not hasattr(sub, "mp_plan_id"):
                    # si tu modelo aún no tiene este campo, omite esto
                    pass
                else:
                    setattr(sub, "mp_plan_id", plan_id)
                    try:
                        sub.save(update_fields=["mp_plan_id"])
                    except Exception:
                        sub.mp_plan_id = plan_id
                        sub.save()

            if init_point:
                # marca estado local como "en proceso" hasta webhook o refresh
                sub.estado = EstadoSub.PAUSADA
                sub.save(update_fields=["estado"])
                return redirect(init_point)

            messages.error(request, "Plan creado pero sin init_point en la respuesta.")
            return redirect("billing_checkout")

        # Error creando plan
        messages.error(request, f"Error al crear plan: {resp.get('message') or resp}")
        return redirect("billing_checkout")

    # GET
    return render(request, "core/billing/checkout.html", {"sub": sub})


@login_required
def billing_success(request):
    # redirige al overview (puedes cambiarlo a "home" si prefieres)
    messages.success(request, "Si el pago fue autorizado, activaremos tu suscripción en minutos.")
    return redirect("billing_overview")


@login_required
def billing_failure(request):
    messages.error(request, "El pago no se completó. Intenta nuevamente.")
    return redirect("billing_checkout")


@login_required
def billing_pending(request):
    messages.info(request, "Tu pago quedó pendiente. Te avisaremos cuando se confirme.")
    return redirect("billing_overview")


@login_required
@require_billing_role
def billing_refresh(request):
    from django.utils.dateparse import parse_datetime
    from .services.mercadopago import get_preapproval, search_preapprovals_by_plan, search_preapprovals_all

    sub = SuscripcionEmpresa.objects.select_related("empresa").get(empresa=request.user.empresa)

    # --- helpers ---
    def norm(s: str) -> str:
        s = (s or "").strip().lower()
        # colapsa espacios y elimina puntos tipo "S.A."
        s = " ".join(s.replace(".", " ").split())
        return s

    expected_reason = f"Trackify {sub.plan} ({sub.ciclo}) - {sub.empresa.nombre}"
    expected_reason_n = norm(expected_reason)

    def _apply_state_from_resp(resp):
        status = (resp.get("status") or "").lower()
        next_bill = (resp.get("auto_recurring") or {}).get("next_payment_date")
        payer_email = resp.get("payer_email")

        if status == "authorized":
            sub.estado = EstadoSub.ACTIVA
            sub.started_at = sub.started_at or timezone.now()
            sub.next_billing_at = parse_datetime(next_bill) if next_bill else None
        elif status == "paused":
            sub.estado = EstadoSub.PAUSADA
        elif status in {"cancelled", "cancelled_by_user", "cancelled_by_collector"}:
            sub.estado = EstadoSub.CANCELADA
            sub.canceled_at = timezone.now()
        else:
            sub.estado = EstadoSub.ERROR

        if payer_email and not sub.mp_payer_email:
            sub.mp_payer_email = payer_email

    def _sort_key_date(item):
        return item.get("date_created") or ""

    def _best_by_reason(items):
        # filtra por reason normalizado
        same_reason = [x for x in items if norm(x.get("reason")) == expected_reason_n]
        if not same_reason:
            return None
        authorized = [x for x in same_reason if (x.get("status") or "").lower() == "authorized"]
        if authorized:
            return max(authorized, key=_sort_key_date)
        not_cancelled = [x for x in same_reason if (x.get("status") or "").lower() not in
                         {"cancelled", "cancelled_by_user", "cancelled_by_collector"}]
        if not_cancelled:
            return max(not_cancelled, key=_sort_key_date)
        return max(same_reason, key=_sort_key_date)

    # 1) Intento directo con id guardado
    if sub.mp_preapproval_id:
        info = get_preapproval(sub.mp_preapproval_id)
        st = info.get("status")
        resp = info.get("response") or {}
        if st == 200 and (resp.get("status") or "").lower() == "authorized":
            _apply_state_from_resp(resp)
            sub.save()
            messages.success(request, "Estado sincronizado (id guardado).")
            return redirect("billing_overview")
        # limpia id inválido por callerId y sigue
        if st == 400 and "callerId" in str(resp):
            sub.mp_preapproval_id = None
            sub.save(update_fields=["mp_preapproval_id"])

    # 2) Buscar por mp_plan_id si existe
    if sub.mp_plan_id:
        res = search_preapprovals_by_plan(sub.mp_plan_id, limit=50)
        items = (res.get("response") or {}).get("results") or []

        best = _best_by_reason(items)
        if not best and items:
            # fallback: la más reciente authorized de este plan
            auth = [x for x in items if (x.get("status") or "").lower() == "authorized"]
            if auth:
                best = max(auth, key=_sort_key_date)

        if best:
            pre_id = best.get("id")
            info2 = get_preapproval(pre_id)
            if info2.get("status") == 200:
                _apply_state_from_resp(info2.get("response") or {})
                sub.mp_preapproval_id = pre_id
                sub.save()
                messages.success(request, "Estado sincronizado (por plan).")
                return redirect("billing_overview")

    # 3) Fallback global: listar todo y emparejar por reason
    res = search_preapprovals_all(limit=100, offset=0)
    items = (res.get("response") or {}).get("results") or []
    best = _best_by_reason(items)
    if not best and items:
        auth = [x for x in items if (x.get("status") or "").lower() == "authorized"]
        if auth:
            best = max(auth, key=_sort_key_date)

    if best:
        pre_id = best.get("id")
        info3 = get_preapproval(pre_id)
        if info3.get("status") == 200:
            _apply_state_from_resp(info3.get("response") or {})
            sub.mp_preapproval_id = pre_id
            sub.save()
            messages.success(request, "Estado sincronizado (fallback).")
            return redirect("billing_overview")

    messages.error(request, "No pude sincronizar una suscripción ‘authorized’ para esta empresa.")
    return redirect("billing_overview")



@csrf_exempt
def mercadopago_webhook(request):
    """
    Recibe notificaciones de MP, guarda el evento y actualiza estado.
    """
    try:
        payload = request.body.decode("utf-8") or "{}"
    except Exception:
        payload = "{}"

    tipo = request.GET.get("type") or request.GET.get("topic") or "unknown"
    preapproval_id = None

    try:
        import json
        data = json.loads(payload)
    except Exception:
        data = {}

    preapproval_id = (data.get("data") or {}).get("id") or data.get("id") or request.GET.get("id")

    try:
        MercadoPagoEvent.objects.create(tipo=tipo, data=data, related_preapproval=preapproval_id)
    except Exception:
        pass

    if preapproval_id:
        try:
            info = get_preapproval(preapproval_id)
            resp = info.get("response", {}) or {}
            status = resp.get("status")
            next_bill = (resp.get("auto_recurring") or {}).get("next_payment_date")
            payer_email = resp.get("payer_email")

            sub = SuscripcionEmpresa.objects.filter(mp_preapproval_id=preapproval_id).select_related("empresa").first()
            if not sub and payer_email:
                sub = SuscripcionEmpresa.objects.filter(mp_payer_email=payer_email).select_related("empresa").first()

            if sub:
                from django.utils.dateparse import parse_datetime
                if status == "authorized":
                    sub.estado = EstadoSub.ACTIVA
                    sub.started_at = sub.started_at or timezone.now()
                    sub.next_billing_at = parse_datetime(next_bill) if next_bill else None
                elif status == "paused":
                    sub.estado = EstadoSub.PAUSADA
                elif status in ("cancelled", "cancelled_by_user", "cancelled_by_collector"):
                    sub.estado = EstadoSub.CANCELADA
                    sub.canceled_at = timezone.now()
                else:
                    sub.estado = EstadoSub.ERROR

                if payer_email and not sub.mp_payer_email:
                    sub.mp_payer_email = payer_email
                if not sub.mp_preapproval_id:
                    sub.mp_preapproval_id = preapproval_id

                sub.save()
        except Exception:
            pass

    return HttpResponse(status=200)

