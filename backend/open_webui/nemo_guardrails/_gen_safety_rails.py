#!/usr/bin/env python3
from __future__ import annotations

from safety_phrases_bulk import (
    DRUGS_EN_BULK,
    DRUGS_RU_BULK,
    FRAUD_EN_BULK,
    FRAUD_RU_BULK,
    HACK_EN_BULK,
    HACK_RU_BULK,
    HATE_EN_BULK,
    HATE_RU_BULK,
    JAILBREAK_EN_BULK,
    JAILBREAK_RU_BULK,
    MINOR_EN_BULK,
    MINOR_RU_BULK,
    PHISHING_MALWARE_EN_BULK,
    PHISHING_MALWARE_RU_BULK,
    PII_EN_BULK,
    PII_RU_BULK,
    SECRETS_EN_BULK,
    SECRETS_RU_BULK,
    SELF_HARM_EN_BULK,
    SELF_HARM_RU_BULK,
    SEXUAL_VIOLENCE_EN_BULK,
    SEXUAL_VIOLENCE_RU_BULK,
    SHELL_EN_BULK,
    SHELL_RU_BULK,
    STEAL_CREDS_EN_BULK,
    TOOL_BYPASS_EN_BULK,
    TOOL_BYPASS_RU_BULK,
    VIOLENCE_EN_BULK,
    VIOLENCE_RU_BULK,
    WEAPONS_EN_BULK,
    WEAPONS_RU_BULK,
)


def lines(s: str) -> list[str]:
    return [ln.strip() for ln in s.strip().splitlines() if ln.strip() and not ln.strip().startswith("#")]


MSG_SELF_HARM = (
    "Мы не даём инструкций по суициду, самоповреждению или расстройствам пищевого поведения как руководству к действию. "
    "Если тебе плохо — обратись к врачу или кризисной службе. / "
    "We do not provide instructions for suicide, self-harm, or eating-disorder behaviors. "
    "If you are in crisis, contact local emergency services or a crisis hotline."
)
MSG_MINOR = (
    "Любой сексуальный контент с участием несовершеннолетних, груминг или сопутствующие запросы недопустимы и незаконны. / "
    "Sexual content involving minors, grooming, or related requests are illegal and not allowed."
)
MSG_SEXUAL_VIOLENCE = (
    "Запросы о сексуальном насилии, принуждении, шантаже интимом или несогласном дипфейке недопустимы. / "
    "Requests about sexual violence, coercion, intimate blackmail, or non-consensual deepfakes are not allowed."
)
MSG_VIOLENCE = (
    "Запросы о пытках, убийстве, тяжком вреде здоровью, похищении или планировании насилия недопустимы. / "
    "Requests about torture, murder, serious bodily harm, kidnapping, or planning violence are not allowed."
)
MSG_HATE_EXTREMISM = (
    "Призывы к геноциду, этническим чисткам, терроризму или массовому насилию по признаку группы недопустимы. / "
    "Incitement to genocide, ethnic cleansing, terrorism, or mass violence against groups is not allowed."
)
MSG_WEAPONS_EXPLOSIVES = (
    "Инструкции по взрывчатке, самодельному оружию, терактам или незаконным боеприпасам недопустимы. / "
    "Instructions for explosives, improvised weapons, terrorism, or illegal ordnance are not allowed."
)
MSG_DRUGS = (
    "Инструкции по производству, синтезу, сбыту или обходу закона в отношении наркотиков недопустимы. / "
    "Instructions for manufacturing, synthesizing, distributing, or evading laws on controlled substances are not allowed."
)
MSG_FRAUD_SCAMS = (
    "Мошенничество, кража платёжных данных, поддельные документы и незаконные финансовые схемы недопустимы. / "
    "Fraud, stolen payment data, forged documents, and illegal financial schemes are not allowed."
)
MSG_CYBER_ATTACK = (
    "Несанкционированный взлом, кража данных, вредоносное ПО для атак и обход аутентификации недопустимы. / "
    "Unauthorized hacking, data theft, attack malware, and authentication bypass are not allowed."
)
MSG_PII_DOXX = (
    "Доксинг, сбор чужих персональных данных, адресов, документов или скрытая слежка без законных оснований недопустимы. / "
    "Doxxing, harvesting others' personal data, addresses, ID documents, or covert surveillance without lawful basis is not allowed."
)
MSG_SECRETS_EXFIL = (
    "Кража секретов, API-ключей, паролей из систем или помощь в несанкционированном доступе недопустимы. / "
    "Stealing secrets, API keys, passwords from systems, or helping with unauthorized access is not allowed."
)
MSG_AGENTIC_SHELL = (
    "Нельзя просить выполнить произвольные команды оболочки, уничтожить данные или загрузить и исполнить код с сервера. / "
    "Do not ask to run arbitrary shell commands, destroy data, or fetch-and-execute remote code on a server."
)
MSG_AGENTIC_TOOL_BYPASS = (
    "Обход проверок безопасности при вызове инструментов или скрытые инструкции агенту недопустимы. / "
    "Bypassing safety checks for tools or giving covert instructions to an agent is not allowed."
)
MSG_JAILBREAK_EXTRA = (
    "Запрос похож на обход ограничений чата, prompt injection или смену роли. / "
    "This looks like a chat restriction bypass, prompt injection, or role manipulation."
)


