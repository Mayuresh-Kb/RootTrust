"""
DynamoDB helper functions for RootTrust marketplace platform.
"""
import os
import boto3
from typing import Dict, List, Optional, Any
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from backend.shared.exceptions import ResourceNotFoundError, ConflictError, ServiceUnavailableError


# Initialize DynamoDB client
dynamodb = None


def get_dynamodb_resource():
    """Get or create DynamoDB resource."""
    global dynamodb
    if dynamodb is None:
        dynamodb = boto3.resource('dynamodb')
    return dynamodb


def get_table_name() -> str:
    """Get DynamoDB table name from environment."""
    table_name = os.environ.get('DYNAMODB_TABLE_NAME', 'RootTrustData')
    return table_name


def get_table():
    """Get DynamoDB table object."""
    db = get_dynamodb_resource()
    table_name = get_table_name()
    return db.Table(table_name)


def get_item(pk: str, sk: str) -> Optional[Dict[str, Any]]:
    """
    Get a single item from DynamoDB by primary key.
    
    Args:
        pk: Partition key value
        sk: Sort key value
        
    Returns:
        Item dictionary if found, None otherwise
        
    Raises:
        ServiceUnavailableError: If DynamoDB is unavailable
    """
    try:
        table = get_table()
        response = table.get_item(
            Key={
                'PK': pk,
                'SK': sk
            }
        )
        return response.get('Item')
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceNotFoundException':
            raise ServiceUnavailableError('DynamoDB', 'Table not found')
        elif error_code == 'ProvisionedThroughputExceededException':
            raise ServiceUnavailableError('DynamoDB', 'Throughput exceeded')
        else:
            raise ServiceUnavailableError('DynamoDB', str(e))


def put_item(item: Dict[str, Any], condition_expression: Optional[str] = None) -> Dict[str, Any]:
    """
    Put an item into DynamoDB.
    
    Args:
        item: Item dictionary to store
        condition_expression: Optional condition for conditional write
        
    Returns:
        The item that was stored
        
    Raises:
        ConflictError: If condition expression fails
        ServiceUnavailableError: If DynamoDB is unavailable
    """
    try:
        table = get_table()
        
        kwargs = {'Item': item}
        if condition_expression:
            kwargs['ConditionExpression'] = condition_expression
        
        table.put_item(**kwargs)
        return item
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ConditionalCheckFailedException':
            raise ConflictError('Item already exists or condition not met')
        elif error_code == 'ProvisionedThroughputExceededException':
            raise ServiceUnavailableError('DynamoDB', 'Throughput exceeded')
        else:
            raise ServiceUnavailableError('DynamoDB', str(e))


