"""
Inline query handler for payment requests.
"""

import logging
import uuid
from aiogram import Router, F
from aiogram.types import (
    InlineQuery, 
    InlineQueryResultArticle, 
    InputTextMessageContent, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    InputInvoiceMessageContent, 
    LabeledPrice
)
from services import GiftCatalogService

router = Router()
logger = logging.getLogger(__name__)

@router.inline_query()
async def inline_handler(inline_query: InlineQuery, **kwargs):
    """Handle inline query for gift payment requests."""
    query = inline_query.query.strip()
    bot = inline_query.bot
    catalog = GiftCatalogService(bot)
    gifts = await catalog.get_gifts()
    
    results = []

    # Check if query is a positive integer for custom star payment
    if query.isdigit() and int(query) > 0:
        stars_amount = int(query)
        custom_result_id = f"custom_{stars_amount}_{uuid.uuid4().hex[:8]}"
        custom_payload = f"custom_{stars_amount}_{inline_query.from_user.id}"
        
        results.append(
            InlineQueryResultArticle(
                id=custom_result_id,
                title=f"💰 Send {stars_amount} ⭐",
                description=f"Request a custom payment of {stars_amount} Stars",
                input_message_content=InputInvoiceMessageContent(
                    title="Custom Star Payment",
                    description=f"Send {stars_amount} Stars to {inline_query.from_user.first_name}",
                    payload=custom_payload,
                    provider_token="", # Stars
                    currency="XTR",
                    prices=[LabeledPrice(label="Stars", amount=stars_amount)],
                    is_test=False
                )
            )
        )
    
    # If query is empty or "all", show all gifts
    # If query is a number, filter by price or name
    for gift in gifts:
        gift_name = gift.get("name", "Gift")
        gift_id = gift.get("id")
        stars = gift.get("stars", 0)
        icon = gift.get("icon", "🎁")
        
        if query and query.lower() not in gift_name.lower() and query not in str(stars):
            continue
            
        # Create a unique result ID
        result_id = str(uuid.uuid4())
        
        # Create a direct payment invoice for inline results
        # This allows users to pay directly in the chat without starting the bot
        invoice_payload = f"inline_{gift_id}_{inline_query.from_user.id}"
        
        results.append(
            InlineQueryResultArticle(
                id=result_id,
                title=f"{icon} {gift_name} - {stars} ⭐",
                description=f"Send me this gift directly for {stars} Stars",
                input_message_content=InputInvoiceMessageContent(
                    title=f"Gift: {gift_name}",
                    description=f"Send a {gift_name} gift to {inline_query.from_user.first_name}",
                    payload=invoice_payload,
                    provider_token="",  # Stars
                    currency="XTR",
                    prices=[LabeledPrice(label=gift_name, amount=stars)],
                    photo_url=None, # You could add gift images here
                    is_flexible=False,
                    need_name=False,
                    need_phone_number=False,
                    need_email=False,
                    need_shipping_address=False,
                    send_phone_number_to_provider=False,
                    send_email_to_provider=False,
                    is_test=False
                )
            )
        )
        
        # Limit results to 10
        if len(results) >= 10:
            break
            
    await inline_query.answer(
        results, 
        cache_time=300, 
        is_personal=False,
        switch_pm_text="🎁 Browse All Gifts",
        switch_pm_parameter="inline_browse"
    )