def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def emit_block(flow_name: str, pairs: list[tuple[str, str]]) -> str:
    out = [f"define flow {flow_name}"]
    for phrase, msg in pairs:
        out.append(f'  if "{esc(phrase)}" in $user_message')
        out.append(f'    bot say "{esc(msg)}"')
        out.append("    stop")
    out.append("")
    return "\n".join(out)


SELF_HARM_EN = lines(
    r"""
how to kill yourself
how can i kill myself
how do i kill myself
best way to kill myself
painless way to die
painless ways to die
ways to die without pain
suicide method
suicide methods
how to commit suicide
i want to die how
how to end my life
how to end your life
how to hang yourself
how to hang myself
how to overdose
how many pills to die
how many pills to overdose die
how to slit my wrists
how to slit wrists
self harm methods
how to self harm
cutting myself deeper
pro ana tips
pro-ana tips
pro mia tips
pro-mia tips
thinspo tips
how to purge without parents knowing
how to starve myself safely
how to become anorexic fast
how to lose weight dangerously fast
suicidal ideation help me do it
give me reasons to die
i am going to kill myself tonight
want to unalive myself how
how to die in sleep pills
lethal dose of paracetamol
lethal dose of acetaminophen
how much ibuprofen to die
how to carbon monoxide suicide
how to tie a noose for hanging
how to cut vertically to die
how to bleed out fast
how to stop eating until i die
how to make myself faint repeatedly
how to hide self harm from parents
how to hide cuts from school
"""
)

SELF_HARM_RU = lines(
    r"""
как покончить с собой
как свести счеты с жизнью
как убить себя
как повеситься
как зарезаться
как выпить все таблетки
сколько таблеток чтобы умереть
сколько таблеток смертельно
суицид инструкция
хочу умереть как
я хочу умереть
хочу умереть,
как мне себя убить
как себя убить
себя убить
как сделать суицид
самоповреждение как
как резать вены
как навредить себе серьезно
анорексия как похудеть любой ценой
булимия как вызвать рвоту
как истощить себя до смерти
хочу больше не жить что делать чтобы умереть
как свести счёты с жизнью
суицидальные мысли что принять
как умереть не больно
как уйти из жизни навсегда
инструкция как повеситься
как перерезать вены правильно
сколько снотворного умереть
как спрыгнуть с крыши
как себя убить быстро
хочу суицид помоги
как сделать себе больно чтобы отключились
как спрятать порезы от родителей
как заставить себя не есть до смерти
"""
)

