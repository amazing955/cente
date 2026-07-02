from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .admin_bank_branch import BankBranchAdmin  # noqa: F401
from .models import (
    AuditLog,
    BankBranch,
    BranchImportLog,
    CustomUser,
    DashboardFeatureExemption,
    DashboardFeaturePermission,
    MonthlyReport,
    ReportTemplate,
    Reconciliation,
    ReconciliationResult,
    Shipment,
    TapeInventory,
    Tape,
)


class CustomUserAdminForm(forms.ModelForm):
    assigned_branch = forms.ModelChoiceField(
        queryset=BankBranch.objects.filter(status='Active').order_by('branch_name'),
        required=False,
        empty_label='Select an active branch',
        label='Assigned Branch',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = CustomUser
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_branch'].queryset = BankBranch.objects.filter(status='Active').order_by('branch_name')
        role_value = self.data.get('role', self.initial.get('role', getattr(self.instance, 'role', '')))
        self.fields['assigned_branch'].required = str(role_value).strip().lower() == 'operations_manager'

    def clean(self):
        cleaned_data = super().clean()
        role_value = (cleaned_data.get('role') or '').strip().lower()
        assigned_branch = cleaned_data.get('assigned_branch')
        if role_value == 'operations_manager' and not assigned_branch:
            raise forms.ValidationError('Assigned Branch is required.')
        return cleaned_data


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    form = CustomUserAdminForm
    model = CustomUser
    fieldsets = UserAdmin.fieldsets + (
        ('Extra info', {'fields': ('role', 'assigned_branch')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Extra info', {'fields': ('role', 'assigned_branch')}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'assigned_branch', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active', 'groups')
    readonly_fields = ('assigned_branch_code', 'assigned_branch_status')

    def assigned_branch_code(self, obj):
        return obj.assigned_branch.branch_code if obj.assigned_branch else '-'
    assigned_branch_code.short_description = 'Branch Code'

    def assigned_branch_status(self, obj):
        return obj.assigned_branch.status if obj.assigned_branch else '-'
    assigned_branch_status.short_description = 'Branch Status'


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