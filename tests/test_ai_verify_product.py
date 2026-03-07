"""
Unit tests for AI product verification endpoint - Core logic tests.
"""
import json
import pytest
import sys
from datetime import datetime, timedelta
from decimal import Decimal

# Add backend to path for imports
sys.path.insert(0, 'backend/shared')
sys.path.insert(0, 'backend/ai')


class TestMarketPriceCalculation:
    """Test cases for market price calculation."""
    
    def test_calculate_market_price_vegetables(self):
        """Test market price for vegetables."""
        from verify_product import calculate_market_price
        
        product = {
            'category': 'vegetables',
            'giTag': {'hasTag': False},
            'seasonal': {'isSeasonal': False}
        }
        
        price = calculate_market_price(product)
        assert price == 50.0
    
    def test_calculate_market_price_with_gi_tag(self):
        """Test market price with GI tag premium."""
        from verify_product import calculate_market_price
        
        product = {
            'category': 'spices',
            'giTag': {'hasTag': True, 'tagName': 'Kashmir Saffron'},
            'seasonal': {'isSeasonal': False}
        }
        
        price = calculate_market_price(product)
        # Base: 200, GI premium: 200 * 1.2 = 240
        assert price == 240.0
    
    def test_calculate_market_price_in_season(self):
        """Test market price for in-season product."""
        from verify_product import calculate_market_price
        
        now = datetime.now()
        product = {
            'category': 'fruits',
            'giTag': {'hasTag': False},
            'seasonal': {
                'isSeasonal': True,
                'seasonStart': (now - timedelta(days=30)).isoformat(),
                'seasonEnd': (now + timedelta(days=30)).isoformat()
            }
        }
        
        price = calculate_market_price(product)
        # Base: 80, In season: 80 * 0.9 = 72
        assert price == 72.0
    
    def test_calculate_market_price_out_of_season(self):
        """Test market price for out-of-season product."""
        from verify_product import calculate_market_price
        
        now = datetime.now()
        product = {
            'category': 'fruits',
            'giTag': {'hasTag': False},
            'seasonal': {
                'isSeasonal': True,
                'seasonStart': (now - timedelta(days=180)).isoformat(),
                'seasonEnd': (now - timedelta(days=90)).isoformat()
            }
        }
        
        price = calculate_market_price(product)
        # Base: 80, Out of season: 80 * 1.3 = 104
        assert price == 104.0
    
    def test_calculate_market_price_grains(self):
        """Test market price for grains."""
        from verify_product import calculate_market_price
        
        product = {
            'category': 'grains',
            'giTag': {'hasTag': False},
            'seasonal': {'isSeasonal': False}
        }
        
        price = calculate_market_price(product)
        assert price == 40.0
    
    def test_calculate_market_price_dairy(self):
        """Test market price for dairy."""
        from verify_product import calculate_market_price
        
        product = {
            'category': 'dairy',
            'giTag': {'hasTag': False},
            'seasonal': {'isSeasonal': False}
        }
        
        price = calculate_market_price(product)
        assert price == 60.0


class TestBedrockPromptConstruction:
    """Test cases for Bedrock prompt construction."""
    
    def test_construct_prompt_with_gi_tag(self):
        """Test prompt construction with GI tag."""
        from verify_product import construct_bedrock_prompt
        
        product = {
            'name': 'Darjeeling Tea',
            'category': 'spices',
            'price': 500.0,
            'unit': 'kg',
            'description': 'Premium Darjeeling tea from West Bengal',
            'giTag': {
                'hasTag': True,
                'tagName': 'Darjeeling Tea',
                'region': 'West Bengal'
            },
            'invoiceDocumentUrl': 's3://bucket/invoice.pdf'
        }
        
        prompt = construct_bedrock_prompt(product)
        
        assert 'Darjeeling Tea' in prompt
        assert 'GI Tag (Geographical Indication): Yes' in prompt
        assert 'West Bengal' in prompt
        assert 'Invoice Document: Provided' in prompt
        assert 'JSON format' in prompt
        assert 'fraudRiskScore' in prompt
        assert 'authenticityConfidence' in prompt
    
    def test_construct_prompt_without_gi_tag(self):
        """Test prompt construction without GI tag."""
        from verify_product import construct_bedrock_prompt
        
        product = {
            'name': 'Regular Tomatoes',
            'category': 'vegetables',
            'price': 40.0,
            'unit': 'kg',
            'description': 'Fresh tomatoes',
            'giTag': {'hasTag': False},
            'invoiceDocumentUrl': None
        }
        
        prompt = construct_bedrock_prompt(product)
        
        assert 'Regular Tomatoes' in prompt
        assert 'GI Tag (Geographical Indication): No' in prompt
        assert 'Invoice Document: Not provided' in prompt
        assert 'vegetables' in prompt
    
    def test_construct_prompt_includes_all_fields(self):
        """Test that prompt includes all required fields."""
        from verify_product import construct_bedrock_prompt
        
        product = {
            'name': 'Test Product',
            'category': 'fruits',
            'price': 100.0,
            'unit': 'kg',
            'description': 'Test description',
            'giTag': {'hasTag': False},
            'invoiceDocumentUrl': 's3://test'
        }
        
        prompt = construct_bedrock_prompt(product)
        
        # Check all required sections are present
        assert 'Product Details:' in prompt
        assert 'Name:' in prompt
        assert 'Category:' in prompt
        assert 'Price:' in prompt
        assert 'Description:' in prompt
        assert 'GI Tag' in prompt
        assert 'Invoice Document:' in prompt


class TestVerificationStatusLogic:
    """Test verification status determination logic."""
    
    def test_fraud_score_above_threshold_flags_product(self):
        """Test that fraud score > 70 results in flagged status."""
        from constants import FRAUD_RISK_THRESHOLD, VerificationStatus
        
        fraud_score = 75.0
        status = VerificationStatus.FLAGGED.value if fraud_score > FRAUD_RISK_THRESHOLD else VerificationStatus.APPROVED.value
        
        assert status == 'flagged'
    
    def test_fraud_score_at_threshold_approves_product(self):
        """Test that fraud score = 70 results in approved status."""
        from constants import FRAUD_RISK_THRESHOLD, VerificationStatus
        
        fraud_score = 70.0
        status = VerificationStatus.FLAGGED.value if fraud_score > FRAUD_RISK_THRESHOLD else VerificationStatus.APPROVED.value
        
        assert status == 'approved'
    
    def test_fraud_score_below_threshold_approves_product(self):
        """Test that fraud score < 70 results in approved status."""
        from constants import FRAUD_RISK_THRESHOLD, VerificationStatus
        
        fraud_score = 45.0
        status = VerificationStatus.FLAGGED.value if fraud_score > FRAUD_RISK_THRESHOLD else VerificationStatus.APPROVED.value
        
        assert status == 'approved'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
