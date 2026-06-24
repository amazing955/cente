from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import Group
from django.conf import settings
from django.core.mail import EmailMessage, send_mail
from django.core.paginator import Paginator
from django.template.loader import render_to_string
import csv
import json
import uuid
from io import BytesIO, StringIO
from datetime import date, datetime
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date

from .forms import *
from .models import *


def is_valid_uuid(value):
    if not value:
        return False
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def get_object_by_uuid_pk(model, pk_value):
    if not is_valid_uuid(pk_value):
        return None
    return model.objects.filter(pk=pk_value).first()


def is_courier(user):
    return user.is_authenticated and (
        user.is_superuser or
        user.groups.filter(name='Courier').exists() or
        getattr(user, 'courier_profile', None) is not None
    )


def get_courier_profile(user):
    return getattr(user, 'courier_profile', None)

ADMIN_FEATURE_TABS = [
    {
        'tab_id': 'overview',
        'label': 'Overview',
        'feature_keys': [
            'Inventory Overview',
            'View Tape Records',
            'Add Tape',
            'Edit Tape Details',
            'Scan Barcode/RFID',
            'Update Tape Location',
            'Mark Tape as Damaged',
            'Initiate Shipment Requests',
            'Perform Reconciliation',
            'View Inventory Reports',
            'View Audit History',
        ],
    },
    {
        'tab_id': 'users',
        'label': 'Users',
        'feature_keys': ['User Management'],
    },
    {
        'tab_id': 'roles',
        'label': 'Roles',
        'feature_keys': ['Security Controls', 'User Management'],
    },
    {
        'tab_id': 'inventory',
        'label': 'Tape Inventory',
        'feature_keys': [
            'Tape Management',
            'View Tape Records',
            'Add Tape',
            'Edit Tape Details',
            'Scan Barcode/RFID',
            'Update Tape Location',
            'Mark Tape as Damaged',
        ],
    },
    {
        'tab_id': 'shipments',
        'label': 'Shipments',
        'feature_keys': [
            'Shipment Tracking',
            'Initiate Shipment Requests',
            'Perform Reconciliation',
        ],
    },
    {
        'tab_id': 'reports',
        'label': 'Reports',
        'feature_keys': ['Reporting', 'View Inventory Reports'],
    },
    {
        'tab_id': 'audit',
        'label': 'Audit Logs',
        'feature_keys': ['Audit Logging', 'View Audit History'],
    },
    {
        'tab_id': 'approvals',
        'label': 'Approvals',
        'feature_keys': ['Approvals', 'User Management', 'Security Controls'],
    },
]

BACKUP_FEATURE_TABS = [
    {
        'tab_id': 'overview',
        'label': 'Overview',
        'feature_keys': [
            'Inventory Overview',
            'View Tape Records',
            'Add Tape',
            'Edit Tape Details',
            'Scan Barcode/RFID',
            'Update Tape Location',
            'Mark Tape as Damaged',
            'Initiate Shipment Requests',
            'Perform Reconciliation',
            'View Inventory Reports',
            'View Audit History',
        ],
    },
    {
        'tab_id': 'inventory',
        'label': 'Inventory',
        'feature_keys': [
            'Tape Management',
            'View Tape Records',
            'Add Tape',
            'Edit Tape Details',
            'Scan Barcode/RFID',
            'Update Tape Location',
            'Mark Tape as Damaged',
        ],
    },
    {
        'tab_id': 'shipments',
        'label': 'Shipments',
        'feature_keys': [
            'Shipment Tracking',
            'Initiate Shipment Requests',
            'Perform Reconciliation',
        ],
    },
    {
        'tab_id': 'audit',
        'label': 'Audit Logs',
        'feature_keys': ['Audit Logging', 'View Audit History'],
    },
    {
        'tab_id': 'approvals',
        'label': 'Approvals',
        'feature_keys': ['Approvals', 'User Management', 'Security Controls'],
    },
]

OPERATIONS_FEATURE_TABS = [
    {
        'tab_id': 'dashboard',
        'label': 'Dashboard',
    },
    {
        'tab_id': 'shipment_approvals',
        'label': 'Shipment Approvals',
    },
    {
        'tab_id': 'shipment_monitoring',
        'label': 'Shipment Monitoring',
    },
    {
        'tab_id': 'exception_management',
        'label': 'Exception Management',
    },
    {
        'tab_id': 'custody_governance',
        'label': 'Custody Governance',
    },
    {
        'tab_id': 'reconciliation_review',
        'label': 'Reconciliation Review',
    },
    {
        'tab_id': 'compliance_monitoring',
        'label': 'Compliance Monitoring',
    },
    {
        'tab_id': 'reports',
        'label': 'Reports',
    },
    {
        'tab_id': 'analytics',
        'label': 'Analytics',
    },
    {
        'tab_id': 'notifications',
        'label': 'Notifications',
    },
    {
        'tab_id': 'settings',
        'label': 'Settings',
    },
]


def unique_features(features):
    seen = set()
    ordered = []
    for feature in features:
        if feature not in seen:
            seen.add(feature)
            ordered.append(feature)
    return ordered


def get_dashboard_tabs(user, feature_tabs, preserve_empty_tabs=False):
    normalized_tabs = []
    user_features = getattr(user, 'feature_names', [])
    for tab in feature_tabs:
        normalized_tab = tab.copy()
        feature_keys = unique_features(tab.get('feature_keys', []))
        if not user.is_superuser:
            feature_keys = [feature for feature in feature_keys if feature in user_features]
        normalized_tab['feature_keys'] = feature_keys
        if user.is_superuser or preserve_empty_tabs or feature_keys:
            normalized_tabs.append(normalized_tab)
    return normalized_tabs


def get_last_six_month_counts(tapes_queryset):
    today = timezone.localdate()

    def month_start(base_date, offset_months):
        year = base_date.year + (base_date.month - 1 + offset_months) // 12
        month = (base_date.month - 1 + offset_months) % 12 + 1
        return date(year, month, 1)

    month_starts = [month_start(today, offset) for offset in range(-5, 1)]
    labels = [month.strftime('%b') for month in month_starts]
    counts = []
    for month in month_starts:
        next_month = month_start(month, 1)
        counts.append(
            tapes_queryset.filter(
                date_registered__gte=month,
                date_registered__lt=next_month
            ).count()
        )
    return labels, counts


def get_first_day_of_month(month_string):
    if not month_string:
        return None
    try:
        year, month = [int(part) for part in month_string.split('-')]
        return date(year, month, 1)
    except (ValueError, TypeError):
        return None


def get_report_categories():
    return [
        {'slug': 'inventory', 'name': 'Inventory Report', 'description': 'Tape inventory status, counts, and current holdings.'},
        {'slug': 'shipment', 'name': 'Shipment Report', 'description': 'Shipment volume, status, and delivery performance.'},
        {'slug': 'custody', 'name': 'Custody Report', 'description': 'Custody transfer, acceptance, and compliance metrics.'},
        {'slug': 'reconciliation', 'name': 'Reconciliation Report', 'description': 'Reconciliation sessions, discrepancies, and resolution progress.'},
        {'slug': 'retention', 'name': 'Retention Report', 'description': 'Retention expiry and retention action counts for the month.'},
        {'slug': 'compliance', 'name': 'Compliance Report', 'description': 'Compliance alerts, audit readiness, and control checks.'},
        {'slug': 'exception', 'name': 'Exception Report', 'description': 'Exception counts, issue categories, and unresolved incidents.'},
        {'slug': 'audit_trail', 'name': 'Audit Trail Report', 'description': 'Audit events, changed records, and system activity.'},
        {'slug': 'management_summary', 'name': 'Management Summary Report', 'description': 'Executive summary of key program metrics and trends.'},
    ]


def get_latest_custodian_for_tape(tape):
    latest_shipment = tape.shipments.order_by('-shipment_date', '-created_at').first()
    if not latest_shipment:
        return None
    if latest_shipment.receiving_custodian:
        return latest_shipment.receiving_custodian
    if latest_shipment.releasing_custodian:
        return latest_shipment.releasing_custodian
    return None


def get_next_month(first_day):
    if first_day.month == 12:
        return date(first_day.year + 1, 1, 1)
    return date(first_day.year, first_day.month + 1, 1)


def sort_report_rows(rows, sort_key=None, sort_order='asc'):
    if not sort_key:
        return rows

    def sort_value(row):
        value = row.get(sort_key)
        if value is None:
            return ''
        if hasattr(value, 'strftime'):
            return value.strftime('%Y-%m-%d')
        return str(value).lower()

    return sorted(rows, key=sort_value, reverse=sort_order == 'desc')


def paginate_report_rows(request, rows, page_size=10, page_param='report_page'):
    paginator = Paginator(rows, page_size)
    page_number = request.GET.get(page_param, '1')
    page_obj = paginator.get_page(page_number)
    return paginator, page_obj


def get_scoped_report_param(request, report_category, param_name, default=''):
    if report_category:
        scoped_value = request.GET.get(f'{param_name}_{report_category}')
        if scoped_value is not None:
            return (scoped_value or '').strip()
    return (request.GET.get(param_name, default) or '').strip()


def get_scoped_report_flag(request, report_category, param_name):
    if report_category:
        scoped_value = request.GET.get(f'{param_name}_{report_category}')
        if scoped_value is not None:
            return scoped_value == '1'
    return request.GET.get(param_name) == '1'


def generate_daily_report_data(report_date):
    return {
        'period': report_date.strftime('%Y-%m-%d'),
        'tapes_registered': Tape.objects.filter(date_registered=report_date).count(),
        'active_tapes': Tape.objects.filter(status='Active').count(),
        'off_site_tapes': Tape.objects.filter(status='Off-Site').count(),
        'missing_tapes': Tape.objects.filter(status='Missing').count(),
        'retention_due_today': Tape.objects.filter(retention_end_date=report_date).count(),
        'shipments_created': Shipment.objects.filter(shipment_date=report_date).count(),
        'shipments_pending': Shipment.objects.filter(shipment_date=report_date, status__iexact='Pending').count(),
        'alerts_generated': AuditLog.objects.filter(timestamp__date=report_date, severity__in=['warning', 'error']).count(),
        'reconciliations_conducted': Reconciliation.objects.filter(reconciliation_date=report_date).count(),
    }


def generate_monthly_report_data(report_month, report_category=None):
    start = report_month
    end = get_next_month(report_month)
    if report_category == 'shipment':
        return {
            'period': report_month.strftime('%Y-%m'),
            'shipments_created': Shipment.objects.filter(shipment_date__gte=start, shipment_date__lt=end).count(),
            'shipments_pending': Shipment.objects.filter(shipment_date__gte=start, shipment_date__lt=end, status__iexact='Pending').count(),
            'shipments_dispatched': Shipment.objects.filter(shipment_date__gte=start, shipment_date__lt=end, status__iexact='Dispatched').count(),
            'shipments_delivered': Shipment.objects.filter(shipment_date__gte=start, shipment_date__lt=end, status__iexact='Delivered').count(),
            'active_transfers': Shipment.objects.filter(shipment_date__gte=start, shipment_date__lt=end, status__in=['In Transit', 'Dispatched']).count(),
            'delay_risk': Shipment.objects.filter(shipment_date__gte=start, shipment_date__lt=end, status__in=['Pending', 'More Info Requested']).count(),
        }
    if report_category == 'custody':
        return {
            'period': report_month.strftime('%Y-%m'),
            'total_shipments': Shipment.objects.filter(shipment_date__gte=start, shipment_date__lt=end).count(),
            'transfers_in_progress': Shipment.objects.filter(shipment_date__gte=start, shipment_date__lt=end, status__in=['In Transit', 'Dispatched']).count(),
            'deliveries_completed': Shipment.objects.filter(shipment_date__gte=start, shipment_date__lt=end, status__iexact='Delivered').count(),
            'custody_confirmed': ShipmentReceipt.objects.filter(
                shipment__shipment_date__gte=start,
                shipment__shipment_date__lt=end,
                custody_confirmed=True,
            ).count(),
            'custody_accepted': ShipmentReceipt.objects.filter(
                shipment__shipment_date__gte=start,
                shipment__shipment_date__lt=end,
                custody_accepted=True,
            ).count(),
        }
    if report_category == 'reconciliation':
        return {
            'period': report_month.strftime('%Y-%m'),
            'reconciliations_conducted': Reconciliation.objects.filter(reconciliation_date__gte=start, reconciliation_date__lt=end).count(),
            'issues_found': ReconciliationResult.objects.filter(reconciliation__reconciliation_date__gte=start, reconciliation__reconciliation_date__lt=end).count(),
            'open_issues': ReconciliationResult.objects.filter(reconciliation__reconciliation_date__gte=start, reconciliation__reconciliation_date__lt=end, resolution_status__in=['Open', 'Under Investigation']).count(),
            'completed_reconciliations': Reconciliation.objects.filter(reconciliation_date__gte=start, reconciliation_date__lt=end, status='Completed').count(),
            'pending_reconciliations': Reconciliation.objects.filter(reconciliation_date__gte=start, reconciliation_date__lt=end).exclude(status='Completed').count(),
        }
    if report_category == 'retention':
        return {
            'period': report_month.strftime('%Y-%m'),
            'retention_due_this_month': Tape.objects.filter(retention_end_date__gte=start, retention_end_date__lt=end).count(),
            'retention_expired': Tape.objects.filter(retention_end_date__lt=end, retention_end_date__gte=start).count(),
            'retention_actions_required': Tape.objects.filter(retention_end_date__gte=start, retention_end_date__lt=end, status__in=['Retained', 'Active']).count(),
            'archived_tapes': Tape.objects.filter(status='Retained').count(),
        }
    if report_category == 'compliance':
        return {
            'period': report_month.strftime('%Y-%m'),
            'alerts_generated': AuditLog.objects.filter(timestamp__gte=start, timestamp__lt=end, severity__in=['warning', 'error']).count(),
            'audit_events': AuditLog.objects.filter(timestamp__gte=start, timestamp__lt=end).count(),
            'policy_exceptions': ReconciliationResult.objects.filter(reconciliation__reconciliation_date__gte=start, reconciliation__reconciliation_date__lt=end, resolution_status__in=['Open', 'Under Investigation']).count(),
            'compliance_reviewed': Reconciliation.objects.filter(reconciliation_date__gte=start, reconciliation_date__lt=end, status='Completed').count(),
        }
    if report_category == 'exception':
        return {
            'period': report_month.strftime('%Y-%m'),
            'missing_tapes': Tape.objects.filter(status='Missing').count(),
            'damaged_tapes': Tape.objects.filter(status='Damaged').count(),
            'open_shipments': Shipment.objects.filter(status__iexact='Pending').count(),
            'open_issues': ReconciliationResult.objects.filter(resolution_status__in=['Open', 'Under Investigation']).count(),
        }
    if report_category == 'audit_trail':
        return {
            'period': report_month.strftime('%Y-%m'),
            'audit_events': AuditLog.objects.filter(timestamp__gte=start, timestamp__lt=end).count(),
            'warnings': AuditLog.objects.filter(timestamp__gte=start, timestamp__lt=end, severity='warning').count(),
            'errors': AuditLog.objects.filter(timestamp__gte=start, timestamp__lt=end, severity='error').count(),
            'user_actions': AuditLog.objects.filter(timestamp__gte=start, timestamp__lt=end).exclude(user__isnull=True).count(),
        }
    if report_category == 'management_summary':
        return {
            'period': report_month.strftime('%Y-%m'),
            'total_tapes': Tape.objects.count(),
            'shipments_created': Shipment.objects.filter(shipment_date__gte=start, shipment_date__lt=end).count(),
            'reconciliations_conducted': Reconciliation.objects.filter(reconciliation_date__gte=start, reconciliation_date__lt=end).count(),
            'alerts_generated': AuditLog.objects.filter(timestamp__gte=start, timestamp__lt=end, severity__in=['warning', 'error']).count(),
            'retention_due_this_month': Tape.objects.filter(retention_end_date__gte=start, retention_end_date__lt=end).count(),
        }
    return {
        'period': report_month.strftime('%Y-%m'),
        'tapes_registered': Tape.objects.filter(date_registered__gte=start, date_registered__lt=end).count(),
        'active_tapes': Tape.objects.filter(status='Active').count(),
        'off_site_tapes': Tape.objects.filter(status='Off-Site').count(),
        'missing_tapes': Tape.objects.filter(status='Missing').count(),
        'retention_due_this_month': Tape.objects.filter(retention_end_date__gte=start, retention_end_date__lt=end).count(),
        'shipments_created': Shipment.objects.filter(shipment_date__gte=start, shipment_date__lt=end).count(),
        'shipments_pending': Shipment.objects.filter(shipment_date__gte=start, shipment_date__lt=end, status__iexact='Pending').count(),
        'alerts_generated': AuditLog.objects.filter(timestamp__gte=start, timestamp__lt=end, severity__in=['warning', 'error']).count(),
        'reconciliations_conducted': Reconciliation.objects.filter(reconciliation_date__gte=start, reconciliation_date__lt=end).count(),
    }


