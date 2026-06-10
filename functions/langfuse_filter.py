import os
import time
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

try:
    from langfuse import Langfuse
except Exception:
    Langfuse = None


class Filter:
    class Valves(BaseModel):
        public_key: str = Field(default=os.getenv("LANGFUSE_PUBLIC_KEY", ""))
        secret_key: str = Field(default=os.getenv("LANGFUSE_SECRET_KEY", ""))
        host: str = Field(default=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"))

    def __init__(self):
        self.valves = self.Valves()
        self.langfuse = None
        self._starts: dict = {}
        self._init_langfuse()

    def _init_langfuse(self):
        if Langfuse is None:
            return
        if not (self.valves.public_key and self.valves.secret_key):
            print("[langfuse_filter] keys not set - tracing disabled")
            return
        try:
            self.langfuse = Langfuse(
                public_key=self.valves.public_key,
                secret_key=self.valves.secret_key,
                host=self.valves.host,
            )
            print(f"[langfuse_filter] connected to {self.valves.host}")
        except Exception as e:
            print(f"[langfuse_filter] init error: {e}")
            self.langfuse = None

    def _key(self, meta: dict) -> str:
        return meta.get("message_id") or meta.get("chat_id") or "default"

    async def inlet(
        self,
        body: dict,
        __user__: Optional[dict] = None,
        __metadata__: Optional[dict] = None,
    ) -> dict:
        self._starts[self._key(__metadata__ or {})] = time.time()
        return body

    async def outlet(
        self,
        body: dict,
        __user__: Optional[dict] = None,
        __metadata__: Optional[dict] = None,
    ) -> dict:
        if self.langfuse is None:
            self._init_langfuse()
            if self.langfuse is None:
                return body

        meta = __metadata__ or {}
        user = __user__ or {}
        messages = body.get("messages", []) or []
        if not messages:
            return body

        last = messages[-1] if isinstance(messages[-1], dict) else {}
        output_text = last.get("content", "") if last.get("role") == "assistant" else ""
        input_messages = messages[:-1] if output_text else messages

        model = body.get("model") or meta.get("model") or "unknown"
        chat_id = meta.get("chat_id")
        user_id = user.get("email") or user.get("id")
        key = self._key(meta)
        start = self._starts.pop(key, None)
        start_dt = datetime.fromtimestamp(start, tz=timezone.utc) if start else None
        end_dt = datetime.now(tz=timezone.utc)

        try:
            trace = self.langfuse.trace(
                name="open-webui-chat",
                user_id=user_id,
                session_id=chat_id,
                input=input_messages,
                output=output_text,
                metadata={"model": model, "chat_id": chat_id},
                tags=["open-webui"],
            )
            trace.generation(
                name="chat-completion",
                model=model,
                input=input_messages,
                output=output_text,
                start_time=start_dt,
                end_time=end_dt,
                usage=body.get("usage"),
            )
            self.langfuse.flush()
        except Exception as e:
            print(f"[langfuse_filter] trace error: {e}")

        return body
