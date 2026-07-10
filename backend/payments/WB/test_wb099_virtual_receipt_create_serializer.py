from decimal import Decimal
import pytest
from rest_framework import serializers
from payments.serializers import VirtualReceiptCreateSerializer
from payments.models import Payment

def test_wb099_tc01_custom_amount_none():
    serializer = VirtualReceiptCreateSerializer(data={
        'virtual_user_id': 1,
        'payment_mode': Payment.Mode.CUSTOM_AMOUNT,
        'amount': None
    })
    assert not serializer.is_valid()
    assert 'amount' in serializer.errors

def test_wb099_tc02_custom_amount_zero():
    serializer = VirtualReceiptCreateSerializer(data={
        'virtual_user_id': 1,
        'payment_mode': Payment.Mode.CUSTOM_AMOUNT,
        'amount': 0
    })
    assert not serializer.is_valid()
    assert 'amount' in serializer.errors

def test_wb099_tc03_selected_items_empty():
    serializer = VirtualReceiptCreateSerializer(data={
        'virtual_user_id': 1,
        'payment_mode': Payment.Mode.SELECTED_ITEMS,
        'debt_ids': []
    })
    assert not serializer.is_valid()
    assert 'debt_ids' in serializer.errors

def test_wb099_tc04_full_mode():
    serializer = VirtualReceiptCreateSerializer(data={
        'virtual_user_id': 1,
        'payment_mode': Payment.Mode.FULL
    })
    assert serializer.is_valid()
