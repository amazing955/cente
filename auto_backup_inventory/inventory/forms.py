from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group
from django.core.validators import validate_email
from django.db.models import Q
from django.utils import timezone

from .models import ApplicationSetting, CustomUser, CourierProfile, Reconciliation, ReconciliationResult, Shipment, ShipmentException, ShipmentReceipt, ShipmentTransportEvent, Tape, DeliveryConfirmation


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
            'barcode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Auto-generated from VolSER', 'required': False}),
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance or not self.instance.pk:
            self.fields['barcode'].required = False
            self.fields['barcode'].widget.attrs['placeholder'] = 'Auto-generated from VolSER and tape type'
            self.fields['barcode'].help_text = 'Leave blank to auto-generate barcode.'

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
        if not barcode:
            return barcode
        qs = Tape.objects.filter(barcode__iexact=barcode)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Barcode already exists.')
        return barcode


class AddTapeForm(forms.ModelForm):
    class Meta:
        model = Tape
        fields = [
            'volser',
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

    def save(self, commit=True):
        tape = super().save(commit=False)
        if not tape.barcode:
            tape.barcode = tape.generate_barcode()
        if commit:
            tape.save()
        return tape

class ShipmentForm(forms.ModelForm):
    courier = forms.ModelChoiceField(
        queryset=CourierProfile.objects.filter(active_status=True).order_by('full_name'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Select Courier',
        required=False,
    )

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
            'releasing_custodian': forms.TextInput(attrs={'class': 'form-control', 'readonly': True}),
            'release_datetime': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'destination_location': forms.TextInput(attrs={'class': 'form-control'}),
            'receiving_organization': forms.TextInput(attrs={'class': 'form-control'}),
            'expected_delivery_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'receiving_custodian': forms.TextInput(attrs={'class': 'form-control'}),
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

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
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
        self.fields['receiving_custodian'].required = False
        
        if request and request.user.is_authenticated:
            self.fields['releasing_custodian'].initial = request.user.get_full_name() or request.user.username
        
        self.fields['courier'].help_text = 'Select a courier profile to auto-fill courier details.'

    def clean(self):
        cleaned_data = super().clean()
        tapes = cleaned_data.get('tapes')
        number_of_tapes = cleaned_data.get('number_of_tapes')
        expected_delivery_date = cleaned_data.get('expected_delivery_date')
        releasing_custodian = cleaned_data.get('releasing_custodian')
        receiving_custodian = cleaned_data.get('receiving_custodian')

        if tapes:
            tape_count = tapes.count()
            if number_of_tapes in [None, 0]:
                cleaned_data['number_of_tapes'] = tape_count
                number_of_tapes = tape_count

            if number_of_tapes != tape_count:
                self.add_error(
                    'number_of_tapes',
                    'Number of tapes must equal selected tapes for a complete manifest.'
                )

            if tapes.filter(Q(legal_hold=True) | Q(audit_hold=True)).exists():
                self.add_error(
                    'tapes',
                    'Selected tapes include legal or audit hold records. Remove hold tapes before shipment creation.'
                )

            if tapes.filter(status='Damaged').exists():
                self.add_error(
                    'tapes',
                    'Selected tapes include damaged tapes. Remove damaged tapes before shipment creation.'
                )

            if tapes.filter(status='Missing').exists():
                self.add_error(
                    'tapes',
                    'Selected tapes include missing tapes. Remove missing tapes before shipment creation.'
                )

            if expected_delivery_date:
                retention_issues = tapes.filter(retention_end_date__lt=expected_delivery_date)
                if retention_issues.exists():
                    self.add_error(
                        'expected_delivery_date',
                        'One or more selected tapes violate retention compliance for the expected delivery date.'
                    )

            if not releasing_custodian or not receiving_custodian:
                self.add_error('releasing_custodian', 'Dual custody requires both releasing and receiving custodians.')
                self.add_error('receiving_custodian', 'Dual custody requires both releasing and receiving custodians.')

        return cleaned_data


class ShipmentApprovalDecisionForm(forms.Form):
    shipment_pk = forms.UUIDField(widget=forms.HiddenInput())
    decision = forms.ChoiceField(
        choices=[
            ('approve', 'Approve Shipment'),
            ('reject', 'Reject Shipment'),
            ('more_info', 'Request More Information'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Decision',
        required=True,
    )
    comments = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Add comments or rationale for this decision'}),
        label='Comments',
        required=False,
    )

    def clean(self):
        cleaned_data = super().clean()
        decision = cleaned_data.get('decision')
        comments = cleaned_data.get('comments')
        if decision == 'reject' and not comments:
            raise forms.ValidationError('Comments are required when rejecting a shipment.')
        return cleaned_data


class ShipmentApprovalFilterForm(forms.Form):
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search by shipment ID, source, destination, user'}),
        label='Search',
    )
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Statuses')] + Shipment.SHIPMENT_STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Status',
    )
    priority = forms.ChoiceField(
        required=False,
        choices=[('', 'All Priorities')] + Shipment.PRIORITY_LEVEL_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Priority',
    )
    risk_level = forms.ChoiceField(
        required=False,
        choices=[('', 'All Risk Levels'), ('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High'), ('Critical', 'Critical')],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Risk Level',
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Date From',
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Date To',
    )


class ManifestSearchForm(forms.Form):
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search manifest by VolSER, barcode or RFID'}),
        label='Search Manifest',
    )
    tape_status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Tape Statuses')] + Tape.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Tape Status',
    )


