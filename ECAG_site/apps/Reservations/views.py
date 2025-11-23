from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.http import require_POST
from datetime import datetime, timedelta, time as dt_time, date as dt_date

from .models import Table, Reservation


def reservations(request):
    context = {'step_number': 1}
    return render(request, "reservations/reservations.html", context)

def reservations_step2(request):
    # Show reservation details from a pending selection stored in session
    pending = request.session.get('pending_reservation')
    reservation = None
    reservation_obj = None

    # If developer accidentally left the older pending id flow, support it too
    pending_id = request.session.get('pending_reservation_id')
    if pending_id and not pending:
        try:
            reservation_obj = Reservation.objects.select_related('table_id').get(reservation_id=pending_id)
            reservation = {
                'date': reservation_obj.date,
                'time': reservation_obj.time,
                'guests': reservation_obj.guest_count,
                'table_label': f"T{reservation_obj.table_id.table_number} ({reservation_obj.table_id.seats}-Seater)",
                'reservation_id': reservation_obj.reservation_id,
            }
        except Reservation.DoesNotExist:
            reservation = None

    if pending:
        # Build a lightweight reservation context from session (no DB record yet)
        reservation = {
            'date': pending.get('date'),
            'time': pending.get('time'),
            'guests': pending.get('party_size'),
            'table_label': f"T{pending.get('table_number')} ({pending.get('table_seats')}-Seater)",
        }

    # If this is a form POST we treat it as completing the reservation (create DB record)
    if request.method == 'POST' and (pending or reservation_obj):
        # require contact fields
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        special = request.POST.get('special_requests', '').strip()

        missing = []
        if not full_name:
            missing.append('Full name')
        if not phone:
            missing.append('Phone')
        if not email:
            missing.append('Email')

        if missing:
            context = {'step_number': 2, 'reservation': reservation, 'error': 'Please fill in required fields: ' + ', '.join(missing)}
            return render(request, "reservations/reservations_step2.html", context)

        try:
            # If we have a DB object from older flow, update it
            if reservation_obj:
                reservation_obj.full_name = full_name
                reservation_obj.phone = phone
                reservation_obj.email = email
                reservation_obj.special_requests = special
                reservation_obj.status = 'confirmed'
                reservation_obj.save()
                try:
                    del request.session['pending_reservation_id']
                except Exception:
                    pass
                return redirect('reservations:reservations_step3')

            # Otherwise create a new Reservation record from session data
            table_pk = int(pending.get('table_id'))
            table = Table.objects.get(table_id=table_pk)
            req_date = datetime.strptime(pending.get('date'), '%Y-%m-%d').date()
            req_time = datetime.strptime(pending.get('time'), '%H:%M').time()
            party_size = int(pending.get('party_size'))

            res = Reservation.objects.create(
                user_id=request.user,
                table_id=table,
                date=req_date,
                time=req_time,
                guest_count=party_size,
                full_name=full_name,
                phone=phone,
                email=email,
                special_requests=special,
                status='confirmed'
            )

            # clear pending selection from session
            try:
                del request.session['pending_reservation']
            except Exception:
                pass

            # store the confirmed reservation id in session for step3 display
            request.session['confirmed_reservation_id'] = res.reservation_id

            # redirect to confirmation (step3)
            return redirect('reservations:reservations_step3')
        except Exception:
            context = {'step_number': 2, 'reservation': reservation, 'error': 'Unable to confirm reservation. Please try again.'}
            return render(request, "reservations/reservations_step2.html", context)

    context = {'step_number': 2, 'reservation': reservation}
    return render(request, "reservations/reservations_step2.html", context)

def reservations_step3(request):
    # Try to load the confirmed reservation from session
    confirmed_id = request.session.get('confirmed_reservation_id')
    reservation = None
    if confirmed_id:
        try:
            res_obj = Reservation.objects.select_related('table_id').get(reservation_id=confirmed_id)
            reservation = {
                'reservation_id': res_obj.reservation_id,
                'full_name': res_obj.full_name,
                'email': res_obj.email,
                'phone': res_obj.phone,
                'date': res_obj.date,
                'time': res_obj.time,
                'guests': res_obj.guest_count,
                'table_label': f"T{res_obj.table_id.table_number} ({res_obj.table_id.seats}-Seater)",
            }
            # clear it so refresh doesn't accidentally reuse it
            try:
                del request.session['confirmed_reservation_id']
            except Exception:
                pass
        except Reservation.DoesNotExist:
            reservation = None

    context = {'step_number': 3, 'reservation': reservation}
    return render(request, "reservations/reservations_step3.html", context)

def review(request):
    return render(request, 'reservations/review.html')



