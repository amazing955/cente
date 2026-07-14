import logging
from django.utils import timezone
from django.db import IntegrityError, transaction

from .models import PendingApproval, AuditLog

logger = logging.getLogger(__name__)


def create_pending_approval(**kwargs):
    """Create a PendingApproval safely and log errors for diagnostics.

    Returns the created PendingApproval instance or None on failure.
    """
    try:
        with transaction.atomic():
            pa = PendingApproval.objects.create(**kwargs)
            AuditLog.objects.create(
                name='PendingApproval Created',
                action=f"Created PendingApproval {pa.transaction_type} ({pa.pk})",
                user=kwargs.get('requester') or None,
                severity='info',
            )
            logger.info('Created PendingApproval %s for %s', pa.pk, kwargs.get('transaction_type'))
            return pa
    except IntegrityError as ie:
        logger.exception('IntegrityError creating PendingApproval: %s', ie)
    except Exception as exc:
        logger.exception('Error creating PendingApproval: %s', exc)
    return None
