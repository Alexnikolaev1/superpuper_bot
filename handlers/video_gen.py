from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from keyboards.main import back_to_main, cancel_kb, video_menu
from services import hailuo_service
from utils.helpers import format_error, safe_edit_text
from utils.storage import add_generation, get_last_image

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
        "⚠️ Видео генерируется 3–10 минут — это нормально!\n\n"
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
        "<i>Пример: Закат над горами, камера медленно движется вправо, кинематографический стиль</i>",
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


async def _make_progress_updater(status_msg: Message):
    last_text = ""

    async def on_progress(_elapsed: int, text: str) -> None:
        nonlocal last_text
        if text != last_text:
            last_text = text
            await safe_edit_text(status_msg, f"{text}\n⏳ Ожидай 3–10 минут")

    return on_progress


@router.message(VideoStates.waiting_t2v_prompt)
async def handle_t2v(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("📝 Опиши сцену текстом.", reply_markup=cancel_kb())
        return

    thinking_msg = await message.answer("🎬 Отправляю задачу в Hailuo...\n⏳ Ожидай 3–10 минут")

    try:
        on_progress = await _make_progress_updater(thinking_msg)
        video_url = await hailuo_service.text_to_video(message.text, on_progress=on_progress)
        video_bytes = await hailuo_service.download_video(video_url)
        add_generation(message.from_user.id, "video_t2v", message.text)

        video_file = BufferedInputFile(video_bytes, filename="generated.mp4")
        await thinking_msg.delete()
        await message.answer_video(
            video_file,
            caption=f"✅ <b>Видео готово!</b>\n📝 {message.text[:100]}",
            reply_markup=back_to_main(),
            parse_mode="HTML",
        )
    except Exception as exc:
        await safe_edit_text(
            thinking_msg,
            f"❌ Ошибка: {format_error(exc)}\n\nПопробуй с другим описанием.",
            reply_markup=cancel_kb(),
        )
    finally:
        await state.clear()


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

    thinking_msg = await message.answer("🎬 Создаю видео из изображения...\n⏳ Подожди 3–10 минут")

    try:
        on_progress = await _make_progress_updater(thinking_msg)
        video_url = await hailuo_service.image_to_video(photo_bytes, message.text, on_progress=on_progress)
        video_bytes = await hailuo_service.download_video(video_url)
        add_generation(message.from_user.id, "video_i2v", message.text)

        video_file = BufferedInputFile(video_bytes, filename="generated.mp4")
        await thinking_msg.delete()
        await message.answer_video(
            video_file,
            caption="✅ <b>Видео готово!</b>",
            reply_markup=back_to_main(),
            parse_mode="HTML",
        )
    except Exception as exc:
        await safe_edit_text(
            thinking_msg,
            f"❌ Ошибка: {format_error(exc)}",
            reply_markup=cancel_kb(),
        )
    finally:
        await state.clear()