class CourierShipmentFilterForm(forms.Form):
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search shipments by ID, source, destination'}),
        label='Search',
    )
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Statuses')] + Shipment.SHIPMENT_STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Status',
    )
    shipment_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Types')] + Shipment.SHIPMENT_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Shipment Type',
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Dispatch From',
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Dispatch To',
    )


class ScanTapeForm(forms.Form):
    SCAN_METHOD_CHOICES = [
        ('volser', 'VolSER'),
        ('barcode', 'Barcode'),
        ('rfid', 'RFID Tag'),
    ]

    scan_method = forms.ChoiceField(
        choices=SCAN_METHOD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Scan Method',
        required=True,
    )
    scan_value = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Scan or enter VolSER / Barcode / RFID'}),
        label='Scan Value',
        required=True,
    )


class ShipmentReceiptForm(forms.ModelForm):
    class Meta:
        model = ShipmentReceipt
        fields = [
            'manifest_reference',
            'pickup_date',
            'pickup_time',
            'pickup_location',
            'notes',
            'all_tapes_scanned',
            'manifest_verified',
            'tape_count_matched',
            'no_damaged_tapes',
            'custody_accepted',
        ]
        widgets = {
            'manifest_reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Manifest Number'}),
            'pickup_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'pickup_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'pickup_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Pickup Location'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Add pickup notes or exceptions'}),
            'all_tapes_scanned': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'manifest_verified': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tape_count_matched': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'no_damaged_tapes': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'custody_accepted': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class DeliveryConfirmationForm(forms.ModelForm):
    class Meta:
        model = DeliveryConfirmation
        fields = [
            'destination_location',
            'receiving_custodian',
            'delivery_date',
            'delivery_time',
            'delivery_status',
            'notes',
            'manifest_matched',
            'all_tapes_delivered',
            'discrepancies_resolved',
        ]
        widgets = {
            'destination_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Destination Location'}),
            'receiving_custodian': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Receiving Custodian'}),
            'delivery_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'delivery_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'delivery_status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Delivery notes or discrepancies'}),
            'manifest_matched': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'all_tapes_delivered': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'discrepancies_resolved': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ShipmentExceptionForm(forms.ModelForm):
    class Meta:
        model = ShipmentException
        fields = [
            'shipment',
            'tape',
            'exception_type',
            'severity',
            'status',
            'description',
        ]
        widgets = {
            'shipment': forms.Select(attrs={'class': 'form-select'}),
            'tape': forms.Select(attrs={'class': 'form-select'}),
            'exception_type': forms.Select(attrs={'class': 'form-select'}),
            'severity': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe the incident in detail'}),
        }

    def __init__(self, *args, **kwargs):
        courier = kwargs.pop('courier', None)
        super().__init__(*args, **kwargs)
        if courier:
            self.fields['shipment'].queryset = Shipment.objects.filter(
                Q(receipts__courier=courier) | Q(deliveries__courier=courier)
            ).distinct().order_by('-shipment_date')
            self.fields['tape'].queryset = Tape.objects.filter(shipments__in=self.fields['shipment'].queryset).distinct().order_by('volser')
        else:
            self.fields['shipment'].queryset = Shipment.objects.order_by('-shipment_date')
            self.fields['tape'].queryset = Tape.objects.order_by('volser')
        self.fields['tape'].required = False


