import uuid
from datetime import time, timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import models
from django.db.models import Count
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import NoReverseMatch, reverse
from django.utils import timezone


def generate_shipment_id():
    return f"SHP-{uuid.uuid4().hex[:8].upper()}"


class ApplicationSetting(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    LOG_LEVEL_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]
    DEFAULT_PANEL_CHOICES = [
        ('inventory', 'Inventory'),
        ('shipments', 'Shipments'),
        ('reports', 'Reports'),
        ('audit', 'Audit Logs'),
    ]

    backup_retention_days = models.PositiveIntegerField(default=90)
    shipment_notification_enabled = models.BooleanField(default=True)
    email_alerts_enabled = models.BooleanField(default=True)
    allow_offsite_transfers = models.BooleanField(default=True)
    max_tapes_per_shipment = models.PositiveIntegerField(default=50)
    audit_logging_level = models.CharField(max_length=20, choices=LOG_LEVEL_CHOICES, default='info')
    audit_retention_years = models.PositiveIntegerField(default=7)
    default_dashboard_section = models.CharField(max_length=50, choices=DEFAULT_PANEL_CHOICES, default='inventory')
    maintenance_window_start = models.TimeField(default=time(2, 0))
    maintenance_window_end = models.TimeField(default=time(4, 0))
    next_reconciliation_date = models.DateField(null=True, blank=True)
    reconciliation_alert_start_days_before = models.PositiveIntegerField(default=7)
    reconciliation_alert_duration_days = models.PositiveIntegerField(default=14)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Application Setting'
        verbose_name_plural = 'Application Settings'

    def __str__(self):
        return 'Global Application Settings'


class BankBranch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
    ]

    branch_code = models.CharField(max_length=50, unique=True)
    branch_name = models.CharField(max_length=200)
    region = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Bank Branch'
        verbose_name_plural = 'Bank Branches'
        ordering = ['branch_name']

    def __str__(self):
        return f"{self.branch_name} ({self.branch_code})"


class BranchImportLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('failed', 'Failed'),
    ]

    filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='branch_import_logs')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    total_rows = models.PositiveIntegerField(default=0)
    created_records = models.PositiveIntegerField(default=0)
    updated_records = models.PositiveIntegerField(default=0)
    skipped_records = models.PositiveIntegerField(default=0)
    failed_records = models.PositiveIntegerField(default=0)
    import_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='success')

    class Meta:
        verbose_name = 'Branch Import Log'
        verbose_name_plural = 'Branch Import Logs'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.filename} ({self.uploaded_at:%Y-%m-%d %H:%M})"


class CustomUser(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)

    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('auditor', 'IT Compliance Auditor'),
        ('user', 'User'),
        ('operations_manager', 'Operations Manager'),
    ]

    role = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        default='user'
    )
    assigned_branch = models.ForeignKey(
        'BankBranch',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_users'
    )
    verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.username


class RoleTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.OneToOneField('auth.Group', on_delete=models.CASCADE)
    features = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Role Template'
        verbose_name_plural = 'Role Templates'

    def __str__(self):
        return self.group.name


class TapeInventory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    active_count = models.PositiveIntegerField(default=0)
    archived_count = models.PositiveIntegerField(default=0)
    retention_due = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name


