"""
Inline query handler for payment requests.
"""

import logging
import uuid
from aiogram import Router, F
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton
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
        
        # This article will show up in the inline results
        # When clicked, it sends a message with a button to start the purchase flow for this gift
        results.append(
            InlineQueryResultArticle(
                id=result_id,
                title=f"{icon} {gift_name} - {stars} ⭐",
                description=f"Send this gift for {stars} Stars",
                input_message_content=InputTextMessageContent(
                    message_text=f"🎁 <b>Gift Request: {gift_name}</b>\n\n"
                                 f"Someone is requesting a {gift_name} gift!\n"
                                 f"Price: {stars} ⭐\n\n"
                                 f"Click the button below to pay and send this gift.",
                    parse_mode="HTML"
                ),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=f"💳 Pay {stars} ⭐ & Send", callback_data=f"gift_select:{gift_id}")]
                ])
            )
        )
        
        # Limit results to 10
        if len(results) >= 10:
            break
            
    await inline_query.answer(results, cache_time=300, is_personal=False)