class TransportEventForm(forms.Form):
    event_type = forms.ChoiceField(
        choices=ShipmentTransportEvent.EVENT_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Transport Event',
    )
    event_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Date',
        initial=timezone.localdate,
    )
    event_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        label='Time',
        initial=timezone.localtime,
    )
    comments = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional comments'}),
        label='Comments',
    )


class ReturnShipmentActionForm(forms.Form):
    shipment_pk = forms.UUIDField(widget=forms.HiddenInput())
    action = forms.ChoiceField(
        choices=[
            ('accept_return', 'Accept Return'),
            ('confirm_pickup', 'Confirm Pickup'),
            ('confirm_delivery', 'Confirm Return Delivery'),
        ],
        widget=forms.HiddenInput(),
        required=True,
    )


class ReconciliationForm(forms.ModelForm):
    class Meta:
        model = Reconciliation
        fields = [
            'reconciliation_date',
            'location',
            'performed_by',
            'reviewed_by',
            'approved_by',
            'start_time',
            'end_time',
            'status',
            'notes',
        ]
        widgets = {
            'reconciliation_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter reconciliation location'}),
            'performed_by': forms.Select(attrs={'class': 'form-select'}),
            'reviewed_by': forms.Select(attrs={'class': 'form-select'}),
            'approved_by': forms.Select(attrs={'class': 'form-select'}),
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Add reconciliation notes'}),
        }


class ReconciliationResultForm(forms.ModelForm):
    class Meta:
        model = ReconciliationResult
        fields = [
            'tape',
            'issue_type',
            'expected_location',
            'actual_location',
            'remarks',
            'resolution_status',
        ]
        widgets = {
            'tape': forms.Select(attrs={'class': 'form-select'}),
            'issue_type': forms.Select(attrs={'class': 'form-select'}),
            'expected_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Expected tape location'}),
            'actual_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Actual tape location'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe any discrepancy'}),
            'resolution_status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tape'].queryset = Tape.objects.order_by('volser')
        self.fields['tape'].required = False
        self.fields['remarks'].required = False


class ReportEmailForm(forms.Form):
    recipients = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'email1@example.com, email2@example.com', 'rows': 2}),
        label='Recipients',
        help_text='Separate multiple addresses with commas.',
        required=True,
    )
    subject = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Email Subject'}),
        label='Subject',
        required=True,
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Optional message to include in the email', 'rows': 4}),
        label='Message',
        required=False,
    )

    def clean_recipients(self):
        recipients_text = self.cleaned_data.get('recipients', '')
        emails = [email.strip() for email in recipients_text.split(',') if email.strip()]
        if not emails:
            raise forms.ValidationError('Please enter at least one recipient email address.')
        for email in emails:
            try:
                validate_email(email)
            except forms.ValidationError:
                raise forms.ValidationError(f'Invalid email address: {email}')
        return emails


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