class Tape(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    TAPE_TYPE_CHOICES = [
        ('LTO-6', 'LTO-6'),
        ('LTO-7', 'LTO-7'),
        ('LTO-8', 'LTO-8'),
        ('LTO-9', 'LTO-9'),
    ]

    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Retained', 'Retained'),
        ('Off-Site', 'Off-Site'),
        ('In Transit', 'In Transit'),
        ('Scratch Eligible', 'Scratch Eligible'),
        ('Damaged', 'Damaged'),
        ('Missing', 'Missing'),
    ]

    volser = models.CharField(max_length=100, unique=True)
    barcode = models.CharField(max_length=100, unique=True)
    rfid_tag = models.CharField(max_length=100, blank=True, null=True)
    tape_type = models.CharField(max_length=10, choices=TAPE_TYPE_CHOICES)
    manufacturer = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    current_location = models.CharField(max_length=200, blank=True)
    retention_end_date = models.DateField()
    legal_hold = models.BooleanField(default=False)
    audit_hold = models.BooleanField(default=False)
    remarks = models.TextField(blank=True)
    date_registered = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_registered']

    def get_scratch_block_reasons(self, new_status, legal_hold=None, audit_hold=None):
        if new_status not in {'Scratch', 'Scratch Eligible'}:
            return []

        if legal_hold is None:
            legal_hold = self.legal_hold
        if audit_hold is None:
            audit_hold = self.audit_hold

        reasons = []
        if legal_hold:
            reasons.append('legal hold')
        if audit_hold:
            reasons.append('audit hold')
        if self.requests.filter(status__in=['Pending', 'Approved']).exists():
            reasons.append('ongoing restore dependency')
        if self.exceptions.exists() or self.reconciliation_results.exclude(resolution_status__in=['Resolved', 'Closed']).exists():
            reasons.append('unresolved exception')
        return reasons

    def get_scratch_rejection_message(self, new_status, reasons):
        reason_text = ', '.join(reasons)
        return f"Cannot mark tape as {new_status} while it is under {reason_text}."

    def generate_barcode(self):
        normalized_volser = self.volser.strip().upper().replace(' ', '').replace('-', '')
        parts = [normalized_volser]

        if self.tape_type:
            parts.append(self.tape_type.replace(' ', '').upper())

        if self.manufacturer:
            manufacturer_code = ''.join(ch for ch in self.manufacturer.strip().upper() if ch.isalnum())[:3]
            if manufacturer_code:
                parts.append(manufacturer_code)

        if self.current_location:
            location_code = ''.join(ch for ch in self.current_location.strip().upper() if ch.isalnum())[:3]
            if location_code:
                parts.append(location_code)

        if self.rfid_tag:
            rfid_code = ''.join(ch for ch in self.rfid_tag.strip().upper() if ch.isalnum())[-4:]
            if rfid_code:
                parts.append(rfid_code)

        barcode_base = '-'.join(parts)
        barcode_candidate = barcode_base
        suffix = 1
        while Tape.objects.filter(barcode=barcode_candidate).exclude(pk=self.pk).exists():
            barcode_candidate = f"{barcode_base}-{suffix:02d}"
            suffix += 1
        return barcode_candidate

    def save(self, *args, **kwargs):
        if not self.barcode:
            self.barcode = self.generate_barcode()

        previous_status = None
        if self.pk:
            previous_status = Tape.objects.filter(pk=self.pk).values_list('status', flat=True).first()

        if self.status in {'Scratch', 'Scratch Eligible'} and (not self.pk or previous_status != self.status):
            reasons = self.get_scratch_block_reasons(self.status, legal_hold=self.legal_hold, audit_hold=self.audit_hold)
            if reasons:
                raise ValidationError(self.get_scratch_rejection_message(self.status, reasons))

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.volser} ({self.barcode})"


class SchemaChangeLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    column_name = models.CharField(max_length=255)
    detected_data_type = models.CharField(max_length=50)
    target_table = models.CharField(max_length=255)
    source_excel_filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='schema_change_logs')
    uploaded_date = models.DateTimeField(default=timezone.now)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_schema_changes')
    approval_timestamp = models.DateTimeField(null=True, blank=True)
    sql_executed = models.TextField(blank=True)
    synchronization_status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('applied', 'Applied'), ('failed', 'Failed'), ('cancelled', 'Cancelled')],
        default='pending',
    )
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-uploaded_date', '-created_at']

    def __str__(self):
        return f"{self.column_name} -> {self.detected_data_type}"


class TapeRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Cancelled', 'Cancelled'),
    ]

    tape = models.ForeignKey('Tape', on_delete=models.CASCADE, related_name='requests')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='requested_tapes')
    quantity = models.PositiveIntegerField(default=1)
    destination_location = models.CharField(max_length=200, blank=True)
    receiving_organization = models.CharField(max_length=200, blank=True)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    request_date = models.DateTimeField(default=timezone.now)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='approved_tape_requests'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approval_notes = models.TextField(blank=True)
    shipment = models.ForeignKey('Shipment', null=True, blank=True, on_delete=models.SET_NULL, related_name='tape_requests')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-request_date', '-created_at']

    def __str__(self):
        return f"Tape request for {self.tape.volser} by {self.requested_by.username}"


