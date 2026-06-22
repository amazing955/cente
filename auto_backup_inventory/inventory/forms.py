from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group

from .models import CustomUser, Tape


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
        if Tape.objects.filter(volser__iexact=volser).exists():
            raise forms.ValidationError('VolSER already exists.')
        return volser

    def clean_barcode(self):
        barcode = self.cleaned_data.get('barcode')
        if Tape.objects.filter(barcode__iexact=barcode).exists():
            raise forms.ValidationError('Barcode already exists.')
        return barcode
