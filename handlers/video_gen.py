import asyncio
import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from keyboards.main import back_to_main, cancel_kb, video_menu
from services import hailuo_service
from utils.helpers import format_error, safe_edit_text
from utils.storage import add_generation, get_last_image

logger = logging.getLogger(__name__)

router = Router()


class VideoStates(StatesGroup):
    waiting_t2v_prompt = State()
    waiting_i2v_photo = State()
    waiting_i2v_prompt = State()


@router.callback_query(F.data == "menu_video")
async def cb_video_menu(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text(
        "🎬 <b>Генерация видео</b> (Hailuo/MiniMax)\n\n"
        "⚠️ Видео может генерироваться до 30 минут — придёт отдельным сообщением.\n\n"
        "Выбери режим:",
        reply_markup=video_menu(),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data == "video_t2v")
async def cb_t2v(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(VideoStates.waiting_t2v_prompt)
    await call.message.edit_text(
        "🎬 <b>Текст → Видео</b>\n\n"
        "Опиши сцену подробно:\n"
        "• Что происходит\n"
        "• Стиль (кинематографический, анимация, реализм)\n"
        "• Движение камеры\n\n"
        "<i>Пример: Закат над горами, камера медленно движется вправо</i>",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data == "video_i2v")
async def cb_i2v(call: CallbackQuery, state: FSMContext) -> None:
    last_img = get_last_image(call.from_user.id)
    if last_img:
        await state.update_data(use_last_image=True)
        await state.set_state(VideoStates.waiting_i2v_prompt)
        await call.message.edit_text(
            "🖼→🎬 <b>Фото → Видео</b>\n\n"
            "Найдено последнее сгенерированное изображение ✅\n\n"
            "Опиши движение и действие:",
            reply_markup=cancel_kb(),
            parse_mode="HTML",
        )
    else:
        await state.set_state(VideoStates.waiting_i2v_photo)
        await call.message.edit_text(
            "🖼→🎬 <b>Фото → Видео</b>\n\n"
            "Отправь фотографию, которую хочешь оживить:",
            reply_markup=cancel_kb(),
            parse_mode="HTML",
        )
    await call.answer()


@router.callback_query(F.data == "action_img2video")
async def cb_img2video(call: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(use_last_image=True)
    await state.set_state(VideoStates.waiting_i2v_prompt)
    await call.message.answer(
        "🖼→🎬 Опиши движение:\n"
        "<i>Например: плавный zoom in, ветер, мерцание света</i>",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )
    await call.answer()


def _make_progress_updater(status_msg: Message):
    last_text = ""

    async def on_progress(_elapsed: int, status: str, text: str) -> None:
        nonlocal last_text
        display = f"{text}\n<i>Статус: {status or 'ожидание'}</i>"
        if display != last_text:
            last_text = display
            await safe_edit_text(status_msg, display, parse_mode="HTML")

    return on_progress


async def _run_video_job(
    message: Message,
    status_msg: Message,
    *,
    prompt: str,
    gen_type: str,
    photo_bytes: bytes | None = None,
) -> None:
    try:
        on_progress = _make_progress_updater(status_msg)
        if photo_bytes:
            video_url = await hailuo_service.image_to_video(photo_bytes, prompt, on_progress=on_progress)
        else:
            video_url = await hailuo_service.text_to_video(prompt, on_progress=on_progress)

        video_bytes = await hailuo_service.download_video(video_url)
        add_generation(message.from_user.id, gen_type, prompt)

        video_file = BufferedInputFile(video_bytes, filename="generated.mp4")
        caption = (
            f"✅ <b>Видео готово!</b>\n📝 {prompt[:100]}"
            if gen_type == "video_t2v"
            else "✅ <b>Видео готово!</b>"
        )
        await status_msg.delete()
        await message.answer_video(
            video_file,
            caption=caption,
            reply_markup=back_to_main(),
            parse_mode="HTML",
        )
    except Exception as exc:
        logger.exception("Video generation failed for user %s", message.from_user.id)
        await safe_edit_text(
            status_msg,
            f"❌ Ошибка: {format_error(exc)}\n\nПопробуй позже или с другим описанием.",
            reply_markup=cancel_kb(),
        )


@router.message(VideoStates.waiting_t2v_prompt)
async def handle_t2v(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("📝 Опиши сцену текстом.", reply_markup=cancel_kb())
        return

    await state.clear()
    status_msg = await message.answer(
        "🎬 <b>Задача создана!</b>\n"
        "Видео придёт отдельным сообщением.\n"
        "⏳ Обычно 5–30 минут (зависит от очереди MiniMax).",
        parse_mode="HTML",
    )
    asyncio.create_task(_run_video_job(
        message, status_msg, prompt=message.text, gen_type="video_t2v",
    ))


@router.message(VideoStates.waiting_i2v_photo, F.photo)
async def handle_i2v_photo(message: Message, state: FSMContext) -> None:
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    photo_bytes = await message.bot.download_file(file.file_path)
    photo_data = photo_bytes.read()

    await state.update_data(photo_bytes=photo_data, use_last_image=False)
    await state.set_state(VideoStates.waiting_i2v_prompt)

    await message.answer(
        "✅ Фото получено!\n\nТеперь опиши движение:",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )


@router.message(VideoStates.waiting_i2v_prompt)
async def handle_i2v_prompt(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("📝 Опиши движение текстом.", reply_markup=cancel_kb())
        return

    data = await state.get_data()
    photo_bytes = get_last_image(message.from_user.id) if data.get("use_last_image") else data.get("photo_bytes")

    if not photo_bytes:
        await message.answer("❌ Изображение не найдено. Попробуй снова.", reply_markup=cancel_kb())
        await state.clear()
        return

    await state.clear()
    status_msg = await message.answer(
        "🎬 <b>Задача создана!</b>\n"
        "Видео придёт отдельным сообщением.\n"
        "⏳ Обычно 5–30 минут.",
        parse_mode="HTML",
    )
    asyncio.create_task(_run_video_job(
        message, status_msg,
        prompt=message.text,
        gen_type="video_i2v",
        photo_bytes=photo_bytes,
    ))
