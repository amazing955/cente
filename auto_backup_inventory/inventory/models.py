import uuid
from datetime import time

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


def generate_shipment_id():
    return f"SHP-{uuid.uuid4().hex[:8].upper()}"


class ApplicationSetting(models.Model):
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
    group = models.OneToOneField('auth.Group', on_delete=models.CASCADE)
    features = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Role Template'
        verbose_name_plural = 'Role Templates'

    def __str__(self):
        return self.group.name


class TapeInventory(models.Model):
    name = models.CharField(max_length=120)
    active_count = models.PositiveIntegerField(default=0)
    archived_count = models.PositiveIntegerField(default=0)
    retention_due = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name


class Tape(models.Model):
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


class Shipment(models.Model):
    SHIPMENT_TYPE_CHOICES = [
        ('Off-Site Transfer', 'Off-Site Transfer'),
        ('Return', 'Return'),
        ('Retrieval', 'Retrieval'),
        ('Destruction', 'Destruction'),
    ]

    SHIPMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
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


class ReportTemplate(models.Model):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class AuditLog(models.Model):
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

    def __str__(self):
        label = self.name or self.action or self.message or 'Audit'
        return f"[{self.severity}] {label}"

    
