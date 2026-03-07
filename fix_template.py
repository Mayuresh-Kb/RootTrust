#!/usr/bin/env python3
"""Fix template.yaml validation issues"""

import re

# Read the template
with open('template.yaml', 'r') as f:
    content = f.read()

# Fix 1: Remove AWS_REGION environment variables (they're redundant)
# Pattern: lines with AWS_REGION: !Ref AWS::Region
content = re.sub(r'\n\s+AWS_REGION: !Ref AWS::Region', '', content)

# Fix 2: Replace !Ref JWTSecretKey with the correct secret reference
content = content.replace(
    'JWT_SECRET_KEY: !Ref JWTSecretKey',
    'JWT_SECRET_KEY: !Sub "{{resolve:secretsmanager:RootTrust-JWT-Secret-${Stage}:SecretString:secret}}"'
)

# Fix 3: Replace JWTSecretName references with the correct secret name
content = content.replace(
    'JWT_SECRET_NAME: !Ref JWTSecretName',
    'JWT_SECRET_NAME: !Sub "RootTrust-JWT-Secret-${Stage}"'
)

content = content.replace(
    '!Sub "arn:aws:secretsmanager:${AWS::Region}:${AWS::AccountId}:secret:${JWTSecretName}*"',
    '!Sub "arn:aws:secretsmanager:${AWS::Region}:${AWS::AccountId}:secret:RootTrust-JWT-Secret-${Stage}*"'
)

# Write the fixed template
with open('template.yaml', 'w') as f:
    f.write(content)

print("✅ Fixed template.yaml:")
print("  - Removed redundant AWS_REGION environment variables")
print("  - Fixed JWTSecretKey reference")
print("  - Fixed JWTSecretName references")
