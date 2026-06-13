from aiogram import Router, F
from aiogram.types import CallbackQuery

from keyboards.main import back_to_main, history_kb
from utils.storage import clear_history, get_history
from utils.texts import TYPE_EMOJI

router = Router()


@router.callback_query(F.data == "menu_history")
async def cb_history(call: CallbackQuery) -> None:
    history = get_history(call.from_user.id)

    if not history:
        await call.message.edit_text(
            "📜 <b>История</b>\n\nПока пусто — начни генерировать!",
            reply_markup=back_to_main(),
            parse_mode="HTML",
        )
        await call.answer()
        return

    lines = ["📜 <b>История генераций</b>\n"]
    for item in reversed(history[-15:]):
        emoji = TYPE_EMOJI.get(item["type"], "🔮")
        prompt = item["prompt"]
        preview = prompt[:60] + "..." if len(prompt) > 60 else prompt
        lines.append(f"{emoji} <code>{item['time']}</code> — {preview}")

    text = "\n".join(lines)
    if len(text) > 3500:
        text = text[:3500] + "\n\n<i>...показаны последние записи</i>"

    await call.message.edit_text(text, reply_markup=history_kb(), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "history_clear")
async def cb_clear_history(call: CallbackQuery) -> None:
    clear_history(call.from_user.id)
    await call.message.edit_text(
        "🗑 <b>История очищена</b>",
        reply_markup=back_to_main(),
        parse_mode="HTML",
    )
    await call.answer("История удалена")
