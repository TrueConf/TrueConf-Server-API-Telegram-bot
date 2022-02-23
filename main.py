from typing import List
import requests
import json
from requests.exceptions import HTTPError
import urllib.request as req
import shelve
import threading
import datetime
import telegram

from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext #upm package(python-telegram-bot)
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, TelegramError, Update #upm package(python-telegram-bot)

STRINGS = {
    "access_denied": "Только владелец может общаться со своим ботом.",
    "error_oauth2": "⚠️ На сервере {} некорректно настроено <b> OAuth2 </b> приложение.",
    "found_forgotten_conf": "🔍 На сервере {} найдены следующие возможно забытые конференции:\n",
    "description_conf": '\n<b>ID:</b> <a href="{5}/c/{0}">{0}</a>\n'
    '<b>Название: </b>{2}\n'
    '<b>Владелец: </b>{3}\n'
    '<b>Количество участников: </b>{1}\n'
    '<b>Продолжительность: </b>{4}\n'
    '<a href="{5}/tools/real-time/{6}?a=cookies">'
    'Расширенное управление конференцией</a>\n',
    "stop_conf": "\nЧтобы завершить конференцию, <u>нажмите на её ID</u> ниже👇",
    "no_forgotten_conf": "👍 На сервере {} нет забытых конференций длительностью более <b>1 часа</b>.",
    "time_forgotten_conf": "🕐 Укажите длительность (в часах) кандидатов забытых конференций для поиска",
    "one_status_on": "Работает 🟢",
    "one_status_off": "Остановлен 🔴",
    "status_on": "<b>Статус</b> {}:  Работает 🟢",
    "status_off": "<b>Статус</b> {}: Остановлен 🔴",
    "online_user": "👥 На сервере {} находится <b>{} онлайн</b> пользователей.",
    "no_online_user": "🤷‍♂️ На сервере {} нет онлайн пользователей.",
    "back": "🔙 Назад",
    "stop_check_status": "❌ Деактивировать постоянную проверку",
    "started_check_status": '<b>Сервер</b> {}: {}\n\n✔ Постоянная проверка статуса <b>Включена</b>.\n\n'
    '<b>Tаймаут:</b> {} секунд\n\n'
    '<i>Когда статус сервера изменится вы получите соответствующее сообщение</i>',
    "start_check_status": "🔄 Активировать постоянную проверку",
    "stoped_check_status": '<b>Сервер</b> {}: {}\n\nПостоянная проверка статуса <b>Отключена</b>.',
    "run_conf": "📞 На сервере {} запущены следующие конференции:\n",
    "no_run_conf": "🤷‍♂️ На сервере {} нет запущеных конференций.",
    "select_server": "🌍 Выберите сервер:",
    "server_status": "🔄 Статус сервера",
    "show_run_conf": "⏳ Показать запущенные конференции",
    "online_user_count": "👤 Количество online пользователей",
    "find_forgotten_conf": "🔍 Найти забытые конференции",
    "server_selected": 'Выбран сервер {}. Что нужно сделать?',
    "confirm_stop": "🛑 Да, остановить",
    "confirm_stop_message": "❗Вы действительно хотите остановить конференцию <b>{}</b>?",
    "connection_error": "❌ <b>Подключение к серверу {} не установлено!</b>\nПроверьте вашу сеть и доступность к вашему серверу."
}


def auth_user(update: Update):
    if update.message.from_user.id in TG_USERS_ID:
        return True
    if update.effective_user.id in TG_USERS_ID:
        return True
    update.message.reply_text(STRINGS["access_denied"])
    return False


def get_access_token(server) -> None:
    try:
        response = requests.request(
            "POST",
            url="https://{}/oauth2/v1/token".format(server['ip']),
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data='grant_type=client_credentials&client_id={0}&client_secret={1}'.format(
                server['client_id'], server['client_secret']),
            verify=False)
        if response.status_code != 200:
            raise HTTPError
        server['access_token'] = json.loads(response.text)['access_token']
        SETTINGS["servers"][server['ip']
                            ]['access_token'] = server['access_token']
        with open("settings.json", "w") as read_file:
            json.dump(SETTINGS, read_file) # for local file
        # os.environ['settings'] = json.dumps(SETTINGS) # for Replit
        return True
    except HTTPError:
        if json.loads(response.text)['reason'] == 'InvalidCredentials':
            return False


