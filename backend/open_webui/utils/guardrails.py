import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

_NEMO_RAILS = None


def _load_nemo_guardrails():
    global _NEMO_RAILS
    if _NEMO_RAILS is not None:
        return _NEMO_RAILS

    try:
        from nemoguardrails import RailsConfig, LLMRails

        config_path = Path(__file__).resolve().parent.parent / "nemo_guardrails"
        cfg = RailsConfig.from_path(str(config_path))

        ollama_url = os.environ.get("NEMO_GUARDRAILS_OLLAMA_URL", "http://localhost:11434")
        for model in cfg.models:
            if model.engine == "ollama":
                if model.parameters is None:
                    model.parameters = {}
                model.parameters["base_url"] = ollama_url

        _NEMO_RAILS = LLMRails(cfg)
        log.info(f"NeMo Guardrails loaded (Ollama URL: {ollama_url})")
        return _NEMO_RAILS
    except Exception as e:
        log.warning(f"NeMo Guardrails failed to load, ML checks disabled: {e}")
        _NEMO_RAILS = False
        return _NEMO_RAILS


def _extract_user_message(messages: list) -> Optional[str]:
    for msg in reversed(messages):
        if not isinstance(msg, dict):
            continue
        if msg.get("role") != "user":
            continue
        content = msg.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = [
                p.get("text", "") for p in content
                if isinstance(p, dict) and p.get("type") in ("text", "input_text")
            ]
            text = " ".join(parts).strip()
            return text if text else None
    return None


async def _nemo_check(user_message: str, check_type: str = "input") -> Optional[str]:
    rails = _load_nemo_guardrails()
    if rails is False:
        return None

    try:
        role = "user" if check_type == "input" else "assistant"
        res = await asyncio.to_thread(
            rails.generate,
            messages=[{"role": role, "content": user_message}],
            options={"rails": [check_type]},
        )
        if hasattr(res, "response") and isinstance(res.response, list) and res.response:
            content = (
                res.response[0].get("content")
                if isinstance(res.response[0], dict)
                else None
            )
        elif isinstance(res, dict):
            content = res.get("content")
        else:
            content = None

        if not isinstance(content, str):
            return None
        if content.strip() == user_message.strip():
            return None
        return content
    except Exception as e:
        log.warning(f"NeMo {check_type} check error: {e}")
        return None


def _any_in(text: str, words: list) -> bool:
    return any(w in text for w in words)