def generate_reconciliation_id():
    return f"REC-{uuid.uuid4().hex[:10].upper()}"


class Reconciliation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
        ('Closed', 'Closed'),
    ]

    reconciliation_id = models.CharField(max_length=20, unique=True, editable=False, default=generate_reconciliation_id)
    reconciliation_date = models.DateField(default=timezone.localdate)
    location = models.CharField(max_length=200)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='performed_reconciliations'
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_reconciliations'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='approved_reconciliations'
    )
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Reconciliation'
        verbose_name_plural = 'Reconciliations'
        ordering = ['-reconciliation_date', '-created_at']

    def __str__(self):
        return f"{self.reconciliation_id} - {self.location}"


class ReconciliationResult(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ISSUE_TYPE_CHOICES = [
        ('Missing', 'Missing'),
        ('Misplaced', 'Misplaced'),
        ('Unexpected', 'Unexpected'),
        ('Duplicate', 'Duplicate'),
        ('Damaged', 'Damaged'),
        ('None', 'None'),
    ]
    RESOLUTION_STATUS_CHOICES = [
        ('Open', 'Open'),
        ('Under Investigation', 'Under Investigation'),
        ('Resolved', 'Resolved'),
        ('Closed', 'Closed'),
    ]

    reconciliation = models.ForeignKey('Reconciliation', on_delete=models.CASCADE, related_name='results')
    tape = models.ForeignKey('Tape', null=True, blank=True, on_delete=models.SET_NULL, related_name='reconciliation_results')
    barcode = models.CharField(max_length=100, blank=True)
    issue_type = models.CharField(max_length=20, choices=ISSUE_TYPE_CHOICES, default='None')
    expected_location = models.CharField(max_length=200, blank=True)
    actual_location = models.CharField(max_length=200, blank=True)
    remarks = models.TextField(blank=True)
    resolution_status = models.CharField(max_length=20, choices=RESOLUTION_STATUS_CHOICES, default='Open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Reconciliation Result'
        verbose_name_plural = 'Reconciliation Results'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if self.tape and not self.barcode:
            self.barcode = self.tape.barcode
        super().save(*args, **kwargs)

    def __str__(self):
        identifier = self.tape.volser if self.tape else 'Unknown Tape'
        return f"{self.reconciliation.reconciliation_id} - {identifier} ({self.issue_type})"


class Shipment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    SHIPMENT_TYPE_CHOICES = [
        ('Off-Site Transfer', 'Off-Site Transfer'),
        ('Return', 'Return'),
        ('Retrieval', 'Retrieval'),
        ('Destruction', 'Destruction'),
    ]

    SHIPMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('More Info Requested', 'More Info Requested'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Dispatched', 'Dispatched'),
        ('Picked Up', 'Picked Up'),
        ('In Transit', 'In Transit'),
        ('Delivered', 'Delivered'),
        ('Completed', 'Completed'),
        ('Return Accepted', 'Return Accepted'),
        ('Cancelled', 'Cancelled'),
    ]

    PRIORITY_LEVEL_CHOICES = [
        ('Normal', 'Normal'),
        ('High', 'High'),
        ('Critical', 'Critical'),
    ]

    DELIVERY_STATUS_CHOICES = [
        ('Delivered', 'Delivered'),
        ('Partially Delivered', 'Partially Delivered'),
    ]

    shipment_id = models.CharField(
        max_length=50,
        unique=True,
        default=generate_shipment_id,
        editable=False,
    )
    shipment_date = models.DateField(default=timezone.localdate)
    shipment_type = models.CharField(max_length=50, choices=SHIPMENT_TYPE_CHOICES)
    status = models.CharField(max_length=50, choices=SHIPMENT_STATUS_CHOICES, default='Pending')
    priority_level = models.CharField(max_length=20, choices=PRIORITY_LEVEL_CHOICES, default='Normal')
    number_of_tapes = models.PositiveIntegerField(default=0)

    source_location = models.CharField(max_length=200, blank=True)
    requesting_branch = models.ForeignKey(
        'BankBranch',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='shipments'
    )
    releasing_custodian = models.CharField(max_length=150, blank=True)
    release_datetime = models.DateTimeField(null=True, blank=True)

    destination_location = models.CharField(max_length=200, blank=True)
    receiving_organization = models.CharField(max_length=200, blank=True)
    expected_delivery_date = models.DateField(null=True, blank=True)
    receiving_custodian = models.CharField(max_length=150, blank=True)

    courier_name = models.CharField(max_length=150, blank=True)
    courier_contact = models.CharField(max_length=100, blank=True)
    vehicle_number = models.CharField(max_length=100, blank=True)
    tracking_number = models.CharField(max_length=150, blank=True)

    tapes = models.ManyToManyField('Tape', blank=True, related_name='shipments')

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='approved_shipments'
    )
    approval_date = models.DateTimeField(null=True, blank=True)
    approval_remarks = models.TextField(blank=True)

    delivery_date = models.DateField(null=True, blank=True)
    delivery_time = models.TimeField(null=True, blank=True)
    received_by = models.CharField(max_length=150, blank=True)
    delivery_status = models.CharField(max_length=30, choices=DELIVERY_STATUS_CHOICES, blank=True)
    delivery_notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_shipments'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='updated_shipments'
    )
    last_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-shipment_date', '-created_at']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return self.shipment_id

    def has_dual_custody(self):
        return bool(self.releasing_custodian and self.receiving_custodian)

    def manifest_count(self):
        return self.tapes.count()

    def is_manifest_complete(self):
        return self.number_of_tapes > 0 and self.tapes.exists() and self.number_of_tapes == self.tapes.count()

    def is_awaiting_evidence(self):
        return self.status in ['Pending', 'More Info Requested'] and (
            not self.courier_name or not self.vehicle_number or not self.tracking_number
        )

    def is_overdue_for_approval(self):
        if not self.shipment_date:
            return False
        return self.status in ['Pending', 'More Info Requested'] and self.shipment_date < (timezone.localdate() - timedelta(days=2))

    def compliance_checks(self):
        checks = {
            'tape_exists': self.tapes.exists(),
            'duplicate_tapes': not self.tapes.values('id').annotate(count=Count('id')).filter(count__gt=1).exists(),
            'manifest_complete': self.is_manifest_complete(),
            'retention_compliance': not self.tapes.filter(retention_end_date__lt=(self.expected_delivery_date or timezone.localdate())).exists(),
            'legal_hold': not self.tapes.filter(legal_hold=True).exists(),
            'audit_hold': not self.tapes.filter(audit_hold=True).exists(),
            'damage_status': not self.tapes.filter(status='Damaged').exists(),
            'missing_tape_status': not self.tapes.filter(status='Missing').exists(),
            'dual_custody': self.has_dual_custody(),
        }
        return checks

    def compliance_passed(self):
        return all(self.compliance_checks().values())

    def risk_score(self):
        score = 0
        if self.tapes.filter(status='Missing').exists():
            score += 30
        if self.tapes.filter(status='Damaged').exists():
            score += 25
        if self.tapes.filter(legal_hold=True).exists():
            score += 20
        if self.tapes.filter(audit_hold=True).exists():
            score += 20
        if not self.is_manifest_complete():
            score += 15
        if self.priority_level == 'Critical':
            score += 15
        elif self.priority_level == 'High':
            score += 8
        return min(score, 100)

    def risk_level(self):
        score = self.risk_score()
        if score >= 70:
            return 'Critical'
        if score >= 45:
            return 'High'
        if score >= 20:
            return 'Medium'
        return 'Low'

    def risk_recommendation(self):
        level = self.risk_level()
        if level == 'Critical':
            return 'Do not approve until all risks are addressed and tape status is reconciled.'
        if level == 'High':
            return 'Review manifest and custody details before approval.'
        if level == 'Medium':
            return 'Confirm documentation and custody handover before approval.'
        return 'Proceed with standard approval workflows.'


