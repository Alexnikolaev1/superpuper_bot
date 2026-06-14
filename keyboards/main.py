from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✍️ AI Текст", callback_data="menu_text"),
            InlineKeyboardButton(text="🖼 Изображение", callback_data="menu_image"),
        ],
        [
            InlineKeyboardButton(text="🎬 Видео", callback_data="menu_video"),
            InlineKeyboardButton(text="📱 Контент", callback_data="menu_content"),
        ],
        [
            InlineKeyboardButton(text="📜 История", callback_data="menu_history"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu_settings"),
        ],
    ])


def text_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🧠 DeepSeek V4 Pro", callback_data="text_deepseek"),
            InlineKeyboardButton(text="⚡ Llama 3.3 70B", callback_data="text_llama"),
        ],
        [InlineKeyboardButton(text="🆓 OpenRouter Free", callback_data="text_openrouter")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main")],
    ])


def image_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎨 FLUX Schnell", callback_data="img_flux_schnell"),
            InlineKeyboardButton(text="✨ FLUX Dev", callback_data="img_flux_dev"),
        ],
        [InlineKeyboardButton(text="🖌 SDXL", callback_data="img_sdxl")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main")],
    ])


def image_ratio_menu(model: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1:1", callback_data=f"ratio_{model}_1024x1024"),
            InlineKeyboardButton(text="9:16", callback_data=f"ratio_{model}_576x1024"),
        ],
        [
            InlineKeyboardButton(text="16:9", callback_data=f"ratio_{model}_1024x576"),
            InlineKeyboardButton(text="4:5", callback_data=f"ratio_{model}_832x1024"),
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_image")],
    ])


def video_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎬 Текст → Видео", callback_data="video_t2v"),
            InlineKeyboardButton(text="🖼→🎬 Фото → Видео", callback_data="video_i2v"),
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main")],
    ])


def content_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📸 Instagram", callback_data="content_instagram"),
            InlineKeyboardButton(text="✈️ Telegram", callback_data="content_telegram"),
        ],
        [
            InlineKeyboardButton(text="🐦 Twitter/X", callback_data="content_twitter"),
            InlineKeyboardButton(text="💼 LinkedIn", callback_data="content_linkedin"),
        ],
        [
            InlineKeyboardButton(text="🎯 Реклама", callback_data="content_ad"),
            InlineKeyboardButton(text="📝 SEO", callback_data="content_seo"),
        ],
        [InlineKeyboardButton(text="💡 10 идей", callback_data="content_ideas")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main")],
    ])


def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="menu_main")],
    ])


def back_to_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu_main")],
    ])


def history_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Очистить историю", callback_data="history_clear")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu_main")],
    ])


def result_actions(has_image: bool = False, regenerate: bool = True) -> InlineKeyboardMarkup:
    buttons = []
    if has_image:
        buttons.append([
            InlineKeyboardButton(text="🎬 Видео из этого", callback_data="action_img2video"),
        ])
    if regenerate:
        buttons.append([
            InlineKeyboardButton(text="🔄 Ещё вариант", callback_data="action_regenerate"),
            InlineKeyboardButton(text="🏠 Меню", callback_data="menu_main"),
        ])
    else:
        buttons.append([InlineKeyboardButton(text="🏠 Меню", callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
