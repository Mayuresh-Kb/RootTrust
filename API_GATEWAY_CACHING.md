# API Gateway Caching Configuration Guide

## Overview

API Gateway caching is **DISABLED by default** for the RootTrust Marketplace prototype to minimize costs. This document explains when to enable caching, how to configure it, and the cost implications.

## Current Configuration

### Cache Settings (Disabled)

```yaml
CacheClusterEnabled: false
CacheClusterSize: "0.5" # 0.5GB cache (smallest available)
```

### Endpoint-Specific Cache Configuration

#### GET /products (Product Listing)

- **TTL**: 300 seconds (5 minutes)
- **Cache Key**: Includes all query parameters
  - `category` (vegetables, fruits, grains, spices, dairy)
  - `seasonal` (true/false)
  - `giTag` (true/false)
  - `search` (keyword)
  - `limit` (pagination)
  - `cursor` (pagination token)
- **Rationale**: Product listings change infrequently but are accessed often. 5-minute cache reduces Lambda invocations while keeping data reasonably fresh.

#### GET /products/{productId} (Product Detail)

- **TTL**: 3600 seconds (1 hour)
- **Cache Key**: Includes path parameter
  - `productId` (unique product identifier)
- **Rationale**: Individual product details change even less frequently. 1-hour cache significantly reduces database queries and Lambda invocations for popular products.

### Cache Key Strategy

The cache key automatically includes:

1. **Path parameters**: `{productId}` for product detail endpoint
2. **Query parameters**: All query strings for product listing endpoint
3. **Authorization header**: User role (farmer/consumer) affects response data

This ensures that:

- Different users with different roles get appropriate cached responses
- Different filter combinations are cached separately
- Each product has its own cache entry

## Cost Analysis

### Caching Costs

| Component             | Cost         |
| --------------------- | ------------ |
| Cache cluster (0.5GB) | $0.02/hour   |
| Monthly cost (24/7)   | $14.40/month |
| Data transfer         | Included     |
| Cache invalidation    | Free         |

### Cost-Benefit Analysis

#### Low Traffic Scenario (Current)

- **Traffic**: 1,000 requests/day
- **Cache hit rate**: ~60%
- **Lambda savings**: ~$0.50/month
- **Net cost**: +$13.90/month ❌
- **Recommendation**: Keep caching DISABLED

#### Moderate Traffic Scenario

- **Traffic**: 10,000 requests/day
- **Cache hit rate**: ~70%
- **Lambda savings**: ~$8/month
- **DynamoDB savings**: ~$5/month
- **Net cost**: +$1.40/month ⚠️
- **Recommendation**: Consider enabling

#### High Traffic Scenario

- **Traffic**: 50,000+ requests/day
- **Cache hit rate**: ~80%
- **Lambda savings**: ~$40/month
- **DynamoDB savings**: ~$25/month
- **Net cost**: -$50.60/month ✅
- **Recommendation**: Enable caching immediately

## When to Enable Caching

### Enable caching when ANY of these conditions are met:

1. **Traffic Threshold**: Daily requests exceed 10,000
2. **Lambda Costs**: Lambda costs exceed $20/month
3. **DynamoDB Costs**: DynamoDB read costs exceed $15/month
4. **Performance Issues**: Response times consistently exceed 500ms
5. **Popular Products**: Top 10 products account for >50% of traffic

### Monitor these metrics:

```bash
# Check daily API Gateway requests
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Count \
  --dimensions Name=ApiName,Value=RootTrustAPI-prod \
  --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Sum

# Check Lambda invocation count
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=RootTrust-Product-List-prod \
  --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Sum

# Check DynamoDB read capacity
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedReadCapacityUnits \
  --dimensions Name=TableName,Value=RootTrustData-prod \
  --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Sum
```

## How to Enable Caching

### Option 1: Update template.yaml and Redeploy

1. **Edit template.yaml**:

```yaml
RootTrustApi:
  Type: AWS::Serverless::Api
  Properties:
    # ... other properties ...
    CacheClusterEnabled: true # Change from false to true
    CacheClusterSize: "0.5"
    MethodSettings:
      - ResourcePath: "/*"
        HttpMethod: "*"
        # ... other settings ...
        CachingEnabled: false # Keep default disabled
      - ResourcePath: "/products"
        HttpMethod: "GET"
        CachingEnabled: true # Enable for product listing
        CacheTtlInSeconds: 300
        CacheDataEncrypted: true
      - ResourcePath: "/products/*"
        HttpMethod: "GET"
        CachingEnabled: true # Enable for product detail
        CacheTtlInSeconds: 3600
        CacheDataEncrypted: true
```

