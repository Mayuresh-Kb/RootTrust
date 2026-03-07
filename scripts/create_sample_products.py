#!/usr/bin/env python3
"""
Create sample products in DynamoDB for demo purposes
"""
import boto3
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('RootTrustData-dev')

def create_sample_farmer():
    """Create a sample farmer user"""
    farmer_id = str(uuid.uuid4())
    farmer_email = "demo.farmer@roottrust.com"
    
    farmer = {
        'PK': f'USER#{farmer_id}',
        'SK': 'PROFILE',
        'EntityType': 'User',
        'userId': farmer_id,
        'email': farmer_email,
        'passwordHash': '$2b$10$dummyhashfordemopurposes',  # Not a real hash
        'role': 'farmer',
        'firstName': 'Rajesh',
        'lastName': 'Kumar',
        'phone': '+91-9876543210',
        'address': {
            'street': '123 Farm Road',
            'city': 'Nashik',
            'state': 'Maharashtra',
            'pincode': '422001'
        },
        'createdAt': datetime.utcnow().isoformat(),
        'emailVerified': True,
        'farmerProfile': {
            'farmName': 'Green Valley Organic Farm',
            'farmLocation': 'Nashik, Maharashtra',
            'certifications': ['Organic India', 'FSSAI'],
            'averageRating': Decimal('4.8'),
            'totalReviews': 45,
            'totalSales': 120,
            'consecutiveSalesStreak': 8,
            'bonusesEarned': 2,
            'featuredStatus': True
        },
        'GSI2PK': 'ROLE#farmer',
        'GSI2SK': f'USER#{datetime.utcnow().isoformat()}'
    }
    
    table.put_item(Item=farmer)
    print(f"✓ Created sample farmer: {farmer_email} (ID: {farmer_id})")
    return farmer_id

def create_sample_products(farmer_id):
    """Create sample products"""
    products = [
        {
            'name': 'Alphonso Mango (Hapus)',
            'category': 'fruits',
            'description': 'Premium Alphonso mangoes from Ratnagiri, known for their rich flavor and golden color. Handpicked at perfect ripeness.',
            'price': Decimal('450'),
            'unit': 'kg',
            'quantity': 50,
            'giTag': {
                'hasTag': True,
                'tagName': 'Ratnagiri Alphonso Mango',
                'region': 'Ratnagiri, Maharashtra'
            },
            'seasonal': {
                'isSeasonal': True,
                'seasonStart': (datetime.utcnow() - timedelta(days=10)).isoformat(),
                'seasonEnd': (datetime.utcnow() + timedelta(days=50)).isoformat()
            },
            'images': [
                {
                    'url': 'https://images.unsplash.com/photo-1553279768-865429fa0078?w=800',
                    'isPrimary': True
                }
            ],
            'verificationStatus': 'approved',
            'fraudRiskScore': Decimal('15'),
            'authenticityConfidence': Decimal('95'),
            'aiExplanation': 'Product verified with high confidence. GI tag validated, seasonal timing correct, price within market range.',
            'predictedMarketPrice': Decimal('420'),
            'averageRating': Decimal('4.9'),
            'totalReviews': 12,
            'totalSales': 35,
            'viewCount': 245,
            'currentViewers': 3,
            'recentPurchaseCount': 8
        },
        {
            'name': 'Organic Basmati Rice',
            'category': 'grains',
            'description': 'Premium aged basmati rice grown using organic farming methods. Long grain, aromatic, and perfect for biryanis and pulao.',
            'price': Decimal('180'),
            'unit': 'kg',
            'quantity': 200,
            'giTag': {
                'hasTag': False,
                'tagName': '',
                'region': ''
            },
            'seasonal': {
                'isSeasonal': False,
                'seasonStart': '',
                'seasonEnd': ''
            },
            'images': [
                {
                    'url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c?w=800',
                    'isPrimary': True
                }
            ],
            'verificationStatus': 'approved',
            'fraudRiskScore': Decimal('20'),
            'authenticityConfidence': Decimal('92'),
            'aiExplanation': 'Organic certification verified. Price competitive with market rates. Farmer has good track record.',
            'predictedMarketPrice': Decimal('175'),
            'averageRating': Decimal('4.7'),
            'totalReviews': 28,
            'totalSales': 85,
            'viewCount': 412,
            'currentViewers': 5,
            'recentPurchaseCount': 15
        },
        {
            'name': 'Fresh Organic Tomatoes',
            'category': 'vegetables',
            'description': 'Farm-fresh organic tomatoes, vine-ripened and pesticide-free. Perfect for salads, cooking, and making fresh sauces.',
            'price': Decimal('60'),
            'unit': 'kg',
            'quantity': 100,
            'giTag': {
                'hasTag': False,
                'tagName': '',
                'region': ''
            },
            'seasonal': {
                'isSeasonal': True,
                'seasonStart': (datetime.utcnow() - timedelta(days=30)).isoformat(),
                'seasonEnd': (datetime.utcnow() + timedelta(days=60)).isoformat()
            },
            'images': [
                {
                    'url': 'https://images.unsplash.com/photo-1546470427-227e2e1e8c8e?w=800',
                    'isPrimary': True
                }
            ],
            'verificationStatus': 'approved',
            'fraudRiskScore': Decimal('10'),
            'authenticityConfidence': Decimal('98'),
            'aiExplanation': 'Excellent verification score. Seasonal timing perfect, organic certification valid, competitive pricing.',
            'predictedMarketPrice': Decimal('55'),
            'averageRating': Decimal('4.8'),
            'totalReviews': 18,
            'totalSales': 42,
            'viewCount': 189,
            'currentViewers': 2,
            'recentPurchaseCount': 6
        }
    ]
    
    created_products = []
    for product_data in products:
        product_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        product = {
            'PK': f'PRODUCT#{product_id}',
            'SK': 'METADATA',
            'EntityType': 'Product',
            'productId': product_id,
            'farmerId': farmer_id,
            'createdAt': now,
            'updatedAt': now,
            'GSI1PK': f'CATEGORY#{product_data["category"]}',
            'GSI1SK': f'PRODUCT#{now}',
            'GSI2PK': f'FARMER#{farmer_id}',
            'GSI2SK': f'PRODUCT#{now}',
            'GSI3PK': f'STATUS#{product_data["verificationStatus"]}',
            'GSI3SK': f'PRODUCT#{now}',
            **product_data
        }
        
        table.put_item(Item=product)
        created_products.append(product)
        print(f"✓ Created product: {product_data['name']} (ID: {product_id})")
    
    return created_products

def main():
    print("Creating sample data for RootTrust Marketplace...")
    print("-" * 60)
    
    # Create sample farmer
    farmer_id = create_sample_farmer()
    
    # Create sample products
    products = create_sample_products(farmer_id)
    
    print("-" * 60)
    print(f"✓ Successfully created {len(products)} sample products!")
    print("\nYou can now:")
    print("1. Browse products at: GET /products")
    print("2. View product details at: GET /products/{productId}")
    print("3. Login as farmer: demo.farmer@roottrust.com (password: demo123)")
    print("\nNote: The farmer password is not set up for actual login.")
    print("Please register a new farmer account through the frontend.")

if __name__ == '__main__':
    main()
