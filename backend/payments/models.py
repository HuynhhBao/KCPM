from django.conf import settings
from django.db import models

from core.models import BaseModel
from expenses.models import Debt
from households.models import Household


class Payment(BaseModel):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Chờ xác nhận'
        CONFIRMED = 'confirmed', 'Đã xác nhận'
        REJECTED = 'rejected', 'Đã từ chối'

    class Mode(models.TextChoices):
        FULL = 'full', 'Thanh toán toàn bộ'
        SELECTED_ITEMS = 'selected_items', 'Chọn khoản thanh toán'
        CUSTOM_AMOUNT = 'custom_amount', 'Thanh toán trước một khoản'

    debt = models.ForeignKey(
        Debt,
        on_delete=models.CASCADE,
        related_name='payments',
        null=True,
        blank=True
    )

    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name='payments'
    )

    payer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments_sent'
    )

    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments_received'
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=0
    )

    payment_mode = models.CharField(
        max_length=30,
        choices=Mode.choices,
        default=Mode.CUSTOM_AMOUNT,
        db_index=True,
    )

    is_pair_payment = models.BooleanField(
        default=False
    )

    remaining_after_confirm = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )

    payer_note = models.TextField(blank=True)
    receiver_note = models.TextField(blank=True)

    confirmed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    rejected_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['debt'],
                condition=(
                    models.Q(status='pending') &
                    models.Q(debt__isnull=False)
                ),
                name='unique_pending_payment_per_debt'
            ),
            models.UniqueConstraint(
                fields=[
                    'household',
                    'payer',
                    'receiver',
                ],
                condition=models.Q(status='pending'),
                name='unique_pending_payment_per_pair'
            ),
        ]

    def __str__(self):
        return (
            f'{self.payer.email} -> {self.receiver.email} '
            f'{self.amount} ({self.status})'
        )

class PaymentAllocation(BaseModel):
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='allocations',
    )

    debt = models.ForeignKey(
        Debt,
        on_delete=models.CASCADE,
        related_name='payment_allocations',
    )

    allocated_amount = models.DecimalField(
        max_digits=12,
        decimal_places=0,
    )

    class Meta:
        ordering = ['created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['payment', 'debt'],
                name='unique_payment_allocation_per_debt',
            ),
        ]

    def __str__(self):
        return (
            f'{self.payment_id} -> {self.debt_id}: '
            f'{self.allocated_amount}'
        )