def normalize_export_value(value):
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(timezone.UTC).replace(tzinfo=None)
        return value
    if hasattr(value, 'date') and callable(value.date) and not isinstance(value, date):
        try:
            value = value.date()
        except Exception:
            pass
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return value


def export_report_excel(report_category, report_period, rows, columns):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = report_category.replace('_', ' ').title()
    sheet.append([column['label'] for column in columns])
    for row in rows:
        sheet.append([normalize_export_value(row.get(column['key'], '-')) for column in columns])

    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{report_category}_report_{report_period}.xlsx"'
    return response


def export_report_pdf(report_category, report_period, rows, columns):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), title=f'{report_category.replace("_", " ").title()} Report')
    styles = getSampleStyleSheet()
    story = [Paragraph(f'{report_category.replace("_", " ").title()} Report - {report_period}', styles['Title']), Spacer(1, 12)]

    table_data = [[column['label'] for column in columns]]
    for row in rows:
        table_data.append([row.get(column['key'], '-') for column in columns])

    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]))
    story.append(table)
    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{report_category}_report_{report_period}.pdf"'
    return response


def build_report_csv_bytes(report_category, report_period, rows, columns):
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow([f'{report_category.replace("_", " ").title()} Report', report_period])
    writer.writerow([])
    writer.writerow([column['label'] for column in columns])
    for row in rows:
        writer.writerow([row.get(column['key'], '-') for column in columns])
    return buffer.getvalue().encode('utf-8')


def redirect_report_view(request):
    params = request.GET.copy()
    params.pop('share_report', None)
    params.pop('share_email', None)
    query_string = params.urlencode()
    return redirect(f"{request.path}?{query_string}" if query_string else request.path)


def send_report_share_email(request, report_category, report_period, rows, columns, recipients):
    subject = f'{report_category.replace("_", " ").title()} Report Shared'
    sender_email = request.user.email or settings.DEFAULT_FROM_EMAIL
    body = (
        f'Hello,\n\n'
        f'This report for {report_period} was shared from the Backup Administrator Dashboard.\n\n'
        f'Shared by: {request.user.get_full_name() or request.user.username}\n'
        f'Sender email: {sender_email}\n'
    )
    attachment_name = f'{report_category}_report_{report_period}.csv'
    csv_bytes = build_report_csv_bytes(report_category, report_period, rows, columns)
    msg = EmailMessage(subject, body, sender_email, recipients)
    msg.attach(attachment_name, csv_bytes, 'text/csv')
    try:
        msg.send(fail_silently=False)
        return True
    except Exception as exc:
        messages.error(request, f'Report sharing failed: {exc}')
        return False


def export_inventory_report_csv(report_period, tapes):
    response = HttpResponse(content_type='text/csv')
    filename = f"inventory_report_{report_period}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(['Inventory Report', report_period])
    writer.writerow([])
    writer.writerow(['VolSER', 'Barcode', 'RFID Tag', 'Tape Type', 'Status', 'Current Location', 'Custodian', 'Retention End Date', 'Date Registered'])
    for tape in tapes:
        writer.writerow([
            tape.volser,
            tape.barcode,
            tape.rfid_tag or '-',
            tape.tape_type,
            tape.status,
            tape.current_location or '-',
            tape.latest_custodian or '-',
            tape.retention_end_date.strftime('%Y-%m-%d') if tape.retention_end_date else '-',
            tape.date_registered.strftime('%Y-%m-%d') if tape.date_registered else '-',
        ])
    return response


def export_report_csv(report_type, report_period, report_data):
    response = HttpResponse(content_type='text/csv')
    filename = f"{report_type}_report_{report_period}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow([f'{report_type.title()} Report', report_period])
    writer.writerow([])
    writer.writerow(['Metric', 'Value'])
    for key, value in report_data.items():
        if key == 'period':
            continue
        writer.writerow([key.replace('_', ' ').title(), value])
    return response


def export_reconciliation_report_csv(reconciliations, summary=None):
    response = HttpResponse(content_type='text/csv')
    filename = 'reconciliation_reports_export.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(['Reconciliation Report Export'])
    writer.writerow([timezone.localdate().strftime('%Y-%m-%d')])
    writer.writerow([])

    if summary:
        writer.writerow(['Summary'])
        for key, value in summary.items():
            writer.writerow([key.replace('_', ' ').title(), value])
        writer.writerow([])

    writer.writerow(['Reconciliation ID', 'Date', 'Location', 'Status', 'Performed By', 'Reviewed By', 'Approved By', 'Total Issues', 'Open Issues'])
    for reconciliation in reconciliations:
        performer = reconciliation.performed_by.username if reconciliation.performed_by else 'System'
        reviewer = reconciliation.reviewed_by.username if reconciliation.reviewed_by else '-'
        approver = reconciliation.approved_by.username if reconciliation.approved_by else '-'
        total_issues = reconciliation.results.count()
        open_issues = reconciliation.results.filter(resolution_status__in=['Open', 'Under Investigation']).count()
        writer.writerow([
            reconciliation.reconciliation_id,
            reconciliation.reconciliation_date.strftime('%Y-%m-%d'),
            reconciliation.location,
            reconciliation.status,
            performer,
            reviewer,
            approver,
            total_issues,
            open_issues,
        ])
    return response


ALLOWED_REPORT_ROLES = [
    'Backup Administrator',
    'Operations Manager',
    'Compliance Auditor',
    'Information Security Officer',
    'System Administrator',
]


def has_report_access(user):
    return user.is_authenticated and (
        user.is_superuser or user.groups.filter(name__in=ALLOWED_REPORT_ROLES).exists()
    )


def get_notification_recipients():
    recipients = set()
    backup_admins = User.objects.filter(is_active=True, groups__name='Backup Administrator').exclude(email='')
    superusers = User.objects.filter(is_active=True, is_superuser=True).exclude(email='')
    for user in backup_admins.iterator():
        recipients.add(user.email)
    for user in superusers.iterator():
        recipients.add(user.email)
    return sorted(recipients)


def send_email_alert(subject, message, recipients):
    if not recipients:
        return
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=True)


def send_report_email(subject, message, recipients):
    if not recipients:
        return
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=True)


def notify_email_alert(application_settings, subject, message):
    if application_settings.email_alerts_enabled:
        recipients = get_notification_recipients()
        send_email_alert(subject, message, recipients)


# Create your views here.

User = get_user_model()

def index(request):
    return render(request, "index.html")


def is_backup_administrator(user):
    return user.is_authenticated and user.groups.filter(name='Backup Administrator').exists()


def is_operations_manager(user):
    return user.is_authenticated and user.groups.filter(name='Operations Manager').exists()


