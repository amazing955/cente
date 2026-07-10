import uuid

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.hashers import make_password

from .admin_bank_branch import BankBranchAdmin  # noqa: F401
from .models import (
    AuditLog,
    BankBranch,
    BranchImportLog,
    CourierProfile,
    CustomUser,
    DashboardFeatureExemption,
    DashboardFeaturePermission,
    MonthlyReport,
    Role,
    ReportTemplate,
    UserRoleAssignment,
    Reconciliation,
    ReconciliationResult,
    Shipment,
    TapeInventory,
    Tape,
)


class UserRoleAssignmentInline(admin.TabularInline):
    model = UserRoleAssignment
    extra = 0
    fk_name = 'user'
    autocomplete_fields = ('role', 'assigned_by', 'backup_approved_by', 'supreme_approved_by')
    fields = (
        'role',
        'status',
        'is_primary_dashboard',
        'assigned_by',
        'backup_approved_by',
        'supreme_approved_by',
        'assigned_at',
        'backup_approved_at',
        'supreme_approved_at',
        'activated_at',
        'rejected_at',
        'rejection_reason',
    )
    readonly_fields = ('assigned_at', 'backup_approved_at', 'supreme_approved_at', 'activated_at', 'rejected_at')


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'dashboard_key', 'group', 'is_active', 'sort_order')
    list_filter = ('dashboard_key', 'is_active')
    search_fields = ('name', 'slug', 'group__name', 'description')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(UserRoleAssignment)
class UserRoleAssignmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'status', 'is_primary_dashboard', 'assigned_at', 'activated_at')
    list_filter = ('status', 'is_primary_dashboard', 'role__dashboard_key')
    search_fields = ('user__username', 'user__email', 'role__name', 'role__dashboard_key')
    autocomplete_fields = ('user', 'role', 'assigned_by', 'backup_approved_by', 'supreme_approved_by')
    readonly_fields = ('assigned_at', 'backup_approved_at', 'supreme_approved_at', 'activated_at', 'rejected_at', 'audit_history')