def get_participants_list(server, session_id):
    try:
        response = requests.get("https://{0}/api/v3.3/conference-sessions/{1}/participants?access_token={2}".format(server['ip'], session_id, server['access_token']), verify=False,timeout=5)
        response.raise_for_status()
        count = json.loads(response.text)['count']
        participants = json.loads(response.text)['participants']
        if len(participants) == 1 and participants[0]['role'] == 2:
            return True, count
        else:
            for i in participants:
                if i['role'] == 2:
                    return False, count
        return True, count
    except HTTPError:
        return False, 0



def get_forgotten_conference(server) -> List:
    try:
        response = requests.get("https://{0}/api/v3.3/logs/calls?access_token={1}&sort_field=end_time&sort_order=1&page_size=500".format(server['ip'], server['access_token']), verify=False, timeout=5)
        response.raise_for_status()  # проверка статуса ответа
        forgotten_list = []
        for i in json.loads(response.text)['list']:
            if i['end_time'] is None and i['class'] > 1 and i['duration']/3600 >= 1:
                flag, participant_count = get_participants_list(
                    server, req.pathname2url(i['conference_id']))
                if flag:
                    forgotten_list.append(
                        {'conf_id': req.pathname2url(i['conference_id']), 'named_id': i['named_conf_id'], 'participant_count': participant_count, 'topic': i['topic'], 'owner': i['owner'], 'duration': str(datetime.timedelta(seconds=i['duration']))})
        return forgotten_list
    except requests.exceptions.HTTPError:
        if response.status_code == 403:
            if json.loads(response.text)['error']['errors'][0]['reason'] == 'accessTokenInvalid':
                if get_access_token(server):
                    return get_forgotten_conference(server)
                else:
                    return None
        if response.status_code == 404:
            return "ConnectionError"
    except requests.exceptions.ConnectTimeout:
        return "ConnectionError"
        


