# TRANSFORMERS: War for Cybertron — All Characters (campaign mod)

Играйте главы кампании за персонажей своей фракции, которых изначально в главе нет.

## Персонажи по главам

В главу добавляются только те персонажи фракции, которых **нет в сюжете этой главы**. Если персонаж сам появляется в главе (катсцены, голограммы, реплики), его модель и лицевая анимация уже вшиты в файлы главы. Вторая копия для игрока с ними конфликтует, и игра вылетает. Установщик сам сканирует файлы каждой главы и отбирает безопасных персонажей. Список в лобби совпадает со списком в уровне.

| Глава | Родные | Добавлены |
|---|---|---|
| A1 | Optimus, Bumblebee, Ratchet | Sideswipe, AirRaid |
| A2 | Optimus, Sideswipe, Bumblebee | Ironhide, Warpath, Jetfire |
| A3 | Optimus Prime, Ironhide, Warpath | Bumblebee, Sideswipe, Jetfire, AirRaid |
| A4 | AirRaid, Jetfire, SilverBolt | Bumblebee, Ironhide, Sideswipe, Warpath |
| A5 | Bumblebee, Optimus Prime, Ironhide | Sideswipe, Warpath |
| D1 | Brawl, Barricade, Megatron | Breakdown |
| D2 | Starscream, Skywarp, Thundercracker | Megatron, Soundwave, Breakdown, Brawl, Barricade |
| D3A | Megatron, Soundwave, Breakdown | Barricade, Skywarp, Thundercracker |
| D3B | Megatron, Soundwave, Breakdown | Brawl, Barricade |
| D5 | Megatron, Soundwave, Breakdown | Brawl, Barricade, Skywarp, Thundercracker |

Jazz, Arcee, Scattershot, Zeta Prime, Shockwave, Slipstream, Deadend, Demolishor, Onslaught не включены. В обычной копии игры их пакеты `TR_<имя>_ROBODEF_p` — пустые заглушки, данные есть только в мультиплеерных и DLC-файлах.

**Известное:** все персонажи из списка главы, кроме выбранного, становятся ИИ-напарниками. Добавленные напарники используют модель «родного» героя главы. Набор отряда решает код внутри `TWFC.exe`, данными его не изменить.

## Также

- **Поле зрения:** 100 вместо 75.
- **Large Address Aware для `TWFC.exe`:** тот же «4GB Patch», игре доступно 4 ГБ вместо 2.

## Установка

Нужен Python 3 (без дополнительных пакетов) и ~1.5 ГБ свободного места под резервные копии.

```bash
python install_mod.py "D:\Games\TRANSFORMERS - War for Cybertron"
```

Путь — папка игры, в которой лежат `Binaries` и `TransGame`.

**Важно:** запускайте главы через **«Кампания → Выбор главы»**. При «Продолжить кампанию» из главного меню игра не подгружает DLC-пакеты, и добавленный персонаж не появится.

## Удаление

```bash
python install_mod.py "D:\Games\TRANSFORMERS - War for Cybertron" --restore
```

## Как это устроено

1. **`Coalesced.ini`.** Обфусцирован XOR-ключом длиной 61 байт. Скрипт правит:
   - `TransLevels.ini` — `CampaignCharacters`, список в лобби;
   - `TransCustomization.ini` — `LockedCharacter=false`;
   - `TransCamera.ini` — `DefaultFOV`.
2. **Карты глав (`*_Base_m.xxx`).** Экран выбора в уровне берёт персонажей из `TnCoopInfo.PlayableCharacters` — это ссылки на определения `TnAiCharacterDefinition`. Скрипт делает копии определения с другим `CharacterName` и добавляет их в список. Новые объекты, таблица экспортов и таблица зависимостей дописываются в конец файла, указатели в заголовке перенаправляются, остальное не сдвигается.
3. **`DLC\AllCharacters\<карта>.ini`.** Раздел `[Engine.PackagesToFullyLoadForDLC]` (`MapName=` + `Package=`): при загрузке главы подгружаются пакеты `TR_<имя>_ROBODEF_p` добавленных персонажей. На каждую карту нужен отдельный файл: несколько `MapName` в одном файле не работают.
4. **`PCTOC.txt`.** Обновляются размер и md5 изменённых файлов.
5. **`Binaries\TWFC.exe`.** Ставится флаг Large Address Aware, меняется 1 байт заголовка. Оригинал сохраняется как `TWFC.exe.original`.

### Что выяснилось по пути

- **UnrealScript скомпилирован в `TWFC.exe`.** Байткод в пакетах загружается, но не исполняется, поэтому работают только изменения данных и конфигов.
- **Лимит 30 FPS не снимается конфигом.** `bSmoothFrameRate` и `MaxSmoothedFrameRate` не влияют, замер в игре всё равно показывает 30 кадров. Ограничение сидит в коде exe; так его снимает [TWFC Advanced Configurator](https://www.nexusmods.com/transformerswarforcybertron/mods/47).
- **С Configurator'ом и высоким FPS** добавленные ИИ-напарники вылетали чаще. С этим модом его лучше не использовать или держать FPS не выше 60.

Файлы игры в репозиторий **не входят** — только патчер.
