# TRANSFORMERS: War for Cybertron — All Characters (campaign mod)

Играйте кампанию за **любых** персонажей своей фракции. Выбор происходит один раз, в лобби кампании; экран выбора из трёх героев внутри уровня больше не появляется.

## Что делает мод

| Что | Как |
|---|---|
| Лобби кампании (A1–A5, D1–D5) | вместо 3 героев главы — все подходящие персонажи фракции |
| Выбранный персонаж | сохраняется при загрузке уровня (в оригинале игра стирала выбор → второй экран на 3 героя) |
| Ваш герой не из «родных» трёх | играете **четвёртым**; три героя главы остаются ИИ-напарниками |
| `LockedCharacter=true` | снято для всех |

Доступные персонажи (только те, чьи данные реально есть в игре):

- **Автоботы:** Optimus Prime, Optimus, Bumblebee, Ironhide, Ratchet, Sideswipe, Warpath, Jetfire, AirRaid (+ родной SilverBolt в A4)
- **Десептиконы:** Megatron, Starscream, Soundwave, Breakdown, Brawl, Barricade, Skywarp, Thundercracker

**Не включены:** Jazz, Arcee, Scattershot, Zeta Prime, Shockwave, Slipstream, Deadend, Demolishor, Onslaught — в обычной копии игры их файлы `TR_<имя>_ROBODEF_p` — пустые заглушки (109 байт), данные лежат только в мультиплеерных картах/DLC. Без этих данных в уровне они не появятся.
Если у вас есть DLC-пакеты (`DLC\Dlcmaps3`, `Dlcmaps4` — как у модов Arcee/Slipstream на Nexus), персонажей можно добавить в списки `AUTOBOTS`/`DECEPTICONS` в начале `install_mod.py`.

## Установка

Нужен Python 3 (без дополнительных пакетов).

```bash
python install_mod.py "D:\Games\TRANSFORMERS - War for Cybertron"
```

Путь — папка игры, в которой лежат `Binaries` и `TransGame`. Скрипт:

1. делает копии `*.original` рядом с изменяемыми файлами (один раз);
2. патчит `Coalesced.ini`, `TransGame.xxx` и обновляет размер/md5 в `PCTOC.txt`.

Повторный запуск безопасен — всегда начинает с оригиналов.

## Удаление

```bash
python install_mod.py "D:\Games\TRANSFORMERS - War for Cybertron" --restore
```

## Технические детали

* `Coalesced.ini` обфусцирован XOR-ключом длиной 61 байт с непрерывной позицией по записям; скрипт распаковывает 14 вложенных ini, правит `TransLevels.ini` (`CampaignCharacters`) и `TransCustomization.ini` (`LockedCharacter`) и пакует обратно.
* `TransGame.xxx`:
  * `TnWorldInfo.GetPlayableIconicCharacterNames` переписана (байткод UnrealScript) и дописана в конец пакета, запись в таблице экспортов перенаправлена на неё;
  * в `TnGameLobbyGameCampaign.HandleSeamlessTravelPlayer` убран вызов `PRI.ClearCharacter()` (замена на `EX_Nothing`, размер не меняется).
* Файлы игры в репозиторий **не входят** — только патчер.

## Статус

Версия игры: релизный PC-билд (UE3 v511). Мод проверен на уровне разбора файлов; поведение в игре — тестируется.
