WELCOME_TEXT = """🚀 <b>ContentBot Pro</b> — AI-комбайн для контента

<b>Возможности:</b>
✍️ <b>AI Текст</b> — DeepSeek V3, Llama 3.3, бесплатные модели
🖼 <b>Изображения</b> — FLUX.1, SDXL в любом соотношении
🎬 <b>Видео</b> — Hailuo: текст→видео и фото→видео
📱 <b>Контент</b> — посты для Instagram, Telegram, X, LinkedIn

<b>Стек:</b> Together.ai · OpenRouter Free · Hailuo/MiniMax

Выбирай режим 👇"""

HELP_TEXT = """<b>📖 Как пользоваться</b>

<b>Текст:</b> модель → запрос (контекст сохраняется)
<b>Изображение:</b> модель → формат → описание
<b>Видео:</b> текст→видео или фото→видео (1–3 мин)
<b>Контент:</b> платформа → тема

<b>Команды:</b>
/start — главное меню
/new — сбросить диалог
/help — справка

<b>💡 Советы:</b>
• Промпты для картинок — лучше на английском
• Бот автоматически улучшает промпты
• Видео генерируется 1–3 минуты — это нормально"""

ACCESS_DENIED = "⛔ Доступ ограничен. Обратись к администратору."

TYPE_EMOJI = {
    "text": "✍️",
    "image": "🖼",
    "video_t2v": "🎬",
    "video_i2v": "🖼→🎬",
    "content_instagram": "📸",
    "content_telegram": "✈️",
    "content_twitter": "🐦",
    "content_linkedin": "💼",
    "content_ad": "🎯",
    "content_seo": "📝",
    "content_ideas": "💡",
}

RATIO_LABELS = {
    "1024x1024": "1:1 Квадрат",
    "576x1024": "9:16 Stories",
    "1024x576": "16:9 YouTube",
    "819x1024": "4:5 Instagram",
}