class ShipmentApprovalHistory(models.Model):
    ACTION_CHOICES = [
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Requested More Information', 'Requested More Information'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shipment = models.ForeignKey('Shipment', on_delete=models.CASCADE, related_name='approval_history')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    comments = models.TextField(blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Shipment Approval History'
        verbose_name_plural = 'Shipment Approval History'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.shipment.shipment_id} - {self.action} by {self.user.username if self.user else "System"}'


def generate_receipt_id():
    return f"RCT-{uuid.uuid4().hex[:8].upper()}"


def generate_delivery_id():
    return f"DLV-{uuid.uuid4().hex[:8].upper()}"


class CourierProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='courier_profile'
    )
    courier_id = models.CharField(max_length=50, unique=True)
    full_name = models.CharField(max_length=200)
    company_name = models.CharField(max_length=200, blank=True)
    phone_number = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    employee_number = models.CharField(max_length=50, blank=True)
    active_status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Courier Profile'
        verbose_name_plural = 'Courier Profiles'
        ordering = ['full_name']

    def __str__(self):
        return f"{self.full_name} ({self.courier_id})"


class ShipmentReceipt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    receipt_id = models.CharField(max_length=50, unique=True, default=generate_receipt_id)
    shipment = models.ForeignKey('Shipment', on_delete=models.CASCADE, related_name='receipts')
    courier = models.ForeignKey(CourierProfile, on_delete=models.CASCADE, related_name='receipts')
    manifest_reference = models.CharField(max_length=150, blank=True)
    pickup_date = models.DateField(default=timezone.localdate)
    pickup_time = models.TimeField(default=timezone.localtime)
    pickup_location = models.CharField(max_length=200)
    custody_confirmed = models.BooleanField(default=False)
    confirmation_timestamp = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    all_tapes_scanned = models.BooleanField(default=False)
    manifest_verified = models.BooleanField(default=False)
    tape_count_matched = models.BooleanField(default=False)
    no_damaged_tapes = models.BooleanField(default=True)
    custody_accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Shipment Receipt'
        verbose_name_plural = 'Shipment Receipts'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.receipt_id} for {self.shipment.shipment_id}"


