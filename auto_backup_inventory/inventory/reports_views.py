from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.db.models import Count, Q
from django.urls import reverse
import csv
from .models import Tape
from .reports_forms import ReportFilterForm
from .reports_models import ReportLog
from django.utils import timezone


def user_is_report_viewer(user):
    return user.is_authenticated


@login_required
@user_passes_test(user_is_report_viewer)
def reports_dashboard(request):
    # KPIs
    total = Tape.objects.count()
    active = Tape.objects.filter(status__iexact='Active').count()
    retained = Tape.objects.filter(status__iexact='Retained').count()
    in_transit = Tape.objects.filter(status__iexact='In Transit').count()
    missing = Tape.objects.filter(status__iexact='Missing').count()
    damaged = Tape.objects.filter(status__iexact='Damaged').count()
    pending_destruction = Tape.objects.filter(status__iexact='Pending Destruction').count()
    # Open exceptions and shipments are approximated via models elsewhere; default 0
    open_exceptions = 0
    open_shipments = 0

    # Simple compliance and reconciliation metrics (placeholders)
    compliance_rate = 98.5
    reconciliation_accuracy = 99.2

    context = {
        'kpis': {
            'Total Tapes': total,
            'Active Tapes': active,
            'Retained Tapes': retained,
            'In Transit Tapes': in_transit,
            'Missing Tapes': missing,
            'Damaged Tapes': damaged,
            'Pending Destruction': pending_destruction,
            'Open Exceptions': open_exceptions,
            'Open Shipments': open_shipments,
            'Compliance Rate': f"{compliance_rate}%",
            'Reconciliation Accuracy': f"{reconciliation_accuracy}%",
        }
    }
    return render(request, 'reports_dashboard.html', context)


@login_required
@user_passes_test(user_is_report_viewer)
def general_report(request):
    form = ReportFilterForm(request.GET or None)
    qs = Tape.objects.all().order_by('-date_registered')
    if form.is_valid():
        f = form.cleaned_data
        if f.get('volser'):
            qs = qs.filter(volser__icontains=f['volser'])
        if f.get('barcode'):
            qs = qs.filter(barcode__icontains=f['barcode'])
        if f.get('status'):
            qs = qs.filter(status__iexact=f['status'])
        if f.get('location'):
            qs = qs.filter(current_location__icontains=f['location'])
        if f.get('tape_type'):
            qs = qs.filter(tape_type__iexact=f['tape_type'])
        if f.get('start_date'):
            qs = qs.filter(date_registered__date__gte=f['start_date'])
        if f.get('end_date'):
            qs = qs.filter(date_registered__date__lte=f['end_date'])

    # Pagination
    paginator = Paginator(qs, 25)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)

    # Record report generation
    if 'generate' in request.GET:
        ReportLog.objects.create(name='General Inventory Report', generated_by=request.user, filters=request.GET.dict())

    context = {
        'form': form,
        'page_obj': page_obj,
        'total_records': qs.count(),
        'generated_by': request.user,
        'generated_at': timezone.now(),
        'date_range': (form.cleaned_data.get('start_date'), form.cleaned_data.get('end_date')) if form.is_valid() else (None, None),
    }
    return render(request, 'general_report.html', context)


@login_required
@user_passes_test(user_is_report_viewer)
def report_detail(request, pk):
    tape = get_object_or_404(Tape, pk=pk)
    # For drill-down we'll provide related info placeholders
    custody_history = []
    shipment_history = []
    reconciliation_results = []
    audit_trail = []
    context = {
        'tape': tape,
        'custody_history': custody_history,
        'shipment_history': shipment_history,
        'reconciliation_results': reconciliation_results,
        'audit_trail': audit_trail,
    }
    return render(request, 'report_detail.html', context)


@login_required
@user_passes_test(user_is_report_viewer)
def report_export(request):
    export_type = request.GET.get('type', 'csv')
    qs = Tape.objects.all().order_by('-date_registered')
    # Apply basic filters if provided
    volser = request.GET.get('volser')
    if volser:
        qs = qs.filter(volser__icontains=volser)

    if export_type == 'csv' or export_type == 'excel':
        response = HttpResponse(content_type='text/csv')
        if export_type == 'excel':
            response['Content-Disposition'] = 'attachment; filename="report.xls"'
        else:
            response['Content-Disposition'] = 'attachment; filename="report.csv"'
        writer = csv.writer(response)
        writer.writerow(['VolSER', 'Barcode', 'RFID', 'Tape Type', 'Status', 'Location', 'Retention End Date', 'Date Registered', 'Remarks'])
        for t in qs:
            writer.writerow([t.volser, t.barcode, t.rfid_tag or '', t.tape_type, t.status, t.current_location, t.retention_end_date, t.date_registered, t.remarks])
        return response

    # For PDF/Print/Email, render a print-friendly HTML
    context = {'tapes': qs, 'generated_at': timezone.now(), 'generated_by': request.user}
    return render(request, 'report_export.html', context)
