import re

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from keyboards.main import cancel_kb, image_menu, image_ratio_menu, result_actions
from services import together_service
from services.together_service import chat_completion
from utils.helpers import format_error, safe_edit_text
from utils.prompts import IMAGE_ENHANCE_PROMPT
from utils.storage import add_generation, save_last_image
from utils.texts import RATIO_LABELS

router = Router()

MODEL_LABELS = {
    "img_flux_schnell": ("flux_schnell", "⚡ FLUX.1 Schnell"),
    "img_flux_dev": ("flux_dev", "✨ FLUX.1 Dev"),
    "img_sdxl": ("sdxl", "🖌 SDXL"),
}

SIZE_PATTERN = re.compile(r"(\d+)x(\d+)$")


class ImageStates(StatesGroup):
    selecting_ratio = State()
    waiting_prompt = State()


def _parse_ratio(callback_data: str) -> tuple[int, int] | None:
    match = SIZE_PATTERN.search(callback_data)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


@router.callback_query(F.data == "menu_image")
async def cb_image_menu(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text(
        "🖼 <b>Генерация изображений</b>\n\nВыбери модель:",
        reply_markup=image_menu(),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data.in_(MODEL_LABELS.keys()))
async def cb_select_image_model(call: CallbackQuery, state: FSMContext) -> None:
    model_key, label = MODEL_LABELS[call.data]
    await state.update_data(model=model_key, model_label=label)
    await state.set_state(ImageStates.selecting_ratio)

    await call.message.edit_text(
        f"<b>{label}</b> ✅\n\nВыбери соотношение сторон:",
        reply_markup=image_ratio_menu(model_key),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data.startswith("ratio_"))
async def cb_select_ratio(call: CallbackQuery, state: FSMContext) -> None:
    size = _parse_ratio(call.data)
    if not size:
        await call.answer("❌ Неверный формат", show_alert=True)
        return

    width, height = size
    size_str = f"{width}x{height}"

    data = await state.get_data()
    model_label = data.get("model_label", "AI")
    await state.update_data(width=width, height=height)
    await state.set_state(ImageStates.waiting_prompt)

    ratio_label = RATIO_LABELS.get(size_str, size_str)
    await call.message.edit_text(
        f"<b>{model_label}</b> | <b>{ratio_label}</b> ✅\n\n"
        "📝 Опиши изображение.\n"
        "<i>Бот автоматически улучшит промпт!</i>",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )
    await call.answer()


@router.message(ImageStates.waiting_prompt)
async def handle_image_prompt(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("📝 Опиши изображение текстом.", reply_markup=cancel_kb())
        return

    data = await state.get_data()
    model_key = data.get("model", "flux_schnell")
    model_label = data.get("model_label", "FLUX")
    width = data.get("width", 1024)
    height = data.get("height", 1024)

    thinking_msg = await message.answer("🎨 Улучшаю промпт и генерирую...")

    try:
        enhanced_prompt = await _enhance_prompt(message.text)

        await safe_edit_text(
            thinking_msg,
            f"🎨 Генерирую с <b>{model_label}</b>...\n"
            f"<i>Промпт: {enhanced_prompt[:100]}...</i>",
            parse_mode="HTML",
        )

        image_bytes = await together_service.generate_image(
            prompt=enhanced_prompt,
            model_key=model_key,
            width=width,
            height=height,
        )

        save_last_image(message.from_user.id, image_bytes)
        add_generation(message.from_user.id, "image", message.text)

        photo = BufferedInputFile(image_bytes, filename="generated.jpg")
        await thinking_msg.delete()
        await message.answer_photo(
            photo,
            caption=f"✅ <b>{model_label}</b>\n📝 {message.text[:100]}",
            reply_markup=result_actions(has_image=True),
            parse_mode="HTML",
        )

    except Exception as exc:
        await safe_edit_text(
            thinking_msg,
            f"❌ Ошибка генерации: {format_error(exc)}",
            reply_markup=cancel_kb(),
        )


@router.callback_query(F.data == "action_regenerate", ImageStates.waiting_prompt)
async def cb_regenerate_image(call: CallbackQuery) -> None:
    await call.message.answer(
        "🔄 Опиши изображение заново — сгенерирую новый вариант",
        reply_markup=cancel_kb(),
    )
    await call.answer()


async def _enhance_prompt(original: str) -> str:
    try:
        response = await chat_completion(
            messages=[{"role": "user", "content": IMAGE_ENHANCE_PROMPT.format(prompt=original)}],
            model_key="llama",
            max_tokens=300,
            temperature=0.8,
        )
        return response.strip()
    except Exception:
        return original
