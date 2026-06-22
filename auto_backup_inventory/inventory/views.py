from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import Group
from django.conf import settings
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.template.loader import render_to_string
import csv
import json
import uuid
from datetime import date
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date

from .forms import CustomUserCreationForm, CustomUserEditForm, UserProfileForm, TapeForm, ShipmentForm, ReconciliationForm, ReconciliationResultForm, UserRoleAssignmentForm, RoleCreationForm, RoleFeatureUpdateForm, ReportEmailForm, SystemSettingsForm, FEATURE_CHOICES
from .models import AuditLog, ApplicationSetting, MonthlyReport, ReportTemplate, Reconciliation, ReconciliationResult, Shipment, Tape, RoleTemplate


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


def get_next_month(first_day):
    if first_day.month == 12:
        return date(first_day.year + 1, 1, 1)
    return date(first_day.year, first_day.month + 1, 1)


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


def generate_monthly_report_data(report_month):
    start = report_month
    end = get_next_month(report_month)
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
                return redirect("dashboard")
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
    tape_form = TapeForm(request.POST or None)
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
    tape_form = TapeForm(request.POST or None)
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
                return redirect('backup-dashboard')
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
    if 'show_profile' in request.GET:
        show_profile_panel = True
    if 'show_settings' in request.GET:
        show_settings_panel = True
    if 'show_add_tape' in request.GET:
        show_add_tape_panel = True
    if 'show_audit' in request.GET:
        show_audit_panel = True
    if 'show_alerts' in request.GET:
        show_alerts_panel = True
        AuditLog.objects.filter(severity__in=['warning', 'error'], is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
    report_type = request.GET.get('report_type')
    report_period = request.GET.get('report_period')
    export_csv = request.GET.get('export_csv') == '1'
    generated_report_data = None
    generated_report_label = None
    generated_report_items = []
    report_email_form = ReportEmailForm(request.POST or None)
    reconciliation_report_summary = None
    export_reconciliation_csv = request.GET.get('export_reconciliation_csv') == '1'

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

    if show_reports_panel and report_type and report_period:
        if report_type == 'daily':
            report_date = parse_date(report_period)
            if report_date:
                generated_report_data = generate_daily_report_data(report_date)
                generated_report_label = f"Daily Report for {report_date.strftime('%Y-%m-%d')}"
        elif report_type == 'monthly':
            report_month = get_first_day_of_month(report_period)
            if report_month:
                generated_report_data = generate_monthly_report_data(report_month)
                generated_report_label = f"Monthly Report for {report_month.strftime('%B %Y')}"
        if generated_report_data:
            generated_report_items = [
                {
                    'label': key.replace('_', ' ').title(),
                    'value': value
                }
                for key, value in generated_report_data.items()
                if key != 'period'
            ]
        if export_csv and generated_report_data:
            return export_report_csv(report_type, report_period, generated_report_data)

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
        'report_period': report_period,
        'report_email_form': report_email_form,
        'search_query': search_query,
        'reconciliation_report_summary': reconciliation_report_summary,
        'report_export_url': f"{reverse('backup-dashboard')}?show_reconciliation_reports=1",
        'status_labels_json': json.dumps(status_labels),
        'status_counts_json': json.dumps(status_counts),
        'monthly_labels_json': json.dumps(monthly_labels),
        'monthly_counts_json': json.dumps(monthly_counts),
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

    custody_transfers_open = shipments.filter(status__in=['Dispatched', 'In Transit']).count()
    custody_transfers_completed = shipments.filter(status__iexact='Delivered').count()
    missing_handoffs = AuditLog.objects.filter(action__icontains='handoff').count()
    unverified_deliveries = shipments.filter(status__iexact='Delivered', delivery_status__in=['', 'Partially Delivered']).count()
    chain_of_custody_compliance = int(max(0, min(100, 100 - (missing_handoffs * 2))))

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
        'open_discrepancies': open_discrepancies,
        'recent_activity': recent_activity,
        'custody_transfers_open': custody_transfers_open,
        'custody_transfers_completed': custody_transfers_completed,
        'missing_handoffs': missing_handoffs,
        'unverified_deliveries': unverified_deliveries,
        'chain_of_custody_compliance': chain_of_custody_compliance,
        **chart_data,
    }
    return render(request, 'operations_dashboard.html', context)


@user_passes_test(lambda u: u.is_superuser or is_backup_administrator(u), login_url='signin')
@login_required(login_url='signin')
def add_tape(request):
    form = TapeForm(request.POST or None)

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