2. **Deploy the changes**:

```bash
sam build
sam deploy --no-confirm-changeset
```

3. **Verify caching is enabled**:

```bash
aws apigateway get-stage \
  --rest-api-id $(aws apigateway get-rest-apis --query "items[?name=='RootTrustAPI-prod'].id" --output text) \
  --stage-name prod \
  --query 'cacheClusterEnabled'
```

### Option 2: Enable via AWS Console

1. Navigate to **API Gateway** → **RootTrustAPI-prod** → **Stages** → **prod**
2. Click **Settings** tab
3. Under **Cache Settings**:
   - Check **Enable API cache**
   - Select **0.5 GB** cache capacity
   - Click **Save Changes**
4. Under **Method Settings**:
   - Add override for `GET /products`:
     - Enable caching: ✓
     - Cache TTL: 300 seconds
     - Cache data encrypted: ✓
   - Add override for `GET /products/{productId}`:
     - Enable caching: ✓
     - Cache TTL: 3600 seconds
     - Cache data encrypted: ✓
5. Click **Deploy API** to apply changes

### Option 3: Enable via AWS CLI

```bash
# Get API ID
API_ID=$(aws apigateway get-rest-apis \
  --query "items[?name=='RootTrustAPI-prod'].id" \
  --output text)

# Enable cache cluster
aws apigateway update-stage \
  --rest-api-id $API_ID \
  --stage-name prod \
  --patch-operations \
    op=replace,path=/cacheClusterEnabled,value=true \
    op=replace,path=/cacheClusterSize,value=0.5

# Enable caching for GET /products
aws apigateway update-stage \
  --rest-api-id $API_ID \
  --stage-name prod \
  --patch-operations \
    op=replace,path=/*/GET/caching/enabled,value=true \
    op=replace,path=/*/GET/caching/ttlInSeconds,value=300

# Enable caching for GET /products/{productId}
aws apigateway update-stage \
  --rest-api-id $API_ID \
  --stage-name prod \
  --patch-operations \
    op=replace,path=/*/*/GET/caching/enabled,value=true \
    op=replace,path=/*/*/GET/caching/ttlInSeconds,value=3600
```

## Cache Invalidation

### When to Invalidate Cache

Invalidate cache when:

1. Product data is updated (price, description, images)
2. Product verification status changes
3. Product is deleted
4. Inventory quantity changes significantly

### How to Invalidate Cache

#### Invalidate Entire Cache

```bash
API_ID=$(aws apigateway get-rest-apis \
  --query "items[?name=='RootTrustAPI-prod'].id" \
  --output text)

aws apigateway flush-stage-cache \
  --rest-api-id $API_ID \
  --stage-name prod
```

**Note**: Flushing the entire cache is free but should be used sparingly as it defeats the purpose of caching.

#### Invalidate Specific Cache Entry

API Gateway doesn't support invalidating individual cache entries. Options:

1. Wait for TTL to expire (5 min for listings, 1 hour for details)
2. Flush entire cache (not recommended)
3. Use shorter TTL values if frequent updates are expected

### Automatic Cache Invalidation (Future Enhancement)

Consider implementing Lambda-triggered cache invalidation:

```python
# backend/products/update_product.py
import boto3

def invalidate_product_cache(product_id):
    """Invalidate cache when product is updated"""
    # Option 1: Flush entire cache (expensive)
    # apigateway.flush_stage_cache(restApiId=api_id, stageName='prod')

    # Option 2: Wait for TTL (recommended)
    # Cache will expire naturally in 5 min (listing) or 1 hour (detail)

    # Option 3: Use CloudFront in front of API Gateway
    # CloudFront supports path-based invalidation
    pass
```

## Monitoring Cache Performance

### Key Metrics to Monitor

1. **Cache Hit Rate**: Percentage of requests served from cache
2. **Cache Miss Rate**: Percentage of requests that hit Lambda
3. **Latency Improvement**: Response time difference with/without cache
4. **Cost Savings**: Lambda invocation reduction

### CloudWatch Metrics

```bash
# Cache hit count
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name CacheHitCount \
  --dimensions Name=ApiName,Value=RootTrustAPI-prod \
  --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum

# Cache miss count
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name CacheMissCount \
  --dimensions Name=ApiName,Value=RootTrustAPI-prod \
  --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum

# Calculate hit rate
# Hit Rate = CacheHitCount / (CacheHitCount + CacheMissCount) * 100
```

### Expected Cache Performance

