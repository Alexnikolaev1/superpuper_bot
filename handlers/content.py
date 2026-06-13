from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from keyboards.main import cancel_kb, content_menu, result_actions
from services import together_service
from utils.helpers import format_error, safe_edit_text, send_long_message
from utils.prompts import SYSTEM_ASSISTANT, get_content_prompt
from utils.storage import add_generation

router = Router()

CONTENT_TYPE_LABELS = {
    "content_instagram": ("instagram", "📸 Instagram"),
    "content_telegram": ("telegram", "✈️ Telegram"),
    "content_twitter": ("twitter", "🐦 Twitter/X"),
    "content_linkedin": ("linkedin", "💼 LinkedIn"),
    "content_ad": ("ad", "🎯 Реклама"),
    "content_seo": ("seo", "📝 SEO статья"),
    "content_ideas": ("ideas", "💡 Идеи"),
}

TOPIC_HINTS = {
    "instagram": "криптовалюта, здоровое питание, путешествия в Японию...",
    "telegram": "новости AI, советы по продуктивности, разбор рынка...",
    "twitter": "стартапы, технологии, личный опыт...",
    "linkedin": "карьера, управление командой, бизнес-кейс...",
    "ad": "название продукта, его главная польза...",
    "seo": "как похудеть к лету, лучшие ноутбуки 2025...",
    "ideas": "фитнес, маркетинг, путешествия, финансы...",
}


class ContentStates(StatesGroup):
    waiting_topic = State()


async def _generate_content(content_type: str, topic: str) -> str:
    prompt = get_content_prompt(content_type, topic)
    return await together_service.chat_completion(
        messages=[
            {"role": "system", "content": SYSTEM_ASSISTANT},
            {"role": "user", "content": prompt},
        ],
        model_key="deepseek",
        max_tokens=2048,
        temperature=0.85,
    )


@router.callback_query(F.data == "menu_content")
async def cb_content_menu(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text(
        "📱 <b>Контент-мейкер</b>\n\nВыбери платформу:",
        reply_markup=content_menu(),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data.in_(CONTENT_TYPE_LABELS.keys()))
async def cb_select_content_type(call: CallbackQuery, state: FSMContext) -> None:
    content_key, label = CONTENT_TYPE_LABELS[call.data]
    await state.update_data(content_type=content_key, content_label=label)
    await state.set_state(ContentStates.waiting_topic)

    await call.message.edit_text(
        f"<b>{label}</b> ✅\n\n"
        f"💬 Напиши тему:\n"
        f"<i>Например: {TOPIC_HINTS.get(content_key, 'любая тема')}</i>",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )
    await call.answer()


@router.message(ContentStates.waiting_topic)
async def handle_content_topic(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("📝 Напиши тему текстом.", reply_markup=cancel_kb())
        return

    data = await state.get_data()
    content_type = data.get("content_type", "telegram")
    content_label = data.get("content_label", "Контент")

    await state.update_data(last_topic=message.text)

    thinking_msg = await message.answer(f"✍️ Генерирую <b>{content_label}</b>...", parse_mode="HTML")

    try:
        result = await _generate_content(content_type, message.text)
        add_generation(message.from_user.id, f"content_{content_type}", message.text)

        header = f"✅ <b>{content_label}</b> | Тема: {message.text[:50]}\n\n"
        await thinking_msg.delete()
        await send_long_message(message, header + result, reply_markup=result_actions())

    except Exception as exc:
        await safe_edit_text(
            thinking_msg,
            f"❌ Ошибка: {format_error(exc)}",
            reply_markup=cancel_kb(),
        )


@router.callback_query(F.data == "action_regenerate", ContentStates.waiting_topic)
async def cb_regenerate_content(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    topic = data.get("last_topic")
    content_type = data.get("content_type", "telegram")
    content_label = data.get("content_label", "Контент")

    if not topic:
        await call.answer("Сначала укажи тему", show_alert=True)
        return

    await call.answer("🔄 Генерирую новый вариант...")
    thinking_msg = await call.message.answer(f"🔄 Новый вариант <b>{content_label}</b>...", parse_mode="HTML")

    try:
        result = await _generate_content(content_type, topic)
        add_generation(call.from_user.id, f"content_{content_type}", topic)

        header = f"✅ <b>{content_label}</b> | Тема: {topic[:50]}\n\n"
        await thinking_msg.delete()
        await send_long_message(call.message, header + result, reply_markup=result_actions())
    except Exception as exc:
        await safe_edit_text(thinking_msg, f"❌ Ошибка: {format_error(exc)}", reply_markup=cancel_kb())
