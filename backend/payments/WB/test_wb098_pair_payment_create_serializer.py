from decimal import Decimal
import pytest
from rest_framework import serializers
from payments.serializers import PairPaymentCreateSerializer
from payments.models import Payment

def test_wb098_tc01_custom_amount_none():
    serializer = PairPaymentCreateSerializer(data={
        'receiver_id': 1,
        'payment_mode': Payment.Mode.CUSTOM_AMOUNT,
        'amount': None
    })
    assert not serializer.is_valid()
    assert 'amount' in serializer.errors

def test_wb098_tc02_custom_amount_zero():
    serializer = PairPaymentCreateSerializer(data={
        'receiver_id': 1,
        'payment_mode': Payment.Mode.CUSTOM_AMOUNT,
        'amount': 0
    })
    assert not serializer.is_valid()
    assert 'amount' in serializer.errors

def test_wb098_tc03_custom_amount_less_than_zero():
    serializer = PairPaymentCreateSerializer(data={
        'receiver_id': 1,
        'payment_mode': Payment.Mode.CUSTOM_AMOUNT,
        'amount': -50
    })
    assert not serializer.is_valid()
    assert 'amount' in serializer.errors

def test_wb098_tc04_selected_items_empty():
    serializer = PairPaymentCreateSerializer(data={
        'receiver_id': 1,
        'payment_mode': Payment.Mode.SELECTED_ITEMS,
        'debt_ids': []
    })
    assert not serializer.is_valid()
    assert 'debt_ids' in serializer.errors

def test_wb098_tc05_full_mode():
    serializer = PairPaymentCreateSerializer(data={
        'receiver_id': 1,
        'payment_mode': Payment.Mode.FULL
    })
    assert serializer.is_valid()
