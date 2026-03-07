"""
Integration test to verify registration endpoint structure and dependencies.
"""
import os
import sys

def test_shared_modules_exist():
    """Verify all required shared modules exist."""
    shared_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'shared')
    
    required_files = [
        '__init__.py',
        'models.py',
        'auth.py',
        'database.py',
        'validators.py',
        'constants.py',
        'exceptions.py'
    ]
    
    for file in required_files:
        file_path = os.path.join(shared_path, file)
        assert os.path.exists(file_path), f"Required shared module {file} is missing"
    
    print("✓ All shared modules exist")


def test_auth_handler_exists():
    """Verify auth handler exists."""
    auth_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'auth')
    
    required_files = [
        'register.py',
        'authorizer.py',
        'requirements.txt'
    ]
    
    for file in required_files:
        file_path = os.path.join(auth_path, file)
        assert os.path.exists(file_path), f"Required auth file {file} is missing"
    
    print("✓ All auth handler files exist")


def test_registration_handler_structure():
    """Verify registration handler has correct structure."""
    register_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'auth', 'register.py')
    
    with open(register_path, 'r') as f:
        content = f.read()
    
    # Check for required imports
    assert 'import json' in content, "Missing json import"
    assert 'import uuid' in content, "Missing uuid import"
    assert 'from datetime import datetime' in content, "Missing datetime import"
    
    # Check for shared module imports
    assert 'from backend.shared.models import' in content, "Missing models import"
    assert 'from backend.shared.auth import' in content, "Missing auth import"
    assert 'from backend.shared.database import' in content, "Missing database import"
    assert 'from backend.shared.validators import' in content, "Missing validators import"
    assert 'from backend.shared.constants import' in content, "Missing constants import"
    assert 'from backend.shared.exceptions import' in content, "Missing exceptions import"
    
    # Check for handler function
    assert 'def handler(event' in content, "Missing handler function"
    
    # Check for key functionality
    assert 'UserRegistrationRequest' in content, "Missing validation schema"
    assert 'hash_password' in content, "Missing password hashing"
    assert 'uuid.uuid4()' in content, "Missing UUID generation"
    assert 'put_item' in content, "Missing DynamoDB put operation"
    assert 'get_item' in content, "Missing DynamoDB get operation"
    assert 'FarmerProfile' in content, "Missing farmer profile creation"
    assert 'ConsumerProfile' in content, "Missing consumer profile creation"
    
    # Check for proper error handling
    assert 'ValidationError' in content, "Missing validation error handling"
    assert 'DuplicateResourceError' in content, "Missing duplicate error handling"
    assert 'RootTrustException' in content, "Missing base exception handling"
    
    # Check for response structure
    assert 'statusCode' in content, "Missing statusCode in response"
    assert 'create_response' in content, "Missing response helper function"
    
    print("✓ Registration handler has correct structure")


def test_template_yaml_has_registration_function():
    """Verify template.yaml includes registration Lambda function."""
    template_path = os.path.join(os.path.dirname(__file__), '..', 'template.yaml')
    
    with open(template_path, 'r') as f:
        content = f.read()
    
    assert 'AuthRegisterFunction' in content, "Missing AuthRegisterFunction in template"
    assert 'register.handler' in content, "Missing register.handler reference"
    assert '/auth/register' in content, "Missing /auth/register endpoint"
    assert 'SharedLayer' in content, "Missing SharedLayer definition"
    
    print("✓ Template.yaml includes registration function")


def test_requirements_include_dependencies():
    """Verify requirements.txt includes all necessary dependencies."""
    req_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'auth', 'requirements.txt')
    
    with open(req_path, 'r') as f:
        content = f.read()
    
    required_deps = ['boto3', 'PyJWT', 'bcrypt', 'pydantic', 'email-validator']
    
    for dep in required_deps:
        assert dep in content, f"Missing required dependency: {dep}"
    
    print("✓ Requirements.txt includes all dependencies")


if __name__ == '__main__':
    print("\n=== Running Integration Tests ===\n")
    
    test_shared_modules_exist()
    test_auth_handler_exists()
    test_registration_handler_structure()
    test_template_yaml_has_registration_function()
    test_requirements_include_dependencies()
    
    print("\n=== All Integration Tests Passed ===\n")
