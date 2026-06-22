from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


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
    shipment_id = models.CharField(max_length=50, unique=True)
    status = models.CharField(
        max_length=50,
        choices=[
            ('In Transit', 'In Transit'),
            ('Delivered', 'Delivered'),
            ('Pending', 'Pending'),
            ('Delayed', 'Delayed'),
        ],
        default='Pending'
    )
    eta = models.CharField(max_length=50)

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

    