class BaseCustomUserAdminForm(forms.ModelForm):
    password = forms.CharField(
        required=False,
        label='Password',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )
    assigned_branch = forms.ModelChoiceField(
        queryset=BankBranch.objects.filter(status='Active').order_by('branch_name'),
        required=False,
        empty_label='Select an active branch',
        label='Assigned Branch',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    vehicle_number = forms.CharField(
        required=False,
        label='Vehicle Number',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Required for courier accounts'}),
    )

    class Meta:
        model = CustomUser
        fields = [
            'username',
            'email',
            'password',
            'first_name',
            'last_name',
            'is_staff',
            'is_active',
            'groups',
            'role',
            'assigned_branch',
            'vehicle_number',
            'verified',
            'verified_at',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password'].required = not bool(getattr(self.instance, 'pk', None))
        self.fields['assigned_branch'].queryset = BankBranch.objects.filter(status='Active').order_by('branch_name')
        role_value = self.data.get('role', self.initial.get('role', getattr(self.instance, 'role', '')))
        self.fields['assigned_branch'].required = str(role_value).strip().lower() == 'operations_manager'

    def clean(self):
        cleaned_data = super().clean()
        role_value = (cleaned_data.get('role') or '').strip().lower()
        assigned_branch = cleaned_data.get('assigned_branch')
        vehicle_number = (cleaned_data.get('vehicle_number') or '').strip()
        selected_groups = cleaned_data.get('groups') or []
        is_courier_group = any(str(group.name).strip().lower() == 'courier' for group in selected_groups)

        if role_value == 'operations_manager' and not assigned_branch:
            raise forms.ValidationError('Assigned Branch is required.')
        if (role_value == 'courier' or is_courier_group) and not vehicle_number:
            raise forms.ValidationError('Vehicle Number is required for courier accounts.')
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        password = self.cleaned_data.get('password') or ''
        if password:
            instance.password = make_password(password)
        if commit:
            instance.save()
        return instance


class CustomUserAdminForm(BaseCustomUserAdminForm):
    pass


class CustomUserChangeForm(BaseCustomUserAdminForm):
    pass


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserAdminForm
    form = CustomUserChangeForm
    model = CustomUser
    inlines = (UserRoleAssignmentInline,)
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password', 'first_name', 'last_name', 'is_staff', 'is_active', 'groups')}),
        ('Extra info', {'fields': ('role', 'assigned_branch', 'vehicle_number', 'verified', 'verified_at')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('username', 'email', 'password', 'first_name', 'last_name', 'is_staff', 'is_active', 'groups')}),
        ('Extra info', {'fields': ('role', 'assigned_branch', 'vehicle_number', 'verified', 'verified_at')}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'primary_dashboard_role', 'assigned_roles_summary', 'assigned_branch', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active', 'groups')
    readonly_fields = ('assigned_branch_code', 'assigned_branch_status', 'assigned_roles_summary', 'primary_dashboard_role', 'role_assignment_status_summary')

    def assigned_roles_summary(self, obj):
        assignments = obj.role_assignments.select_related('role').all()
        if not assignments:
            return '-'
        labels = []
        for assignment in assignments:
            marker = ' (Primary)' if assignment.is_primary_dashboard else ''
            labels.append(f'{assignment.role.name} [{assignment.status}]{marker}')
        return ', '.join(labels)
    assigned_roles_summary.short_description = 'Assigned Roles'

    def primary_dashboard_role(self, obj):
        assignment = obj.primary_role_assignment
        if assignment and assignment.role:
            return assignment.role.name
        return obj.get_primary_dashboard_key().replace('_', ' ').title()
    primary_dashboard_role.short_description = 'Primary Role'

    def role_assignment_status_summary(self, obj):
        assignments = obj.role_assignments.all()
        if not assignments:
            return 'No role assignments'
        counts = {
            status: assignments.filter(status=status).count()
            for status in ['Pending', 'Backup Approved', 'Supreme Approved', 'Active', 'Rejected']
        }
        return ', '.join(f'{label}: {value}' for label, value in counts.items() if value)
    role_assignment_status_summary.short_description = 'Approval Status'

    def assigned_branch_code(self, obj):
        return obj.assigned_branch.branch_code if obj.assigned_branch else '-'
    assigned_branch_code.short_description = 'Branch Code'

    def assigned_branch_status(self, obj):
        return obj.assigned_branch.status if obj.assigned_branch else '-'
    assigned_branch_status.short_description = 'Branch Status'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        vehicle_number = (form.cleaned_data.get('vehicle_number') or '').strip()
        selected_groups = form.cleaned_data.get('groups') or []
        is_courier_group = any(str(group.name).strip().lower() == 'courier' for group in selected_groups)
        if not is_courier_group or not vehicle_number:
            return

        courier_profile = CourierProfile.objects.filter(user=obj).first()
        if courier_profile:
            courier_profile.vehicle_number = vehicle_number
            courier_profile.full_name = obj.get_full_name() or obj.username
            courier_profile.email = obj.email or ''
            courier_profile.save(update_fields=['vehicle_number', 'full_name', 'email'])
        else:
            CourierProfile.objects.create(
                user=obj,
                courier_id=f'CR-{uuid.uuid4().hex[:8].upper()}',
                full_name=obj.get_full_name() or obj.username,
                email=obj.email or '',
                vehicle_number=vehicle_number,
                active_status=True,
            )


@admin.register(DashboardFeaturePermission)
class DashboardFeaturePermissionAdmin(admin.ModelAdmin):
    list_display = ('role', 'feature_key', 'can_view')
    list_filter = ('role', 'can_view', 'feature_key')
    search_fields = ('role__name', 'feature_key')


@admin.register(DashboardFeatureExemption)
class DashboardFeatureExemptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'feature_key', 'is_active', 'reason')
    list_filter = ('is_active', 'feature_key')
    search_fields = ('user__username', 'user__email', 'feature_key', 'reason')


@admin.register(TapeInventory)
class TapeInventoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'active_count', 'archived_count', 'retention_due')


@admin.register(Tape)
class TapeAdmin(admin.ModelAdmin):
    list_display = ('volser', 'barcode', 'tape_type', 'status', 'current_location', 'retention_end_date', 'legal_hold', 'audit_hold', 'date_registered')
    list_filter = ('tape_type', 'status', 'legal_hold', 'audit_hold')
    search_fields = ('volser', 'barcode', 'rfid_tag', 'current_location')


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = (
        'shipment_id',
        'shipment_date',
        'shipment_type',
        'status',
        'priority_level',
        'number_of_tapes',
        'destination_location',
        'expected_delivery_date',
        'created_at',
    )
    list_filter = ('status', 'shipment_type', 'priority_level')
    search_fields = ('shipment_id', 'source_location', 'destination_location', 'courier_name', 'tracking_number')


@admin.register(Reconciliation)
class ReconciliationAdmin(admin.ModelAdmin):
    list_display = ('reconciliation_id', 'reconciliation_date', 'location', 'status', 'performed_by', 'created_at')
    list_filter = ('status', 'reconciliation_date')
    search_fields = ('reconciliation_id', 'location', 'performed_by__username')


@admin.register(ReconciliationResult)
class ReconciliationResultAdmin(admin.ModelAdmin):
    list_display = ('reconciliation', 'tape', 'issue_type', 'resolution_status', 'updated_at')
    list_filter = ('issue_type', 'resolution_status')
    search_fields = ('reconciliation__reconciliation_id', 'tape__volser', 'expected_location', 'actual_location')


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')


@admin.register(MonthlyReport)
class MonthlyReportAdmin(admin.ModelAdmin):
    list_display = ('report_name', 'report_month', 'generated_by', 'created_at')
    list_filter = ('report_month',)
    search_fields = ('report_name', 'generated_by__username')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'severity', 'module', 'status', 'action', 'name')
    list_filter = ('severity', 'is_read')
    search_fields = ('name', 'action', 'message', 'user__username')
    ordering = ('-timestamp',)
    readonly_fields = ('timestamp', 'log_type', 'module', 'status')