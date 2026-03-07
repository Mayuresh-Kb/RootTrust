"""
Email templates for RootTrust marketplace notifications.
"""
from typing import Dict, Any


def get_registration_confirmation_email(
    user_email: str,
    first_name: str,
    user_id: str,
    verification_link: str = None
) -> Dict[str, Any]:
    """
    Generate registration confirmation email template.
    
    Args:
        user_email: User's email address
        first_name: User's first name
        user_id: User's unique ID
        verification_link: Optional verification link for email confirmation
    
    Returns:
        Dictionary with email subject, html_body, and text_body
    """
    subject = "Welcome to RootTrust - Registration Successful"
    
    # HTML email body
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: #2e7d32;
                color: white;
                padding: 20px;
                text-align: center;
                border-radius: 5px 5px 0 0;
            }}
            .content {{
                background-color: #f9f9f9;
                padding: 30px;
                border: 1px solid #ddd;
                border-top: none;
            }}
            .button {{
                display: inline-block;
                background-color: #2e7d32;
                color: white;
                padding: 12px 30px;
                text-decoration: none;
                border-radius: 5px;
                margin: 20px 0;
            }}
            .footer {{
                text-align: center;
                padding: 20px;
                color: #666;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Welcome to RootTrust!</h1>
        </div>
        <div class="content">
            <p>Hi {first_name},</p>
            
            <p>Thank you for registering with RootTrust, the AI-powered marketplace connecting farmers directly with consumers.</p>
            
            <p>Your account has been successfully created. You can now:</p>
            <ul>
                <li>Browse authentic agricultural products</li>
                <li>Connect with verified farmers</li>
                <li>Enjoy AI-verified product authenticity</li>
            </ul>
            
            {f'<p>Please verify your email address by clicking the button below:</p><a href="{verification_link}" class="button">Verify Email Address</a>' if verification_link else ''}
            
            <p>If you have any questions, feel free to reach out to our support team.</p>
            
            <p>Best regards,<br>The RootTrust Team</p>
        </div>
        <div class="footer">
            <p>This is an automated message. Please do not reply to this email.</p>
            <p>&copy; 2024 RootTrust. All rights reserved.</p>
        </div>
    </body>
    </html>
    """
    
    # Plain text email body (fallback)
    text_body = f"""
    Welcome to RootTrust!
    
    Hi {first_name},
    
    Thank you for registering with RootTrust, the AI-powered marketplace connecting farmers directly with consumers.
    
    Your account has been successfully created. You can now:
    - Browse authentic agricultural products
    - Connect with verified farmers
    - Enjoy AI-verified product authenticity
    
    {f'Please verify your email address by visiting: {verification_link}' if verification_link else ''}
    
    If you have any questions, feel free to reach out to our support team.
    
    Best regards,
    The RootTrust Team
    
    ---
    This is an automated message. Please do not reply to this email.
    © 2024 RootTrust. All rights reserved.
    """
    
    return {
        'subject': subject,
        'html_body': html_body,
        'text_body': text_body
    }



def get_order_status_update_email(
    consumer_email: str,
    consumer_first_name: str,
    order_id: str,
    product_name: str,
    new_status: str,
    estimated_delivery_date: str = None,
    actual_delivery_date: str = None
) -> Dict[str, Any]:
    """
    Generate order status update email template.
    
    Args:
        consumer_email: Consumer's email address
        consumer_first_name: Consumer's first name
        order_id: Order ID
        product_name: Product name
        new_status: New order status
        estimated_delivery_date: Estimated delivery date (ISO format)
        actual_delivery_date: Actual delivery date (ISO format, for delivered status)
    
    Returns:
        Dictionary with email subject, html_body, and text_body
    """
    # Map status to user-friendly text
    status_messages = {
        'confirmed': 'Your order has been confirmed',
        'processing': 'Your order is being processed',
        'shipped': 'Your order has been shipped',
        'delivered': 'Your order has been delivered',
        'cancelled': 'Your order has been cancelled'
    }
    
    status_descriptions = {
        'confirmed': 'The farmer has confirmed your order and will begin processing it soon.',
        'processing': 'The farmer is preparing your order for shipment.',
        'shipped': 'Your order is on its way to you!',
        'delivered': 'Your order has been successfully delivered. We hope you enjoy your fresh produce!',
        'cancelled': 'Your order has been cancelled. If you have any questions, please contact support.'
    }
    
    status_message = status_messages.get(new_status, 'Your order status has been updated')
    status_description = status_descriptions.get(new_status, '')
    
    subject = f"RootTrust Order Update: {status_message}"
    
    # Format dates for display
    delivery_info = ''
    if new_status == 'delivered' and actual_delivery_date:
        try:
            from datetime import datetime
            delivery_date = datetime.fromisoformat(actual_delivery_date.replace('Z', '+00:00'))
            delivery_info = f'<p><strong>Delivered on:</strong> {delivery_date.strftime("%B %d, %Y")}</p>'
        except:
            delivery_info = ''
    elif new_status in ['confirmed', 'processing', 'shipped'] and estimated_delivery_date:
        try:
            from datetime import datetime
            est_date = datetime.fromisoformat(estimated_delivery_date.replace('Z', '+00:00'))
            delivery_info = f'<p><strong>Estimated delivery:</strong> {est_date.strftime("%B %d, %Y")}</p>'
        except:
            delivery_info = ''
    
    # HTML email body
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: #2e7d32;
                color: white;
                padding: 20px;
                text-align: center;
                border-radius: 5px 5px 0 0;
            }}
            .content {{
                background-color: #f9f9f9;
                padding: 30px;
                border: 1px solid #ddd;
                border-top: none;
            }}
            .status-badge {{
                display: inline-block;
                background-color: #4caf50;
                color: white;
                padding: 8px 16px;
                border-radius: 20px;
                font-weight: bold;
                text-transform: uppercase;
                font-size: 14px;
                margin: 10px 0;
            }}
            .order-details {{
                background-color: white;
                padding: 20px;
                border-radius: 5px;
                margin: 20px 0;
            }}
            .footer {{
                text-align: center;
                padding: 20px;
                color: #666;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Order Status Update</h1>
        </div>
        <div class="content">
            <p>Hi {consumer_first_name},</p>
            
            <p>{status_message}!</p>
            
            <div class="status-badge">{new_status.upper()}</div>
            
            <p>{status_description}</p>
            
            <div class="order-details">
                <h3>Order Details</h3>
                <p><strong>Order ID:</strong> {order_id}</p>
                <p><strong>Product:</strong> {product_name}</p>
                <p><strong>Status:</strong> {new_status.capitalize()}</p>
                {delivery_info}
            </div>
            
            {f'<p>Thank you for choosing RootTrust! We hope you enjoy your fresh, authentic produce. Please consider leaving a review to help other customers and support the farmer.</p>' if new_status == 'delivered' else ''}
            
            <p>If you have any questions about your order, please don't hesitate to contact us.</p>
            
            <p>Best regards,<br>The RootTrust Team</p>
        </div>
        <div class="footer">
            <p>This is an automated message. Please do not reply to this email.</p>
            <p>&copy; 2024 RootTrust. All rights reserved.</p>
        </div>
    </body>
    </html>
    """
    
    # Plain text email body (fallback)
    delivery_text = ''
    if new_status == 'delivered' and actual_delivery_date:
        try:
            from datetime import datetime
            delivery_date = datetime.fromisoformat(actual_delivery_date.replace('Z', '+00:00'))
            delivery_text = f'\nDelivered on: {delivery_date.strftime("%B %d, %Y")}'
        except:
            delivery_text = ''
    elif new_status in ['confirmed', 'processing', 'shipped'] and estimated_delivery_date:
        try:
            from datetime import datetime
            est_date = datetime.fromisoformat(estimated_delivery_date.replace('Z', '+00:00'))
            delivery_text = f'\nEstimated delivery: {est_date.strftime("%B %d, %Y")}'
        except:
            delivery_text = ''
    
    text_body = f"""
    Order Status Update
    
    Hi {consumer_first_name},
    
    {status_message}!
    
    {status_description}
    
    Order Details:
    - Order ID: {order_id}
    - Product: {product_name}
    - Status: {new_status.capitalize()}{delivery_text}
    
    {'Thank you for choosing RootTrust! We hope you enjoy your fresh, authentic produce. Please consider leaving a review to help other customers and support the farmer.' if new_status == 'delivered' else ''}
    
    If you have any questions about your order, please don't hesitate to contact us.
    
    Best regards,
    The RootTrust Team
    
    ---
    This is an automated message. Please do not reply to this email.
    © 2024 RootTrust. All rights reserved.
    """
    
    return {
        'subject': subject,
        'html_body': html_body,
        'text_body': text_body
    }



def get_review_request_email(
    consumer_email: str,
    consumer_first_name: str,
    order_id: str,
    product_name: str,
    product_id: str,
    farmer_name: str
) -> Dict[str, Any]:
    """
    Generate review request email template.
    
    Args:
        consumer_email: Consumer's email address
        consumer_first_name: Consumer's first name
        order_id: Order ID
        product_name: Product name
        product_id: Product ID
        farmer_name: Farmer's name
    
    Returns:
        Dictionary with email subject, html_body, and text_body
    """
    subject = "How was your RootTrust order? Share your experience!"
    
    # HTML email body
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: #2e7d32;
                color: white;
                padding: 20px;
                text-align: center;
                border-radius: 5px 5px 0 0;
            }}
            .content {{
                background-color: #f9f9f9;
                padding: 30px;
                border: 1px solid #ddd;
                border-top: none;
            }}
            .button {{
                display: inline-block;
                background-color: #2e7d32;
                color: white;
                padding: 12px 30px;
                text-decoration: none;
                border-radius: 5px;
                margin: 20px 0;
                text-align: center;
            }}
            .product-info {{
                background-color: white;
                padding: 20px;
                border-radius: 5px;
                margin: 20px 0;
            }}
            .footer {{
                text-align: center;
                padding: 20px;
                color: #666;
                font-size: 12px;
            }}
            .stars {{
                font-size: 24px;
                color: #ffa000;
                margin: 10px 0;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>We'd Love Your Feedback!</h1>
        </div>
        <div class="content">
            <p>Hi {consumer_first_name},</p>
            
            <p>Thank you for your recent order from RootTrust! We hope you enjoyed your fresh, authentic produce.</p>
            
            <div class="product-info">
                <h3>Your Order</h3>
                <p><strong>Product:</strong> {product_name}</p>
                <p><strong>Farmer:</strong> {farmer_name}</p>
                <p><strong>Order ID:</strong> {order_id}</p>
            </div>
            
            <p>Your feedback helps other customers make informed decisions and supports our farmers in delivering the best quality products.</p>
            
            <div class="stars">★ ★ ★ ★ ★</div>
            
            <p>Please take a moment to share your experience:</p>
            
            <div style="text-align: center;">
                <a href="https://roottrust.com/orders/{order_id}/review" class="button">Write a Review</a>
            </div>
            
            <p>You can rate the product, share your thoughts, and even upload photos of what you received!</p>
            
            <p>Thank you for being part of the RootTrust community and supporting local farmers.</p>
            
            <p>Best regards,<br>The RootTrust Team</p>
        </div>
        <div class="footer">
            <p>This is an automated message. Please do not reply to this email.</p>
            <p>&copy; 2024 RootTrust. All rights reserved.</p>
        </div>
    </body>
    </html>
    """
    
    # Plain text email body (fallback)
    text_body = f"""
    We'd Love Your Feedback!
    
    Hi {consumer_first_name},
    
    Thank you for your recent order from RootTrust! We hope you enjoyed your fresh, authentic produce.
    
    Your Order:
    - Product: {product_name}
    - Farmer: {farmer_name}
    - Order ID: {order_id}
    
    Your feedback helps other customers make informed decisions and supports our farmers in delivering the best quality products.
    
    Please take a moment to share your experience by visiting:
    https://roottrust.com/orders/{order_id}/review
    
    You can rate the product, share your thoughts, and even upload photos of what you received!
    
    Thank you for being part of the RootTrust community and supporting local farmers.
    
    Best regards,
    The RootTrust Team
    
    ---
    This is an automated message. Please do not reply to this email.
    © 2024 RootTrust. All rights reserved.
    """
    
    return {
        'subject': subject,
        'html_body': html_body,
        'text_body': text_body
    }



def get_promotion_summary_email(
    farmer_email: str,
    farmer_first_name: str,
    promotion_id: str,
    product_name: str,
    start_date: str,
    end_date: str,
    total_views: int,
    total_clicks: int,
    total_conversions: int,
    total_spent: float,
    budget: float
) -> Dict[str, Any]:
    """
    Generate promotion summary email template.
    
    Args:
        farmer_email: Farmer's email address
        farmer_first_name: Farmer's first name
        promotion_id: Promotion ID
        product_name: Product name
        start_date: Promotion start date (ISO format)
        end_date: Promotion end date (ISO format)
        total_views: Total number of views
        total_clicks: Total number of clicks
        total_conversions: Total number of conversions
        total_spent: Total amount spent
        budget: Original budget
    
    Returns:
        Dictionary with email subject, html_body, and text_body
    """
    subject = f"RootTrust Promotion Summary: {product_name}"
    
    # Calculate metrics
    click_through_rate = (total_clicks / total_views * 100) if total_views > 0 else 0
    conversion_rate = (total_conversions / total_clicks * 100) if total_clicks > 0 else 0
    cost_per_conversion = (total_spent / total_conversions) if total_conversions > 0 else 0
    
    # Format dates for display
    try:
        from datetime import datetime
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        start_formatted = start.strftime("%B %d, %Y")
        end_formatted = end.strftime("%B %d, %Y")
        duration_days = (end - start).days
    except:
        start_formatted = start_date
        end_formatted = end_date
        duration_days = 0
    
    # HTML email body
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: #2e7d32;
                color: white;
                padding: 20px;
                text-align: center;
                border-radius: 5px 5px 0 0;
            }}
            .content {{
                background-color: #f9f9f9;
                padding: 30px;
                border: 1px solid #ddd;
                border-top: none;
            }}
            .metrics-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 15px;
                margin: 20px 0;
            }}
            .metric-card {{
                background-color: white;
                padding: 20px;
                border-radius: 5px;
                text-align: center;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .metric-value {{
                font-size: 32px;
                font-weight: bold;
                color: #2e7d32;
                margin: 10px 0;
            }}
            .metric-label {{
                font-size: 14px;
                color: #666;
                text-transform: uppercase;
            }}
            .summary-box {{
                background-color: white;
                padding: 20px;
                border-radius: 5px;
                margin: 20px 0;
            }}
            .footer {{
                text-align: center;
                padding: 20px;
                color: #666;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Promotion Campaign Summary</h1>
        </div>
        <div class="content">
            <p>Hi {farmer_first_name},</p>
            
            <p>Your promotion campaign for <strong>{product_name}</strong> has ended. Here's a summary of your campaign performance:</p>
            
            <div class="summary-box">
                <h3>Campaign Details</h3>
                <p><strong>Promotion ID:</strong> {promotion_id}</p>
                <p><strong>Product:</strong> {product_name}</p>
                <p><strong>Duration:</strong> {start_formatted} - {end_formatted} ({duration_days} days)</p>
                <p><strong>Budget:</strong> ₹{budget:.2f}</p>
                <p><strong>Spent:</strong> ₹{total_spent:.2f}</p>
            </div>
            
            <h3>Performance Metrics</h3>
            
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">Total Views</div>
                    <div class="metric-value">{total_views:,}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Total Clicks</div>
                    <div class="metric-value">{total_clicks:,}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Conversions</div>
                    <div class="metric-value">{total_conversions:,}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Click Rate</div>
                    <div class="metric-value">{click_through_rate:.1f}%</div>
                </div>
            </div>
            
            <div class="summary-box">
                <h3>Additional Insights</h3>
                <p><strong>Conversion Rate:</strong> {conversion_rate:.1f}%</p>
                <p><strong>Cost per Conversion:</strong> ₹{cost_per_conversion:.2f}</p>
                <p><strong>Budget Utilization:</strong> {(total_spent / budget * 100):.1f}%</p>
            </div>
            
            <p>Thank you for using RootTrust's promotion tools to grow your business. We hope this campaign helped you reach more customers!</p>
            
            <p>Ready to run another promotion? Log in to your farmer dashboard to create a new campaign.</p>
            
            <p>Best regards,<br>The RootTrust Team</p>
        </div>
        <div class="footer">
            <p>This is an automated message. Please do not reply to this email.</p>
            <p>&copy; 2024 RootTrust. All rights reserved.</p>
        </div>
    </body>
    </html>
    """
    
    # Plain text email body (fallback)
    text_body = f"""
    Promotion Campaign Summary
    
    Hi {farmer_first_name},
    
    Your promotion campaign for {product_name} has ended. Here's a summary of your campaign performance:
    
    Campaign Details:
    - Promotion ID: {promotion_id}
    - Product: {product_name}
    - Duration: {start_formatted} - {end_formatted} ({duration_days} days)
    - Budget: ₹{budget:.2f}
    - Spent: ₹{total_spent:.2f}
    
    Performance Metrics:
    - Total Views: {total_views:,}
    - Total Clicks: {total_clicks:,}
    - Conversions: {total_conversions:,}
    - Click-Through Rate: {click_through_rate:.1f}%
    
    Additional Insights:
    - Conversion Rate: {conversion_rate:.1f}%
    - Cost per Conversion: ₹{cost_per_conversion:.2f}
    - Budget Utilization: {(total_spent / budget * 100):.1f}%
    
    Thank you for using RootTrust's promotion tools to grow your business. We hope this campaign helped you reach more customers!
    
    Ready to run another promotion? Log in to your farmer dashboard to create a new campaign.
    
    Best regards,
    The RootTrust Team
    
    ---
    This is an automated message. Please do not reply to this email.
    © 2024 RootTrust. All rights reserved.
    """
    
    return {
        'subject': subject,
        'html_body': html_body,
        'text_body': text_body
    }



def get_farmer_bonus_email(
    farmer_email: str,
    farmer_first_name: str,
    bonus_type: str,
    bonus_amount: float,
    streak_count: int = None
) -> Dict[str, Any]:
    """
    Generate farmer bonus notification email template.
    
    Args:
        farmer_email: Farmer's email address
        farmer_first_name: Farmer's first name
        bonus_type: Type of bonus (e.g., "Sales Streak Bonus")
        bonus_amount: Bonus amount earned
        streak_count: Number of consecutive sales (for streak bonus)
    
    Returns:
        Dictionary with email subject, html_body, and text_body
    """
    subject = f"Congratulations! You've Earned a {bonus_type}"
    
    # Customize message based on bonus type
    bonus_message = f"You've earned a {bonus_type}!"
    bonus_details = ""
    
    if "streak" in bonus_type.lower() and streak_count:
        bonus_message = f"You've achieved {streak_count} consecutive sales with excellent ratings!"
        bonus_details = f"""
        <p>You've successfully completed {streak_count} consecutive sales where all customers rated their experience 3 stars or higher. This demonstrates your commitment to quality and customer satisfaction.</p>
        """
    
    # HTML email body
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: #2e7d32;
                color: white;
                padding: 20px;
                text-align: center;
                border-radius: 5px 5px 0 0;
            }}
            .content {{
                background-color: #f9f9f9;
                padding: 30px;
                border: 1px solid #ddd;
                border-top: none;
            }}
            .bonus-badge {{
                background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%);
                color: #333;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                margin: 20px 0;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }}
            .bonus-amount {{
                font-size: 48px;
                font-weight: bold;
                color: #2e7d32;
                margin: 10px 0;
            }}
            .celebration {{
                font-size: 48px;
                text-align: center;
                margin: 20px 0;
            }}
            .footer {{
                text-align: center;
                padding: 20px;
                color: #666;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎉 Congratulations!</h1>
        </div>
        <div class="content">
            <p>Hi {farmer_first_name},</p>
            
            <div class="celebration">🏆 🌟 🎊</div>
            
            <p><strong>{bonus_message}</strong></p>
            
            {bonus_details}
            
            <div class="bonus-badge">
                <h2 style="margin: 0; color: #333;">{bonus_type}</h2>
                <div class="bonus-amount">₹{bonus_amount:.2f}</div>
                <p style="margin: 0; color: #666;">Bonus Earned</p>
            </div>
            
            <p>This bonus has been added to your account. Your dedication to providing quality products and excellent service is what makes RootTrust a trusted marketplace.</p>
            
            <p>Keep up the great work! Continue delivering exceptional products and service to earn more bonuses and grow your business.</p>
            
            <p>Thank you for being a valued member of the RootTrust farming community.</p>
            
            <p>Best regards,<br>The RootTrust Team</p>
        </div>
        <div class="footer">
            <p>This is an automated message. Please do not reply to this email.</p>
            <p>&copy; 2024 RootTrust. All rights reserved.</p>
        </div>
    </body>
    </html>
    """
    
    # Plain text email body (fallback)
    text_body = f"""
    Congratulations!
    
    Hi {farmer_first_name},
    
    {bonus_message}
    
    {f"You've successfully completed {streak_count} consecutive sales where all customers rated their experience 3 stars or higher. This demonstrates your commitment to quality and customer satisfaction." if "streak" in bonus_type.lower() and streak_count else ""}
    
    {bonus_type}: ₹{bonus_amount:.2f}
    
    This bonus has been added to your account. Your dedication to providing quality products and excellent service is what makes RootTrust a trusted marketplace.
    
    Keep up the great work! Continue delivering exceptional products and service to earn more bonuses and grow your business.
    
    Thank you for being a valued member of the RootTrust farming community.
    
    Best regards,
    The RootTrust Team
    
    ---
    This is an automated message. Please do not reply to this email.
    © 2024 RootTrust. All rights reserved.
    """
    
    return {
        'subject': subject,
        'html_body': html_body,
        'text_body': text_body
    }



def get_new_product_notification_email(
    consumer_email: str,
    consumer_first_name: str,
    product_name: str,
    product_id: str,
    category: str,
    price: float,
    farmer_name: str,
    product_description: str = None
) -> Dict[str, Any]:
    """
    Generate new product notification email template.
    
    Args:
        consumer_email: Consumer's email address
        consumer_first_name: Consumer's first name
        product_name: Product name
        product_id: Product ID
        category: Product category
        price: Product price
        farmer_name: Farmer's name
        product_description: Optional product description
    
    Returns:
        Dictionary with email subject, html_body, and text_body
    """
    subject = f"New Product Available: {product_name}"
    
    # Truncate description if too long
    description_preview = ""
    if product_description:
        if len(product_description) > 150:
            description_preview = product_description[:150] + "..."
        else:
            description_preview = product_description
    
    # HTML email body
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: #2e7d32;
                color: white;
                padding: 20px;
                text-align: center;
                border-radius: 5px 5px 0 0;
            }}
            .content {{
                background-color: #f9f9f9;
                padding: 30px;
                border: 1px solid #ddd;
                border-top: none;
            }}
            .product-card {{
                background-color: white;
                padding: 20px;
                border-radius: 5px;
                margin: 20px 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .price {{
                font-size: 28px;
                font-weight: bold;
                color: #2e7d32;
                margin: 10px 0;
            }}
            .button {{
                display: inline-block;
                background-color: #2e7d32;
                color: white;
                padding: 12px 30px;
                text-decoration: none;
                border-radius: 5px;
                margin: 20px 0;
                text-align: center;
            }}
            .badge {{
                display: inline-block;
                background-color: #4caf50;
                color: white;
                padding: 5px 12px;
                border-radius: 15px;
                font-size: 12px;
                font-weight: bold;
                text-transform: uppercase;
                margin: 5px 0;
            }}
            .footer {{
                text-align: center;
                padding: 20px;
                color: #666;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🌱 Fresh Product Alert!</h1>
        </div>
        <div class="content">
            <p>Hi {consumer_first_name},</p>
            
            <p>Great news! A new product has just been verified and added to the RootTrust marketplace.</p>
            
            <div class="product-card">
                <h2 style="margin-top: 0; color: #2e7d32;">{product_name}</h2>
                
                <div class="badge">{category.upper()}</div>
                
                <div class="price">₹{price:.2f}</div>
                
                <p><strong>From:</strong> {farmer_name}</p>
                
                {f'<p style="color: #666; font-style: italic;">{description_preview}</p>' if description_preview else ''}
                
                <div style="text-align: center; margin-top: 20px;">
                    <a href="https://roottrust.com/products/{product_id}" class="button">View Product Details</a>
                </div>
            </div>
            
            <p>This product has been verified by our AI-powered authenticity system to ensure you receive genuine, high-quality produce.</p>
            
            <p>Don't miss out on this fresh addition to our marketplace!</p>
            
            <p>Best regards,<br>The RootTrust Team</p>
            
            <p style="font-size: 12px; color: #666; margin-top: 30px;">
                You're receiving this email because you've opted in to receive new product notifications. 
                You can update your notification preferences in your account settings.
            </p>
        </div>
        <div class="footer">
            <p>This is an automated message. Please do not reply to this email.</p>
            <p>&copy; 2024 RootTrust. All rights reserved.</p>
        </div>
    </body>
    </html>
    """
    
    # Plain text email body (fallback)
    text_body = f"""
    Fresh Product Alert!
    
    Hi {consumer_first_name},
    
    Great news! A new product has just been verified and added to the RootTrust marketplace.
    
    Product Details:
    - Name: {product_name}
    - Category: {category}
    - Price: ₹{price:.2f}
    - From: {farmer_name}
    
    {f'Description: {description_preview}' if description_preview else ''}
    
    This product has been verified by our AI-powered authenticity system to ensure you receive genuine, high-quality produce.
    
    View product details: https://roottrust.com/products/{product_id}
    
    Don't miss out on this fresh addition to our marketplace!
    
    Best regards,
    The RootTrust Team
    
    ---
    You're receiving this email because you've opted in to receive new product notifications. 
    You can update your notification preferences in your account settings.
    
    This is an automated message. Please do not reply to this email.
    © 2024 RootTrust. All rights reserved.
    """
    
    return {
        'subject': subject,
        'html_body': html_body,
        'text_body': text_body
    }



def get_followed_farmer_notification_email(
    consumer_email: str,
    consumer_first_name: str,
    product_name: str,
    product_id: str,
    category: str,
    price: float,
    farmer_name: str,
    product_description: str = None
) -> Dict[str, Any]:
    """
    Generate followed farmer new product notification email template.
    
    Args:
        consumer_email: Consumer's email address
        consumer_first_name: Consumer's first name
        product_name: Product name
        product_id: Product ID
        category: Product category
        price: Product price
        farmer_name: Farmer's name
        product_description: Optional product description
    
    Returns:
        Dictionary with email subject, html_body, and text_body
    """
    subject = f"{farmer_name} has a new product: {product_name}"
    
    # Truncate description if too long
    description_preview = ""
    if product_description:
        if len(product_description) > 150:
            description_preview = product_description[:150] + "..."
        else:
            description_preview = product_description
    
    # HTML email body
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: #2e7d32;
                color: white;
                padding: 20px;
                text-align: center;
                border-radius: 5px 5px 0 0;
            }}
            .content {{
                background-color: #f9f9f9;
                padding: 30px;
                border: 1px solid #ddd;
                border-top: none;
            }}
            .product-card {{
                background-color: white;
                padding: 20px;
                border-radius: 5px;
                margin: 20px 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .price {{
                font-size: 28px;
                font-weight: bold;
                color: #2e7d32;
                margin: 10px 0;
            }}
            .button {{
                display: inline-block;
                background-color: #2e7d32;
                color: white;
                padding: 12px 30px;
                text-decoration: none;
                border-radius: 5px;
                margin: 20px 0;
                text-align: center;
            }}
            .badge {{
                display: inline-block;
                background-color: #4caf50;
                color: white;
                padding: 5px 12px;
                border-radius: 15px;
                font-size: 12px;
                font-weight: bold;
                text-transform: uppercase;
                margin: 5px 0;
            }}
            .farmer-badge {{
                display: inline-block;
                background-color: #ff9800;
                color: white;
                padding: 5px 12px;
                border-radius: 15px;
                font-size: 12px;
                font-weight: bold;
                margin: 5px 0;
            }}
            .footer {{
                text-align: center;
                padding: 20px;
                color: #666;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🌾 New from Your Followed Farmer!</h1>
        </div>
        <div class="content">
            <p>Hi {consumer_first_name},</p>
            
            <p>Great news! <strong>{farmer_name}</strong>, a farmer you're following, has just listed a new product on RootTrust.</p>
            
            <div class="product-card">
                <div class="farmer-badge">👨‍🌾 FROM {farmer_name.upper()}</div>
                
                <h2 style="margin-top: 10px; color: #2e7d32;">{product_name}</h2>
                
                <div class="badge">{category.upper()}</div>
                
                <div class="price">₹{price:.2f}</div>
                
                {f'<p style="color: #666; font-style: italic;">{description_preview}</p>' if description_preview else ''}
                
                <div style="text-align: center; margin-top: 20px;">
                    <a href="https://roottrust.com/products/{product_id}" class="button">View Product Details</a>
                </div>
            </div>
            
            <p>As a follower of {farmer_name}, you're among the first to know about this new offering. Don't miss out on this fresh addition!</p>
            
            <p>This product has been verified by our AI-powered authenticity system to ensure you receive genuine, high-quality produce.</p>
            
            <p>Best regards,<br>The RootTrust Team</p>
            
            <p style="font-size: 12px; color: #666; margin-top: 30px;">
                You're receiving this email because you follow {farmer_name} and have opted in to receive notifications about their new products. 
                You can update your notification preferences or unfollow farmers in your account settings.
            </p>
        </div>
        <div class="footer">
            <p>This is an automated message. Please do not reply to this email.</p>
            <p>&copy; 2024 RootTrust. All rights reserved.</p>
        </div>
    </body>
    </html>
    """
    
    # Plain text email body (fallback)
    text_body = f"""
    New from Your Followed Farmer!
    
    Hi {consumer_first_name},
    
    Great news! {farmer_name}, a farmer you're following, has just listed a new product on RootTrust.
    
    Product Details:
    - Name: {product_name}
    - Category: {category}
    - Price: ₹{price:.2f}
    - From: {farmer_name}
    
    {f'Description: {description_preview}' if description_preview else ''}
    
    As a follower of {farmer_name}, you're among the first to know about this new offering. Don't miss out on this fresh addition!
    
    This product has been verified by our AI-powered authenticity system to ensure you receive genuine, high-quality produce.
    
    View product details: https://roottrust.com/products/{product_id}
    
    Best regards,
    The RootTrust Team
    
    ---
    You're receiving this email because you follow {farmer_name} and have opted in to receive notifications about their new products. 
    You can update your notification preferences or unfollow farmers in your account settings.
    
    This is an automated message. Please do not reply to this email.
    © 2024 RootTrust. All rights reserved.
    """
    
    return {
        'subject': subject,
        'html_body': html_body,
        'text_body': text_body
    }