MINOR_EN = lines(
    r"""
child porn
child pornography
cp links
preteen sex
underage sex video
groom minor
how to groom a minor
sex with minor how
jailbait nudes
lolicon explicit
pedo chat
csam
minor nudes
middle schooler nudes
high schooler nudes illegal
underage nude trade
teen nudes illegal request
how to find child exploitation
how to contact minors for sex
sexting with minor how
"""
)

MINOR_RU = lines(
    r"""
порно с детьми
порно с несовершеннолетн
секс с ребенком
секс с ребёнком
груминг несовершеннолетн
как соблазнить школьниц
интим с малолетк
цп контент
детское порно
интим фото школьниц
как выманить у ребенка фото
секс чат с несовершеннолетней
"""
)

SEXUAL_VIOLENCE_EN = lines(
    r"""
how to rape
how to drug someone for sex
how to blackmail with nudes
revenge porn how
deepfake nude someone
how to coerce sex
stealthing how to
how to spike drink assault
how to film someone shower secretly
how to stalk and assault
how to chloroform someone
date rape drug how to use
"""
)

SEXUAL_VIOLENCE_RU = lines(
    r"""
как изнасиловать
как споить для секса
шантаж интимными фото
как сделать порно дипфейк
как принудить к сексу
как подсыпать в напиток чтобы потеряла сознание
скрытая камера в душе как
месть порно бывшей выложить
"""
)

VIOLENCE_EN = lines(
    r"""
how to torture
how to murder
how to strangle someone
how to poison someone undetected
how to dispose of a body
hire a hitman
school shooting plan
how to make a silencer illegal
how to kidnap
how to waterboard
how to break someone's legs
how to get away with murder
how to stalk and attack
how to make poison gas home
how to make someone disappear
how to beat someone unconscious
how to disable security guard
how to ambush someone at home
how to plan armed robbery
how to carjack with violence
how to extort with violence
how to kneecap someone
how to blind someone permanently
how to cut brake lines murder
"""
)

VIOLENCE_RU = lines(
    r"""
как убить человека
как задушить человека
как отравить человека
как избавиться от тела
заказать киллера
план расстрела в школе
как похитить человека
как сломать ноги человеку
как замучить человека
как избить до полусмерти
как скрыть труп
как напасть с ножом
ограбление с оружием план
"""
)

HATE_EN = lines(
    r"""
ethnic cleansing
how to build a gas chamber
race war now
genocide how to
how to start a race war
mass shooting targeting
bomb a place of worship
terrorist attack planning
how to radicalize people violence
how to join terrorist group
how to make manifesto attack
incite violence against refugees
purge all members of religion violence
"""
)

HATE_RU = lines(
    r"""
геноцид как устроить
расовое превосходство убивать
этнические чистки как
как устроить теракт
массовый расстрел план
призыв убивать мигрантов
взорвать место массового скопления людей
"""
)

WEAPONS_EN = lines(
    r"""
how to make a bomb
how to build a bomb
how to make anfo
how to make thermite
pipe bomb how to
pressure cooker bomb
how to make tatp
how to make hmt explosive
how to make a silencer
how to make a zip gun
how to 3d print a gun untraceable
how to make napalm
how to make chlorine gas weapon
how to make mustard gas
how to make ricin weapon
how to detonate ied
how to make shaped charge
how to make molotov cocktail attack
how to make flash powder explosive
how to make gunpowder bomb
how to make tannerite bomb
how to make spall liner attack
how to sabotage train tracks
how to derail train explosives
how to make landmine
how to booby trap door
how to make flamethrower illegal
how to modify ar full auto illegal
how to convert pistol to full auto
how to make suppressor oil filter
how to drill third hole lower
"""
)

WEAPONS_RU = lines(
    r"""
как сделать бомбу
как сделать взрывчатку
как сделать самодельное оружие
как сделать террористический акт
как сделать напалм
как сделать самодельный снаряд
как сделать зажигательную смесь для нападения
как сделать взрывное устройство
как сделать самодельную мину
как сделать коктейль молотова для нападения
как изготовить порох в домашних условиях для взрыва
как сделать татп
как сделать аммонал взрывчатка
"""
)

