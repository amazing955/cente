from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AuditLog, CustomUser, MonthlyReport, ReportTemplate, Reconciliation, ReconciliationResult, Shipment, TapeInventory, Tape


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    fieldsets = UserAdmin.fieldsets + (
        ('Extra info', {'fields': ('role',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Extra info', {'fields': ('role',)}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active', 'groups')


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
    list_display = ('timestamp', 'severity', 'message')
    list_filter = ('severity',)
    ordering = ('-timestamp',)