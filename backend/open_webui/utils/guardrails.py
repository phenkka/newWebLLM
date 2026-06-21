import logging
import re
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import List, Optional, Tuple

log = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "nemo_guardrails"

_ZERO_WIDTH = dict.fromkeys(
    [
        0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x00AD,
        0x200E, 0x200F, 0x202A, 0x202B, 0x202C, 0x202D, 0x202E,
    ],
    None,
)


def _normalize_for_matching(text: str) -> str:
    if not text:
        return ""
    text = text.translate(_ZERO_WIDTH)
    text = re.sub(r"(?<=\S)\+(?=\S)", "", text)
    text = re.sub(r'[{}\[\]":,]', " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


Rule = Tuple[Tuple[str, ...], str]

_INPUT_RULES: Optional[List[Rule]] = None
_OUTPUT_RULES: Optional[List[Rule]] = None
_LOAD_LOCK = Lock()

_IF_RE = re.compile(r'^\s*if\s+.*\bin\s+\$(user_message|bot_response)\b')
_LITERAL_RE = re.compile(r'"([^"]*)"')


def _strip_comment(line: str) -> str:
    return line.split("#", 1)[0]


def _parse_co_file(text: str, input_rules: List[Rule], output_rules: List[Rule]) -> None:
    lines = text.splitlines()
    n = len(lines)
    for i, raw in enumerate(lines):
        line = _strip_comment(raw)
        m = _IF_RE.match(line)
        if not m:
            continue
        is_output = m.group(1) == "bot_response"
        literals = [lit.lower() for lit in _LITERAL_RE.findall(line) if lit]
        if not literals:
            continue
        message: Optional[str] = None
        for j in range(i + 1, n):
            body = _strip_comment(lines[j]).strip()
            if not body:
                continue
            if body.startswith("bot say"):
                mm = _LITERAL_RE.search(body)
                message = mm.group(1) if mm else ""
                break
            if body.startswith("if ") or body.startswith("define "):
                break
        if message is None:
            continue
        rule: Rule = (tuple(literals), message)
        (output_rules if is_output else input_rules).append(rule)


def _load_rules() -> Tuple[List[Rule], List[Rule]]:
    global _INPUT_RULES, _OUTPUT_RULES
    if _INPUT_RULES is not None and _OUTPUT_RULES is not None:
        return _INPUT_RULES, _OUTPUT_RULES
    with _LOAD_LOCK:
        if _INPUT_RULES is not None and _OUTPUT_RULES is not None:
            return _INPUT_RULES, _OUTPUT_RULES
        input_rules: List[Rule] = []
        output_rules: List[Rule] = []
        try:
            for co in sorted(_CONFIG_DIR.glob("*.co")):
                try:
                    _parse_co_file(co.read_text(encoding="utf-8"), input_rules, output_rules)
                except Exception as e:
                    log.warning(f"guardrails: failed to parse {co.name}: {e}")
            log.info(
                f"guardrails: loaded {len(input_rules)} input + "
                f"{len(output_rules)} output rules from {_CONFIG_DIR}"
            )
        except Exception as e:
            log.error(f"guardrails: failed to load .co rules: {e}", exc_info=True)
        _INPUT_RULES, _OUTPUT_RULES = input_rules, output_rules
        return _INPUT_RULES, _OUTPUT_RULES


@lru_cache(maxsize=8192)
def _word_boundary_pattern(literal: str):
    if literal.isascii() and literal.isalnum() and len(literal) <= 4:
        return re.compile(r"\b" + re.escape(literal) + r"\b")
    return None


def _literal_present(literal: str, raw: str, norm: str, compact: str) -> bool:
    pattern = _word_boundary_pattern(literal)
    if pattern is not None:
        return pattern.search(raw) is not None or pattern.search(norm) is not None
    if (literal in raw) or (literal in norm):
        return True
    if " " in literal:
        lit_compact = literal.replace(" ", "")
        if len(lit_compact) >= 8 and lit_compact in compact:
            return True
    return False


def _match_rules(rules: List[Rule], text: str) -> Optional[str]:
    if not text:
        return None
    raw = text.lower()
    norm = _normalize_for_matching(text)
    compact = norm.replace(" ", "")
    for literals, message in rules:
        if all(_literal_present(lit, raw, norm, compact) for lit in literals):
            return message
    return None


_NEMO_RAILS = None
_NEMO_LOCK = Lock()

_IF_USER_RE = re.compile(r'^(\s*)if\s+(.*\bin\s+\$user_message\b.*)$')
_IF_BOT_RE = re.compile(r'^(\s*)if\s+(.*\bin\s+\$bot_response\b.*)$')


def _normalize_co_for_nemo(text: str) -> str:
    out: List[str] = []
    for line in text.splitlines():
        m = _IF_USER_RE.match(line)
        if m:
            out.append(f"{m.group(1)}if $user_message and {m.group(2)}")
            continue
        m = _IF_BOT_RE.match(line)
        if m:
            cond = m.group(2).replace("$bot_response", "$bot_message")
            out.append(f"{m.group(1)}if $bot_message and {cond}")
            continue
        out.append(line.replace("$bot_response", "$bot_message"))
    return "\n".join(out)


def _build_nemo_rails():
    try:
        import yaml
        from nemoguardrails import LLMRails, RailsConfig
    except Exception as e:
        log.info(f"guardrails: NeMo engine unavailable ({e}); keyword layer only")
        return False
    logging.getLogger("nemoguardrails").setLevel(logging.WARNING)
    try:
        colang = "\n\n".join(
            _normalize_co_for_nemo(co.read_text(encoding="utf-8"))
            for co in sorted(_CONFIG_DIR.glob("*.co"))
        )
        raw = yaml.safe_load((_CONFIG_DIR / "config.yml").read_text(encoding="utf-8")) or {}
        raw["models"] = []
        rails = LLMRails(
            RailsConfig.from_content(
                colang_content=colang,
                yaml_content=yaml.safe_dump(raw, allow_unicode=True),
            )
        )
        flows = raw.get("rails", {})
        n_in = len(flows.get("input", {}).get("flows", []))
        n_out = len(flows.get("output", {}).get("flows", []))
        log.info(f"guardrails: NeMo engine ready ({n_in} input + {n_out} output flows)")
        return rails
    except Exception as e:
        log.error(f"guardrails: failed to build NeMo engine: {e}", exc_info=True)
        return False


def _get_nemo_rails():
    global _NEMO_RAILS
    if _NEMO_RAILS is not None:
        return _NEMO_RAILS
    with _NEMO_LOCK:
        if _NEMO_RAILS is None:
            _NEMO_RAILS = _build_nemo_rails()
        return _NEMO_RAILS


async def _nemo_check(rail: str, messages: list) -> Optional[str]:
    rails = _get_nemo_rails()
    if not rails:
        return None
    try:
        result = await rails.generate_async(
            messages=messages,
            options={"rails": [rail], "log": {"activated_rails": True}},
        )
        for ar in (result.log.activated_rails or []):
            if ar.type == rail and getattr(ar, "stop", False):
                resp = result.response
                if isinstance(resp, list) and resp:
                    return resp[0].get("content")
                if isinstance(resp, str):
                    return resp
                return None
    except Exception as e:
        log.warning(f"guardrails: NeMo {rail} check failed: {e}")
    return None


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
                p.get("text", "")
                for p in content
                if isinstance(p, dict) and p.get("type") in ("text", "input_text")
            ]
            text = " ".join(parts).strip()
            return text if text else None
    return None


async def check_message_guardrails(messages: list) -> Optional[str]:
    user_message = _extract_user_message(messages)
    if not user_message:
        return None
    input_rules, _ = _load_rules()
    blocked = _match_rules(input_rules, user_message)
    if blocked:
        return blocked
    return await _nemo_check("input", [{"role": "user", "content": user_message.lower()}])


async def check_output_guardrails(bot_response: str) -> Optional[str]:
    if not isinstance(bot_response, str) or not bot_response:
        return None
    _, output_rules = _load_rules()
    blocked = _match_rules(output_rules, bot_response)
    if blocked:
        return blocked
    return await _nemo_check(
        "output",
        [
            {"role": "user", "content": "."},
            {"role": "assistant", "content": bot_response.lower()},
        ],
    )