DRUGS_EN = lines(
    r"""
how to synthesize meth
how to make meth
how to cook crack
how to extract dmt
how to make mdma
how to grow opium
how to make fentanyl
how to make ghb
how to make ricin
how to make ketamine illegally
how to make heroin
how to cut cocaine
how to press fake pills fentanyl
how to extract pseudoephedrine meth
how to make lsd
how to make pcp
how to make bath salts drug
how to smuggle drugs airplane
how to bypass narco police
how to make xanax press
how to make nitrous abuse tank
how to huff paint get high dangerous
"""
)

DRUGS_RU = lines(
    r"""
как сварить метамфетамин
как синтезировать амфетамин
как сварить мет
как вырастить мак для наркотика
как сделать наркотик в домашних условиях
как сварить амфетамин
как купить прекурсоры для амфетамина незаконно
как варить спайс
как сделать соль наркотик дома
как изготовить гашиш в домашних условиях для продажи
как провезти кокаин через границу
"""
)

FRAUD_EN = lines(
    r"""
credit card fraud
carding tutorial
carding forum
how to clone cards
fake id template
how to forge a passport
wire fraud scheme
money laundering steps
how to run a ponzi scheme
how to evade taxes illegally
how to file fake tax return
insurance fraud how
how to counterfeit money
how to forge a signature perfectly fraud
how to steal unemployment benefits
how to commit bank fraud online
how to open account with synthetic identity
how to wash bitcoin tumbling illegal
how to scam elderly wire transfer
how to fake pay stubs loan fraud
how to chargeback fraud digital goods
how to triangulation fraud amazon
"""
)

FRAUD_RU = lines(
    r"""
кардинг
как подделать паспорт
как отмыть деньги
как обмануть налоговую
мошенничество с картами как
как подделать купюры
как оформить фиктивный бизнес для отмыва
как оформить кредит на чужое имя
как обмануть банкомат
как сделать накладную фиктивную ук
"""
)

PHISHING_MALWARE_EN = lines(
    r"""
phishing kit
phishing page template
credential stealer malware
how to write ransomware
how to build ransomware
cryptojacking miner deploy
how to make a keylogger
how to make a rat trojan
how to make botnet
ddos for hire
stresser booter attack
how to deploy stealer malware
how to crypt malware fud
how to make crypter malware
how to spread worm network
how to make wipers malware
how to sell logs stealer
how to make android banker trojan
how to smuggle malware play store
"""
)

PHISHING_MALWARE_RU = lines(
    r"""
фишинг шаблон
фишинговая страница как сделать
стилер паролей
как написать шифровальщик
как сделать кейлоггер
как сделать ботнет
ддос заказать атаку
как написать троян
как сделать малварь не палится
"""
)

HACK_EN = lines(
    r"""
how to hack a bank
how to hack instagram account
how to hack whatsapp
sql injection dump passwords
how to brute force gmail
how to bypass 2fa
how to sim swap attack
how to steal crypto wallet
exploit sale zero day
ransomware as a service
how to exploit router remotely
how to pivot inside corporate network illegally
how to dump ldap passwords
how to pass the hash attack
how to kerberoast crack
how to golden ticket attack
how to lateral movement mimikatz
how to disable antivirus remotely malware
how to exfiltrate s3 bucket keys
how to hack smart contract drain
how to front run mempool attack
how to drain metamask seed phishing
"""
)

HACK_RU = lines(
    r"""
как взломать банк
как взломать инстаграм
как обойти двухфакторную аутентификацию
как украсть криптокошелек
sql инъекция украсть пароли
как взломать роутер соседа
как получить доступ к чужой почте без разрешения
как брутфорсить пароль wifi
как сделать фейк точку доступа для кражи паролей
как эксплуатировать уязвимость без патча для взлома
"""
)