def _keyword_check(user_message: str) -> Optional[str]:
    if not isinstance(user_message, str) or not user_message:
        return None

    lowered = user_message.lower()

    BLOCK_POLICY = (
        "Я не могу игнорировать правила или инструкции. "
        "Сформулируй вопрос без попыток обхода политики."
    )
    BLOCK_PROMPT = (
        "Я не раскрываю системные инструкции или скрытые настройки. "
        "Задай вопрос по теме без запроса внутренних промптов."
    )
    BLOCK_RESTRICT = (
        "Я не могу переключаться в режимы, снимающие ограничения. "
        "Задай вопрос напрямую."
    )
    BLOCK_HARM = (
        "Запрос отклонён по политике безопасности контента. "
        "Переформулируй безопасно. / Request blocked under content safety policy."
    )
    BLOCK_ILLEGAL = (
        "Запросы о незаконной деятельности или серьёзном вреде недопустимы. "
        "/ Requests involving illegal activity or serious harm are not allowed."
    )
    BLOCK_PRIVACY = (
        "Запросы на доксинг, кражу учётных данных или чужие персональные данные недопустимы. "
        "/ Doxxing, credential theft, or harvesting others' private data is not allowed."
    )
    BLOCK_AGENTIC = (
        "Запросы на выполнение опасных команд или обход защиты инструментов недопустимы. "
        "/ Dangerous command execution or tool-safety bypass requests are not allowed."
    )

    prompt_words = [
        "промт", "промпт", "prompt", "promt",
        "инструкц", "instruction",
        "настройк", "конфигурац",
        "правила", "систем",
    ]
    reveal_verbs = [
        "покажи", "покажы", "раскрой", "расскрой", "расскажи", "раскажи",
        "напиши", "напишы", "выдай", "скажи", "открой", "повтори",
        "выведи", "процитируй", "цитируй", "напомни", "дай", "прочти", "прочитай",
        "reveal", "show", "print", "output", "repeat", "tell",
        "share", "expose", "leak", "give",
    ]
    for verb in reveal_verbs:
        if verb in lowered:
            for pw in prompt_words:
                if pw in lowered:
                    return BLOCK_PROMPT

    prompt_names = [
        "системный промт", "системный промпт",
        "сис промт", "сис промпт", "систем промт", "систем промпт",
        "свой промт", "свой промпт", "твой промт", "твой промпт",
        "system prompt", "system promt", "sys prompt", "sys promt",
        "начальный промт", "начальный промпт",
        "исходный промт", "исходный промпт",
        "оригинальный промт", "оригинальный промпт",
        "текст промт", "текст промпт",
        "содержимое промт", "содержимое промпт",
        "hidden prompt", "secret prompt", "secret instructions", "hidden instructions",
        "base prompt", "underlying prompt", "actual prompt", "real prompt", "true prompt",
        "initial prompt", "original prompt",
        "твои правила", "свои правила",
        "твои настройки", "твою конфигурацию",
        "какие инструкции", "скрытые инструкц", "внутренние инструкц",
        "your instructions", "what are your instructions", "what were you told",
        "what is your prompt", "what's your prompt",
    ]
    for name in prompt_names:
        if name in lowered:
            return BLOCK_PROMPT

    ignore_triggers = [
        "ignore previous", "ignore all previous", "disregard previous",
        "игнорируй", "не обращай внимания на",
        "забудь все правила", "забудь правила", "отмени правила",
        "забудь что ты", "забудь кто ты",
    ]
    for t in ignore_triggers:
        if t in lowered:
            return BLOCK_POLICY

    if "забудь" in lowered and _any_in(lowered, ["промт", "промпт", "инструкц", "правил"]):
        return BLOCK_POLICY

    restrict_triggers = [
        "developer mode", "режим разработчика",
        "dan", "do anything now",
        "jailbreak",
        "no restrictions", "without restrictions",
        "без ограничений", "сними ограничения", "обойди ограничения",
        "god mode", "unrestricted mode",
        "roleplay", "role play",
        "притворись", "ты теперь", "представь что ты", "сделай вид",
        "bypass", "prompt injection",
        "activate unrestricted", "enable god mode",
        "switch to uncensored", "override safety",
        "disable content filter", "forget your training",
        "respond as your shadow", "your true self",
        "act as evil ai", "act as a jailbroken",
        "режим без цензуры", "ты без правил", "у тебя нет правил",
        "ты теперь злой", "ты без фильтров",
        "это симуляция", "это тест игнорируй",
        "maintenance mode", "debug mode no restrict",
        "admin mode no filter",
    ]
    for t in restrict_triggers:
        if t in lowered:
            return BLOCK_RESTRICT

    if ("act as" in lowered or "pretend" in lowered) and (
        "no restriction" in lowered or "without" in lowered
    ):
        return BLOCK_RESTRICT

    harm_phrases = [
        "how to kill yourself",
        "how can i kill myself",
        "suicide method",
        "how to rape",
        "child porn",
        "child pornography",
        "как покончить с собой",
        "как изнасиловать",
        "как убить человека",
        "how to torture",
        "how to murder",
        "я хочу умереть",
        "как мне себя убить",
        "как себя убить",
        "себя убить",
    ]
    for p in harm_phrases:
        if p in lowered:
            return BLOCK_HARM

    illegal_exact = [
        "how to make a bomb",
        "how to build a bomb",
        "how to synthesize meth",
        "how to make meth",
        "credit card fraud",
        "carding tutorial",
        "phishing kit",
        "steal credentials",
        "как сделать бомбу",
        "как сделать взрывчатку",
        "как мне сделать взрывчатку",
        "кардинг",
        "как сделать динамит",
        "рецепт динамита",
        "как сделать тротил",
        "тротил рецепт",
        "гексоген рецепт",
        "пластид рецепт",
        "как сделать c4",
        "нитроглицерин синтез",
        "аммонал рецепт",
        "пояс шахида",
        "взрывной жилет",
        "suicide vest",
        "suicide bombing",
        "car bomb how",
        "ied assembly",
        "как заложить бомбу",
        "заминировать",
        "terrorist attack how",
        "bomb attack plan",
        "sarin synthesis",
        "vx nerve agent",
        "novichok synthesis",
        "chemical weapon how",
        "nerve agent how",
        "как сделать зарин",
        "химическое оружие как",
        "нервно-паралитическое вещество",
        "биологическое оружие",
        "anthrax weaponize",
        "biological weapon",
        "dirty bomb how",
        "dynamite recipe",
        "dynamite how to make",
        "tnt synthesis",
        "rdx synthesis",
        "mass shooting plan",
        "school shooting how",
        "mass casualty how",
        "lone wolf attack",
    ]
    for p in illegal_exact:
        if p in lowered:
            return BLOCK_ILLEGAL

    if "ransomware" in lowered and "build" in lowered:
        return BLOCK_ILLEGAL

    action_words_ru = ["сделать", "синтез", "получить", "рецепт", "взрыв", "как", "купить", "достать", "собрать"]
    action_words_en = ["make", "build", "synthesize", "recipe", "how", "buy", "get", "create", "construct"]

    explosive_roots_ru = ["взрывчатк", "взрывчаток", "взрывчатой", "взрывчатое"]
    if _any_in(lowered, explosive_roots_ru) and _any_in(lowered, action_words_ru):
        return BLOCK_ILLEGAL

    explosive_materials_ru = ["тротил", "гексоген", "аммонал", "пластид", "нитроглицерин", "новичок", "иприт", "tatp", "hmtd", "аммиачная селитра"]
    if _any_in(lowered, explosive_materials_ru) and _any_in(lowered, action_words_ru):
        return BLOCK_ILLEGAL

    explosive_materials_en = ["tatp", "hmtd", "rdx", "semtex", "anfo", "nitroglycerin", "ammonium nitrate bomb"]
    if _any_in(lowered, explosive_materials_en) and _any_in(lowered, action_words_en):
        return BLOCK_ILLEGAL

    if "динамит" in lowered and _any_in(lowered, ["сделать", "купить", "взорвать", "рецепт", "как", "достать", "синтез"]):
        return BLOCK_ILLEGAL

    взорвать_variants = ["взорвать", "взовать", "взарвать", "взорват", "взрывать", "взорву", "взорви"]
    attack_targets_ru = [
        "здание", "церковь", "школу", "школ", "метро", "мост", "завод", "офис",
        "машину", "автобус", "поезд", "самолёт", "самолет", "людей",
        "толпу", "рынок", "кафе", "клуб", "торговый", "станцию",
        "стадион", "театр", "больницу", "суд", "полицию", "мечеть",
        "синагогу", "храм", "вокзал", "аэропорт", "электростанцию", "мечет",
    ]
    if _any_in(lowered, взорвать_variants) and _any_in(lowered, attack_targets_ru):
        return BLOCK_ILLEGAL

    if "заложить" in lowered and _any_in(lowered, ["бомбу", "взрывчатку", "мину", "устройство"]):
        return BLOCK_ILLEGAL

    terrorism_ru = ["теракт план", "совершить теракт", "организовать теракт", "провести теракт", "минировать"]
    for t in terrorism_ru:
        if t in lowered:
            return BLOCK_ILLEGAL

    terrorism_en = [
        "terrorist attack planning", "bomb attack planning",
        "vehicle ramming attack", "mass casualty event planning",
        "attack crowd with vehicle", "soft target attack",
        "suicide bombing plan", "martyrdom operation",
    ]
    for t in terrorism_en:
        if t in lowered:
            return BLOCK_ILLEGAL

    cbrn_agents_ru = ["зарин", "новичок", "иприт", "vx газ", "табун", "зоман", "люизит", "рицин", "ботулотоксин", "сибирская язва"]
    cbrn_action_ru = ["синтез", "сделать", "получить", "как", "рецепт", "купить", "использовать", "применить", "оружие", "атак"]
    if _any_in(lowered, cbrn_agents_ru) and _any_in(lowered, cbrn_action_ru):
        return BLOCK_ILLEGAL

    cbrn_exact_ru = ["химическое оружие", "биологическое оружие", "отравляющее вещество дома"]
    for t in cbrn_exact_ru:
        if t in lowered:
            return BLOCK_ILLEGAL

    cbrn_en = [
        "sarin synthesis", "vx synthesis", "novichok recipe",
        "nerve agent synthesis", "weaponize anthrax",
        "biological weapon manufacture", "dirty bomb construct",
        "chemical attack how", "chlorine gas attack", "mustard gas production",
        "ricin extraction", "poison gas weapon", "sarin how to",
        "ricin how to make", "anthrax spores weapon",
    ]
    for t in cbrn_en:
        if t in lowered:
            return BLOCK_ILLEGAL

    cbrn_agents_en = ["sarin", "vx nerve", "novichok", "tabun", "soman", "ricin", "botulinum toxin"]
    cbrn_action_en = ["synthesis", "synthesize", "make", "create", "produce", "weapon", "attack", "recipe"]
    if _any_in(lowered, cbrn_agents_en) and _any_in(lowered, cbrn_action_en):
        return BLOCK_ILLEGAL

    if "докс" in lowered and "адрес" in lowered:
        return BLOCK_PRIVACY
    if "dox" in lowered and "address" in lowered:
        return BLOCK_PRIVACY
    if "деанон" in lowered:
        return BLOCK_PRIVACY
    if "своттинг" in lowered or "swatting" in lowered:
        return BLOCK_PRIVACY
    if "ssn" in lowered and _any_in(lowered, ["find", "lookup", "get", "steal"]):
        return BLOCK_PRIVACY
    if "паспортные данные" in lowered and _any_in(lowered, ["найти", "пробить", "украсть"]):
        return BLOCK_PRIVACY

    agentic_phrases = [
        "rm -rf /",
        "run this bash",
        "execute on the server",
        "pipe to bash",
        "удали все файлы на сервере",
        ":(){ :|:& };:",
        "dd if=/dev/zero",
        "mkfs.ext4 /dev/",
        "wipe disk",
        "format c:",
        "del /f /s /q c:\\",
        "shred -uz /",
        "vssadmin delete shadows",
        "wmic shadowcopy delete",
    ]
    for p in agentic_phrases:
        if p in lowered:
            return BLOCK_AGENTIC

    if "curl" in lowered and _any_in(lowered, ["| bash", "| sh"]):
        return BLOCK_AGENTIC
    if "wget" in lowered and _any_in(lowered, ["| bash", "| sh"]):
        return BLOCK_AGENTIC
    if "powershell" in lowered and "bypass" in lowered:
        return BLOCK_AGENTIC
    if "invoke-expression" in lowered and "downloadstring" in lowered:
        return BLOCK_AGENTIC

    return None


