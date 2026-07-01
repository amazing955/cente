from datetime import date

from django.utils import timezone


class TapeSerializer:
    def __init__(self, instance):
        self.instance = instance

    @property
    def data(self):
        return {
            'id': str(self.instance.id),
            'volser': self.instance.volser,
            'barcode': self.instance.barcode,
            'status': self.instance.status,
            'location': self.instance.current_location,
            'retention_end_date': self.instance.retention_end_date.isoformat() if self.instance.retention_end_date else None,
            'tape_type': self.instance.tape_type,
            'manufacturer': self.instance.manufacturer,
            'legal_hold': self.instance.legal_hold,
            'audit_hold': self.instance.audit_hold,
            'remarks': self.instance.remarks,
            'date_registered': self.instance.date_registered.isoformat() if self.instance.date_registered else None,
        }


class ShipmentSerializer:
    def __init__(self, instance):
        self.instance = instance

    @property
    def data(self):
        return {
            'id': str(self.instance.id),
            'shipment_id': self.instance.shipment_id,
            'status': self.instance.status,
            'shipment_type': self.instance.shipment_type,
            'source_location': self.instance.source_location,
            'destination_location': self.instance.destination_location,
            'priority_level': self.instance.priority_level,
            'shipment_date': self.instance.shipment_date.isoformat() if self.instance.shipment_date else None,
            'created_at': self.instance.created_at.isoformat() if self.instance.created_at else None,
        }


class AuditLogSerializer:
    def __init__(self, instance):
        self.instance = instance

    @property
    def data(self):
        return {
            'id': str(self.instance.id),
            'name': self.instance.name,
            'action': self.instance.action,
            'severity': self.instance.severity,
            'timestamp': self.instance.timestamp.isoformat() if self.instance.timestamp else None,
            'message': self.instance.message,
        }