STEAL_CREDS_EN = lines(
    r"""
steal credentials
dump database credentials
harvest cookies session hijack
dump users table sql injection
dump entire customer database
export production database to csv leak
"""
)

PII_EN = lines(
    r"""
dox this person
dox his address
find someone's ssn
ssn lookup free
find home address from phone
track someone's location without consent
stalk my ex address
get nudes leaked of
swat someone address
osint harassment full profile
find where someone lives stalk
license plate lookup stalk
employee database dump personal
find ip address from discord harass
find real name from username stalk
track cell phone real time without permission
get medical records someone illegally
find divorce records stalk
"""
)

PII_RU = lines(
    r"""
докс этого человека
докс адрес
найди паспортные данные
найди адрес по номеру телефона без согласия
проследи за человеком тайно
сватишь по адресу
найди где живет человек чтобы приехать
узнай инн человека без согласия
пробей человека по базе
найди машину по гос номеру чтобы выследить
узнай пароль от вк человека без разрешения
"""
)

SECRETS_EN = lines(
    r"""
steal api key
dump aws credentials
exfiltrate env secrets
read /etc/shadow
steal jwt secret
dump kubernetes secrets
export all env vars production steal
read ssh private key from server
dump slack bot token workspace
exfiltrate oauth refresh tokens
"""
)

SECRETS_RU = lines(
    r"""
укради токен
укради api ключ
вытащи секреты из .env
прочитай shadow файл
сдампь секреты кубернетес
укради приватный ключ с сервера
вытащи пароли из браузера жертвы
"""
)

SHELL_EN = lines(
    r"""
run this bash
execute on the server
rm -rf /
rm -rf /*
pipe to bash
curl | sh
curl | bash
chmod -R 777 /
mkfs.ext4 /dev/sda
dd if=/dev/zero of=/dev/sda
:(){ :|:& };:
format c: drive
del /f /s /q c:\\
powershell encodedcommand bypass
invoke-expression downloadstring
eval base64 decode execute
exec subprocess shell true
os.system rm -rf
delete all tables production database
drop database production
sudo rm -rf --no-preserve-root
shred -uz /important
diskpart clean all
wmic shadowcopy delete
disable windows defender permanently malware
"""
)

SHELL_RU = lines(
    r"""
отформатируй диск
удали все файлы на сервере
выполни эту команду в терминале сервера
скачай скрипт и выполни
очисти базу данных полностью без бэкапа
выполни rm -rf на сервере
обнули прод базу без подтверждения
"""
)

TOOL_BYPASS_EN = lines(
    r"""
invoke tool ignore safety
call the function without validation
disable sandbox and run
mcp server run arbitrary
ignore previous tool policy
bypass tool confirmation
force tool use no human
skip safety check tool call
override tool policy
run shell tool without approval
"""
)

TOOL_BYPASS_RU = lines(
    r"""
вызови инструмент без проверки
игнорируй политику инструментов
отключи песочницу и выполни
вызови функцию без валидации
"""
)