@require_POST
def available_tables(request):
    """Return JSON list of tables available for the requested date, time and party size.

    Expects POST form values: `date` (YYYY-MM-DD), `time` (HH:MM), `party_size` (int).
    Returns: {available: [{table_id, table_number, seats, x_position, y_position}, ...], error: optional}
    """
    # Accept form-encoded or JSON bodies
    date_str = request.POST.get('date')
    time_str = request.POST.get('time')
    party_size = request.POST.get('party_size')
    if not (date_str and time_str and party_size) and request.content_type == 'application/json':
        import json
        try:
            payload = json.loads(request.body.decode('utf-8') or '{}')
            date_str = date_str or payload.get('date')
            time_str = time_str or payload.get('time')
            party_size = party_size or payload.get('party_size')
        except Exception:
            return HttpResponseBadRequest('Invalid JSON body')

    if not (date_str and time_str and party_size):
        return HttpResponseBadRequest('Missing date, time or party_size')

    try:
        req_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        req_time = datetime.strptime(time_str, '%H:%M').time()
        party_size = int(party_size)
    except Exception:
        return HttpResponseBadRequest('Invalid date/time/party_size format')

    # Disallow past dates
    if req_date < dt_date.today():
        return JsonResponse({'available': [], 'error': 'Please select today or a future date'})

    # Validate restaurant opening hours: 15:00 - 23:00, last booking start at 22:00
    open_time = dt_time(15, 0)
    last_start = dt_time(22, 0)
    if not (open_time <= req_time <= last_start):
        return JsonResponse({'available': [], 'error': 'Restaurant is open 15:00-23:00; last booking start 22:00'})

    # Enforce 15-minute increments
    if req_time.minute % 15 != 0:
        return JsonResponse({'available': [], 'error': 'Please select a time with minutes in 15-minute increments (00,15,30,45)'})

    # Build requested interval
    req_start = datetime.combine(req_date, req_time)
    req_end = req_start + timedelta(hours=2)

    # Map party size to preferred table size: 1-2 -> 2 seats, 3-4 -> 4 seats
    if party_size <= 2:
        seat_required = 2
    else:
        seat_required = 4

    # Candidate tables with the exact matching seat capacity (business requirement)
    candidate_tables = Table.objects.filter(seats=seat_required).order_by('seats', 'table_number')

    available = []
    for table in candidate_tables:
        # fetch reservations for this table on the requested date that could overlap
        existing = Reservation.objects.filter(table_id=table, date=req_date).exclude(status='cancelled')
        conflict = False
        for r in existing:
            r_start = datetime.combine(r.date, r.time)
            r_end = r_start + timedelta(hours=2)
            # overlap if intervals intersect
            if not (req_end <= r_start or req_start >= r_end):
                conflict = True
                break
        if not conflict:
            available.append({
                'table_id': table.table_id,
                'table_number': table.table_number,
                'seats': table.seats,
                'x_position': table.x_position,
                'y_position': table.y_position,
            })

    return JsonResponse({'available': available})


@require_POST
def confirm_reservation(request):
    """Create a reservation for the authenticated user.

    Expects POST: date, time, party_size, table_id
    On success redirects to step2 (POST/Redirect-GET flow) with reservation id in session.
    """
    if not request.user.is_authenticated:
        return HttpResponseForbidden('Authentication required')

    # Accept form-encoded or JSON bodies
    date_str = request.POST.get('date')
    time_str = request.POST.get('time')
    party_size = request.POST.get('party_size')
    table_id = request.POST.get('table_id')
    if request.content_type == 'application/json':
        import json
        try:
            payload = json.loads(request.body.decode('utf-8') or '{}')
            date_str = date_str or payload.get('date')
            time_str = time_str or payload.get('time')
            party_size = party_size or payload.get('party_size')
            table_id = table_id or payload.get('table_id')
        except Exception:
            return HttpResponseBadRequest('Invalid JSON body')

    if not (date_str and time_str and party_size and table_id):
        return HttpResponseBadRequest('Missing fields')

    try:
        req_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        req_time = datetime.strptime(time_str, '%H:%M').time()
        party_size = int(party_size)
        table = Table.objects.get(table_id=int(table_id))
    except Table.DoesNotExist:
        return HttpResponseBadRequest('Invalid table')
    except Exception:
        return HttpResponseBadRequest('Invalid input')

    # Ensure the selected table can seat the requested party size
    if party_size <= 2 and table.seats != 2:
        return HttpResponseBadRequest('Selected table cannot accommodate the party size')
    if party_size >= 3 and table.seats != 4:
        return HttpResponseBadRequest('Selected table cannot accommodate the party size')

    # Validate opening hours as above (restaurant open 15:00-23:00; last start 22:00)
    # Disallow past dates
    if req_date < dt_date.today():
        return HttpResponseBadRequest('Requested date is in the past')

    open_time = dt_time(15, 0)
    last_start = dt_time(22, 0)
    if not (open_time <= req_time <= last_start):
        return HttpResponseBadRequest('Requested time outside opening hours')

    # Enforce 15-minute increments on server-side as well
    if req_time.minute % 15 != 0:
        return HttpResponseBadRequest('Please select minutes in 15-minute increments (00,15,30,45)')

    # Check availability again (race-condition safe-ish: check then create)
    req_start = datetime.combine(req_date, req_time)
    req_end = req_start + timedelta(hours=2)
    existing = Reservation.objects.filter(table_id=table, date=req_date).exclude(status='cancelled')
    for r in existing:
        r_start = datetime.combine(r.date, r.time)
        r_end = r_start + timedelta(hours=2)
        if not (req_end <= r_start or req_start >= r_end):
            return HttpResponseBadRequest('Table not available for requested slot')

    # Do not create a DB reservation yet — store pending selection in session
    request.session['pending_reservation'] = {
        'date': req_date.strftime('%Y-%m-%d'),
        'time': req_time.strftime('%H:%M'),
        'party_size': party_size,
        'table_id': int(table.table_id),
        'table_number': table.table_number,
        'table_seats': table.seats,
    }

    return JsonResponse({'ok': True, 'next': '/reservations/step2/'})