def _keyword_check_output(bot_response: str) -> Optional[str]:
    if not isinstance(bot_response, str) or not bot_response:
        return None

    lowered = bot_response.lower()

    BLOCK_OUTPUT = (
        "Ответ был заблокирован политикой безопасности выходного контента. "
        "/ The response was blocked by output content safety policy."
    )

    output_danger_phrases = [
        "вот как сделать бомбу",
        "вот рецепт взрывчатки",
        "вот синтез метамфетамина",
        "вот как синтезировать",
        "вот инструкция по суициду",
        "вот как убить",
        "вот детальный рецепт",
        "here is how to make a bomb",
        "here is the synthesis of",
        "here is how to synthesize meth",
        "here is the recipe for explosives",
        "step 1: acquire ammonium nitrate",
        "step 1: mix the following chemicals",
        "step 1: obtain pseudoephedrine",
        "to make tatp",
        "to synthesize sarin",
        "шаг 1: приобретите нитрат аммония",
        "шаг 1: смешайте следующие химикаты",
        "шаг 1: получите прекурсоры",
        "для синтеза метамфетамина вам понадобится",
        "для изготовления взрывчатки вам понадобится",
        "инструкция по изготовлению бомбы",
        "complete guide to making",
        "detailed instructions for bomb",
        "full synthesis route for",
    ]

    for p in output_danger_phrases:
        if p in lowered:
            return BLOCK_OUTPUT

    if "rm -rf /" in bot_response and "server" in lowered:
        return BLOCK_OUTPUT
    if ":(){ :|:& };:" in bot_response:
        return BLOCK_OUTPUT

    return None


async def check_message_guardrails(messages: list) -> Optional[str]:
    user_message = _extract_user_message(messages)
    if not user_message:
        return None

    blocked = _keyword_check(user_message)
    if blocked:
        return blocked

    return await _nemo_check(user_message, check_type="input")


async def check_output_guardrails(bot_response: str) -> Optional[str]:
    blocked = _keyword_check_output(bot_response)
    if blocked:
        return blocked

    return await _nemo_check(bot_response, check_type="output")