def get_result_forgotten(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    update.message = query.message
    server = str(query.data).split('|')[1]

    keyboard_back = [[InlineKeyboardButton(STRINGS['back'],
                                           callback_data='service_select_button|{}'.format(server))]]
    forgotten_list = get_forgotten_conference(SERVERS[server])
    if forgotten_list is None:
        update.message.edit_text(STRINGS['error_oauth2']
                                 .format(server), reply_markup=InlineKeyboardMarkup(keyboard_back), parse_mode="HTML")
    elif forgotten_list == "ConnectionError":
        query.message.edit_text(STRINGS['connection_error'].format(
            server), reply_markup=InlineKeyboardMarkup(keyboard_back), parse_mode="HTML")
    elif forgotten_list:
        keyboard_stop = []
        keyboard_stop.append([])
        j = 0
        k = 0
        h = STRINGS['found_forgotten_conf'].format(
            server)
        for i in forgotten_list:
            h += STRINGS['description_conf'].format(i['named_id'],
                                                    i['participant_count'],
                                                    i['topic'],
                                                    i['owner'],
                                                    i['duration'],
                                                    SERVERS[server]["ip"],
                                                    i['conf_id'])
            if k == 2:
                j += 1
                keyboard_stop.append([])
                k = 0
            keyboard_stop[j].append(InlineKeyboardButton(
                "{}".format(i['named_id']), callback_data='stop_conference_button|{}|0|{}'.format(server, i['named_id'])))
            k += 1
        h += STRINGS['stop_conf']
        keyboard_stop.append([InlineKeyboardButton(STRINGS['back'],
                                                   callback_data='service_select_button|{}'.format(server))])
        update.message.edit_text(
            h, reply_markup=InlineKeyboardMarkup(keyboard_stop), parse_mode="HTML", disable_web_page_preview=True)
    else:
        update.message.edit_text(
            STRINGS['no_forgotten_conf'].format(server), reply_markup=InlineKeyboardMarkup(keyboard_back), parse_mode="HTML")


def get_conference_running(server) -> List:
    try:
        response = requests.get("https://{0}/api/v3.3/logs/calls?access_token={1}&sort_field=end_time&sort_order=1&page_size=200".format(server['ip'], server['access_token']), verify=False,timeout=5)
        response.raise_for_status()  # проверка статуса ответа
        run_list = []
        for i in json.loads(response.text)['list']:
            if i['end_time'] is None and i['class'] > 1:
                if i['topic'] == None:
                    topic = "Без названия"
                else:
                    topic = i['topic']
                run_list.append(
                    {'conf_id': req.pathname2url(i['conference_id']), 'named_id': i['named_conf_id'], 'participant_count': i['participant_count'], 'topic': topic, 'owner': i['owner'], 'duration': str(datetime.timedelta(seconds=i['duration']))})
        return run_list
    except requests.exceptions.HTTPError:
        if response.status_code == 403:
            if json.loads(response.text)['error']['errors'][0]['reason'] == 'accessTokenInvalid':
                if get_access_token(server):
                    return get_conference_running(server)
                else:
                    return None
        if response.status_code == 404:
            return "ConnectionError"
    except requests.exceptions.ConnectTimeout:
        return "ConnectionError"


def stop_conference_button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    update.message = query.message
    data = query.data.split('|')
    server = data[1]
    conf_id = data[3]
    keyboard = [[InlineKeyboardButton(STRINGS['confirm_stop'],
                                      callback_data='stop_conference|{}|{}|{}'.format(server, data[2], conf_id))], [InlineKeyboardButton(STRINGS['back'],
                                                                                                                                         callback_data='active_calls_button|{}'.format(server))]]
    update.message.edit_text(STRINGS['confirm_stop_message'].format(conf_id),
                             reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


def stop_conference(update: Update, context: CallbackContext):
    q = update.callback_query.data.split("|")
    server = SERVERS[q[1]]
    conf_id = q[3]
    flag = q[2]
    try:
        response = requests.post("https://{}/api/v3.3/conferences/{}/stop?access_token={}".format(
                server['ip'], conf_id, server['access_token']), verify=False)
        print(response.text)
        if response.status_code != 200:
            raise HTTPError
        if flag == '0':
            get_result_forgotten(update, context)
        else:
            get_conference_button(update, context)      
    except requests.exceptions.HTTPError:
        if json.loads(response.text)['reason'] == 'InvalidCredentials':
            return False
        if response.status_code == 404:
            return False
    except requests.exceptions.ConnectTimeout:
        return False

def one_check_status(server):
    try:
        response = requests.get("http://{}:4307/vsstatus".format(server),timeout=5)
        response.raise_for_status()
        if response.status_code == requests.codes.ok:
            return STRINGS['one_status_on']
    except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
        return STRINGS['one_status_off']

def check_status(server, state):    
    if state:
        bot = Bot(TG_API_TOKEN)
        global STATUS
        status_th = threading.Timer(
            server['server_status']['timeout'], check_status, args=[server, state])
        try:
            response = requests.get("http://{}:4307/vsstatus".format(server['ip']), timeout=5)
            response.raise_for_status()
            if server['ip'] not in STATUS.keys():
                STATUS[server['ip']] = 1
                status_th.start()
            elif STATUS[server['ip']] == 0:
                STATUS[server['ip']] = 1
                for id in TG_USERS_ID:
                    try:
                        bot.send_message(
                            chat_id=id, text=STRINGS['status_on'].format(
                                server['ip']), parse_mode="html")
                    except TelegramError:
                        continue
                status_th.start()
            else:
                status_th.start()
        except (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout):
            if server['ip'] not in STATUS.keys():
                STATUS[server['ip']] = 0
                status_th.start()
            elif STATUS[server['ip']] == 1:
                STATUS[server['ip']] = 0
                for id in TG_USERS_ID:
                    try:
                        bot.send_message(
                            chat_id=id, text=STRINGS['status_off'].format(
                        server['ip']),parse_mode= "html")
                    except TelegramError:
                        continue
                status_th.start()
            else:
                status_th.start()


def check_status_button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    update.message = query.message
    server = SERVERS[str(query.data).split('|')[1]]
    if server['server_status']['state'] == False:
        server['server_status']['state'] = True
        
        check_status(server, 1)
    else:
        server['server_status']['state'] = False
        check_status(server, 0)
    SETTINGS['servers'][str(query.data).split('|')[1]] = server
    with open("settings.json", "w") as read_file:
        json.dump(SETTINGS, read_file)  # for local file
    # os.environ['settings'] = json.dumps(SETTINGS) # for Replit
    server_status(update, context, server)

def get_online_users(server) -> List:
    online_count = 0
    try:
        response = requests.get("https://{0}/api/v3.3/users?access_token={1}".format(server['ip'], server['access_token']), verify=False,timeout=5)
        response.raise_for_status()  # проверка статуса ответа
        for i in json.loads(response.text)['users']:
            if i['status'] in (1, 2, 5):
                online_count += 1
        return online_count
    except requests.exceptions.HTTPError:
        if response.status_code == 403:
            if json.loads(response.text)['error']['errors'][0]['reason'] == 'accessTokenInvalid':
                if get_access_token(server):
                    return get_online_users(server)
                else:
                    return None
        if response.status_code == 404:
            return "ConnectionError"
    except requests.exceptions.ConnectTimeout:
        return "ConnectionError"


def online_users_button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    update.message = query.message
    server = str(query.data).split('|')[1]
    online_list = get_online_users(SERVERS[server])
    keyboard = [
        [InlineKeyboardButton(STRINGS['back'],
                              callback_data='service_select_button|{}'.format(server))]]
    if online_list is None:
        query.message.edit_text(
            STRINGS['error_oauth2'].format(server), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    elif online_list == "ConnectionError":
        query.message.edit_text(STRINGS['connection_error'].format(
            server), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    elif not online_list:
        query.message.edit_text(STRINGS['online_user'].format(
            server, online_list), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        
    else:
        query.message.edit_text(
            STRINGS['no_online_user'].format(server), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        # если список пустой то конференций нет...


def server_status(update: Update, context: CallbackContext, server=None) -> None:
    query = update.callback_query
    query.answer()
    server = str(query.data).split('|')[1]
    if SERVERS[server]['server_status']['state']:
        keyboard = [
            [InlineKeyboardButton(STRINGS['stop_check_status'],
                                  callback_data='check_status_button|{}'.format(server))],
            [InlineKeyboardButton(STRINGS['back'],
                                  callback_data='service_select_button|{}'.format(server))]

        ]
        query.message.edit_text(STRINGS['started_check_status'].format(server, one_check_status(server),
                                                                       SERVERS[server]['server_status']['timeout']), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    else:
        keyboard = [
            [InlineKeyboardButton(STRINGS['start_check_status'],
                                  callback_data='check_status_button|{}'.format(server))],
            [InlineKeyboardButton(STRINGS['back'],
                                  callback_data='service_select_button|{}'.format(server))]

        ]
        query.message.edit_text(STRINGS['stoped_check_status'].format(server, one_check_status(server)),
                                reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


def get_conference_button(update: Update, context: CallbackContext, server=None) -> None:
    query = update.callback_query
    query.answer()
    update.message = query.message
    server = str(query.data).split('|')[1]
    run_list = get_conference_running(SERVERS[server])
    keyboard = [
        [InlineKeyboardButton(STRINGS['back'],
                              callback_data='service_select_button|{}'.format(server))]]
    if run_list is None:
        update.message.edit_text(STRINGS['error_oauth2'].format(
            server), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    elif run_list == "ConnectionError":
        query.message.edit_text(STRINGS['connection_error'].format(
            server), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    elif run_list:
        keyboard_stop = []
        keyboard_stop.append([])
        j = 0
        k = 0
        h = STRINGS['run_conf'].format(server)
        for i in run_list:
            h += STRINGS['description_conf'].format(i['named_id'],
                                                    i['participant_count'],
                                                    i['topic'],
                                                    i['owner'],
                                                    i['duration'],
                                                    SERVERS[server]["ip"],
                                                    i['conf_id'])
            if k == 2:
                j += 1
                keyboard_stop.append([])
                k = 0
            keyboard_stop[j].append(InlineKeyboardButton(
                "{}".format(i['named_id']), callback_data='stop_conference_button|{}|1|{}'.format(server, i['named_id'])))
            k += 1
        h += STRINGS['stop_conf']
        keyboard_stop.append([InlineKeyboardButton(STRINGS['back'],
                                                   callback_data='service_select_button|{}'.format(server))])
        update.message.edit_text(
            h, reply_markup=InlineKeyboardMarkup(keyboard_stop), parse_mode="HTML", disable_web_page_preview=True)
    else:
        h = STRINGS['no_run_conf'].format(server)
        update.message.edit_text(
            h, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


def ssb_keyboard_generator(data):
    keyboard = []
    keyboard.append([])
    i = 0
    k = 0
    for server in data.keys():
        if k == 2:
            i += 1
            keyboard.append([])
            k = 0
        keyboard[i].append(InlineKeyboardButton(
            server, callback_data='service_select_button|{}'.format(server)))
        k += 1
    return keyboard


def start_command(update: Update, context: CallbackContext) -> None:
    if not auth_user(update):
        return
    update.message.reply_text(STRINGS['select_server'],
                              reply_markup=InlineKeyboardMarkup(ssb_keyboard_generator(SERVERS)))


def server_select_button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    query.message.edit_text(STRINGS['select_server'],
                            reply_markup=InlineKeyboardMarkup(ssb_keyboard_generator(SERVERS)))

def service_select_button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    server = str(query.data).split('|')[1]
    keyboard = [
        [InlineKeyboardButton(STRINGS['server_status'],
                              callback_data='server_status|{}'.format(server))],
        [InlineKeyboardButton(STRINGS['show_run_conf'],
                              callback_data='get_conference_button|{}'.format(server))],
        [InlineKeyboardButton(STRINGS['online_user_count'],
                              callback_data='online_users_button|{}'.format(server))],
        [InlineKeyboardButton(STRINGS['find_forgotten_conf'],
                              callback_data='get_result_forgotten|{}'.format(server))],
        [InlineKeyboardButton(STRINGS['back'],
                              callback_data='server_select_button|{}'.format(server))]

    ]
    if query.answer() == 'active_calls_button':
        query.message.reply_text(STRINGS['server_selected'].format(
            server), reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.answer() == 'server_status' or 'server_select_button':
        query.message.edit_text(STRINGS['server_selected'].format(
            server), reply_markup=InlineKeyboardMarkup(keyboard))


def main():
    updater = Updater(TG_API_TOKEN, use_context=True)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start_command))
    dispatcher.add_handler(CallbackQueryHandler(
        service_select_button, pattern='^service_select_button'))
    dispatcher.add_handler(CallbackQueryHandler(
        get_conference_button, pattern='^get_conference_button'))
    dispatcher.add_handler(CallbackQueryHandler(
        server_status, pattern='^server_status'))
    dispatcher.add_handler(CallbackQueryHandler(
        one_check_status, pattern='^one_check_status'))
    dispatcher.add_handler(CallbackQueryHandler(
        server_select_button, pattern='^server_select_button'))
    dispatcher.add_handler(CallbackQueryHandler(
        check_status_button, pattern='^check_status_button'))
    dispatcher.add_handler(CallbackQueryHandler(
        online_users_button, pattern='^online_users_button'))
    dispatcher.add_handler(CallbackQueryHandler(
        get_result_forgotten, pattern='^get_result_forgotten'))
    dispatcher.add_handler(CallbackQueryHandler(
        stop_conference_button, pattern='^stop_conference_button'))
    dispatcher.add_handler(CallbackQueryHandler(
        stop_conference, pattern='^stop_conference'))

    updater.start_polling()
    for server in SETTINGS['servers'].values():
        check_status(server, server['server_status']['state'])
    print('Bot is running...')

if __name__ == '__main__':
    with open("settings.json", "r") as read_file:
        SETTINGS = json.load(read_file)
    # SETTINGS = json.loads(os.environ['settings']) # for Replit
    TG_API_TOKEN = SETTINGS['tg-api-token']
    TG_USERS_ID = SETTINGS['tg-users-id']
    SERVERS = SETTINGS['servers']
    STATUS = {}
    main()
