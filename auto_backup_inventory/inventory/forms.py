from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group

from .models import ApplicationSetting, CustomUser, Shipment, Tape


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = [
            'username',
            'email',
            'first_name',
            'last_name',
            'role',
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter username', 'required': True}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email', 'required': True}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
        }


class CustomUserEditForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = [
            'username',
            'email',
            'first_name',
            'last_name',
            'role',
            'is_active',
        ]


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = [
            'username',
            'email',
            'first_name',
            'last_name',
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'required': True}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'required': True}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


FEATURE_CHOICES = [
    ('Inventory Overview', 'Inventory Overview'),
    ('Add Tape', 'Add Tape'),
    ('Edit Tape Details', 'Edit Tape Details'),
    ('View Tape Records', 'View Tape Records'),
    ('Scan Barcode/RFID', 'Scan Barcode/RFID'),
    ('Update Tape Location', 'Update Tape Location'),
    ('Mark Tape as Damaged', 'Mark Tape as Damaged'),
    ('Initiate Shipment Requests', 'Initiate Shipment Requests'),
    ('Perform Reconciliation', 'Perform Reconciliation'),
    ('View Inventory Reports', 'View Inventory Reports'),
    ('View Audit History', 'View Audit History'),
    ('Tape Management', 'Tape Management'),
    ('Shipment Tracking', 'Shipment Tracking'),
    ('Audit Logging', 'Audit Logging'),
    ('Reporting', 'Reporting'),
    ('User Management', 'User Management'),
    ('Security Controls', 'Security Controls'),
    ('Approvals', 'Approvals'),
]


class RoleCreationForm(forms.Form):
    role_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter role name', 'required': True}),
        label='Role Name',
    )
    features = forms.MultipleChoiceField(
        choices=FEATURE_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label='Features',
        required=False,
    )


class RoleFeatureUpdateForm(forms.Form):
    group = forms.ModelChoiceField(
        queryset=Group.objects.all().order_by('name'),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_role_feature_group'}),
        label='Role',
    )
    features = forms.MultipleChoiceField(
        choices=FEATURE_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label='Features',
        required=False,
    )


class UserRoleAssignmentForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=CustomUser.objects.all().order_by('username'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='User',
    )
    group = forms.ModelChoiceField(
        queryset=Group.objects.all().order_by('name'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Role',
    )


class TapeForm(forms.ModelForm):
    class Meta:
        model = Tape
        fields = [
            'volser',
            'barcode',
            'rfid_tag',
            'tape_type',
            'manufacturer',
            'status',
            'current_location',
            'retention_end_date',
            'legal_hold',
            'audit_hold',
            'remarks',
        ]
        widgets = {
            'volser': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter VolSER', 'required': True}),
            'barcode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Barcode', 'required': True}),
            'rfid_tag': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter RFID Tag'}),
            'tape_type': forms.Select(attrs={'class': 'form-select'}),
            'manufacturer': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Manufacturer'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'current_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Current Location'}),
            'retention_end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'required': True}),
            'legal_hold': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'audit_hold': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Add remarks'}),
        }

    def clean_volser(self):
        volser = self.cleaned_data.get('volser')
        qs = Tape.objects.filter(volser__iexact=volser)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('VolSER already exists.')
        return volser

    def clean_barcode(self):
        barcode = self.cleaned_data.get('barcode')
        qs = Tape.objects.filter(barcode__iexact=barcode)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Barcode already exists.')
        return barcode


class ShipmentForm(forms.ModelForm):
    class Meta:
        model = Shipment
        fields = [
            'shipment_date',
            'shipment_type',
            'status',
            'priority_level',
            'number_of_tapes',
            'source_location',
            'releasing_custodian',
            'release_datetime',
            'destination_location',
            'receiving_organization',
            'expected_delivery_date',
            'receiving_custodian',
            'courier_name',
            'courier_contact',
            'vehicle_number',
            'tracking_number',
            'tapes',
            'approved_by',
            'approval_date',
            'approval_remarks',
            'delivery_date',
            'delivery_time',
            'received_by',
            'delivery_status',
            'delivery_notes',
        ]
        widgets = {
            'shipment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'shipment_type': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'priority_level': forms.Select(attrs={'class': 'form-select'}),
            'number_of_tapes': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'source_location': forms.TextInput(attrs={'class': 'form-control'}),
            'releasing_custodian': forms.TextInput(attrs={'class': 'form-control'}),
            'release_datetime': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'destination_location': forms.TextInput(attrs={'class': 'form-control'}),
            'receiving_organization': forms.TextInput(attrs={'class': 'form-control'}),
            'expected_delivery_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'receiving_custodian': forms.TextInput(attrs={'class': 'form-control'}),
            'courier_name': forms.TextInput(attrs={'class': 'form-control'}),
            'courier_contact': forms.TextInput(attrs={'class': 'form-control'}),
            'vehicle_number': forms.TextInput(attrs={'class': 'form-control'}),
            'tracking_number': forms.TextInput(attrs={'class': 'form-control'}),
            'tapes': forms.SelectMultiple(attrs={'class': 'form-select', 'size': '6'}),
            'approved_by': forms.Select(attrs={'class': 'form-select'}),
            'approval_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'approval_remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'delivery_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'delivery_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'received_by': forms.TextInput(attrs={'class': 'form-control'}),
            'delivery_status': forms.Select(attrs={'class': 'form-select'}),
            'delivery_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tapes'].queryset = Tape.objects.order_by('volser')
        self.fields['approved_by'].queryset = CustomUser.objects.filter(is_active=True).order_by('username')
        self.fields['approved_by'].required = False
        self.fields['approval_date'].required = False
        self.fields['approval_remarks'].required = False
        self.fields['delivery_date'].required = False
        self.fields['delivery_time'].required = False
        self.fields['received_by'].required = False
        self.fields['delivery_status'].required = False
        self.fields['delivery_notes'].required = False


class SystemSettingsForm(forms.ModelForm):
    class Meta:
        model = ApplicationSetting
        fields = [
            'backup_retention_days',
            'shipment_notification_enabled',
            'email_alerts_enabled',
            'allow_offsite_transfers',
            'max_tapes_per_shipment',
            'audit_logging_level',
            'audit_retention_years',
            'default_dashboard_section',
            'maintenance_window_start',
            'maintenance_window_end',
        ]
        widgets = {
            'backup_retention_days': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'shipment_notification_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_alerts_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_offsite_transfers': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'max_tapes_per_shipment': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'audit_logging_level': forms.Select(attrs={'class': 'form-select'}),
            'audit_retention_years': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'default_dashboard_section': forms.Select(attrs={'class': 'form-select'}),
            'maintenance_window_start': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'maintenance_window_end': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        }
