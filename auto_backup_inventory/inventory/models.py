import uuid
from datetime import time, timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.mail import send_mail
from django.db import models
from django.db.models import Count
from django.db.models.signals import post_save
from django.dispatch import receiver
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Application Setting'
        verbose_name_plural = 'Application Settings'

    def __str__(self):
        return 'Global Application Settings'


class CustomUser(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)

    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('user', 'User'),
    ]

    role = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        default='user'
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

    def __str__(self):
        return f"{self.volser} ({self.barcode})"


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
        ('In Transit', 'In Transit'),
        ('Delivered', 'Delivered'),
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


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=120, blank=True)
    action = models.CharField(max_length=120, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    message = models.CharField(max_length=255, blank=True)
    severity = models.CharField(
        max_length=20,
        choices=[
            ('info', 'Info'),
            ('success', 'Success'),
            ('warning', 'Warning'),
            ('error', 'Error'),
        ],
        default='info'
    )
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

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