class DeliveryConfirmation(models.Model):
    DELIVERY_STATUS_CHOICES = [
        ('Delivered', 'Delivered'),
        ('Partially Delivered', 'Partially Delivered'),
        ('Delayed', 'Delayed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    delivery_id = models.CharField(max_length=50, unique=True, default=generate_delivery_id)
    shipment = models.ForeignKey('Shipment', on_delete=models.CASCADE, related_name='deliveries')
    courier = models.ForeignKey(CourierProfile, on_delete=models.CASCADE, related_name='deliveries')
    destination_location = models.CharField(max_length=200)
    receiving_custodian = models.CharField(max_length=150)
    delivery_date = models.DateField(default=timezone.localdate)
    delivery_time = models.TimeField(default=timezone.localtime)
    delivery_status = models.CharField(max_length=30, choices=DELIVERY_STATUS_CHOICES, default='Delivered')
    notes = models.TextField(blank=True)
    manifest_matched = models.BooleanField(default=False)
    all_tapes_delivered = models.BooleanField(default=False)
    discrepancies_resolved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Delivery Confirmation'
        verbose_name_plural = 'Delivery Confirmations'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.delivery_id} for {self.shipment.shipment_id}"


def generate_exception_id():
    return f"EXC-{uuid.uuid4().hex[:8].upper()}"


class ShipmentException(models.Model):
    EXCEPTION_TYPE_CHOICES = [
        ('Missing Tape', 'Missing Tape'),
        ('Damaged Tape', 'Damaged Tape'),
        ('Incorrect Manifest', 'Incorrect Manifest'),
        ('Delivery Delay', 'Delivery Delay'),
        ('Custody Dispute', 'Custody Dispute'),
        ('Unexpected Tape', 'Unexpected Tape'),
    ]

    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('Investigating', 'Investigating'),
        ('Resolved', 'Resolved'),
        ('Closed', 'Closed'),
    ]

    SEVERITY_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Critical', 'Critical'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exception_id = models.CharField(max_length=50, unique=True, default=generate_exception_id)
    shipment = models.ForeignKey('Shipment', on_delete=models.CASCADE, related_name='exceptions')
    tape = models.ForeignKey('Tape', null=True, blank=True, on_delete=models.SET_NULL, related_name='exceptions')
    exception_type = models.CharField(max_length=50, choices=EXCEPTION_TYPE_CHOICES)
    description = models.TextField()
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    reported_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='Medium')

    class Meta:
        verbose_name = 'Shipment Exception'
        verbose_name_plural = 'Shipment Exceptions'
        ordering = ['-reported_date']

    def __str__(self):
        return f"{self.exception_id} ({self.exception_type})"


