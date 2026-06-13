from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from keyboards.main import back_to_main, main_menu
from utils.storage import clear_conversation, get_history_stats
from utils.texts import HELP_TEXT, TYPE_EMOJI, WELCOME_TEXT

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(WELCOME_TEXT, reply_markup=main_menu(), parse_mode="HTML")


@router.message(Command("new"))
async def cmd_new(message: Message) -> None:
    clear_conversation(message.from_user.id)
    await message.answer(
        "🔄 <b>Диалог очищен.</b> Начинаем с чистого листа!",
        reply_markup=main_menu(),
        parse_mode="HTML",
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, parse_mode="HTML", reply_markup=back_to_main())


@router.callback_query(F.data == "menu_main")
async def cb_main_menu(call: CallbackQuery) -> None:
    await call.message.edit_text(WELCOME_TEXT, reply_markup=main_menu(), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "menu_settings")
async def cb_settings(call: CallbackQuery) -> None:
    stats = get_history_stats(call.from_user.id)
    stats_lines = []
    for gen_type, count in sorted(stats.items(), key=lambda x: -x[1]):
        emoji = TYPE_EMOJI.get(gen_type, "🔮")
        stats_lines.append(f"  {emoji} {gen_type}: <b>{count}</b>")

    stats_block = "\n".join(stats_lines) if stats_lines else "  <i>Пока нет генераций</i>"

    text = f"""⚙️ <b>Настройки</b>

<b>Сервисы:</b>
✅ Together.ai — текст и изображения
✅ OpenRouter Free — резервные модели
✅ Hailuo — видеогенерация

<b>Твоя статистика:</b>
{stats_block}

<b>Команды:</b>
/new — сбросить контекст диалога
/help — справка"""

    await call.message.edit_text(text, parse_mode="HTML", reply_markup=back_to_main())
    await call.answer()
