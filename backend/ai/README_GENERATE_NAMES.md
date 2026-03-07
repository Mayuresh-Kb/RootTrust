# AI Product Name Generation Endpoint

## Overview

The product name generation endpoint uses Amazon Bedrock (Claude 3 Haiku) to generate 3 creative product name variations for farmers. Each name emphasizes a different value proposition to help farmers choose the most appealing name for their products.

## Endpoint

**POST** `/ai/generate-names`

## Authentication

Requires JWT token in Authorization header. Only users with `farmer` role can access this endpoint.

## Request

### Headers

```
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

### Body

```json
{
  "name": "Tomatoes",
  "category": "vegetables",
  "description": "Fresh organic tomatoes from local farm",
  "giTag": {
    "hasTag": true,
    "tagName": "Nashik Tomatoes",
    "region": "Maharashtra"
  }
}
```

### Parameters

| Field         | Type    | Required | Description                                                  |
| ------------- | ------- | -------- | ------------------------------------------------------------ |
| name          | string  | Yes      | Current product name                                         |
| category      | string  | Yes      | Product category (vegetables, fruits, grains, spices, dairy) |
| description   | string  | No       | Product description                                          |
| giTag         | object  | No       | GI tag information                                           |
| giTag.hasTag  | boolean | No       | Whether product has GI tag                                   |
| giTag.tagName | string  | No       | GI tag name                                                  |
| giTag.region  | string  | No       | GI tag region                                                |

## Response

### Success Response (200 OK)

```json
{
  "names": [
    "Premium Farm-Fresh Tomatoes",
    "Authentic Nashik Tomatoes",
    "Healthy Garden Tomatoes"
  ]
}
```

### Response Fields

| Field | Type          | Description                                |
| ----- | ------------- | ------------------------------------------ |
| names | array[string] | Array of exactly 3 generated product names |

The 3 names emphasize different value propositions:

1. **Quality-focused**: Emphasizes premium quality, freshness, or superior characteristics
2. **Origin-focused**: Emphasizes geographical origin, authenticity, or traditional methods
3. **Benefit-focused**: Emphasizes health benefits, taste experience, or customer outcomes

### Error Responses

#### 401 Unauthorized

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Missing authorization token"
  }
}
```

#### 403 Forbidden

```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "Only farmers can generate product names"
  }
}
```

#### 400 Bad Request

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "name is required"
  }
}
```

#### 503 Service Unavailable

```json
{
  "error": {
    "code": "SERVICE_UNAVAILABLE",
    "message": "Failed to invoke AI model: <error details>"
  }
}
```

## Implementation Details

### AI Model

- **Model**: Claude 3 Haiku (`anthropic.claude-3-haiku-20240307-v1:0`)
- **Temperature**: 0.8 (higher for creative name generation)
- **Max Tokens**: 300
- **Cost**: Optimized for cost efficiency

### Prompt Engineering

The prompt is carefully crafted to:

- Request exactly 3 name variations
- Emphasize different value propositions (quality, origin, benefit)
- Incorporate GI tag information when available
- Generate memorable, marketable names (2-5 words)
- Use descriptive adjectives that evoke positive emotions

### Response Parsing

The function handles various response formats:

- Plain JSON array: `["Name 1", "Name 2", "Name 3"]`
- Markdown code blocks: ` ```json\n["Name 1", "Name 2", "Name 3"]\n``` `
- Whitespace trimming for
  clean names

### Validation

The function validates that:

- Exactly 3 names are returned
- All names are strings
- No names are empty
- Response is a valid JSON array

If validation fails, a `ServiceUnavailableError` is raised.

## Usage Example

### cURL

```bash
curl -X POST https://api.roottrust.com/dev/ai/generate-names \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Basmati Rice",
    "category": "grains",
    "description": "Premium aged basmati rice",
    "giTag": {
      "hasTag": true,
      "tagName": "Basmati Rice",
      "region": "Punjab"
    }
  }'
```

### JavaScript (Fetch API)

```javascript
const response = await fetch(
  "https://api.roottrust.com/dev/ai/generate-names",
  {
    method: "POST",
    headers: {
      Authorization: `Bearer ${jwtToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      name: "Basmati Rice",
      category: "grains",
      description: "Premium aged basmati rice",
      giTag: {
        hasTag: true,
        tagName: "Basmati Rice",
        region: "Punjab",
      },
    }),
  },
);

const data = await response.json();
console.log(data.names); // ["Premium Aged Basmati", "Authentic Punjab Basmati", "Healthy Aromatic Rice"]
```

### Python (requests)

```python
import requests

response = requests.post(
    'https://api.roottrust.com/dev/ai/generate-names',
    headers={
        'Authorization': f'Bearer {jwt_token}',
        'Content-Type': 'application/json'
    },
    json={
        'name': 'Basmati Rice',
        'category': 'grains',
        'description': 'Premium aged basmati rice',
        'giTag': {
            'hasTag': True,
            'tagName': 'Basmati Rice',
            'region': 'Punjab'
        }
    }
)

data = response.json()
print(data['names'])
```

## Requirements Validation

This endpoint validates the following requirements:

- **Requirement 18.1**: AI Marketing Engine suggests optimized product names
- **Requirement 18.2**: AI Marketing Engine generates three name variations emphasizing different value propositions

## Testing

Unit tests are provided in `tests/test_ai_generate_names.py` covering:

- Prompt construction with and without GI tags
- Bedrock invocation and response parsing
- Various response formats (plain JSON, markdown code blocks)
- Error handling (wrong count, invalid format, empty names)
- Lambda handler authorization and validation
- Role-based access control

## Cost Optimization

- Uses Claude 3 Haiku (most cost-effective model)
- No caching (names should be unique each time)
- Minimal token usage (300 max tokens)
- Fast response time

## Related Endpoints

- `POST /ai/generate-description` - Generate product descriptions
- `POST /ai/enhance-description` - Enhance existing descriptions
- `POST /ai/generate-social` - Generate social media content
- `POST /ai/generate-launch` - Generate launch announcements
