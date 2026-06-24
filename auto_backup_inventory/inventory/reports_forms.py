from django import forms
from django.utils import timezone
from .models import Tape


STATUS_CHOICES = [('', 'Any')] + [(s, s) for s, _ in Tape.STATUS_CHOICES]
TAPE_TYPE_CHOICES = [('', 'Any')] + [(t, t) for t, _ in Tape.TAPE_TYPE_CHOICES]


class ReportFilterForm(forms.Form):
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    volser = forms.CharField(required=False)
    barcode = forms.CharField(required=False)
    status = forms.ChoiceField(required=False, choices=STATUS_CHOICES)
    location = forms.CharField(required=False)
    custodian = forms.CharField(required=False)
    shipment_id = forms.CharField(required=False)
    shipment_status = forms.CharField(required=False)
    legal_hold = forms.NullBooleanField(required=False)
    audit_hold = forms.NullBooleanField(required=False)
    tape_type = forms.ChoiceField(required=False, choices=TAPE_TYPE_CHOICES)
    min_retention_days = forms.IntegerField(required=False, min_value=0)

    def clean(self):
        cleaned = super().clean()
        sd = cleaned.get('start_date')
        ed = cleaned.get('end_date')
        if sd and ed and sd > ed:
            raise forms.ValidationError('Start date must be before end date')
        return cleaned
