# TrueConf-Server-API-Telegram-bot

Администратор [TrueConf Server](https://trueconf.ru/products/tcsf/besplatniy-server-videoconferenciy.html) может получать быстрый доступ к важной информации сервера, используя для этого популярные мессенджеры, например, Telegram. Для этого можно создать бота, который с помощью [TrueConf Server API](https://developers.trueconf.ru/api/server/) будет получать необходимые данные. Разместить бота можно как на своём сервере локально, так и на специализированном сервисе для онлайн-разработки.

В данном примере мы покажем, как создать Telegram бота, и запустить его на онлайн-сервисе Replit, при этом мы предоставляем готовый пример кода реализации задачи на Python. Предлагаемый бот обладает следующими возможностями:

1. Проверка статуса сервера (работает/остановлен).
1. Получение списка запущенных конференций.
1. Проверка количества онлайн пользователей.
1. Поиск ошибочно активных длительное время конференций и остановка любой из них.

Далее по тексту ошибочно запущенные конференции для краткости названы "забытыми", то есть их забыли остановить владелец и ведущие. Например, проводился вебинар, гости покинули его, а ведущий свернул клиентское приложение, не остановив мероприятие. Оно продолжает идти, а если была включена запись – то и зря занимать место на SSD или HDD разрастающимся файлом записи.

Для примера “забытой” мы считаем такую конференцию:

- она длится дольше одного часа;
- в ней остался один только владелец или ведущий;
- в ней есть участники, но среди них нет ни одного ведущего.

<div align="center"><img style="border: 1px solid #D1CCCC;" src="https://trueconf.ru/blog/wp-content/uploads/2022/02/2022-01-28_011132.png" height="450"/></div>

## Необходимые условия для запуска

Для успешного запуска бота требуется выполнение двух условий:

- каждый контролируемый сервер должен быть доступен по своему IP-адресу или DNS-имени на ПК, где запускается бот;
- ПК с ботом должен иметь выход в интернет.

:warning: **Внимание!**

> Представленный код является ознакомительным примером. Безопасность бота обеспечивается на уровне протокола OAuth 2.0, сервиса Telegram путём заявленного на его стороне шифрования данных, а также на стороне настроек сети (правила доступа, брандмауэр и т.п.). Т.к. через интерфейс бота передаются только сигналы от кнопок виртуальной клавиатуры, то через него нельзя будет послать какие-либо несанкционированные команды или исполняемый код.

## Регистрация своего бота и его настройка

Для использования Telegram-бота вам понадобится официальный бот [BotFather](http://t.me/BotFather).

BotFather – это единственный бот, который управляет ботами в Telegram. Подробнее читайте в [официальной документации](https://core.telegram.org/bots).

Чтобы создать бота:

1. Откройте [BotFather](http://t.me/BotFather) и нажмите **Запустить** или **Старт**.
1. У вас откроется список возможностей бота. Вам понадобится команда `/newbot`. Нажмите на неё в списке, или отправьте боту новое сообщение `/newbot`.

:information_source: **Примечание**

> В дальнейшем список доступных команд можно открыть с помощью кнопок `Меню`(мобильная версия), `/` (десктопная версия) или просто набрав `/` в поле ввода сообщения в чате с BotFather.

Далее BotFather предложит назвать нового бота. Придумайте название, например `TCS [name_org]`, где `[name_org]` — название вашей организации.

Теперь придумайте имя пользователя (username) для вашего бота.  В имени **обязательно** должно присутствовать слово `bot`, это требование Telegram, например, `tcs_[name_org]_bot`.

:warning: **Внимание!**

> Обратите внимание, что название бота и его имя пользователя – это публичные имена, по которым его можно найти через глобальный поиск.

В ответ вы получите сообщение со сведениями о созданном боте и токеном доступа к нему с помощью HTTP API в виде:

```text
5032177032:AAGahjzZ6zbWSEsVFj13Ki-YMPhPEPzQjxE
```

Нажмите на токен в тексте сообщения, чтобы скопировать его в буфер обмена. После чего сохраните его в надёжном месте – он понадобится вам в дальнейшем для использования бота.

Для того чтобы перейти в настройки вашего бота, выполните команду `/mybots` и выберите соответствующее имя пользователя. У вас откроется меню, в котором можно:

- аннулировать текущий токен, при этом новый токен создаётся автоматически;
- редактировать имя, приветственное сообщение, описание, изображение;
- добавить команды.

Теперь, когда бот настроен, можно перейти к его запуску.

## Подготовка файла SETTINGS

Предварительно вам понадобится подготовить файл настроек с данными для доступа к своему боту и параметрами серверов.

На вашей рабочей машине создайте файл в формате JSON, например, `settings.json`. Откройте в любом текстовом редакторе и вставьте в него этот текст:

```json
{
    "tg-api-token": "",
    "tg-users-id": [],
    "servers": {
        "server-name": {
            "ip": "",
            "client_id": "",
            "client_secret": "",
            "access_token": "",
            "server_status": {
                "state": 0,
                "timeout": 15
            },
            "ssl_certificate": ""
        }
    }
}
```

Теперь вам нужно правильно заполнить эту структуру данных.

**tg-api-token** — токен доступа HTTP API Telegram.

**tg-users-id** — ваш числовой Telegram ID. Telegram обеспечивает безопасность доступа к боту с помощью уникальных ID пользователей, поэтому чтобы вы могли получить ответ от бота, вам понадобится узнать свой Telegram ID. Чтобы получить его, пришлите боту [@userinfobot](http://t.me/userinfobot) любое сообщение.

:information_source: **Примечание**
> Если вы хотите, чтобы несколько человек получили доступ к боту, вы можете написать их ID через запятую.

**servers** — словарь, который содержит информацию о ваших серверах.
Замените `server-name` на ваше имя сервера, т.к. это имя будет отображаться в названии кнопок.

<div align="center"><img src="https://trueconf.ru/blog/wp-content/uploads/2022/02/2022-02-07_171650.png" height="110"/></div>

**ip** — IP-адрес сервера, или доменное имя.

**client_id**, **client_secret** будут доступны вам после создания OAuth2 приложения. О том, как его создать, читайте в [нашей документации](https://docs.trueconf.com/server/admin/web-config/#oauth2).

Для нашего примера вам понадобится отметить такие разрешения в OAuth приложении:

- conferences;
- users:read;
- logs.calls:read;
- logs.calls.participants:read.

<div align="center"><img style="border: 1px solid #D1CCCC;" src="https://trueconf.ru/blog/wp-content/uploads/2022/02/2022-03-05_130120.png" width="700" /></div>

**server_status** - словарь, содержащий в себе служебную информацию, которая используется в работе функции автоматической проверки статуса.

**timeout** — это время в секундах, через которое бот будет проверять статус сервера (Работает, Отключен). По умолчанию указано 15 секунд, но вы можете ввести своё значение.

**ssl_certificate** — если этот параметр `true` (чувствительно к регистру), то каждый запрос сервера будет проходить проверку SSL сертификата. Если ваш сервер использует самоподписанный сертификат, то в этом параметре в кавычках укажите путь к нему (используйте прямой слеш `/`). Если код используется на доверенной машине (например, находящейся в вашей корпоративной сети и доступ к ней только у вас), то напишите `false` – это отключит проверку сертификата. Если в кавычках не указан путь, то это также приравнивается к `false`.

После заполнения файла у вас должна получится структура как на примере ниже:

```json
{
    "tg-api-token": "5032177032:AAGahjzZ6zbWSEsVFj13Ki-YMPhPEPzQjxE",
    "tg-users-id": [123456789,123456789,123456789],
    "servers": {
        "192.168.0.1": {
            "ip": "192.168.0.1",
            "client_id": "e2633da5cfbc56f43f69c30f06727dfe4fa1a067",
            "client_secret": "b97fc03b30d8f3011dc13abd205ec9f5610861e0",
            "access_token": "2f7d2b5eeba33fcfbe7c2f419b0d2114dbe5dc27",
            "server_status": {
                "state": 0,
                "timeout": 15
            },
            "ssl_certificate": true
        },
        "server #2": {
            "ip": "192.168.0.2",
            "client_id": "e2633da5cfbc56f43f69c30f06727dfe4fa1a067",
            "client_secret": "b97fc03b30d8f3011dc13abd205ec9f5610861e0",
            "access_token": "2f7d2b5eeba33fcfbe7c2f419b0d2114dbe5dc27",
            "server_status": {
                "state": 0,
                "timeout": 15
            },
            "ssl_certificate": false
        },
        "Сервер 3": {
            "ip": "192.168.0.3",
            "client_id": "e2633da5cfbc56f43f69c30f06727dfe4fa1a067",
            "client_secret": "b97fc03b30d8f3011dc13abd205ec9f5610861e0",
            "access_token": "2f7d2b5eeba33fcfbe7c2f419b0d2114dbe5dc27",
            "server_status": {
                "state": 0,
                "timeout": 15
            },
            "ssl_certificate": "C:/certificates/ca.crt"
        }
    }
}
```

## Как запустить бота локально

Чтобы запустить бота на локальной машине, нужно установить Python, настроить виртуальное окружение и установить в него все недостающие зависимости (библиотеки).

Если вы используете операционную систему Windows, вам нужно установить Python. В ОС Linux Python установлен по умолчанию, в терминале выполните команду `python --version` чтобы проверить это.

### Установка Python на Windows

Перейдите на официальный сайт [python.org](http://python.org), в меню выберите пункт **Downloads** и под строкой **Download for Windows** нажмите кнопку **Python x.x.x**, где `x.x.x` — текущая релизная версия Python.

Откройте скачанный установочный файл, отметьте флажок **Add Python x.x to PATH** и нажмите **Install Now**.

## Загрузка репозитория

Чтобы скопировать репозиторий к себе на компьютер, откройте его страницу, нажмите кнопку **Code → Download ZIP**, и распакуйте загруженный архив.

### Запуск с использованием Poetry

Для запуска бота на локальной машине мы советуем вам использовать Poetry.

[Poetry](https://python-poetry.org/) — это инструмент для управления зависимостями в Python.

Для начала вам нужно установить Poetry, для этого откройте PowerShell и выполните команду:

```powershell
(Invoke-WebRequest -Uri <https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py> -UseBasicParsing).Content | python -
```

:information_source: **Примечание**
> Для корректной работы Poetry перезапустите PowerShell.

Теперь в PowerShell перейдите в папку с ранее распакованными файлами, и выполните команду `poetry install`. После установки необходимых зависимостей выполните команду `poetry run python main.py`.

При успешном запуске бота в терминале отобразится надпись **Bot is running…**

## Использование облачных сервисов

Прежде чем перейти к запуску бота в облачном сервисе, нужно клонировать наш репозиторий GitHub. Поэтому вам понадобится учетная запись на GitHub, чтобы создать аккаунт нажмите кнопку **Sing up** в правом верхнем углу.

Если у вас уже аккаунт, нажмите кнопку **Fork** на странице нашего репозитория. После этого у вас откроется скопированный репозиторий в вашем аккаунте.

### Replit

#### Регистрация

[Replit](https://replit.com/) — это веб-сервис, где можно писать и запускать код прямо в браузере, ничего не устанавливая к себе на компьютер.

Чтобы пользоваться сервисом вам понадобиться создать аккаунт. Для этого в правом верхнем углу нажмите на кнопку **Sing up**, введите логин, email и пароль или войдите с помощью популярного сервиса:

<div align="center"><img src="https://trueconf.ru/blog/wp-content/uploads/2022/02/2022-01-25_162636.png" width="550"/></div>

#### Импортирование проекта с GitHub

1. Нажмите кнопку Create.
1. В открывшимся окне нажмите Import from GitHub.
1. В выпадающем списке GitHub URL выберите нужный репозиторий.
1. Нажмите кнопку Import from Github.

Начнется процесс импорта репозитория:

<div align="center"><img src="https://trueconf.ru/blog/wp-content/uploads/2022/02/image1.png" width="900"/></div>

По завершении процесса, у вас откроется окно с данной инструкцией по использованию бота.

Далее в левом меню нажмите кнопку <img src="https://trueconf.ru/blog/wp-content/uploads/2022/02/2022-01-27_000440.png" width="25"/>, в поле **key** введите `settings`, в поле **value** вставьте содержимое [ранее подготовленного](#--settings) файла `settings.json` и нажмите кнопку **Add new secret**.

:warning: **Внимание!**

>Мы настоятельно не рекомендуем загружать в Replit ваши сертификаты, так как это небезопасно. Перед добавлением содержимого из settings.json, убедитесь что параметр `ssl_certificate` правильно отредактирован.

#### Редактирование файла main.py

Откройте файл main.py и в функции `def get_access_token` закомментируйте строки:

```python
with open("settings.json", "w") as read_file:
    json.dump(SETTINGS, read_file) # for local file
```

и раскомментируйте строку:

```python
# os.environ['settings'] = json.dumps(SETTINGS)
```

Аналогично в конце файла в блоке `if __name__ == '__main__'` закомментируйте строки:

```python
with open("settings.json", "r") as read_file
    SETTINGS = json.load(read_file)
```

и раскомментируйте строку:

```python
# SETTINGS = json.loads(os.environ['settings']) # for Replit
```

#### Запуск бота на сервисе

Чтобы активировать исполнение кода бота, нажмите кнопку Run в верхней части страницы. Если вы всё верно настроили, то в правой части окна в панели вывода отобразится строка `Bot is running...`.

#### Непрерывное выполнение кода

По умолчанию любой проект в бесплатном аккаунте на Replit “засыпает” через определенное время, на практике было получено значение в один час. Чтобы изменить это поведение, вам нужно оформить подписку на платный тариф **Hacker**. Для этого выполните:

1. Войдите в ваш аккаунт и нажмите кнопку **Upgrade**.
1. Нажмите кнопку **Upgrade to Hacker**.
1. Оплатите подписку с помощью платежной системы Stripe. Заполните все необходимые поля и нажмите кнопку **Подписаться**.

Далее откройте ваш проект и нажмите по его названию в верхнем левом углу. В нижней части появившегося окна переведите переключатель **Always On** в активное положение. Теперь ваш бот будет работать до тех пор, пока вы не остановите его сами вручную.

Также подписка на план Hacker дает возможность сделать ваш проект приватным (недоступным другим пользователям сервиса), а также увеличить мощность виртуальной машины, в которой работает бот. Подробнее читайте на [странице с тарифными планами](https://replit.com/pricing).
