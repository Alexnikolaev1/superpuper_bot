from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from keyboards.main import cancel_kb, result_actions, text_menu
from services import openrouter_service, together_service
from utils.helpers import format_error, safe_edit_text, send_long_message
from utils.prompts import SYSTEM_ASSISTANT
from utils.storage import add_generation, add_message, get_conversation

router = Router()


class TextStates(StatesGroup):
    waiting_prompt = State()
    in_conversation = State()


MODEL_LABELS = {
    "text_deepseek": ("deepseek", "🧠 DeepSeek V3"),
    "text_llama": ("llama", "⚡ Llama 3.3 70B"),
    "text_openrouter": ("openrouter", "🆓 OpenRouter Free"),
}


def _build_messages(user_id: int, user_text: str) -> list[dict]:
    history = get_conversation(user_id)
    messages: list[dict] = [{"role": "system", "content": SYSTEM_ASSISTANT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_text})
    return messages


@router.callback_query(F.data == "menu_text")
async def cb_text_menu(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text(
        "✍️ <b>AI Текст</b>\n\nВыбери модель:",
        reply_markup=text_menu(),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data.in_(MODEL_LABELS.keys()))
async def cb_select_model(call: CallbackQuery, state: FSMContext) -> None:
    model_key, label = MODEL_LABELS[call.data]
    await state.update_data(model=model_key, model_label=label)
    await state.set_state(TextStates.waiting_prompt)

    await call.message.edit_text(
        f"<b>{label}</b> активирована ✅\n\n"
        "💬 Напиши запрос. Я помню контекст разговора.\n\n"
        "<i>/new — сбросить диалог</i>",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )
    await call.answer()


@router.message(TextStates.waiting_prompt)
@router.message(TextStates.in_conversation)
async def handle_text_prompt(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("📝 Отправь текстовое сообщение.", reply_markup=cancel_kb())
        return

    data = await state.get_data()
    model_key = data.get("model", "deepseek")

    thinking_msg = await message.answer("⏳ Думаю...")

    try:
        user_id = message.from_user.id
        messages = _build_messages(user_id, message.text)

        if model_key == "openrouter":
            response = await openrouter_service.chat_completion(messages=messages, model_key="smart")
        else:
            response = await together_service.chat_completion(messages=messages, model_key=model_key)

        add_message(user_id, "user", message.text)
        add_message(user_id, "assistant", response)
        add_generation(user_id, "text", message.text[:100])

        await state.set_state(TextStates.in_conversation)
        await thinking_msg.delete()
        await send_long_message(message, response, reply_markup=result_actions())

    except Exception as exc:
        await safe_edit_text(
            thinking_msg,
            f"❌ Ошибка: {format_error(exc)}\n\nПопробуй ещё раз или смени модель.",
            reply_markup=cancel_kb(),
        )


@router.callback_query(F.data == "action_regenerate", TextStates.waiting_prompt)
@router.callback_query(F.data == "action_regenerate", TextStates.in_conversation)
async def cb_regenerate(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    model_label = data.get("model_label", "AI")
    await call.message.answer(
        f"🔄 <b>{model_label}</b> — напиши новый запрос",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )
    await call.answer()
