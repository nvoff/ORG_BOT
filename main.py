import json
import asyncio
from typing import List, Union
from aiogram.types import InputMediaPhoto
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.handler import CancelHandler
from aiogram.dispatcher.middlewares import BaseMiddleware

bot = Bot(
    token=(''),
    timeout=1000
)
dp = Dispatcher(bot, no_throttle_error=True)

statuses = {}


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await bot.send_message(
        chat_id=message.chat.id,
        text='Добро пожаловать в *ORG Бота*!\n\nС его помощью вы можете отправить заявку сотрудникам организационно-технического отдела',
        #        parse_mode=types.ParseMode.MARKDOWN
    )


@dp.message_handler(content_types=types.ContentType.ANY)
async def message(message: types.Message, album: List[types.Message]=[]):
    admin_group = -

    if message.chat.id != admin_group:

        await bot.send_message(
            chat_id=message.chat.id,
            text='Ваш запрос был отправлен специалистам, ожидайте ответа!',
            #            parse_mode=types.ParseMode.MARKDOWN
        )

        if str(message.chat.id) not in statuses or statuses.get(str(message.chat.id)) != 'inprogress':
            username = message.from_user.username or ""
            first_name = message.from_user.first_name or ""
            last_name = message.from_user.last_name or ""

            chat_id = admin_group

            user_text = message.caption if message.caption else message.text
            text = f'Request: \n\n{user_text}\n\nSender: \n— ID: {message.from_user.id}\n— Telegram: @{username}\n— Name: {first_name} {last_name}'
            reply_markup = types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton(text='В работе', callback_data='adm_act_inprogress_' + str(message.chat.id))
            ).add(
                types.InlineKeyboardButton(text='Решено', callback_data='adm_act_solve_' + str(message.chat.id)),
                types.InlineKeyboardButton(text='Отклонить', callback_data='adm_act_reject_' + str(message.chat.id))
            )

            if message.photo:
                media = ([InputMediaPhoto(media=(album[0].photo[0].file_id if len(album) else message.photo[0].file_id),
                                          caption=text)] +
                         list(map(lambda a: InputMediaPhoto(media=a.photo[0].file_id), album[1:])))
                await bot.send_media_group(chat_id=chat_id,
                                           media=media)
            else:
                await bot.send_message(chat_id=chat_id, text=text)

            await bot.send_message(chat_id=chat_id, text='Choose an action:', reply_markup=reply_markup)

        else:
            await bot.forward_message(
                chat_id=admin_group,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
    else:
        reply = message.reply_to_message

        if reply is not None:
            if reply.from_user.is_bot:

                if reply.reply_markup is not None:
                    markup = reply.reply_markup['inline_keyboard']
                    uid = markup[0][0]['callback_data'].split('_')[3]
                    await bot.send_message(
                        chat_id=int(uid),
                        text="Вопрос от специалиста:\n\n_" + message.text + "_",
                        #                       parse_mode=types.ParseMode.MARKDOWN
                    )


@dp.callback_query_handler(lambda c: c.data.startswith('adm_act_'))
async def inprogress(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    command = callback_query.data.replace('adm_act_', '').split('_')

    uid = int(command[1])

    if command[0] == 'inprogress':
        statuses[str(uid)] = 'inprogress'
        await bot.send_message(
            chat_id=uid,
            text='Ваш запрос в работе!',
            #            parse_mode=types.ParseMode.MARKDOWN
        )
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            #            parse_mode=types.ParseMode.MARKDOWN,
            text=callback_query.message.text.replace('\n\nВыберите действие',
                                                     '') + '\n\nИстория действий\n\nℹ️ Запрос в работе!',
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton(text='Решено', callback_data='adm_act_solve_' + str(uid)),
                types.InlineKeyboardButton(text='Отклонить', callback_data='adm_act_reject_' + str(uid))
            )
        )
    elif command[0] == 'solve':
        try:
            del statuses[str(uid)]
        except:
            pass
        await bot.send_message(
            chat_id=uid,
            text='Ваш запрос решен!',
            #            parse_mode=types.ParseMode.MARKDOWN
        )
        text_ = callback_query.message.text
        if "Выберите действие" in text_:
            text_ = text_.replace('Выберите действие', 'История действий')
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text=text_ + '\n✅ Запрос решен!',
            reply_markup=None,
            #            parse_mode=types.ParseMode.MARKDOWN
        )
    elif command[0] == 'reject':
        try:
            del statuses[str(uid)]
        except:
            pass
        await bot.send_message(
            chat_id=uid,
            text='Ваш запрос отклонен!',
            #            parse_mode=types.ParseMode.MARKDOWN
        )
        text_ = callback_query.message.text
        if "Выберите действие" in text_:
            text_ = text_.replace('Выберите действие', 'История действий\n\n')
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text=text_ + '\n❌ Отклонён!',
            reply_markup=None,
            #            parse_mode=types.ParseMode.MARKDOWN
        )


class AlbumMiddleware(BaseMiddleware):
    """This middleware is for capturing media groups."""

    album_data: dict = {}

    def __init__(self, latency: Union[int, float] = 0.01):
        """
        You can provide custom latency to make sure
        albums are handled properly in highload.
        """
        self.latency = latency
        super().__init__()

    async def on_process_message(self, message: types.Message, data: dict):
        if not message.media_group_id:
            return

        try:
            self.album_data[message.media_group_id].append(message)
            raise CancelHandler()  # Tell aiogram to cancel handler for this group element
        except KeyError:
            self.album_data[message.media_group_id] = [message]
            await asyncio.sleep(self.latency)

            message.conf["is_last"] = True
            data["album"] = self.album_data[message.media_group_id]

    async def on_post_process_message(self, message: types.Message, result: dict, data: dict):
        """Clean up after handling our album."""
        if message.media_group_id and message.conf.get("is_last"):
            del self.album_data[message.media_group_id]


dp.middleware.setup(AlbumMiddleware())
executor.start_polling(dp, skip_updates=True, timeout=1000)