| Metric                      | Expected Value | Good   | Needs Tuning |
| --------------------------- | -------------- | ------ | ------------ |
| Cache Hit Rate              | 60-80%         | >70%   | <50%         |
| Avg Latency (cached)        | 10-50ms        | <50ms  | >100ms       |
| Avg Latency (uncached)      | 200-500ms      | <300ms | >500ms       |
| Lambda Invocation Reduction | 60-80%         | >70%   | <50%         |

## Cache Size Optimization

### Available Cache Sizes

| Size    | Cost/Hour | Cost/Month | Recommended For        |
| ------- | --------- | ---------- | ---------------------- |
| 0.5 GB  | $0.020    | $14.40     | <50K requests/day      |
| 1.6 GB  | $0.038    | $27.36     | 50K-200K requests/day  |
| 6.1 GB  | $0.200    | $144.00    | 200K-500K requests/day |
| 13.5 GB | $0.250    | $180.00    | 500K-1M requests/day   |

### When to Increase Cache Size

Monitor **Cache Eviction Rate**:

- If eviction rate > 10%, consider increasing cache size
- If eviction rate > 25%, definitely increase cache size

```bash
# Check cache evictions (not directly available, infer from hit rate drop)
# If hit rate drops over time, cache is too small
```

## Best Practices

### DO ✅

1. **Start with caching disabled** for low traffic
2. **Monitor traffic patterns** before enabling
3. **Use appropriate TTL values** (5 min for listings, 1 hour for details)
4. **Enable encryption** for cached data
5. **Include authorization in cache key** to prevent data leakage
6. **Monitor cache hit rate** after enabling
7. **Document cache invalidation strategy**

### DON'T ❌

1. **Don't enable caching for low traffic** (<10K requests/day)
2. **Don't cache POST/PUT/DELETE requests** (only GET)
3. **Don't use very long TTL** (>1 hour) for frequently updated data
4. **Don't flush cache frequently** (defeats the purpose)
5. **Don't cache authenticated endpoints without proper cache key**
6. **Don't forget to encrypt cached data**
7. **Don't enable caching without monitoring**

## Troubleshooting

### Issue: Cache not working

**Symptoms**: Cache hit count is 0

**Solutions**:

1. Verify `CacheClusterEnabled: true` in template.yaml
2. Verify `CachingEnabled: true` for specific methods
3. Check that cache cluster is provisioned (takes 5-10 minutes)
4. Verify requests are GET methods (POST/PUT/DELETE are not cached)

### Issue: Stale data in cache

**Symptoms**: Users see outdated product information

**Solutions**:

1. Reduce TTL values (e.g., 300s → 60s)
2. Implement cache invalidation on product updates
3. Flush cache manually if critical update
4. Consider using CloudFront for better invalidation control

### Issue: Cache hit rate too low

**Symptoms**: Cache hit rate <50%

**Solutions**:

1. Increase cache size (0.5GB → 1.6GB)
2. Increase TTL values (if acceptable)
3. Analyze traffic patterns (too many unique queries?)
4. Consider normalizing query parameters

### Issue: Costs higher than expected

**Symptoms**: Monthly costs exceed budget

**Solutions**:

1. Verify cache size is 0.5GB (not larger)
2. Check if cache is actually reducing Lambda costs
3. Calculate net savings (Lambda + DynamoDB savings - cache cost)
4. Disable caching if net savings are negative

## Summary

### Current Status: DISABLED ❌

- **Reason**: Low traffic (<10K requests/day)
- **Cost**: $0/month
- **Lambda invocations**: Not optimized
- **Recommendation**: Keep disabled until traffic increases

### When to Enable: Traffic > 10K requests/day ✅

- **Cost**: $14.40/month
- **Savings**: $13-65/month (depending on traffic)
- **Net benefit**: $0-50/month
- **Recommendation**: Enable when cost-effective

### Configuration Summary

```yaml
# Disabled (Current)
CacheClusterEnabled: false
CachingEnabled: false

# Enabled (When traffic increases)
CacheClusterEnabled: true
CacheClusterSize: "0.5"
GET /products: 300s TTL
GET /products/{productId}: 3600s TTL
```

## References

- [AWS API Gateway Caching Documentation](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-caching.html)
- [API Gateway Pricing](https://aws.amazon.com/api-gateway/pricing/)
- [Cost Optimization Guide](./COST_OPTIMIZATION.md)
- [Requirements 19.1](./requirements.md#requirement-19-aws-infrastructure-and-cost-management)

## Revision History

| Date       | Version | Changes                                     |
| ---------- | ------- | ------------------------------------------- |
| 2024-01-XX | 1.0     | Initial configuration with caching disabled |
| TBD        | 2.0     | Enable caching when traffic threshold met   |