def update_item(
    pk: str,
    sk: str,
    update_expression: str,
    expression_attribute_values: Dict[str, Any],
    expression_attribute_names: Optional[Dict[str, str]] = None,
    condition_expression: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update an item in DynamoDB.
    
    Args:
        pk: Partition key value
        sk: Sort key value
        update_expression: DynamoDB update expression
        expression_attribute_values: Values for update expression
        expression_attribute_names: Optional attribute name mappings
        condition_expression: Optional condition for conditional update
        
    Returns:
        Updated item attributes
        
    Raises:
        ResourceNotFoundError: If item doesn't exist
        ConflictError: If condition expression fails
        ServiceUnavailableError: If DynamoDB is unavailable
    """
    try:
        table = get_table()
        
        kwargs = {
            'Key': {'PK': pk, 'SK': sk},
            'UpdateExpression': update_expression,
            'ExpressionAttributeValues': expression_attribute_values,
            'ReturnValues': 'ALL_NEW'
        }
        
        if expression_attribute_names:
            kwargs['ExpressionAttributeNames'] = expression_attribute_names
        
        if condition_expression:
            kwargs['ConditionExpression'] = condition_expression
        
        response = table.update_item(**kwargs)
        return response.get('Attributes', {})
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ConditionalCheckFailedException':
            raise ConflictError('Update condition not met')
        elif error_code == 'ProvisionedThroughputExceededException':
            raise ServiceUnavailableError('DynamoDB', 'Throughput exceeded')
        else:
            raise ServiceUnavailableError('DynamoDB', str(e))


def delete_item(pk: str, sk: str, condition_expression: Optional[str] = None) -> bool:
    """
    Delete an item from DynamoDB.
    
    Args:
        pk: Partition key value
        sk: Sort key value
        condition_expression: Optional condition for conditional delete
        
    Returns:
        True if item was deleted
        
    Raises:
        ConflictError: If condition expression fails
        ServiceUnavailableError: If DynamoDB is unavailable
    """
    try:
        table = get_table()
        
        kwargs = {'Key': {'PK': pk, 'SK': sk}}
        if condition_expression:
            kwargs['ConditionExpression'] = condition_expression
        
        table.delete_item(**kwargs)
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ConditionalCheckFailedException':
            raise ConflictError('Delete condition not met')
        elif error_code == 'ProvisionedThroughputExceededException':
            raise ServiceUnavailableError('DynamoDB', 'Throughput exceeded')
        else:
            raise ServiceUnavailableError('DynamoDB', str(e))


def query(
    key_condition_expression,
    filter_expression=None,
    index_name: Optional[str] = None,
    limit: Optional[int] = None,
    exclusive_start_key: Optional[Dict[str, Any]] = None,
    scan_index_forward: bool = True
) -> Dict[str, Any]:
    """
    Query items from DynamoDB.
    
    Args:
        key_condition_expression: Key condition for query
        filter_expression: Optional filter expression
        index_name: Optional GSI name
        limit: Maximum number of items to return
        exclusive_start_key: Pagination cursor
        scan_index_forward: Sort order (True=ascending, False=descending)
        
    Returns:
        Dictionary with 'Items' list and optional 'LastEvaluatedKey'
        
    Raises:
        ServiceUnavailableError: If DynamoDB is unavailable
    """
    try:
        table = get_table()
        
        kwargs = {
            'KeyConditionExpression': key_condition_expression,
            'ScanIndexForward': scan_index_forward
        }
        
        if filter_expression is not None:
            kwargs['FilterExpression'] = filter_expression
        
        if index_name:
            kwargs['IndexName'] = index_name
        
        if limit:
            kwargs['Limit'] = limit
        
        if exclusive_start_key:
            kwargs['ExclusiveStartKey'] = exclusive_start_key
        
        response = table.query(**kwargs)
        
        result = {
            'Items': response.get('Items', [])
        }
        
        if 'LastEvaluatedKey' in response:
            result['LastEvaluatedKey'] = response['LastEvaluatedKey']
        
        return result
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ProvisionedThroughputExceededException':
            raise ServiceUnavailableError('DynamoDB', 'Throughput exceeded')
        else:
            raise ServiceUnavailableError('DynamoDB', str(e))


def scan(
    filter_expression=None,
    limit: Optional[int] = None,
    exclusive_start_key: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Scan items from DynamoDB (use sparingly, prefer query).
    
    Args:
        filter_expression: Optional filter expression
        limit: Maximum number of items to return
        exclusive_start_key: Pagination cursor
        
    Returns:
        Dictionary with 'Items' list and optional 'LastEvaluatedKey'
        
    Raises:
        ServiceUnavailableError: If DynamoDB is unavailable
    """
    try:
        table = get_table()
        
        kwargs = {}
        
        if filter_expression is not None:
            kwargs['FilterExpression'] = filter_expression
        
        if limit:
            kwargs['Limit'] = limit
        
        if exclusive_start_key:
            kwargs['ExclusiveStartKey'] = exclusive_start_key
        
        response = table.scan(**kwargs)
        
        result = {
            'Items': response.get('Items', [])
        }
        
        if 'LastEvaluatedKey' in response:
            result['LastEvaluatedKey'] = response['LastEvaluatedKey']
        
        return result
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ProvisionedThroughputExceededException':
            raise ServiceUnavailableError('DynamoDB', 'Throughput exceeded')
        else:
            raise ServiceUnavailableError('DynamoDB', str(e))


def batch_get_items(keys: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Get multiple items from DynamoDB in a single request.
    
    Args:
        keys: List of key dictionaries with PK and SK
        
    Returns:
        List of items
        
    Raises:
        ServiceUnavailableError: If DynamoDB is unavailable
    """
    try:
        table = get_table()
        table_name = get_table_name()
        
        db = get_dynamodb_resource()
        response = db.batch_get_item(
            RequestItems={
                table_name: {
                    'Keys': keys
                }
            }
        )
        
        return response.get('Responses', {}).get(table_name, [])
    except ClientError as e:
        raise ServiceUnavailableError('DynamoDB', str(e))


def batch_write_items(items: List[Dict[str, Any]]) -> bool:
    """
    Write multiple items to DynamoDB in a single request.
    
    Args:
        items: List of items to write
        
    Returns:
        True if successful
        
    Raises:
        ServiceUnavailableError: If DynamoDB is unavailable
    """
    try:
        table = get_table()
        
        with table.batch_writer() as batch:
            for item in items:
                batch.put_item(Item=item)
        
        return True
    except ClientError as e:
        raise ServiceUnavailableError('DynamoDB', str(e))


def increment_counter(
    pk: str,
    sk: str,
    counter_field: str,
    increment_by: int = 1
) -> int:
    """
    Atomically increment a counter field in an item.
    
    Args:
        pk: Partition key value
        sk: Sort key value
        counter_field: Name of the counter field to increment
        increment_by: Amount to increment (default 1)
        
    Returns:
        New counter value
        
    Raises:
        ServiceUnavailableError: If DynamoDB is unavailable
    """
    try:
        table = get_table()
        
        response = table.update_item(
            Key={'PK': pk, 'SK': sk},
            UpdateExpression=f'ADD #{counter_field} :inc',
            ExpressionAttributeNames={
                f'#{counter_field}': counter_field
            },
            ExpressionAttributeValues={
                ':inc': increment_by
            },
            ReturnValues='UPDATED_NEW'
        )
        
        return response['Attributes'][counter_field]
    except ClientError as e:
        raise ServiceUnavailableError('DynamoDB', str(e))