class ShipmentTransportEvent(models.Model):
    EVENT_TYPE_CHOICES = [
        ('Picked Up', 'Picked Up'),
        ('In Transit', 'In Transit'),
        ('Delayed', 'Delayed'),
        ('Delivered', 'Delivered'),
        ('Return Accepted', 'Return Accepted'),
        ('Return Delivered', 'Return Delivered'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shipment = models.ForeignKey('Shipment', on_delete=models.CASCADE, related_name='transport_events')
    courier = models.ForeignKey(CourierProfile, null=True, blank=True, on_delete=models.SET_NULL, related_name='transport_events')
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES)
    event_date = models.DateField(default=timezone.localdate)
    event_time = models.TimeField(default=timezone.localtime)
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Shipment Transport Event'
        verbose_name_plural = 'Shipment Transport Events'
        ordering = ['-event_date', '-event_time', '-created_at']

    def __str__(self):
        return f"{self.shipment.shipment_id} - {self.event_type}"


class ReportTemplate(models.Model):
    id  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class MonthlyReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report_month = models.DateField()
    report_name = models.CharField(max_length=200)
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Monthly Report'
        verbose_name_plural = 'Monthly Reports'
        ordering = ['-report_month', '-created_at']

    def __str__(self):
        return f"{self.report_name} ({self.report_month.strftime('%B %Y')})"


def infer_log_type(*values):
    haystack = ' '.join(str(value or '').lower() for value in values if value)
    if any(keyword in haystack for keyword in ['login', 'logout', 'auth', 'authenticate', 'password', 'session', 'token', 'signin']):
        return 'Authentication'
    if any(keyword in haystack for keyword in ['shipment', 'courier', 'dispatch', 'delivery', 'manifest', 'tracking']):
        return 'Shipment'
    if any(keyword in haystack for keyword in ['approve', 'approval', 'approved', 'rejected', 'reject', 'decision']):
        return 'Approval'
    if any(keyword in haystack for keyword in ['inventory', 'tape', 'vault', 'barcode', 'retention', 'reconciliation']):
        return 'Inventory'
    if any(keyword in haystack for keyword in ['audit', 'audit trail', 'compliance', 'exception', 'review']):
        return 'Audit'
    if any(keyword in haystack for keyword in ['notification', 'email', 'alert', 'reminder']):
        return 'Notification'
    if any(keyword in haystack for keyword in ['api', 'endpoint', 'rest']):
        return 'API'
    if any(keyword in haystack for keyword in ['import', 'upload', 'excel']):
        return 'Import'
    if any(keyword in haystack for keyword in ['export', 'download']):
        return 'Export'
    if any(keyword in haystack for keyword in ['security', 'permission', 'role', 'user', 'group']):
        return 'Security'
    if any(keyword in haystack for keyword in ['config', 'configuration', 'settings']):
        return 'Configuration'
    if any(keyword in haystack for keyword in ['error', 'failed', 'exception']):
        return 'Error'
    if any(keyword in haystack for keyword in ['request', 'submitted', 'created', 'updated']):
        return 'Request'
    return 'System'


def infer_module(*values):
    haystack = ' '.join(str(value or '').lower() for value in values if value)
    if any(keyword in haystack for keyword in ['shipment', 'courier', 'dispatch', 'manifest', 'delivery']):
        return 'Shipment'
    if any(keyword in haystack for keyword in ['tape', 'inventory', 'barcode', 'vault', 'retention']):
        return 'Inventory'
    if any(keyword in haystack for keyword in ['branch', 'bank']):
        return 'Bank Branches'
    if any(keyword in haystack for keyword in ['user', 'role', 'permission', 'group']):
        return 'Users'
    if any(keyword in haystack for keyword in ['report', 'compliance', 'audit']):
        return 'Reports'
    if any(keyword in haystack for keyword in ['api', 'endpoint', 'rest']):
        return 'API'
    if any(keyword in haystack for keyword in ['notification', 'alert', 'email']):
        return 'Notifications'
    if any(keyword in haystack for keyword in ['dashboard']):
        return 'Dashboard'
    return 'System'


def infer_status(*values):
    haystack = ' '.join(str(value or '').lower() for value in values if value)
    if any(keyword in haystack for keyword in ['approved', 'approve']):
        return 'Approved'
    if any(keyword in haystack for keyword in ['rejected', 'reject']):
        return 'Rejected'
    if any(keyword in haystack for keyword in ['failed', 'error', 'exception']):
        return 'Failed'
    if any(keyword in haystack for keyword in ['pending', 'submitted', 'created', 'updated']):
        return 'Pending'
    if any(keyword in haystack for keyword in ['success', 'completed', 'done']):
        return 'Success'
    return ''


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    name = models.CharField(max_length=255, blank=True, db_index=True)
    action = models.CharField(max_length=255, blank=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    message = models.CharField(max_length=255, blank=True, db_index=True)
    severity = models.CharField(
        max_length=20,
        choices=[
            ('info', 'Info'),
            ('success', 'Success'),
            ('warning', 'Warning'),
            ('error', 'Error'),
        ],
        default='info',
        db_index=True,
    )
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    @property
    def log_type(self):
        return infer_log_type(self.name, self.action, self.message)

    @property
    def module(self):
        return infer_module(self.name, self.action, self.message)

    @property
    def status(self):
        return infer_status(self.name, self.action, self.message)

    def __str__(self):
        label = self.name or self.action or self.message or 'Audit'
        return f"[{self.severity}] {label}"


@receiver(post_save, sender=AuditLog)
def send_auditlog_email_notification(sender, instance, created, **kwargs):
    if not created:
        return

    if instance.severity not in ['warning', 'error']:
        return

    user = instance.user
    if not user or not user.email:
        return

    application_settings = ApplicationSetting.objects.first() or ApplicationSetting.objects.create()
    if not application_settings.email_alerts_enabled:
        return

    subject = f"New alert: {instance.name or instance.action or 'Audit Notification'}"
    message = (
        f"A new alert was generated in the system.\n\n"
        f"Name: {instance.name}\n"
        f"Action: {instance.action}\n"
        f"Message: {instance.message}\n"
        f"Severity: {instance.severity}\n"
        f"Timestamp: {instance.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
    )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)


DASHBOARD_FEATURE_CATALOG = [
    {
        'key': 'backup_dashboard',
        'name': 'Dashboard',
        'icon': 'bi bi-speedometer2',
        'url_name': 'feature-module',
        'scope': 'backup',
        'description': 'Backup administrator overview',
        'url_params': {},
    },
    {
        'key': 'add_tape',
        'name': 'Add Tape',
        'icon': 'bi bi-plus-circle',
        'url_name': 'feature-module',
        'scope': 'backup',
        'description': 'Create a new tape record',
        'url_params': {'show_add_tape': '1'},
    },
    {
        'key': 'tape_inventory',
        'name': 'Tape Inventory',
        'icon': 'bi bi-hdd-stack',
        'url_name': 'feature-module',
        'scope': 'backup',
        'description': 'Browse tape inventory',
        'url_params': {'show_tape_inventory': '1'},
    },
    {
        'key': 'shipments',
        'name': 'Shipments',
        'icon': 'bi bi-truck',
        'url_name': 'feature-module',
        'scope': 'backup',
        'description': 'Shipment management',
        'url_params': {'show_shipments': '1'},
    },
    {
        'key': 'reconciliation',
        'name': 'Reconciliation',
        'icon': 'bi bi-arrow-repeat',
        'url_name': 'feature-module',
        'scope': 'backup',
        'description': 'Perform reconciliation reviews',
        'url_params': {'show_reconciliation': '1'},
    },
    {
        'key': 'reports',
        'name': 'Reports',
        'icon': 'bi bi-file-earmark-bar-graph',
        'url_name': 'feature-module',
        'scope': 'backup',
        'description': 'Backup reporting',
        'url_params': {'show_reports': 'reports'},
    },
    {
        'key': 'audit_logs',
        'name': 'Audit Logs',
        'icon': 'bi bi-shield-check',
        'url_name': 'feature-module',
        'scope': 'backup',
        'description': 'Review system audit logs',
        'url_params': {'show_audit': '1'},
    },
    {
        'key': 'operations_dashboard',
        'name': 'Operations Dashboard',
        'icon': 'bi bi-speedometer2',
        'url_name': 'feature-module',
        'scope': 'operations',
        'description': 'Operations overview',
        'url_params': {},
    },
    {
        'key': 'shipment_approvals',
        'name': 'Shipment Approvals',
        'icon': 'bi bi-check2-square',
        'url_name': 'feature-module',
        'scope': 'operations',
        'description': 'Approve shipment requests',
        'url_params': {},
    },
    {
        'key': 'exception_management',
        'name': 'Exception Management',
        'icon': 'bi bi-exclamation-triangle',
        'url_name': 'feature-module',
        'scope': 'operations',
        'description': 'Review shipment exceptions',
        'url_params': {'show_reports': 'reports', 'report_category': 'reconciliation'},
    },
]

DASHBOARD_FEATURE_CHOICES = [(entry['key'], entry['name']) for entry in DASHBOARD_FEATURE_CATALOG]


def get_dashboard_feature_catalog(scope=None):
    features = []
    for entry in DASHBOARD_FEATURE_CATALOG:
        if scope and entry['scope'] != scope:
            continue
        features.append({
            'key': entry['key'],
            'name': entry['name'],
            'icon': entry['icon'],
            'url_name': entry['url_name'],
            'url_params': entry.get('url_params', {}),
            'url_kwargs': {'feature_key': entry['key']},
            'scope': entry['scope'],
            'description': entry['description'],
        })
    return features


class DashboardFeaturePermission(models.Model):

    role = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='dashboard_feature_permissions',
        verbose_name='Group'
    )
    feature_key = models.CharField(
        max_length=100,
        choices=DASHBOARD_FEATURE_CHOICES,
        verbose_name='Feature'
    )
    can_view = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Dashboard Feature Permission'
        verbose_name_plural = 'Dashboard Feature Permissions'
        ordering = ['role__name', 'feature_key']

    def __str__(self):
        feature_name = dict(DASHBOARD_FEATURE_CHOICES).get(self.feature_key, self.feature_key)
        return f"{feature_name} → {self.role.name}"

    def get_feature(self):
        for entry in DASHBOARD_FEATURE_CATALOG:
            if entry['key'] == self.feature_key:
                return entry
        return None


class DashboardFeatureExemption(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='dashboard_feature_exemptions',
        verbose_name='User'
    )
    feature_key = models.CharField(
        max_length=100,
        choices=DASHBOARD_FEATURE_CHOICES,
        verbose_name='Feature'
    )
    is_active = models.BooleanField(default=True)
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Dashboard Feature Exemption'
        verbose_name_plural = 'Dashboard Feature Exemptions'
        ordering = ['user__username', 'feature_key']

    def __str__(self):
        feature_name = dict(DASHBOARD_FEATURE_CHOICES).get(self.feature_key, self.feature_key)
        return f"{self.user.username} exempted from {feature_name}"