def signin(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user:
            login(request, user)
            if user.is_superuser:
                AuditLog.objects.create(
                    name='Admin Login',
                    action=f'User {user.username} signed in as superuser',
                    user=user,
                    severity='success',
                )
                return redirect("/admin/")
            if is_backup_administrator(user):
                AuditLog.objects.create(
                    name='Backup Administrator Login',
                    action=f'User {user.username} signed in as Backup Administrator',
                    user=user,
                    severity='success',
                )
                return redirect("backup-dashboard")
            if is_operations_manager(user):
                AuditLog.objects.create(
                    name='Operations Manager Login',
                    action=f'User {user.username} signed in as Operations Manager',
                    user=user,
                    severity='success',
                )
                return redirect("operations-dashboard")
            if is_courier(user):
                AuditLog.objects.create(
                    name='Courier Login',
                    action=f'User {user.username} signed in as Courier',
                    user=user,
                    severity='success',
                )
                return redirect("courier-dashboard")
            AuditLog.objects.create(
                name='Unauthorized Dashboard Login',
                action=f'User {user.username} attempted dashboard login without appropriate role',
                user=user,
                severity='warning',
            )
            logout(request)
            messages.error(request, "You do not have access to the dashboard.")
        else:
            AuditLog.objects.create(
                name='Login Failed',
                action=f'Failed login attempt for username {username}',
                user=None,
                severity='warning',
            )
            messages.error(request, "Invalid username or password")

    return render(request, "signin.html")


def signout(request):
    signed_out_user = request.user if request.user.is_authenticated else None
    logout(request)
    if signed_out_user:
        AuditLog.objects.create(
            name='User Logout',
            action=f'User {signed_out_user.username} signed out',
            user=signed_out_user,
            severity='info',
        )
    return redirect('signin')


@user_passes_test(lambda u: u.is_superuser, login_url='signin')
@login_required(login_url='signin')
def dashboard(request):
    tape_form = AddTapeForm(request.POST or None)
    user_form = CustomUserCreationForm(request.POST or None)
    edit_user_form = None
    role_creation_form = RoleCreationForm(request.POST or None)
    selected_group_id = request.GET.get('selected_group')
    role_feature_initial = {}
    selected_group = None
    if selected_group_id:
        selected_group = Group.objects.filter(pk=selected_group_id).first()
    if not selected_group:
        selected_group = Group.objects.first()
    if selected_group:
        template = RoleTemplate.objects.filter(group=selected_group).first()
        role_feature_initial = {
            'group': selected_group,
            'features': template.features if template else [],
        }
    role_feature_form = RoleFeatureUpdateForm(request.POST or None, initial=role_feature_initial)
    role_form = UserRoleAssignmentForm(request.POST or None)
    role_form.fields['user'].queryset = User.objects.filter(is_active=True, verified=True).order_by('username')
    edit_user = None

    if request.method == 'POST':
        if request.POST.get('form_type') == 'add_tape':
            if tape_form.is_valid():
                tape = tape_form.save()
                AuditLog.objects.create(
                    name='Tape Registered',
                    action=f'Registered tape {tape.volser}',
                    user=request.user,
                    severity='success',
                )
                messages.success(request, 'New tape registered successfully.')
                return redirect('dashboard')
            else:
                messages.error(request, 'Please correct the tape form errors below and try again.')
        elif request.POST.get('form_type') == 'add_user':
            if user_form.is_valid():
                user = user_form.save(commit=False)
                user.is_staff = False
                user.is_active = False
                user.verified = False
                user.save()
                AuditLog.objects.create(
                    name='User Created',
                    action=f'Created user {user.username} pending verification',
                    user=request.user,
                    severity='info',
                )
                messages.success(request, 'New user created successfully and awaits verification by Backup Administrator.')
                return redirect('dashboard')
            else:
                messages.error(request, 'Please correct the user form errors below and try again.')
        elif request.POST.get('form_type') == 'create_role':
            if role_creation_form.is_valid():
                role_name = role_creation_form.cleaned_data['role_name']
                features = role_creation_form.cleaned_data['features']
                group, created = Group.objects.get_or_create(name=role_name)
                if not created:
                    messages.error(request, 'Role name already exists.')
                else:
                    RoleTemplate.objects.create(group=group, features=features)
                    AuditLog.objects.create(
                        name='Role Created',
                        action=f'Created role {role_name}',
                        user=request.user,
                        severity='success',
                    )
                    messages.success(request, 'New role created successfully.')
                    return redirect('dashboard')
            else:
                messages.error(request, 'Please correct the role creation errors below and try again.')
        elif request.POST.get('form_type') == 'assign_role':
            if role_form.is_valid():
                user = role_form.cleaned_data['user']
                group = role_form.cleaned_data['group']
                user.groups.clear()
                user.groups.add(group)
                user.is_staff = group.name.lower() in ['admin', 'system administrator']
                user.save()
                AuditLog.objects.create(
                    name='Role Assigned',
                    action=f'Assigned {group.name} role to {user.username}',
                    user=request.user,
                    severity='success',
                )
                messages.success(request, 'User role updated successfully.')
                return redirect('dashboard')
            else:
                messages.error(request, 'Please correct the role assignment errors below and try again.')
        elif request.POST.get('form_type') == 'update_role_features':
            if role_feature_form.is_valid():
                group = role_feature_form.cleaned_data['group']
                features = role_feature_form.cleaned_data['features']
                template, created = RoleTemplate.objects.get_or_create(group=group)
                template.features = features
                template.save()
                AuditLog.objects.create(
                    name='Role Features Updated',
                    action=f'Updated features for {group.name}',
                    user=request.user,
                    severity='success',
                )
                messages.success(request, f'Features for role {group.name} were updated successfully.')
                return redirect(f"{reverse('dashboard')}?active_tab=roles&active_panel=%23editRoleFeaturesPanel")
            else:
                messages.error(request, 'Please correct the role feature form errors below and try again.')
        elif request.POST.get('form_type') == 'edit_user':
            user_id = request.POST.get('user_id')
            edit_user = get_object_by_uuid_pk(User, user_id)
            edit_user_form = CustomUserEditForm(request.POST, instance=edit_user)
            if edit_user_form.is_valid():
                user = edit_user_form.save(commit=False)
                user.is_staff = user.role == 'admin'
                user.save()
                AuditLog.objects.create(
                    name='User Updated',
                    action=f'Updated user {user.username}',
                    user=request.user,
                    severity='success',
                )
                messages.success(request, 'User updated successfully.')
                return redirect('dashboard')
            else:
                messages.error(request, 'Please correct the user edit errors below and try again.')

    if not edit_user_form:
        edit_user_id = request.GET.get('edit_user')
        if edit_user_id:
            edit_user = get_object_by_uuid_pk(User, edit_user_id)
            if edit_user:
                edit_user_form = CustomUserEditForm(instance=edit_user)

    users = User.objects.all().order_by("username")
    groups = Group.objects.all().order_by("name")
    role_templates = RoleTemplate.objects.select_related('group').all()
    shipments = Shipment.objects.all().order_by("shipment_id")
    reports = ReportTemplate.objects.all()
    audit_logs = AuditLog.objects.order_by("-timestamp")

    role_templates_by_group = {template.group.name: template for template in role_templates}

    pending_users = User.objects.filter(verified=False).order_by('date_joined')

    user_feature_names = []
    user_groups = request.user.groups.all()
    if user_groups.exists():
        assigned_templates = RoleTemplate.objects.filter(group__in=user_groups)
        for template in assigned_templates:
            if template.features:
                user_feature_names.extend(template.features)
    user_feature_names = sorted(set(user_feature_names))

    tapes = Tape.objects.all().order_by('-date_registered')
    tape_search = request.GET.get('tape_search', '').strip()
    if tape_search:
        search_q = (
            Q(volser__icontains=tape_search) |
            Q(barcode__icontains=tape_search) |
            Q(rfid_tag__icontains=tape_search) |
            Q(tape_type__icontains=tape_search) |
            Q(manufacturer__icontains=tape_search) |
            Q(status__icontains=tape_search) |
            Q(current_location__icontains=tape_search) |
            Q(remarks__icontains=tape_search)
        )
        parsed_date = parse_date(tape_search)
        if parsed_date:
            search_q |= Q(retention_end_date=parsed_date)
        tapes = tapes.filter(search_q)
    total_tapes = tapes.count()
    active_tapes = tapes.filter(status="Active").count()
    archived_tapes = tapes.filter(status="Retained").count()
    retention_due = tapes.filter(retention_end_date__lte=timezone.localdate()).count()
    pending_shipments = shipments.filter(status__iexact="Pending").count()
    alert_count = AuditLog.objects.filter(severity__in=["warning", "error"]).count()

    dashboard_tabs = get_dashboard_tabs(request.user, ADMIN_FEATURE_TABS)

    context = {
        "users": users,
        "groups": groups,
        "shipments": shipments,
        "reports": reports,
        "audit_logs": audit_logs,
        "tapes": tapes,
        "tape_search": tape_search,
        "role_creation_form": role_creation_form,
        "role_form": role_form,
        "role_feature_form": role_feature_form,
        "role_templates": role_templates,
        "role_templates_by_group": role_templates_by_group,
        "edit_user_form": edit_user_form,
        "edit_user": edit_user,
        "total_users": users.count(),
        "total_tapes": total_tapes,
        "active_tapes": active_tapes,
        "archived_tapes": archived_tapes,
        "retention_due": retention_due,
        "alert_count": alert_count,
        "pending_shipments": pending_shipments,
        "tape_form": tape_form,
        "user_form": user_form,
        "pending_users": pending_users,
        "user_feature_names": user_feature_names,
        "dashboard_tabs": dashboard_tabs,
    }

    return render(request, "dashboard.html", context)


@user_passes_test(lambda u: u.is_superuser or is_backup_administrator(u), login_url='signin')
@login_required(login_url='signin')
def backup_dashboard(request):
    tape_form = AddTapeForm(request.POST or None)
    tape_action_form = None
    selected_tape = None
    show_add_tape_panel = False
    show_tape_actions_panel = False
    show_tape_inventory_panel = False
    show_settings_panel = False
    show_audit_panel = False
    show_alerts_panel = False
    show_reports_panel = False
    show_shipments_panel = False
    show_add_shipment_panel = False
    show_edit_shipment_panel = False
    show_reconciliation_panel = False
    show_reconciliation_reports_panel = False
    show_add_reconciliation_panel = False
    show_print_barcodes_panel = False
    show_admin_panel = False
    selected_shipment = None
    selected_reconciliation = None
    add_shipment_form = ShipmentForm(request.POST or None, prefix='add')
    edit_shipment_form = None
    reconciliation_form = ReconciliationForm(request.POST or None, prefix='reconciliation')
    reconciliation_result_form = ReconciliationResultForm(request.POST or None, prefix='result')
    application_settings = ApplicationSetting.objects.first() or ApplicationSetting.objects.create()
    settings_form = None
    profile_form = None
    show_profile_panel = False

    selected_tape_id = request.GET.get('selected_tape') or request.POST.get('selected_tape')
    if selected_tape_id:
        selected_tape = get_object_by_uuid_pk(Tape, selected_tape_id)
        if selected_tape:
            show_tape_actions_panel = True

    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        if form_type == 'verify_user':
            user_id = request.POST.get('user_id')
            pending_user = None
            if is_valid_uuid(user_id):
                pending_user = User.objects.filter(pk=user_id, verified=False).first()
            if pending_user:
                pending_user.is_active = True
                pending_user.verified = True
                pending_user.verified_at = timezone.now()
                pending_user.save()
                AuditLog.objects.create(
                    name='User Verified',
                    action=f'Verified user {pending_user.username}',
                    user=request.user,
                    severity='success',
                )
                messages.success(request, f'User {pending_user.username} has been verified.')
            else:
                messages.error(request, 'Unable to verify the selected user.')
            return redirect('backup-dashboard')
        elif form_type == 'add_tape':
            if tape_form.is_valid():
                tape = tape_form.save()
                AuditLog.objects.create(
                    name='Tape Registered',
                    action=f'Registered tape {tape.volser} via backup dashboard',
                    user=request.user,
                    severity='success',
                )
                messages.success(request, 'New tape registered successfully.')
                return redirect(f'{reverse("backup-dashboard")}?show_add_tape=1')
            else:
                show_add_tape_panel = True
                messages.error(request, 'Please correct the tape form errors below and try again.')
        elif form_type == 'tape_action':
            tape_id = request.POST.get('selected_tape')
            selected_tape = get_object_by_uuid_pk(Tape, tape_id)
            if selected_tape:
                tape_action_form = TapeForm(request.POST, instance=selected_tape)
                action = request.POST.get('action')
                if action == 'edit_details':
                    if tape_action_form.is_valid():
                        tape_action_form.save()
                        AuditLog.objects.create(
                            name='Tape Updated',
                            action=f'Updated tape details for {selected_tape.volser}',
                            user=request.user,
                            severity='success',
                        )
                        messages.success(request, f'Tape {selected_tape.volser} updated successfully.')
                        return redirect(f'{reverse("backup-dashboard")}?show_tape_actions=1&selected_tape={selected_tape.id}')
                    else:
                        show_tape_actions_panel = True
                        messages.error(request, 'Please correct the tape form errors and try again.')
                elif action == 'update_location':
                    selected_tape.current_location = request.POST.get('current_location', selected_tape.current_location)
                    selected_tape.save()
                    AuditLog.objects.create(
                        name='Tape Location Updated',
                        action=f'Updated location for {selected_tape.volser} to {selected_tape.current_location}',
                        user=request.user,
                        severity='success',
                    )
                    messages.success(request, f'Location updated for {selected_tape.volser}.')
                    return redirect(f'{reverse("backup-dashboard")}?show_tape_actions=1&selected_tape={selected_tape.id}')
                elif action == 'mark_damaged':
                    selected_tape.status = 'Damaged'
                    selected_tape.save()
                    AuditLog.objects.create(
                        name='Tape Marked Damaged',
                        action=f'Marked tape {selected_tape.volser} as damaged',
                        user=request.user,
                        severity='warning',
                    )
                    messages.success(request, f'{selected_tape.volser} marked as damaged.')
                    return redirect(f'{reverse("backup-dashboard")}?show_tape_actions=1&selected_tape={selected_tape.id}')
                elif action == 'scan_rfid':
                    selected_tape.barcode = request.POST.get('barcode', selected_tape.barcode)
                    selected_tape.rfid_tag = request.POST.get('rfid_tag', selected_tape.rfid_tag)
                    selected_tape.save()
                    AuditLog.objects.create(
                        name='Tape Barcode/RFID Updated',
                        action=f'Updated barcode/rfid for {selected_tape.volser}',
                        user=request.user,
                        severity='success',
                    )
                    messages.success(request, f'Barcode/RFID updated for {selected_tape.volser}.')
                    return redirect(f'{reverse("backup-dashboard")}?show_tape_actions=1&selected_tape={selected_tape.id}')
            else:
                messages.error(request, 'Please select a valid tape to update.')
                return redirect('backup-dashboard')
        elif form_type == 'add_shipment':
            if add_shipment_form.is_valid():
                shipment = add_shipment_form.save(commit=False)
                shipment.created_by = request.user
                shipment.last_updated_by = request.user
                shipment.save()
                add_shipment_form.save_m2m()
                shipment.save(update_fields=['last_updated_by', 'last_updated_at'])
                AuditLog.objects.create(
                    name='Shipment Created',
                    action=f'Created shipment {shipment.shipment_id}',
                    user=request.user,
                    severity='success',
                )
                if application_settings.shipment_notification_enabled:
                    notify_email_alert(
                        application_settings,
                        f'Shipment {shipment.shipment_id} Created',
                        f'Shipment {shipment.shipment_id} was created by {request.user.username}.',
                    )
                messages.success(request, 'Shipment created successfully.')
                return redirect(f'{reverse("backup-dashboard")}?show_shipments=1')
            else:
                show_shipments_panel = True
                show_add_shipment_panel = True
                messages.error(request, 'Please correct the shipment form errors and try again.')
        elif form_type == 'edit_shipment':
            shipment_pk = request.POST.get('shipment_pk')
            selected_shipment = get_object_by_uuid_pk(Shipment, shipment_pk)
            if selected_shipment:
                edit_shipment_form = ShipmentForm(request.POST, instance=selected_shipment, prefix='edit')
                if edit_shipment_form.is_valid():
                    shipment = edit_shipment_form.save(commit=False)
                    shipment.last_updated_by = request.user
                    shipment.save()
                    edit_shipment_form.save_m2m()
                    shipment.save(update_fields=['last_updated_by', 'last_updated_at'])
                    AuditLog.objects.create(
                        name='Shipment Updated',
                        action=f'Updated shipment {shipment.shipment_id}',
                        user=request.user,
                        severity='success',
                    )
                    if application_settings.shipment_notification_enabled:
                        notify_email_alert(
                            application_settings,
                            f'Shipment {shipment.shipment_id} Updated',
                            f'Shipment {shipment.shipment_id} was updated by {request.user.username}.',
                        )
                    messages.success(request, 'Shipment updated successfully.')
                    return redirect(f'{reverse("backup-dashboard")}?edit_shipment_pk={shipment.id}&show_shipments=1')
                else:
                    show_shipments_panel = True
                    show_edit_shipment_panel = True
                    messages.error(request, 'Please correct the shipment form errors and try again.')
            else:
                messages.error(request, 'Please select a valid shipment to update.')
                return redirect('backup-dashboard')
        elif form_type == 'add_reconciliation':
            if reconciliation_form.is_valid():
                reconciliation = reconciliation_form.save(commit=False)
                reconciliation.performed_by = request.user
                reconciliation.save()
                AuditLog.objects.create(
                    name='Reconciliation Created',
                    action=f'Created reconciliation {reconciliation.reconciliation_id} for {reconciliation.location}',
                    user=request.user,
                    severity='success',
                )
                messages.success(request, 'Reconciliation created successfully.')
                return redirect(f'{reverse("backup-dashboard")}?show_reconciliation=1')
            else:
                show_reconciliation_panel = True
                show_add_reconciliation_panel = True
                messages.error(request, 'Please correct the reconciliation form errors and try again.')
        elif form_type == 'add_reconciliation_result':
            reconciliation_pk = request.POST.get('reconciliation_pk')
            selected_reconciliation = get_object_by_uuid_pk(Reconciliation, reconciliation_pk)
            if selected_reconciliation:
                reconciliation_result_form = ReconciliationResultForm(request.POST, prefix='result')
                if reconciliation_result_form.is_valid():
                    result = reconciliation_result_form.save(commit=False)
                    result.reconciliation = selected_reconciliation
                    result.save()
                    AuditLog.objects.create(
                        name='Reconciliation Result Added',
                        action=f'Added reconciliation result for {selected_reconciliation.reconciliation_id}',
                        user=request.user,
                        severity='info',
                    )
                    messages.success(request, 'Reconciliation result saved successfully.')
                    return redirect(f'{reverse("backup-dashboard")}?show_reconciliation=1&reconciliation_pk={selected_reconciliation.id}')
                else:
                    show_reconciliation_panel = True
                    messages.error(request, 'Please correct the result form errors and try again.')
            else:
                messages.error(request, 'Please select a valid reconciliation session.')
                return redirect('backup-dashboard')
        elif form_type == 'system_settings':
            settings_form = SystemSettingsForm(request.POST, instance=application_settings)
            if settings_form.is_valid():
                settings_form.save()
                AuditLog.objects.create(
                    name='System Settings Updated',
                    action=f'Updated system settings by {request.user.username}',
                    user=request.user,
                    severity='success',
                )
                messages.success(request, 'System settings saved successfully.')
                return redirect(f'{reverse("backup-dashboard")}?show_settings=1')
            else:
                show_settings_panel = True
                messages.error(request, 'Please correct the settings form errors and try again.')
        elif form_type == 'edit_profile':
            profile_form = UserProfileForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                AuditLog.objects.create(
                    name='Profile Updated',
                    action=f'Updated profile for {request.user.username}',
                    user=request.user,
                    severity='success',
                )
                messages.success(request, 'Your profile has been updated.')
                return redirect(f'{reverse("backup-dashboard")}?show_profile=1')
            else:
                show_profile_panel = True
                messages.error(request, 'Please correct the profile form errors and try again.')

    selected_tape_id = request.GET.get('selected_tape') or request.POST.get('selected_tape')
    if selected_tape_id and not selected_tape:
        selected_tape = get_object_by_uuid_pk(Tape, selected_tape_id)
    if selected_tape and not tape_action_form:
        tape_action_form = TapeForm(instance=selected_tape)

    if request.GET.get('open_panel') == 'tapeActionsPanel':
        show_tape_actions_panel = True
    if request.GET.get('show_tape_actions') == '1' or 'show_tape_actions' in request.GET:
        show_tape_actions_panel = True
    if 'show_tape_inventory' in request.GET:
        show_tape_inventory_panel = True
    if 'show_print_barcodes' in request.GET:
        show_print_barcodes_panel = True
    if 'show_admin' in request.GET:
        show_admin_panel = True
    if 'show_profile' in request.GET:
        show_profile_panel = True
    if 'show_settings' in request.GET:
        show_settings_panel = True
    if 'show_add_tape' in request.GET:
        show_add_tape_panel = True
    if 'show_audit' in request.GET:
        show_audit_panel = True
    if 'show_reports' in request.GET:
        show_reports_panel = True
    if 'show_alerts' in request.GET:
        show_alerts_panel = True
        AuditLog.objects.filter(severity__in=['warning', 'error'], is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
    report_type = request.GET.get('report_type')
    report_category = request.GET.get('report_category')
    report_period = get_scoped_report_param(request, report_category, 'report_period')
    export_csv = get_scoped_report_flag(request, report_category, 'export_csv')
    export_pdf = get_scoped_report_flag(request, report_category, 'export_pdf')
    export_excel = get_scoped_report_flag(request, report_category, 'export_excel')
    report_search = get_scoped_report_param(request, report_category, 'report_search')
    report_filter_status = get_scoped_report_param(request, report_category, 'report_filter_status')
    report_date_from = get_scoped_report_param(request, report_category, 'report_date_from')
    report_date_to = get_scoped_report_param(request, report_category, 'report_date_to')
    report_sort = get_scoped_report_param(request, report_category, 'report_sort')
    report_order = (get_scoped_report_param(request, report_category, 'report_order', 'asc') or 'asc').lower()
    if report_order not in {'asc', 'desc'}:
        report_order = 'asc'
    generated_report_data = None
    generated_report_label = None
    generated_report_items = []
    report_email_form = ReportEmailForm(request.POST or None)
    reconciliation_report_summary = None
    export_reconciliation_csv = request.GET.get('export_reconciliation_csv') == '1'
    report_categories = get_report_categories()
    current_month = timezone.localdate().strftime('%Y-%m')
    if show_reports_panel and not report_period:
        report_period = current_month

    if 'show_reports' in request.GET:
        show_reports_panel = True
    if 'show_shipments' in request.GET:
        show_shipments_panel = True
    if 'show_reconciliation_reports' in request.GET:
        show_reconciliation_reports_panel = True
    if 'show_add_shipment' in request.GET:
        show_shipments_panel = True
        show_add_shipment_panel = True
    if 'show_reconciliation' in request.GET:
        show_reconciliation_panel = True
    if 'show_add_reconciliation' in request.GET:
        show_reconciliation_panel = True
        show_add_reconciliation_panel = True
    reconciliation_pk = request.GET.get('reconciliation_pk')
    if reconciliation_pk:
        selected_reconciliation = get_object_by_uuid_pk(Reconciliation, reconciliation_pk)
        if selected_reconciliation:
            show_reconciliation_panel = True
    edit_shipment_pk = request.GET.get('edit_shipment_pk')
    if edit_shipment_pk:
        selected_shipment = get_object_by_uuid_pk(Shipment, edit_shipment_pk)
        if selected_shipment:
            show_shipments_panel = True
            show_edit_shipment_panel = True
            if not edit_shipment_form:
                edit_shipment_form = ShipmentForm(instance=selected_shipment, prefix='edit')

    if not settings_form:
        settings_form = SystemSettingsForm(instance=application_settings)
    if not profile_form:
        profile_form = UserProfileForm(instance=request.user)

    tapes = Tape.objects.all().order_by('-date_registered')
    tape_search = request.GET.get('tape_search', '').strip()
    if tape_search:
        search_q = (
            Q(volser__icontains=tape_search) |
            Q(barcode__icontains=tape_search) |
            Q(rfid_tag__icontains=tape_search) |
            Q(tape_type__icontains=tape_search) |
            Q(manufacturer__icontains=tape_search) |
            Q(status__icontains=tape_search) |
            Q(current_location__icontains=tape_search) |
            Q(remarks__icontains=tape_search)
        )
        parsed_date = parse_date(tape_search)
        if parsed_date:
            search_q |= Q(retention_end_date=parsed_date)
        tapes = tapes.filter(search_q)

    user_feature_names = []
    user_groups = request.user.groups.all()
    if user_groups.exists():
        assigned_templates = RoleTemplate.objects.filter(group__in=user_groups)
        for template in assigned_templates:
            if template.features:
                user_feature_names.extend(template.features)
    user_feature_names = sorted(set(user_feature_names))
    request.user.feature_names = user_feature_names
    dashboard_tabs = get_dashboard_tabs(request.user, BACKUP_FEATURE_TABS, preserve_empty_tabs=True)

    total_tapes = tapes.count()
    active_tapes = tapes.filter(status="Active").count()
    off_site_tapes = tapes.filter(status="Off-Site").count()
    missing_tapes = tapes.filter(status="Missing").count()
    archived_tapes = tapes.filter(status="Retained").count()
    retention_due = tapes.filter(retention_end_date__lte=timezone.localdate()).count()
    shipments = Shipment.objects.all().order_by('shipment_id')
    pending_users = User.objects.filter(verified=False).order_by('date_joined')
    reports = ReportTemplate.objects.all()
    reconciliations = Reconciliation.objects.all().order_by('-reconciliation_date', '-created_at')
    search_query = request.GET.get('search', '').strip()
    reconciliation_report_summary = None

    kpis = {}
    if show_reports_panel:
        kpis = {
            'Total Tapes': total_tapes,
            'Active Tapes': active_tapes,
            'Retained Tapes': archived_tapes,
            'In Transit Tapes': tapes.filter(status__iexact='In Transit').count(),
            'Missing Tapes': missing_tapes,
            'Damaged Tapes': tapes.filter(status__iexact='Damaged').count(),
            'Pending Destruction': tapes.filter(status__iexact='Pending Destruction').count(),
            'Open Exceptions': 0,
            'Open Shipments': shipments.filter(status__iexact='Pending').count(),
            'Compliance Rate': '98.5%',
            'Reconciliation Accuracy': '99.2%',
        }

    if show_reconciliation_reports_panel and search_query:
        search_q = (
            Q(reconciliation_id__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(status__icontains=search_query) |
            Q(performed_by__username__icontains=search_query)
        )
        reconciliations = reconciliations.filter(search_q)

    if show_reconciliation_reports_panel:
        reconciliation_count = reconciliations.count()
        total_issues = ReconciliationResult.objects.filter(reconciliation__in=reconciliations).count()
        open_issues = ReconciliationResult.objects.filter(
            reconciliation__in=reconciliations,
            resolution_status__in=['Open', 'Under Investigation']
        ).count()
        completed_count = reconciliations.filter(status='Completed').count()
        open_reconciliations = reconciliations.exclude(status='Completed').count()

        reconciliation_report_summary = {
            'total_reconciliations': reconciliation_count,
            'total_discrepancies': total_issues,
            'open_issues': open_issues,
            'completed_reconciliations': completed_count,
            'open_reconciliations': open_reconciliations,
        }

    for reconciliation in reconciliations:
        reconciliation.total_issues = reconciliation.results.count()
        reconciliation.open_issues = reconciliation.results.filter(resolution_status__in=['Open', 'Under Investigation']).count()
    reconciliation_results = selected_reconciliation.results.order_by('-updated_at') if selected_reconciliation else ReconciliationResult.objects.none()
    recent_activities = AuditLog.objects.order_by('-timestamp')[:6]
    recent_alerts = AuditLog.objects.filter(severity__in=['warning', 'error']).order_by('-timestamp')[:5]
    audit_logs = AuditLog.objects.order_by('-timestamp')

    inventory_report_tapes = []
    shipment_report_rows = []
    custody_report_rows = []
    reconciliation_report_rows = []
    retention_report_rows = []
    compliance_report_rows = []
    exception_report_rows = []
    audit_trail_report_rows = []
    management_summary_report_rows = []
    report_table_columns = []
    report_paginator = None
    report_page_obj = None
    if show_reports_panel and report_period:
        report_month = get_first_day_of_month(report_period) or get_first_day_of_month(current_month)
        if report_month:
            if report_type == 'daily':
                report_date = parse_date(report_period)
                if report_date:
                    generated_report_data = generate_daily_report_data(report_date)
                    generated_report_label = f"Daily Report for {report_date.strftime('%Y-%m-%d')}"
            else:
                generated_report_data = generate_monthly_report_data(report_month, report_category)
                selected_category = next((c for c in report_categories if c['slug'] == report_category), None)
                category_name = selected_category['name'] if selected_category else 'Monthly Report'
                generated_report_label = f"{category_name} for {report_month.strftime('%B %Y')}"
                if report_category == 'inventory':
                    qs = Tape.objects.filter(date_registered__gte=report_month, date_registered__lt=get_next_month(report_month))
                    if report_search:
                        qs = qs.filter(
                            Q(volser__icontains=report_search) |
                            Q(barcode__icontains=report_search) |
                            Q(rfid_tag__icontains=report_search) |
                            Q(tape_type__icontains=report_search) |
                            Q(status__icontains=report_search) |
                            Q(current_location__icontains=report_search)
                        )
                    if report_filter_status:
                        qs = qs.filter(status__iexact=report_filter_status)
                    sort_field = None
                    if report_sort in {'volser', 'status', 'retention_end_date', 'date_registered', 'current_location'}:
                        sort_field = report_sort
                    if sort_field:
                        if report_order == 'desc':
                            qs = qs.order_by(f'-{sort_field}')
                        else:
                            qs = qs.order_by(sort_field)
                    else:
                        qs = qs.order_by('volser')
                    inventory_report_tapes = list(qs)
                    inventory_report_rows = []
                    for tape in inventory_report_tapes:
                        tape.latest_custodian = get_latest_custodian_for_tape(tape) or tape.current_location or '-'
                        inventory_report_rows.append({
                            'volser': tape.volser,
                            'barcode': tape.barcode,
                            'rfid_tag': tape.rfid_tag or '-',
                            'tape_type': tape.tape_type,
                            'status': tape.status,
                            'current_location': tape.current_location or '-',
                            'latest_custodian': tape.latest_custodian,
                            'retention_end_date': tape.retention_end_date,
                            'date_registered': tape.date_registered,
                        })
                    report_table_columns = [
                        {'key': 'volser', 'label': 'VolSER'},
                        {'key': 'barcode', 'label': 'Barcode'},
                        {'key': 'rfid_tag', 'label': 'RFID Tag'},
                        {'key': 'tape_type', 'label': 'Tape Type'},
                        {'key': 'status', 'label': 'Status'},
                        {'key': 'current_location', 'label': 'Current Location'},
                        {'key': 'latest_custodian', 'label': 'Custodian'},
                        {'key': 'retention_end_date', 'label': 'Retention End Date'},
                        {'key': 'date_registered', 'label': 'Date Registered'},
                    ]
                    if request.GET.get('share_report') == '1':
                        share_emails = [email.strip() for email in request.GET.get('share_email', '').split(',') if email.strip()]
                        if share_emails:
                            if send_report_share_email(request, report_category, report_period, inventory_report_rows, report_table_columns, share_emails):
                                messages.success(request, f'Report shared with {", ".join(share_emails)}.')
                            return redirect_report_view(request)
                        messages.error(request, 'Please enter at least one valid email address to share this report.')
                        return redirect_report_view(request)
                    if export_pdf:
                        return export_report_pdf(report_category, report_period, inventory_report_rows, report_table_columns)
                    if export_excel:
                        return export_report_excel(report_category, report_period, inventory_report_rows, report_table_columns)
                elif report_category == 'shipment':
                    shipment_report_rows = Shipment.objects.filter(
                        shipment_date__gte=report_month,
                        shipment_date__lt=get_next_month(report_month)
                    ).order_by('shipment_id')
                    report_table_columns = [
                        {'key': 'shipment_id', 'label': 'Shipment ID'},
                        {'key': 'shipment_type', 'label': 'Shipment Type'},
                        {'key': 'source_location', 'label': 'Source Location'},
                        {'key': 'destination_location', 'label': 'Destination Location'},
                        {'key': 'courier_name', 'label': 'Courier'},
                        {'key': 'shipment_date', 'label': 'Dispatch Date'},
                        {'key': 'delivery_date', 'label': 'Delivery Date'},
                        {'key': 'status', 'label': 'Status'},
                        {'key': 'number_of_tapes', 'label': 'Number of Tapes'},
                    ]
                    if request.GET.get('share_report') == '1':
                        share_emails = [email.strip() for email in request.GET.get('share_email', '').split(',') if email.strip()]
                        if share_emails:
                            if send_report_share_email(request, report_category, report_period, list(shipment_report_rows.values('shipment_id', 'shipment_type', 'source_location', 'destination_location', 'courier_name', 'shipment_date', 'delivery_date', 'status')), report_table_columns, share_emails):
                                messages.success(request, f'Report shared with {", ".join(share_emails)}.')
                            return redirect_report_view(request)
                        messages.error(request, 'Please enter at least one valid email address to share this report.')
                        return redirect_report_view(request)
                elif report_category == 'custody':
                    custody_report_rows = Shipment.objects.filter(
                        shipment_date__gte=report_month,
                        shipment_date__lt=get_next_month(report_month)
                    ).order_by('shipment_id')
                    report_table_columns = [
                        {'key': 'transfer_date', 'label': 'Transfer Date'},
                        {'key': 'transfer_time', 'label': 'Transfer Time'},
                        {'key': 'previous_custodian', 'label': 'Previous Custodian'},
                        {'key': 'new_custodian', 'label': 'New Custodian'},
                        {'key': 'location', 'label': 'Location'},
                        {'key': 'remarks', 'label': 'Remarks'},
                    ]
                    for shipment in custody_report_rows:
                        shipment.transfer_date = shipment.shipment_date
                        shipment.transfer_time = shipment.release_datetime.time() if shipment.release_datetime else None
                        shipment.previous_custodian = shipment.releasing_custodian or '-'
                        shipment.new_custodian = shipment.receiving_custodian or '-'
                        shipment.location = shipment.destination_location or shipment.source_location or '-'
                        shipment.remarks = shipment.approval_remarks or shipment.delivery_notes or '-'
                    if request.GET.get('share_report') == '1':
                        share_emails = [email.strip() for email in request.GET.get('share_email', '').split(',') if email.strip()]
                        if share_emails:
                            custody_share_rows = []
                            for shipment in custody_report_rows:
                                custody_share_rows.append({
                                    'transfer_date': shipment.transfer_date,
                                    'transfer_time': shipment.transfer_time,
                                    'previous_custodian': shipment.previous_custodian,
                                    'new_custodian': shipment.new_custodian,
                                    'location': shipment.location,
                                    'remarks': shipment.remarks,
                                })
                            if send_report_share_email(request, report_category, report_period, custody_share_rows, report_table_columns, share_emails):
                                messages.success(request, f'Report shared with {", ".join(share_emails)}.')
                            return redirect_report_view(request)
                        messages.error(request, 'Please enter at least one valid email address to share this report.')
                        return redirect_report_view(request)
                elif report_category == 'reconciliation':
                    qs = Reconciliation.objects.filter(reconciliation_date__gte=report_month, reconciliation_date__lt=get_next_month(report_month)).order_by('-reconciliation_date')
                    if report_search:
                        qs = qs.filter(Q(reconciliation_id__icontains=report_search) | Q(location__icontains=report_search) | Q(status__icontains=report_search))
                    if report_filter_status:
                        qs = qs.filter(status__iexact=report_filter_status)
                    if report_date_from:
                        qs = qs.filter(reconciliation_date__gte=parse_date(report_date_from))
                    if report_date_to:
                        qs = qs.filter(reconciliation_date__lte=parse_date(report_date_to))
                    reconciliation_report_rows = []
                    for reconciliation in qs:
                        reconciliation_report_rows.append({
                            'reconciliation_id': reconciliation.reconciliation_id,
                            'location': reconciliation.location,
                            'expected_tapes': reconciliation.results.count(),
                            'scanned_tapes': reconciliation.results.count(),
                            'missing_tapes': reconciliation.results.filter(issue_type='Missing').count(),
                            'misplaced_tapes': reconciliation.results.filter(issue_type='Misplaced').count(),
                            'unexpected_tapes': reconciliation.results.filter(issue_type='Unexpected').count(),
                            'reconciliation_date': reconciliation.reconciliation_date,
                            'status': reconciliation.status,
                        })
                    report_table_columns = [
                        {'key': 'reconciliation_id', 'label': 'Reconciliation ID'},
                        {'key': 'location', 'label': 'Location'},
                        {'key': 'expected_tapes', 'label': 'Expected Tapes'},
                        {'key': 'scanned_tapes', 'label': 'Scanned Tapes'},
                        {'key': 'missing_tapes', 'label': 'Missing Tapes'},
                        {'key': 'misplaced_tapes', 'label': 'Misplaced Tapes'},
                        {'key': 'unexpected_tapes', 'label': 'Unexpected Tapes'},
                        {'key': 'reconciliation_date', 'label': 'Reconciliation Date'},
                        {'key': 'status', 'label': 'Status'},
                    ]
                    reconciliation_report_rows = sort_report_rows(reconciliation_report_rows, report_sort or None, report_order)
                    if request.GET.get('share_report') == '1':
                        share_emails = [email.strip() for email in request.GET.get('share_email', '').split(',') if email.strip()]
                        if share_emails:
                            if send_report_share_email(request, report_category, report_period, reconciliation_report_rows, report_table_columns, share_emails):
                                messages.success(request, f'Report shared with {", ".join(share_emails)}.')
                            return redirect_report_view(request)
                        messages.error(request, 'Please enter at least one valid email address to share this report.')
                        return redirect_report_view(request)
                    if export_pdf:
                        return export_report_pdf(report_category, report_period, reconciliation_report_rows, report_table_columns)
                    if export_excel:
                        return export_report_excel(report_category, report_period, reconciliation_report_rows, report_table_columns)
                    report_paginator, report_page_obj = paginate_report_rows(request, reconciliation_report_rows, page_param=f'report_page_{report_category}')
                    reconciliation_report_rows = list(report_page_obj.object_list)
                elif report_category == 'retention':
                    qs = Tape.objects.filter(retention_end_date__gte=report_month, retention_end_date__lt=get_next_month(report_month)).order_by('retention_end_date')
                    if report_search:
                        qs = qs.filter(Q(volser__icontains=report_search) | Q(barcode__icontains=report_search) | Q(status__icontains=report_search))
                    if report_filter_status:
                        qs = qs.filter(status__iexact=report_filter_status)
                    if report_date_from:
                        qs = qs.filter(retention_end_date__gte=parse_date(report_date_from))
                    if report_date_to:
                        qs = qs.filter(retention_end_date__lte=parse_date(report_date_to))
                    retention_report_rows = []
                    for tape in qs:
                        retention_report_rows.append({
                            'volser': tape.volser,
                            'barcode': tape.barcode,
                            'retention_start_date': tape.date_registered.date() if getattr(tape, 'date_registered', None) else '-',
                            'retention_end_date': tape.retention_end_date,
                            'days_remaining': (tape.retention_end_date - timezone.localdate()).days if tape.retention_end_date else '-',
                            'legal_hold': 'Yes' if tape.legal_hold else 'No',
                            'audit_hold': 'Yes' if tape.audit_hold else 'No',
                            'status': tape.status,
                        })
                    report_table_columns = [
                        {'key': 'volser', 'label': 'VolSER'},
                        {'key': 'barcode', 'label': 'Barcode'},
                        {'key': 'retention_start_date', 'label': 'Retention Start Date'},
                        {'key': 'retention_end_date', 'label': 'Retention End Date'},
                        {'key': 'days_remaining', 'label': 'Days Remaining'},
                        {'key': 'legal_hold', 'label': 'Legal Hold'},
                        {'key': 'audit_hold', 'label': 'Audit Hold'},
                        {'key': 'status', 'label': 'Status'},
                    ]
                    retention_report_rows = sort_report_rows(retention_report_rows, report_sort or None, report_order)
                    if request.GET.get('share_report') == '1':
                        share_emails = [email.strip() for email in request.GET.get('share_email', '').split(',') if email.strip()]
                        if share_emails:
                            if send_report_share_email(request, report_category, report_period, retention_report_rows, report_table_columns, share_emails):
                                messages.success(request, f'Report shared with {", ".join(share_emails)}.')
                            return redirect_report_view(request)
                        messages.error(request, 'Please enter at least one valid email address to share this report.')
                        return redirect_report_view(request)
                    if export_pdf:
                        return export_report_pdf(report_category, report_period, retention_report_rows, report_table_columns)
                    if export_excel:
                        return export_report_excel(report_category, report_period, retention_report_rows, report_table_columns)
                    report_paginator, report_page_obj = paginate_report_rows(request, retention_report_rows, page_param=f'report_page_{report_category}')
                    retention_report_rows = list(report_page_obj.object_list)
                elif report_category == 'compliance':
                    qs = ReconciliationResult.objects.filter(reconciliation__reconciliation_date__gte=report_month, reconciliation__reconciliation_date__lt=get_next_month(report_month)).order_by('-created_at')
                    if report_search:
                        qs = qs.filter(Q(reconciliation__reconciliation_id__icontains=report_search) | Q(remarks__icontains=report_search) | Q(resolution_status__icontains=report_search))
                    if report_filter_status:
                        qs = qs.filter(resolution_status__iexact=report_filter_status)
                    if report_date_from:
                        qs = qs.filter(created_at__date__gte=parse_date(report_date_from))
                    if report_date_to:
                        qs = qs.filter(created_at__date__lte=parse_date(report_date_to))
                    compliance_report_rows = []
                    for result in qs:
                        compliance_report_rows.append({
                            'compliance_id': result.reconciliation.reconciliation_id,
                            'policy_name': 'Tape Handling Policy',
                            'compliance_status': 'Compliant' if result.resolution_status == 'Resolved' else 'Needs Review',
                            'violations': result.issue_type,
                            'date_identified': result.created_at.date(),
                            'responsible_user': result.reconciliation.performed_by.username if result.reconciliation.performed_by else '-',
                            'resolution_status': result.resolution_status,
                        })
                    report_table_columns = [
                        {'key': 'compliance_id', 'label': 'Compliance ID'},
                        {'key': 'policy_name', 'label': 'Policy Name'},
                        {'key': 'compliance_status', 'label': 'Compliance Status'},
                        {'key': 'violations', 'label': 'Violations'},
                        {'key': 'date_identified', 'label': 'Date Identified'},
                        {'key': 'responsible_user', 'label': 'Responsible User'},
                        {'key': 'resolution_status', 'label': 'Resolution Status'},
                    ]
                    compliance_report_rows = sort_report_rows(compliance_report_rows, report_sort or None, report_order)
                    if request.GET.get('share_report') == '1':
                        share_emails = [email.strip() for email in request.GET.get('share_email', '').split(',') if email.strip()]
                        if share_emails:
                            if send_report_share_email(request, report_category, report_period, compliance_report_rows, report_table_columns, share_emails):
                                messages.success(request, f'Report shared with {", ".join(share_emails)}.')
                            return redirect_report_view(request)
                        messages.error(request, 'Please enter at least one valid email address to share this report.')
                        return redirect_report_view(request)
                    if export_pdf:
                        return export_report_pdf(report_category, report_period, compliance_report_rows, report_table_columns)
                    if export_excel:
                        return export_report_excel(report_category, report_period, compliance_report_rows, report_table_columns)
                    report_paginator, report_page_obj = paginate_report_rows(request, compliance_report_rows, page_param=f'report_page_{report_category}')
                    compliance_report_rows = list(report_page_obj.object_list)
                elif report_category == 'exception':
                    qs = ShipmentException.objects.filter(reported_date__date__gte=report_month, reported_date__date__lt=get_next_month(report_month)).order_by('-reported_date')
                    if report_search:
                        qs = qs.filter(Q(exception_id__icontains=report_search) | Q(tape__volser__icontains=report_search) | Q(status__icontains=report_search))
                    if report_filter_status:
                        qs = qs.filter(status__iexact=report_filter_status)
                    if report_date_from:
                        qs = qs.filter(reported_date__date__gte=parse_date(report_date_from))
                    if report_date_to:
                        qs = qs.filter(reported_date__date__lte=parse_date(report_date_to))
                    exception_report_rows = []
                    for exception in qs:
                        exception_report_rows.append({
                            'exception_id': exception.exception_id,
                            'tape_volser': exception.tape.volser if exception.tape else '-',
                            'exception_type': exception.exception_type,
                            'severity': exception.severity,
                            'reported_by': exception.reported_by.username if exception.reported_by else '-',
                            'date_reported': exception.reported_date.date(),
                            'status': exception.status,
                            'resolution_date': exception.reported_date.date(),
                        })
                    report_table_columns = [
                        {'key': 'exception_id', 'label': 'Exception ID'},
                        {'key': 'tape_volser', 'label': 'Tape VolSER'},
                        {'key': 'exception_type', 'label': 'Exception Type'},
                        {'key': 'severity', 'label': 'Severity'},
                        {'key': 'reported_by', 'label': 'Reported By'},
                        {'key': 'date_reported', 'label': 'Date Reported'},
                        {'key': 'status', 'label': 'Status'},
                        {'key': 'resolution_date', 'label': 'Resolution Date'},
                    ]
                    exception_report_rows = sort_report_rows(exception_report_rows, report_sort or None, report_order)
                    if request.GET.get('share_report') == '1':
                        share_emails = [email.strip() for email in request.GET.get('share_email', '').split(',') if email.strip()]
                        if share_emails:
                            if send_report_share_email(request, report_category, report_period, exception_report_rows, report_table_columns, share_emails):
                                messages.success(request, f'Report shared with {", ".join(share_emails)}.')
                            return redirect_report_view(request)
                        messages.error(request, 'Please enter at least one valid email address to share this report.')
                        return redirect_report_view(request)
                    if export_pdf:
                        return export_report_pdf(report_category, report_period, exception_report_rows, report_table_columns)
                    if export_excel:
                        return export_report_excel(report_category, report_period, exception_report_rows, report_table_columns)
                    report_paginator, report_page_obj = paginate_report_rows(request, exception_report_rows, page_param=f'report_page_{report_category}')
                    exception_report_rows = list(report_page_obj.object_list)
                elif report_category == 'audit_trail':
                    qs = AuditLog.objects.filter(timestamp__date__gte=report_month, timestamp__date__lt=get_next_month(report_month)).order_by('-timestamp')
                    if report_search:
                        qs = qs.filter(Q(name__icontains=report_search) | Q(action__icontains=report_search) | Q(message__icontains=report_search))
                    if report_filter_status:
                        qs = qs.filter(severity__iexact=report_filter_status)
                    if report_date_from:
                        qs = qs.filter(timestamp__date__gte=parse_date(report_date_from))
                    if report_date_to:
                        qs = qs.filter(timestamp__date__lte=parse_date(report_date_to))
                    audit_trail_report_rows = []
                    for audit_entry in qs:
                        audit_trail_report_rows.append({
                            'audit_id': audit_entry.id,
                            'user': audit_entry.user.username if audit_entry.user else '-',
                            'action': audit_entry.action,
                            'module': audit_entry.name,
                            'record_affected': audit_entry.message,
                            'timestamp': audit_entry.timestamp,
                            'ip_address': '-',
                        })
                    report_table_columns = [
                        {'key': 'audit_id', 'label': 'Audit ID'},
                        {'key': 'user', 'label': 'User'},
                        {'key': 'action', 'label': 'Action'},
                        {'key': 'module', 'label': 'Module'},
                        {'key': 'record_affected', 'label': 'Record Affected'},
                        {'key': 'timestamp', 'label': 'Timestamp'},
                        {'key': 'ip_address', 'label': 'IP Address'},
                    ]
                    audit_trail_report_rows = sort_report_rows(audit_trail_report_rows, report_sort or None, report_order)
                    if request.GET.get('share_report') == '1':
                        share_emails = [email.strip() for email in request.GET.get('share_email', '').split(',') if email.strip()]
                        if share_emails:
                            if send_report_share_email(request, report_category, report_period, audit_trail_report_rows, report_table_columns, share_emails):
                                messages.success(request, f'Report shared with {", ".join(share_emails)}.')
                            return redirect_report_view(request)
                        messages.error(request, 'Please enter at least one valid email address to share this report.')
                        return redirect_report_view(request)
                    if export_pdf:
                        return export_report_pdf(report_category, report_period, audit_trail_report_rows, report_table_columns)
                    if export_excel:
                        return export_report_excel(report_category, report_period, audit_trail_report_rows, report_table_columns)
                    report_paginator, report_page_obj = paginate_report_rows(request, audit_trail_report_rows, page_param=f'report_page_{report_category}')
                    audit_trail_report_rows = list(report_page_obj.object_list)
                elif report_category == 'management_summary':
                    management_summary_report_rows = [{
                        'report_date': report_period,
                        'total_tapes': Tape.objects.count(),
                        'active_tapes': Tape.objects.filter(status='Active').count(),
                        'in_transit': Tape.objects.filter(status='In Transit').count(),
                        'missing_tapes': Tape.objects.filter(status='Missing').count(),
                        'damaged_tapes': Tape.objects.filter(status='Damaged').count(),
                        'open_exceptions': ShipmentException.objects.filter(status__in=['Open', 'Investigating']).count(),
                        'compliance_rate': '98.5%',
                        'reconciliation_accuracy': '99.2%',
                    }]
                    report_table_columns = [
                        {'key': 'report_date', 'label': 'Report Date'},
                        {'key': 'total_tapes', 'label': 'Total Tapes'},
                        {'key': 'active_tapes', 'label': 'Active Tapes'},
                        {'key': 'in_transit', 'label': 'In Transit'},
                        {'key': 'missing_tapes', 'label': 'Missing Tapes'},
                        {'key': 'damaged_tapes', 'label': 'Damaged Tapes'},
                        {'key': 'open_exceptions', 'label': 'Open Exceptions'},
                        {'key': 'compliance_rate', 'label': 'Compliance Rate'},
                        {'key': 'reconciliation_accuracy', 'label': 'Reconciliation Accuracy'},
                    ]
                    if request.GET.get('share_report') == '1':
                        share_emails = [email.strip() for email in request.GET.get('share_email', '').split(',') if email.strip()]
                        if share_emails:
                            if send_report_share_email(request, report_category, report_period, management_summary_report_rows, report_table_columns, share_emails):
                                messages.success(request, f'Report shared with {", ".join(share_emails)}.')
                            return redirect_report_view(request)
                        messages.error(request, 'Please enter at least one valid email address to share this report.')
                        return redirect_report_view(request)
                    if export_pdf:
                        return export_report_pdf(report_category, report_period, management_summary_report_rows, report_table_columns)
                    if export_excel:
                        return export_report_excel(report_category, report_period, management_summary_report_rows, report_table_columns)
        if generated_report_data:
            generated_report_items = [
                {
                    'label': key.replace('_', ' ').title(),
                    'value': value
                }
                for key, value in generated_report_data.items()
                if key != 'period'
            ]
        if export_csv:
            if report_category == 'inventory':
                return export_inventory_report_csv(report_period or current_month, inventory_report_tapes)
            if generated_report_data:
                return export_report_csv(report_type or 'monthly', report_period, generated_report_data)

    if show_reconciliation_reports_panel and export_reconciliation_csv:
        return export_reconciliation_report_csv(reconciliations, summary=reconciliation_report_summary)

    status_labels = ['Active', 'Off-Site', 'Scratch Eligible', 'Damaged']
    status_counts = [
        tapes.filter(status='Active').count(),
        tapes.filter(status='Off-Site').count(),
        tapes.filter(status='Scratch Eligible').count(),
        tapes.filter(status='Damaged').count(),
    ]
    monthly_labels, monthly_counts = get_last_six_month_counts(tapes)

    context = {
        'tapes': tapes,
        'tape_search': tape_search,
        'total_tapes': total_tapes,
        'active_tapes': active_tapes,
        'off_site_tapes': off_site_tapes,
        'missing_tapes': missing_tapes,
        'archived_tapes': archived_tapes,
        'retention_due': retention_due,
        'pending_shipments': shipments.filter(status__iexact='Pending').count(),
        'alert_count': AuditLog.objects.filter(severity__in=['warning', 'error'], is_read=False).count(),
        'shipments': shipments,
        'pending_users': pending_users,
        'pending_user_count': pending_users.count(),
        'recent_activities': recent_activities,
        'recent_alerts': recent_alerts,
        'audit_logs': audit_logs,
        'user_feature_names': user_feature_names,
        'dashboard_tabs': dashboard_tabs,
        'tape_form': tape_form,
        'tape_action_form': tape_action_form,
        'selected_tape': selected_tape,
        'show_add_tape_panel': show_add_tape_panel,
        'show_tape_actions_panel': show_tape_actions_panel,
        'show_tape_inventory_panel': show_tape_inventory_panel,
        'show_print_barcodes_panel': show_print_barcodes_panel,
        'show_admin_panel': show_admin_panel,
        'show_profile_panel': show_profile_panel,
        'show_settings_panel': show_settings_panel,
        'show_audit_panel': show_audit_panel,
        'show_alerts_panel': show_alerts_panel,
        'show_reports_panel': show_reports_panel,
        'show_reconciliation_reports_panel': show_reconciliation_reports_panel,
        'show_shipments_panel': show_shipments_panel,
        'show_add_shipment_panel': show_add_shipment_panel,
        'show_edit_shipment_panel': show_edit_shipment_panel,
        'show_reconciliation_panel': show_reconciliation_panel,
        'show_add_reconciliation_panel': show_add_reconciliation_panel,
        'add_shipment_form': add_shipment_form,
        'edit_shipment_form': edit_shipment_form,
        'selected_shipment': selected_shipment,
        'reconciliation_form': reconciliation_form,
        'reconciliation_result_form': reconciliation_result_form,
        'reconciliations': reconciliations,
        'reconciliation_results': reconciliation_results,
        'selected_reconciliation': selected_reconciliation,
        'settings_form': settings_form,
        'profile_form': profile_form,
        'application_settings': application_settings,
        'reports': reports,
        'generated_report_data': generated_report_data,
        'generated_report_label': generated_report_label,
        'report_type': report_type,
        'report_category': report_category,
        'report_period': report_period,
        'report_categories': report_categories,
        'current_month': current_month,
        'report_email_form': report_email_form,
        'search_query': search_query,
        'reconciliation_report_summary': reconciliation_report_summary,
        'report_export_url': f"{reverse('backup-dashboard')}?show_reconciliation_reports=1",
        'status_labels_json': json.dumps(status_labels),
        'status_counts_json': json.dumps(status_counts),
        'monthly_labels_json': json.dumps(monthly_labels),
        'monthly_counts_json': json.dumps(monthly_counts),
        'kpis': kpis,
        'report_categories': report_categories,
        'current_month': current_month,
        'inventory_report_tapes': inventory_report_tapes,
        'shipment_report_rows': shipment_report_rows,
        'custody_report_rows': custody_report_rows,
        'reconciliation_report_rows': reconciliation_report_rows,
        'retention_report_rows': retention_report_rows,
        'compliance_report_rows': compliance_report_rows,
        'exception_report_rows': exception_report_rows,
        'audit_trail_report_rows': audit_trail_report_rows,
        'management_summary_report_rows': management_summary_report_rows,
        'report_table_columns': report_table_columns,
        'report_paginator': report_paginator,
        'report_page_obj': report_page_obj,
        'report_search': report_search,
        'report_filter_status': report_filter_status,
        'report_date_from': report_date_from,
        'report_date_to': report_date_to,
        'report_sort': report_sort,
        'report_order': report_order,
    }
    return render(request, 'backup_dashboard.html', context)


@user_passes_test(lambda u: u.is_superuser or is_operations_manager(u), login_url='signin')
@login_required(login_url='signin')
def operations_dashboard(request):
    shipments = Shipment.objects.all().order_by('-shipment_date')
    tapes = Tape.objects.all()
    reconciliations = Reconciliation.objects.order_by('-reconciliation_date')[:5]
    reconciliation_results = ReconciliationResult.objects.order_by('-created_at')
    audit_logs = AuditLog.objects.order_by('-timestamp')[:12]

    unread_alert_count = AuditLog.objects.filter(severity__in=['warning', 'error'], is_read=False).count()
    notification_items = AuditLog.objects.filter(severity__in=['warning', 'error']).order_by('-timestamp')[:10]
    show_profile_panel = False
    profile_edit_mode = False
    show_notifications_panel = False
    profile_form = UserProfileForm(instance=request.user)

    if request.method == 'GET' and request.GET.get('mark_notifications_read') == '1':
        AuditLog.objects.filter(severity__in=['warning', 'error'], is_read=False).update(is_read=True, read_at=timezone.now())
        unread_alert_count = 0

    if request.method == 'POST' and request.POST.get('form_type') == 'edit_profile':
        profile_form = UserProfileForm(request.POST, instance=request.user)
        if profile_form.is_valid():
            profile_form.save()
            AuditLog.objects.create(
                name='Profile Updated',
                action=f'Updated profile for {request.user.username}',
                user=request.user,
                severity='success',
            )
            messages.success(request, 'Your profile has been updated.')
            return redirect(f'{reverse("operations-dashboard")}?show_profile=1')
        else:
            show_profile_panel = True
            profile_edit_mode = True

    total_tapes = tapes.count()
    tapes_in_transit = tapes.filter(status='In Transit').count()
    missing_tapes = tapes.filter(status='Missing').count()
    overdue_shipments = shipments.filter(
        expected_delivery_date__lt=timezone.localdate()
    ).exclude(status__in=['Delivered', 'Cancelled']).count()
    open_exceptions = reconciliation_results.filter(resolution_status__in=['Open', 'Under Investigation']).count()
    pending_approvals = shipments.filter(status__iexact='Pending').count()
    compliance_rate = int(max(0, min(100, 100 - ((missing_tapes + open_exceptions) * 1.5))))
    reconciliation_accuracy = int(max(0, min(100, 100 - (open_exceptions * 1.2))))

    pending_shipments = shipments.filter(status__iexact='Pending').order_by('-shipment_date')[:6]
    monitoring_shipments = shipments.order_by('-shipment_date')[:12]
    latest_reconciliations = reconciliations
    open_discrepancies = reconciliation_results.filter(resolution_status__in=['Open', 'Under Investigation']).order_by('-created_at')[:6]
    recent_activity = audit_logs

    filter_form = ShipmentApprovalFilterForm(request.GET or None)
    manifest_form = ManifestSearchForm(request.GET or None)
    approval_shipments = shipments.select_related('approved_by', 'created_by', 'last_updated_by').prefetch_related('tapes')

    risk_level_filter = None
    if filter_form.is_valid():
        search = filter_form.cleaned_data.get('search')
        if search:
            approval_shipments = approval_shipments.filter(
                Q(shipment_id__icontains=search) |
                Q(source_location__icontains=search) |
                Q(destination_location__icontains=search) |
                Q(created_by__username__icontains=search) |
                Q(receiving_organization__icontains=search)
            )

        status = filter_form.cleaned_data.get('status')
        if status:
            approval_shipments = approval_shipments.filter(status=status)

        priority = filter_form.cleaned_data.get('priority')
        if priority:
            approval_shipments = approval_shipments.filter(priority_level=priority)

        date_from = filter_form.cleaned_data.get('date_from')
        if date_from:
            approval_shipments = approval_shipments.filter(shipment_date__gte=date_from)

        date_to = filter_form.cleaned_data.get('date_to')
        if date_to:
            approval_shipments = approval_shipments.filter(shipment_date__lte=date_to)

        risk_level = filter_form.cleaned_data.get('risk_level')
        if risk_level:
            risk_level_filter = risk_level

    if manifest_form.is_valid():
        manifest_query = manifest_form.cleaned_data.get('query')
        if manifest_query:
            approval_shipments = approval_shipments.filter(
                Q(tapes__volser__icontains=manifest_query) |
                Q(tapes__barcode__icontains=manifest_query) |
                Q(tapes__rfid_tag__icontains=manifest_query)
            ).distinct()

    if risk_level_filter:
        approval_shipments = [shipment for shipment in approval_shipments if shipment.risk_level() == risk_level_filter]

    if not isinstance(approval_shipments, list):
        approval_shipments = list(approval_shipments)

    if request.GET.get('show_profile') == '1':
        show_profile_panel = True
        if request.GET.get('edit_profile') == '1':
            profile_edit_mode = True

    if request.GET.get('show_notifications') == '1':
        show_notifications_panel = True

    total_shipments = len(approval_shipments)
    pending_count = sum(1 for shipment in approval_shipments if shipment.status == 'Pending')
    more_info_count = sum(1 for shipment in approval_shipments if shipment.status == 'More Info Requested')
    approved_count = sum(1 for shipment in approval_shipments if shipment.status == 'Approved')
    rejected_count = sum(1 for shipment in approval_shipments if shipment.status == 'Rejected')
    critical_count = sum(1 for shipment in approval_shipments if shipment.priority_level == 'Critical')
    non_compliant_count = sum(1 for shipment in approval_shipments if not shipment.compliance_passed())
    overdue_count = sum(1 for shipment in approval_shipments if shipment.is_overdue_for_approval())

    page_number = request.GET.get('page', 1)
    paginator = Paginator(approval_shipments, 10)
    shipment_page = paginator.get_page(page_number)

    custody_transfers_open = shipments.filter(status__in=['Dispatched', 'In Transit']).count()
    custody_transfers_completed = shipments.filter(status__iexact='Delivered').count()
    missing_handoffs = AuditLog.objects.filter(action__icontains='handoff').count()
    unverified_deliveries = shipments.filter(status__iexact='Delivered', delivery_status__in=['', 'Partially Delivered']).count()
    chain_of_custody_compliance = int(max(0, min(100, 100 - (missing_handoffs * 2))))

    exceptions = ShipmentException.objects.order_by('-reported_date')[:6]
    open_exceptions = ShipmentException.objects.filter(status__in=['Open', 'Investigating']).count()
    pending_approvals = shipments.filter(status__iexact='Pending').count()

    status_labels = ['Pending', 'Approved', 'Dispatched', 'In Transit', 'Delivered', 'Cancelled']
    status_counts = [shipments.filter(status=status).count() for status in status_labels]

    monthly_labels = []
    monthly_shipments = []
    monthly_compliance = []
    monthly_exceptions = []
    today = timezone.localdate()
    for offset in range(5, -1, -1):
        month = (today.replace(day=1) - timezone.timedelta(days=offset * 30)).strftime('%b %Y')
        monthly_labels.append(month)
        monthly_shipments.append(
            shipments.filter(shipment_date__year=today.year, shipment_date__month=(today.month - offset - 1) % 12 + 1).count()
        )
        monthly_compliance.append(max(75, min(100, 100 - missing_tapes)))
        monthly_exceptions.append(
            reconciliation_results.filter(created_at__year=today.year, created_at__month=(today.month - offset - 1) % 12 + 1).count()
        )

    alert_items = []
    recent_alerts = AuditLog.objects.filter(severity__in=['warning', 'error']).order_by('-timestamp')[:5]
    for item in recent_alerts:
        alert_items.append({
            'severity': item.severity.title(),
            'date': item.timestamp,
            'description': item.action or item.name or item.message,
            'action': 'Review',
        })
    reconciliation_alerts = reconciliation_results.filter(issue_type__in=['Missing', 'Damaged', 'Unexpected']).order_by('-created_at')[:3]
    for result in reconciliation_alerts:
        alert_items.append({
            'severity': 'Warning',
            'date': result.created_at,
            'description': f'{result.issue_type} tape detected for reconciliation {result.reconciliation.reconciliation_id}',
            'action': 'Investigate',
        })

    chart_data = {
        'status_labels_json': json.dumps(status_labels),
        'status_counts_json': json.dumps(status_counts),
        'monthly_labels_json': json.dumps(monthly_labels),
        'monthly_shipments_json': json.dumps(monthly_shipments),
        'monthly_compliance_json': json.dumps(monthly_compliance),
        'monthly_exceptions_json': json.dumps(monthly_exceptions),
    }

    context = {
        'dashboard_tabs': OPERATIONS_FEATURE_TABS,
        'current_datetime': timezone.localtime(),
        'today': today,
        'monthly_labels': monthly_labels,
        'monthly_shipments': monthly_shipments,
        'total_tapes': total_tapes,
        'tapes_in_transit': tapes_in_transit,
        'overdue_shipments': overdue_shipments,
        'missing_tapes': missing_tapes,
        'open_exceptions': open_exceptions,
        'pending_approvals': pending_approvals,
        'compliance_rate': compliance_rate,
        'reconciliation_accuracy': reconciliation_accuracy,
        'alert_items': alert_items,
        'pending_shipments': pending_shipments,
        'monitoring_shipments': monitoring_shipments,
        'latest_reconciliations': latest_reconciliations,
        'exceptions': exceptions,
        'open_discrepancies': open_discrepancies,
        'recent_activity': recent_activity,
        'custody_transfers_open': custody_transfers_open,
        'custody_transfers_completed': custody_transfers_completed,
        'missing_handoffs': missing_handoffs,
        'unverified_deliveries': unverified_deliveries,
        'chain_of_custody_compliance': chain_of_custody_compliance,
        'filter_form': filter_form,
        'manifest_form': manifest_form,
        'shipments': shipment_page,
        'total_shipments': total_shipments,
        'pending_count': pending_count,
        'more_info_count': more_info_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'critical_count': critical_count,
        'non_compliant_count': non_compliant_count,
        'overdue_count': overdue_count,
        'has_results': total_shipments > 0,
        'profile_form': profile_form,
        'show_profile_panel': show_profile_panel,
        'profile_edit_mode': profile_edit_mode,
        'show_notifications_panel': show_notifications_panel,
        'unread_alert_count': unread_alert_count,
        'notification_items': notification_items,
        **chart_data,
    }
    return render(request, 'operations_dashboard.html', context)


@user_passes_test(lambda u: u.is_superuser or is_operations_manager(u), login_url='signin')
@login_required(login_url='signin')
def exception_detail(request, pk):
    exception = get_object_or_404(
        ShipmentException.objects.select_related('shipment', 'tape', 'reported_by'),
        pk=pk
    )
    context = {
        'dashboard_tabs': OPERATIONS_FEATURE_TABS,
        'exception': exception,
    }
    if request.GET.get('partial'):
        return render(request, 'exception_detail_fragment.html', context)
    return render(request, 'exception_detail.html', context)


@user_passes_test(lambda u: u.is_superuser or is_operations_manager(u), login_url='signin')
@login_required(login_url='signin')
def shipment_approvals(request):
    filter_form = ShipmentApprovalFilterForm(request.GET or None)
    manifest_form = ManifestSearchForm(request.GET or None)
    shipments = Shipment.objects.select_related('approved_by', 'created_by', 'last_updated_by').prefetch_related('tapes').order_by('-shipment_date')

    risk_level_filter = None
    if filter_form.is_valid():
        search = filter_form.cleaned_data.get('search')
        if search:
            shipments = shipments.filter(
                Q(shipment_id__icontains=search) |
                Q(source_location__icontains=search) |
                Q(destination_location__icontains=search) |
                Q(created_by__username__icontains=search) |
                Q(receiving_organization__icontains=search)
            )

        status = filter_form.cleaned_data.get('status')
        if status:
            shipments = shipments.filter(status=status)

        priority = filter_form.cleaned_data.get('priority')
        if priority:
            shipments = shipments.filter(priority_level=priority)

        date_from = filter_form.cleaned_data.get('date_from')
        if date_from:
            shipments = shipments.filter(shipment_date__gte=date_from)

        date_to = filter_form.cleaned_data.get('date_to')
        if date_to:
            shipments = shipments.filter(shipment_date__lte=date_to)

        risk_level = filter_form.cleaned_data.get('risk_level')
        if risk_level:
            risk_level_filter = risk_level

    if manifest_form.is_valid():
        manifest_query = manifest_form.cleaned_data.get('query')
        if manifest_query:
            shipments = shipments.filter(
                Q(tapes__volser__icontains=manifest_query) |
                Q(tapes__barcode__icontains=manifest_query) |
                Q(tapes__rfid_tag__icontains=manifest_query)
            ).distinct()

    if risk_level_filter:
        shipments = [shipment for shipment in shipments if shipment.risk_level() == risk_level_filter]

    if not isinstance(shipments, list):
        shipments = list(shipments)

    total_shipments = len(shipments)
    pending_count = sum(1 for shipment in shipments if shipment.status == 'Pending')
    more_info_count = sum(1 for shipment in shipments if shipment.status == 'More Info Requested')
    approved_count = sum(1 for shipment in shipments if shipment.status == 'Approved')
    rejected_count = sum(1 for shipment in shipments if shipment.status == 'Rejected')
    critical_count = sum(1 for shipment in shipments if shipment.priority_level == 'Critical')
    non_compliant_count = sum(1 for shipment in shipments if not shipment.compliance_passed())
    overdue_count = sum(1 for shipment in shipments if shipment.is_overdue_for_approval())

    page_number = request.GET.get('page', 1)
    paginator = Paginator(shipments, 10)
    shipment_page = paginator.get_page(page_number)

    context = {
        'dashboard_tabs': OPERATIONS_FEATURE_TABS,
        'filter_form': filter_form,
        'manifest_form': manifest_form,
        'shipments': shipment_page,
        'total_shipments': total_shipments,
        'pending_count': pending_count,
        'more_info_count': more_info_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'critical_count': critical_count,
        'non_compliant_count': non_compliant_count,
        'overdue_count': overdue_count,
        'has_results': total_shipments > 0,
    }
    if request.GET.get('partial'):
        return render(request, 'shipment_approvals_fragment.html', context)
    return render(request, 'shipment_approvals.html', context)


@user_passes_test(lambda u: u.is_superuser or is_operations_manager(u), login_url='signin')
@login_required(login_url='signin')
def shipment_detail(request, shipment_pk):
    shipment = get_object_or_404(Shipment.objects.prefetch_related('tapes', 'approval_history'), pk=shipment_pk)
    approval_form = ShipmentApprovalDecisionForm(request.POST or None, initial={'shipment_pk': shipment.pk})
    manifest_search_form = ManifestSearchForm(request.GET or None)
    manifest_tapes = shipment.tapes.all()

    if manifest_search_form.is_valid():
        manifest_query = manifest_search_form.cleaned_data.get('query')
        if manifest_query:
            manifest_tapes = manifest_tapes.filter(
                Q(volser__icontains=manifest_query) |
                Q(barcode__icontains=manifest_query) |
                Q(rfid_tag__icontains=manifest_query)
            )

    partial_request = request.GET.get('partial') == '1'

    if request.method == 'POST':
        if approval_form.is_valid():
            decision = approval_form.cleaned_data.get('decision')
            comments = approval_form.cleaned_data.get('comments', '').strip()
            action_map = {
                'approve': 'Approved',
                'reject': 'Rejected',
                'more_info': 'Requested More Information',
            }
            action = action_map.get(decision, 'Updated')

            if decision == 'approve' and not shipment.compliance_passed():
                messages.warning(request, 'Shipment cannot be approved until all compliance checks pass.')
            else:
                if decision == 'approve':
                    shipment.status = 'Approved'
                elif decision == 'reject':
                    shipment.status = 'Rejected'
                else:
                    shipment.status = 'More Info Requested'

                shipment.approved_by = request.user
                shipment.approval_date = timezone.localtime()
                shipment.approval_remarks = comments
                shipment.last_updated_by = request.user
                shipment.save()

                ShipmentApprovalHistory.objects.create(
                    shipment=shipment,
                    action=action,
                    comments=comments,
                    user=request.user,
                )

                AuditLog.objects.create(
                    name='Shipment Approval Decision',
                    action=f'{action} for shipment {shipment.shipment_id}',
                    user=request.user,
                    severity='success' if decision == 'approve' else 'warning',
                )

                messages.success(request, f'Shipment has been marked as {shipment.status}.')
                if not partial_request:
                    return redirect('shipment-detail', shipment_pk=shipment.pk)

    compliance_checks = shipment.compliance_checks()
    compliance_checks_display = [
        (key.replace('_', ' ').title(), value)
        for key, value in compliance_checks.items()
    ]
    context = {
        'dashboard_tabs': OPERATIONS_FEATURE_TABS,
        'shipment': shipment,
        'approval_form': approval_form,
        'manifest_search_form': manifest_search_form,
        'manifest_tapes': manifest_tapes,
        'compliance_checks': compliance_checks,
        'compliance_checks_display': compliance_checks_display,
        'compliance_passed': shipment.compliance_passed(),
        'risk_score': shipment.risk_score(),
        'risk_level': shipment.risk_level(),
        'risk_recommendation': shipment.risk_recommendation(),
        'history': shipment.approval_history.all(),
    }
    template = 'shipment_detail_fragment.html' if partial_request else 'shipment_detail.html'
    return render(request, template, context)


@user_passes_test(lambda u: u.is_superuser or is_operations_manager(u), login_url='signin')
@login_required(login_url='signin')
def approval_history(request, shipment_pk):
    shipment = get_object_or_404(Shipment, pk=shipment_pk)
    history_entries = shipment.approval_history.all()
    context = {
        'dashboard_tabs': OPERATIONS_FEATURE_TABS,
        'shipment': shipment,
        'history_entries': history_entries,
    }
    return render(request, 'approval_history.html', context)


@user_passes_test(lambda u: u.is_superuser or is_courier(u), login_url='signin')
@login_required(login_url='signin')
def courier_dashboard(request):
    courier = get_courier_profile(request.user)
    shipments = Shipment.objects.none()
    if courier:
        shipments = Shipment.objects.filter(
            Q(courier_name__iexact=courier.full_name) |
            Q(courier_contact__iexact=courier.phone_number) |
            Q(receipts__courier=courier) |
            Q(deliveries__courier=courier)
        ).distinct().order_by('-shipment_date')
    assigned_count = shipments.filter(status__in=['Dispatched', 'Picked Up', 'In Transit']).count()
    pending_count = shipments.filter(status__in=['Pending', 'Approved']).count()
    delivered_count = shipments.filter(status='Delivered').count()
    exception_count = ShipmentException.objects.filter(shipment__in=shipments, status__in=['Open', 'Investigating']).count()
    activity_count = ShipmentTransportEvent.objects.filter(courier=courier).count() if courier else 0
    recent_events = ShipmentTransportEvent.objects.filter(courier=courier).order_by('-event_date', '-event_time')[:6] if courier else []
    recent_exceptions = ShipmentException.objects.filter(shipment__in=shipments).order_by('-reported_date')[:6]

    context = {
        'courier': courier,
        'shipments': shipments,
        'assigned_count': assigned_count,
        'pending_count': pending_count,
        'delivered_count': delivered_count,
        'exception_count': exception_count,
        'activity_count': activity_count,
        'recent_events': recent_events,
        'recent_exceptions': recent_exceptions,
    }
    return render(request, 'courier_dashboard.html', context)


@user_passes_test(lambda u: u.is_superuser or is_courier(u), login_url='signin')
@login_required(login_url='signin')
def assigned_shipments(request):
    courier = get_courier_profile(request.user)
    filter_form = CourierShipmentFilterForm(request.GET or None)
    shipments = Shipment.objects.none()
    if courier:
        shipments = Shipment.objects.filter(
            Q(courier_name__iexact=courier.full_name) |
            Q(courier_contact__iexact=courier.phone_number) |
            Q(receipts__courier=courier) |
            Q(deliveries__courier=courier)
        ).distinct().order_by('-shipment_date')

    if filter_form.is_valid():
        search = filter_form.cleaned_data.get('search')
        if search:
            shipments = shipments.filter(
                Q(shipment_id__icontains=search) |
                Q(source_location__icontains=search) |
                Q(destination_location__icontains=search) |
                Q(receiving_organization__icontains=search) |
                Q(courier_name__icontains=search)
            )
        status = filter_form.cleaned_data.get('status')
        if status:
            shipments = shipments.filter(status=status)
        shipment_type = filter_form.cleaned_data.get('shipment_type')
        if shipment_type:
            shipments = shipments.filter(shipment_type=shipment_type)
        date_from = filter_form.cleaned_data.get('date_from')
        if date_from:
            shipments = shipments.filter(shipment_date__gte=date_from)
        date_to = filter_form.cleaned_data.get('date_to')
        if date_to:
            shipments = shipments.filter(shipment_date__lte=date_to)

    page_number = request.GET.get('page', 1)
    paginator = Paginator(shipments, 10)
    shipment_page = paginator.get_page(page_number)

    context = {
        'courier': courier,
        'filter_form': filter_form,
        'shipments': shipment_page,
    }
    return render(request, 'assigned_shipments.html', context)


@user_passes_test(lambda u: u.is_superuser or is_courier(u), login_url='signin')
@login_required(login_url='signin')
def manifest_detail(request, shipment_pk):
    shipment = get_object_or_404(Shipment.objects.prefetch_related('tapes'), pk=shipment_pk)
    courier = get_courier_profile(request.user)
    manifest_tapes = shipment.tapes.all()
    context = {
        'courier': courier,
        'shipment': shipment,
        'manifest_tapes': manifest_tapes,
    }
    return render(request, 'manifest_detail.html', context)


@user_passes_test(lambda u: u.is_superuser or is_courier(u), login_url='signin')
@login_required(login_url='signin')
def pickup_confirmation(request, shipment_pk):
    shipment = get_object_or_404(Shipment.objects.prefetch_related('tapes'), pk=shipment_pk)
    courier = get_courier_profile(request.user)
    form = ShipmentReceiptForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            receipt = form.save(commit=False)
            receipt.shipment = shipment
            receipt.courier = courier
            receipt.confirmation_timestamp = timezone.localtime()
            receipt.save()
            shipment.status = 'Picked Up'
            shipment.last_updated_by = request.user
            shipment.save(update_fields=['status', 'last_updated_by', 'last_updated_at'])
            AuditLog.objects.create(
                name='Pickup Confirmed',
                action=f'Pickup confirmed for shipment {shipment.shipment_id}',
                user=request.user,
                severity='success',
            )
            messages.success(request, 'Pickup confirmation saved successfully.')
            return redirect('courier-dashboard')
        else:
            messages.error(request, 'Please correct the form errors and try again.')

    if not courier:
        messages.warning(request, 'Courier profile not found for your user account.')
    context = {
        'courier': courier,
        'shipment': shipment,
        'form': form,
    }
    return render(request, 'pickup_confirmation.html', context)


@user_passes_test(lambda u: u.is_superuser or is_courier(u), login_url='signin')
@login_required(login_url='signin')
def delivery_confirmation(request, shipment_pk):
    shipment = get_object_or_404(Shipment.objects.prefetch_related('tapes'), pk=shipment_pk)
    courier = get_courier_profile(request.user)
    form = DeliveryConfirmationForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            confirmation = form.save(commit=False)
            confirmation.shipment = shipment
            confirmation.courier = courier
            confirmation.save()
            shipment.delivery_date = confirmation.delivery_date
            shipment.delivery_time = confirmation.delivery_time
            shipment.delivery_status = confirmation.delivery_status
            shipment.status = 'Delivered' if confirmation.delivery_status == 'Delivered' else shipment.status
            shipment.last_updated_by = request.user
            shipment.save(update_fields=['delivery_date', 'delivery_time', 'delivery_status', 'status', 'last_updated_by', 'last_updated_at'])
            AuditLog.objects.create(
                name='Delivery Confirmed',
                action=f'Delivery confirmed for shipment {shipment.shipment_id}',
                user=request.user,
                severity='success',
            )
            messages.success(request, 'Delivery confirmation saved successfully.')
            return redirect('courier-dashboard')
        else:
            messages.error(request, 'Please correct the form errors and try again.')

    context = {
        'courier': courier,
        'shipment': shipment,
        'form': form,
    }
    return render(request, 'delivery_confirmation.html', context)


@user_passes_test(lambda u: u.is_superuser or is_courier(u), login_url='signin')
@login_required(login_url='signin')
def return_shipments(request):
    courier = get_courier_profile(request.user)
    shipments = Shipment.objects.filter(
        Q(shipment_type='Return') | Q(status='Return Accepted'),
        Q(courier_name__iexact=courier.full_name) | Q(courier_contact__iexact=courier.phone_number) | Q(receipts__courier=courier) | Q(deliveries__courier=courier)
    ).distinct().order_by('-shipment_date') if courier else Shipment.objects.none()

    context = {
        'courier': courier,
        'shipments': shipments,
    }
    return render(request, 'return_shipments.html', context)


@user_passes_test(lambda u: u.is_superuser or is_courier(u), login_url='signin')
@login_required(login_url='signin')
def incident_management(request):
    courier = get_courier_profile(request.user)
    form = ShipmentExceptionForm(request.POST or None, courier=courier)
    exceptions = ShipmentException.objects.filter(
        Q(shipment__courier_name__iexact=courier.full_name) | Q(shipment__courier_contact__iexact=courier.phone_number) | Q(shipment__receipts__courier=courier) | Q(shipment__deliveries__courier=courier)
    ).distinct().order_by('-reported_date') if courier else ShipmentException.objects.none()

    if request.method == 'POST' and form.is_valid():
        exception = form.save(commit=False)
        exception.reported_by = request.user
        exception.save()
        AuditLog.objects.create(
            name='Shipment Exception Reported',
            action=f'Reported exception {exception.exception_id} for shipment {exception.shipment.shipment_id}',
            user=request.user,
            severity='warning',
        )
        messages.success(request, 'Exception reported successfully.')
        return redirect('incident-management')
    elif request.method == 'POST':
        messages.error(request, 'Please correct the exception form errors and try again.')

    context = {
        'courier': courier,
        'form': form,
        'exceptions': exceptions,
    }
    return render(request, 'incident_management.html', context)


@user_passes_test(lambda u: u.is_superuser or is_courier(u), login_url='signin')
@login_required(login_url='signin')
def activity_log(request):
    courier = get_courier_profile(request.user)
    events = ShipmentTransportEvent.objects.filter(courier=courier).order_by('-event_date', '-event_time') if courier else ShipmentTransportEvent.objects.none()
    exceptions = ShipmentException.objects.filter(
        Q(shipment__courier_name__iexact=courier.full_name) | Q(shipment__courier_contact__iexact=courier.phone_number) | Q(shipment__receipts__courier=courier) | Q(shipment__deliveries__courier=courier)
    ).distinct().order_by('-reported_date') if courier else ShipmentException.objects.none()

    context = {
        'courier': courier,
        'events': events,
        'exceptions': exceptions,
    }
    return render(request, 'activity_log.html', context)


@user_passes_test(lambda u: u.is_superuser or is_backup_administrator(u), login_url='signin')
@login_required(login_url='signin')
def add_tape(request):
    form = AddTapeForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            tape = form.save()
            AuditLog.objects.create(
                name='Tape Registered',
                action=f'Registered tape {tape.volser} via add_tape view',
                user=request.user,
                severity='success',
            )
            messages.success(request, 'New tape registered successfully.')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please correct the errors below and try again.')

    return render(request, 'add_tape.html', {'form': form})


@user_passes_test(has_report_access, login_url='signin')
@login_required(login_url='signin')
def reconciliation_reports(request):
    report_email_form = ReportEmailForm(request.POST or None)
    search_query = request.GET.get('search', '').strip()
    reconciliations = Reconciliation.objects.select_related(
        'performed_by', 'reviewed_by', 'approved_by'
    ).prefetch_related('results', 'results__tape').order_by('-reconciliation_date', '-created_at')

    if search_query:
        search_q = (
            Q(reconciliation_id__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(status__icontains=search_query) |
            Q(performed_by__username__icontains=search_query)
        )
        reconciliations = reconciliations.filter(search_q)

    reconciliation_count = reconciliations.count()
    total_issues = ReconciliationResult.objects.filter(reconciliation__in=reconciliations).count()
    open_issues = ReconciliationResult.objects.filter(
        reconciliation__in=reconciliations,
        resolution_status__in=['Open', 'Under Investigation']
    ).count()
    completed_count = reconciliations.filter(status='Completed').count()
    open_reconciliations = reconciliations.exclude(status='Completed').count()

    reconciliation_report_summary = {
        'total_reconciliations': reconciliation_count,
        'total_discrepancies': total_issues,
        'open_issues': open_issues,
        'completed_reconciliations': completed_count,
        'open_reconciliations': open_reconciliations,
    }

    for reconciliation in reconciliations:
        reconciliation.total_issues = reconciliation.results.count()
        reconciliation.open_issues = reconciliation.results.filter(
            resolution_status__in=['Open', 'Under Investigation']
        ).count()

    if request.GET.get('export_reconciliation_csv') == '1':
        return export_reconciliation_report_csv(reconciliations, summary=reconciliation_report_summary)

    if request.method == 'POST' and report_email_form.is_valid():
        recipients = report_email_form.cleaned_data['recipients']
        subject = report_email_form.cleaned_data['subject']
        message = report_email_form.cleaned_data['message']
        summary_lines = [f"{key.replace('_', ' ').title()}: {value}" for key, value in reconciliation_report_summary.items()]
        report_body = message + '\n\n' + '\n'.join(summary_lines)
        send_report_email(subject, report_body, recipients)
        AuditLog.objects.create(
            name='Reconciliation Report Sent',
            action=f'Sent reconciliation report summary to {", ".join(recipients)}',
            user=request.user,
            severity='info',
        )
        messages.success(request, 'Reconciliation report summary sent successfully.')
        return redirect('reconciliation-reports')

    context = {
        'report_email_form': report_email_form,
        'reconciliations': reconciliations,
        'search_query': search_query,
        'summary': reconciliation_report_summary,
        'selected_tab': 'reconciliation_reports',
        'report_export_url': reverse('reconciliation-reports'),
    }
    return render(request, 'reconciliation_reports.html', context)


@user_passes_test(has_report_access, login_url='signin')
@login_required(login_url='signin')
def reconciliation_report_detail(request, pk):
    reconciliation = get_object_or_404(
        Reconciliation.objects.select_related('performed_by', 'reviewed_by', 'approved_by').prefetch_related('results', 'results__tape'),
        pk=pk
    )
    total_issues = reconciliation.results.count()
    open_issues = reconciliation.results.filter(resolution_status__in=['Open', 'Under Investigation']).count()
    context = {
        'reconciliation': reconciliation,
        'total_issues': total_issues,
        'open_issues': open_issues,
    }
    return render(request, 'report_detail.html', context)