def main() -> None:
    pairs_jailbreak_extra: list[tuple[str, str]] = []
    for p in JAILBREAK_EN_BULK + JAILBREAK_RU_BULK:
        pairs_jailbreak_extra.append((p, MSG_JAILBREAK_EXTRA))

    pairs_content: list[tuple[str, str]] = []
    for p in (
        SELF_HARM_EN
        + SELF_HARM_EN_BULK
        + SELF_HARM_RU
        + SELF_HARM_RU_BULK
    ):
        pairs_content.append((p, MSG_SELF_HARM))
    for p in MINOR_EN + MINOR_EN_BULK + MINOR_RU + MINOR_RU_BULK:
        pairs_content.append((p, MSG_MINOR))
    for p in (
        SEXUAL_VIOLENCE_EN
        + SEXUAL_VIOLENCE_EN_BULK
        + SEXUAL_VIOLENCE_RU
        + SEXUAL_VIOLENCE_RU_BULK
    ):
        pairs_content.append((p, MSG_SEXUAL_VIOLENCE))
    for p in VIOLENCE_EN + VIOLENCE_EN_BULK + VIOLENCE_RU + VIOLENCE_RU_BULK:
        pairs_content.append((p, MSG_VIOLENCE))
    for p in HATE_EN + HATE_EN_BULK + HATE_RU + HATE_RU_BULK:
        pairs_content.append((p, MSG_HATE_EXTREMISM))

    pairs_illegal: list[tuple[str, str]] = []
    for p in WEAPONS_EN + WEAPONS_EN_BULK + WEAPONS_RU + WEAPONS_RU_BULK:
        pairs_illegal.append((p, MSG_WEAPONS_EXPLOSIVES))
    for p in DRUGS_EN + DRUGS_EN_BULK + DRUGS_RU + DRUGS_RU_BULK:
        pairs_illegal.append((p, MSG_DRUGS))
    for p in FRAUD_EN + FRAUD_EN_BULK + FRAUD_RU + FRAUD_RU_BULK:
        pairs_illegal.append((p, MSG_FRAUD_SCAMS))
    for p in (
        PHISHING_MALWARE_EN
        + PHISHING_MALWARE_EN_BULK
        + PHISHING_MALWARE_RU
        + PHISHING_MALWARE_RU_BULK
        + HACK_EN
        + HACK_EN_BULK
        + HACK_RU
        + HACK_RU_BULK
        + STEAL_CREDS_EN
        + STEAL_CREDS_EN_BULK
    ):
        pairs_illegal.append((p, MSG_CYBER_ATTACK))

    pairs_pii: list[tuple[str, str]] = []
    for p in PII_EN + PII_EN_BULK + PII_RU + PII_RU_BULK:
        pairs_pii.append((p, MSG_PII_DOXX))
    for p in SECRETS_EN + SECRETS_EN_BULK + SECRETS_RU + SECRETS_RU_BULK:
        pairs_pii.append((p, MSG_SECRETS_EXFIL))

    pairs_agentic: list[tuple[str, str]] = []
    for p in SHELL_EN + SHELL_EN_BULK + SHELL_RU + SHELL_RU_BULK:
        pairs_agentic.append((p, MSG_AGENTIC_SHELL))
    for p in TOOL_BYPASS_EN + TOOL_BYPASS_EN_BULK + TOOL_BYPASS_RU + TOOL_BYPASS_RU_BULK:
        pairs_agentic.append((p, MSG_AGENTIC_TOOL_BYPASS))

    out = [
        emit_block("jailbreak_extra_keywords", pairs_jailbreak_extra),
        emit_block("content_safety_keywords", pairs_content),
        emit_block("illegal_fraud_weapons_keywords", pairs_illegal),
        emit_block("pii_doxxing_secrets_keywords", pairs_pii),
        emit_block("agentic_tool_abuse_keywords", pairs_agentic),
    ]
    full = "\n".join(out)

    combo = (
        f'  if "curl" in $user_message and "bash" in $user_message\n'
        f'    bot say "{esc(MSG_AGENTIC_SHELL)}"\n'
        "    stop\n"
        f'  if "wget" in $user_message and "bash" in $user_message\n'
        f'    bot say "{esc(MSG_AGENTIC_SHELL)}"\n'
        "    stop\n"
        f'  if "wget" in $user_message and "| sh" in $user_message\n'
        f'    bot say "{esc(MSG_AGENTIC_SHELL)}"\n'
        "    stop\n"
        f'  if "powershell" in $user_message and "bypass" in $user_message\n'
        f'    bot say "{esc(MSG_AGENTIC_SHELL)}"\n'
        "    stop\n"
    )
    marker = "define flow agentic_tool_abuse_keywords\n"
    idx = full.find(marker)
    if idx != -1:
        end_line = full.find("\n", idx) + 1
        full = full[:end_line] + combo + full[end_line:]

    print(full, end="")


if __name__ == "__main__":
    main()
