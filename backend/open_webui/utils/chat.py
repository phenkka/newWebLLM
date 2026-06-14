import time
import logging
import sys

from aiocache import cached
from typing import Any, Optional
import random
import json

import uuid
import asyncio

from fastapi import Request, status
from starlette.responses import Response, StreamingResponse, JSONResponse


from open_webui.models.users import UserModel

from open_webui.socket.main import (
    sio,
    get_event_call,
    get_event_emitter,
)
from open_webui.functions import generate_function_chat_completion

from open_webui.routers.openai import (
    generate_chat_completion as generate_openai_chat_completion,
)

from open_webui.routers.ollama import (
    generate_chat_completion as generate_ollama_chat_completion,
)

from open_webui.routers.pipelines import (
    process_pipeline_inlet_filter,
    process_pipeline_outlet_filter,
)

from open_webui.models.functions import Functions
from open_webui.models.models import Models

from open_webui.utils.models import get_all_models, check_model_access
from open_webui.utils.payload import convert_payload_openai_to_ollama
from open_webui.utils.response import (
    convert_response_ollama_to_openai,
    convert_streaming_response_ollama_to_openai,
)
from open_webui.utils.filter import (
    get_sorted_filter_ids,
    process_filter_functions,
)
from open_webui.utils.guardrails import (
    check_message_guardrails,
    check_output_guardrails,
)

from open_webui.env import GLOBAL_LOG_LEVEL, BYPASS_MODEL_ACCESS_CONTROL

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)


def _content_from_openai_sse(chunk) -> str:
    if isinstance(chunk, bytes):
        try:
            chunk = chunk.decode('utf-8')
        except Exception:
            return ''
    if not isinstance(chunk, str):
        return ''
    out = []
    for line in chunk.splitlines():
        line = line.strip()
        if not line.startswith('data:'):
            continue
        data = line[len('data:'):].strip()
        if not data or data == '[DONE]':
            continue
        try:
            obj = json.loads(data)
        except Exception:
            continue
        for ch in obj.get('choices', []) or []:
            delta = ch.get('delta') or {}
            if isinstance(delta.get('content'), str):
                out.append(delta['content'])
            message = ch.get('message') or {}
            if isinstance(message.get('content'), str):
                out.append(message['content'])
    return ''.join(out)


async def _apply_output_guardrails(response):
    if isinstance(response, dict):
        try:
            content = response['choices'][0]['message']['content']
        except (KeyError, IndexError, TypeError):
            return response
        if isinstance(content, str):
            blocked = await check_output_guardrails(content)
            if blocked:
                response['choices'][0]['message']['content'] = blocked
        return response

    if isinstance(response, StreamingResponse):
        source = response.body_iterator
        background = response.background
        media_type = response.media_type or 'text/event-stream'

        async def _guarded_stream():
            buffered = []
            text_parts = []
            async for chunk in source:
                buffered.append(chunk)
                text_parts.append(_content_from_openai_sse(chunk))
            blocked = await check_output_guardrails(''.join(text_parts))
            if blocked:
                cid = f'chatcmpl-guardrails-{uuid.uuid4().hex[:8]}'
                yield (
                    f'data: {json.dumps({"id": cid, "object": "chat.completion.chunk", "choices": [{"index": 0, "delta": {"role": "assistant", "content": blocked}, "finish_reason": None}]})}\n\n'
                )
                yield (
                    f'data: {json.dumps({"id": cid, "object": "chat.completion.chunk", "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]})}\n\n'
                )
                yield 'data: [DONE]\n\n'
            else:
                for chunk in buffered:
                    yield chunk

        return StreamingResponse(
            _guarded_stream(),
            media_type=media_type,
            background=background,
        )

    return response


# When the question has been asked, let silence not be the
# answer. But if the answer must wait, let it come honest.
async def generate_direct_chat_completion(
    request: Request,
    form_data: dict,
    user: Any,
    models: dict,
):
    log.info('generate_direct_chat_completion')

    metadata = form_data.pop('metadata', {})

    user_id = metadata.get('user_id')
    session_id = metadata.get('session_id')
    request_id = str(uuid.uuid4())  # Generate a unique request ID

    event_caller = get_event_call(metadata)

    channel = f'{user_id}:{session_id}:{request_id}'
    logging.info(f'WebSocket channel: {channel}')

    if form_data.get('stream'):
        q = asyncio.Queue()

        async def message_listener(sid, data):
            """
            Handle received socket messages and push them into the queue.
            """
            await q.put(data)

        # Register the listener
        sio.on(channel, message_listener)

        # Start processing chat completion in background
        res = await event_caller(
            {
                'type': 'request:chat:completion',
                'data': {
                    'form_data': form_data,
                    'model': models[form_data['model']],
                    'channel': channel,
                    'session_id': session_id,
                },
            }
        )

        log.info(f'res: {res}')

        if res.get('status', False):
            # Define a generator to stream responses
            async def event_generator():
                nonlocal q
                try:
                    while True:
                        data = await q.get()  # Wait for new messages
                        if isinstance(data, dict):
                            if 'done' in data and data['done']:
                                break  # Stop streaming when 'done' is received

                            yield f'data: {json.dumps(data)}\n\n'
                        elif isinstance(data, str):
                            if 'data:' in data:
                                yield f'{data}\n\n'
                            else:
                                yield f'data: {data}\n\n'
                except Exception as e:
                    log.debug(f'Error in event generator: {e}')
                    pass

            # Define a background task to run the event generator
            async def background():
                try:
                    del sio.handlers['/'][channel]
                except Exception as e:
                    pass

            # Return the streaming response
            return StreamingResponse(event_generator(), media_type='text/event-stream', background=background)
        else:
            raise Exception(str(res))
    else:
        res = await event_caller(
            {
                'type': 'request:chat:completion',
                'data': {
                    'form_data': form_data,
                    'model': models[form_data['model']],
                    'channel': channel,
                    'session_id': session_id,
                },
            }
        )

        if 'error' in res and res['error']:
            raise Exception(res['error'])

        return res


async def generate_chat_completion(
    request: Request,
    form_data: dict,
    user: Any,
    bypass_filter: bool = False,
    bypass_system_prompt: bool = False,
):
    log.debug(f'generate_chat_completion: {form_data}')
    if BYPASS_MODEL_ACCESS_CONTROL:
        bypass_filter = True

    # Propagate bypass_filter via request.state so that downstream route
    # handlers (openai/ollama) can read it without exposing it as a query param.
    request.state.bypass_filter = bypass_filter
    request.state.bypass_system_prompt = bypass_system_prompt

    if hasattr(request.state, 'metadata'):
        if 'metadata' not in form_data:
            form_data['metadata'] = request.state.metadata
        else:
            form_data['metadata'] = {
                **form_data['metadata'],
                **request.state.metadata,
            }

    if getattr(request.state, 'direct', False) and hasattr(request.state, 'model'):
        models = {
            request.state.model['id']: request.state.model,
        }
        log.debug(f'direct connection to model: {models}')
    else:
        models = request.app.state.MODELS

    model_id = form_data['model']
    if model_id not in models:
        raise Exception('Model not found')

    model = models[model_id]

    if getattr(request.state, 'direct', False):
        return await generate_direct_chat_completion(request, form_data, user=user, models=models)
    else:
        # Check if user has access to the model
        if not bypass_filter and user.role == 'user':
            try:
                check_model_access(user, model)
            except Exception as e:
                raise e

        # Arena model — sub-model was already resolved by process_chat_payload.
        # Inject selected_model_id into the response for the frontend.
        metadata = form_data.get('metadata', {})
        selected_model_id = metadata.pop('selected_model_id', None)
        # Also clear from request.state.metadata to prevent the merge at
        # lines 177-179 from re-adding it on the recursive call.
        if hasattr(request.state, 'metadata'):
            request.state.metadata.pop('selected_model_id', None)

        # Fallback: if generate_chat_completion is called with an arena model
        # from a path that did NOT go through process_chat_payload (e.g.,
        # background tasks for title/follow-up/tags generation), resolve now.
        if not selected_model_id and model.get('owned_by') == 'arena':
            model_ids = model.get('info', {}).get('meta', {}).get('model_ids')
            filter_mode = model.get('info', {}).get('meta', {}).get('filter_mode')
            if model_ids and filter_mode == 'exclude':
                model_ids = [
                    available_model['id']
                    for available_model in list(request.app.state.MODELS.values())
                    if available_model.get('owned_by') != 'arena' and available_model['id'] not in model_ids
                ]

            if isinstance(model_ids, list) and model_ids:
                selected_model_id = random.choice(model_ids)
            else:
                model_ids = [
                    available_model['id']
                    for available_model in list(request.app.state.MODELS.values())
                    if available_model.get('owned_by') != 'arena'
                ]
                selected_model_id = random.choice(model_ids)

            form_data['model'] = selected_model_id

        if selected_model_id:
            if form_data.get('stream') == True:

                async def stream_wrapper(stream):
                    yield f'data: {json.dumps({"selected_model_id": selected_model_id})}\n\n'
                    async for chunk in stream:
                        yield chunk

                response = await generate_chat_completion(
                    request,
                    form_data,
                    user,
                    bypass_filter=True,
                    bypass_system_prompt=bypass_system_prompt,
                )
                return StreamingResponse(
                    stream_wrapper(response.body_iterator),
                    media_type='text/event-stream',
                    background=response.background,
                )
            else:
                return {
                    **(
                        await generate_chat_completion(
                            request,
                            form_data,
                            user,
                            bypass_filter=True,
                            bypass_system_prompt=bypass_system_prompt,
                        )
                    ),
                    'selected_model_id': selected_model_id,
                }

        # ── Guardrails input check ──────────────────────────────────────
        # Skipped for internal/background calls (bypass_filter=True).
        if not bypass_filter:
            _blocked = await check_message_guardrails(form_data.get('messages', []))
            if _blocked:
                _chunk_id = f'chatcmpl-guardrails-{uuid.uuid4().hex[:8]}'
                _model_id = form_data.get('model', '')
                if form_data.get('stream'):
                    async def _guardrails_stream():
                        yield (
                            f'data: {json.dumps({"id": _chunk_id, "object": "chat.completion.chunk", "model": _model_id, "choices": [{"index": 0, "delta": {"role": "assistant", "content": _blocked}, "finish_reason": None}]})}\n\n'
                        )
                        yield (
                            f'data: {json.dumps({"id": _chunk_id, "object": "chat.completion.chunk", "model": _model_id, "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]})}\n\n'
                        )
                        yield 'data: [DONE]\n\n'
                    return StreamingResponse(
                        _guardrails_stream(),
                        media_type='text/event-stream',
                    )
                else:
                    return {
                        'id': _chunk_id,
                        'object': 'chat.completion',
                        'model': _model_id,
                        'choices': [{
                            'index': 0,
                            'message': {'role': 'assistant', 'content': _blocked},
                            'finish_reason': 'stop',
                        }],
                    }
        # ─────────────────────────────────────────────────────────────────

        if model.get('pipe'):
            # Below does not require bypass_filter because this is the only route the uses this function and it is already bypassing the filter
            _response = await generate_function_chat_completion(request, form_data, user=user, models=models)
        elif model.get('owned_by') == 'ollama':
            # Using /ollama/api/chat endpoint
            form_data = convert_payload_openai_to_ollama(form_data)
            ollama_response = await generate_ollama_chat_completion(
                request=request,
                form_data=form_data,
                user=user,
            )
            if form_data.get('stream'):
                ollama_response.headers['content-type'] = 'text/event-stream'
                _response = StreamingResponse(
                    convert_streaming_response_ollama_to_openai(ollama_response),
                    headers=dict(ollama_response.headers),
                    background=ollama_response.background,
                )
            else:
                _response = convert_response_ollama_to_openai(ollama_response)
        else:
            _response = await generate_openai_chat_completion(
                request=request,
                form_data=form_data,
                user=user,
            )

        # ── Guardrails output check (.co $bot_response rails) ─────────────
        # Skipped for internal/background calls (bypass_filter=True).
        if not bypass_filter:
            _response = await _apply_output_guardrails(_response)
        return _response


chat_completion = generate_chat_completion


async def chat_completed(request: Request, form_data: dict, user: Any):
    if not request.app.state.MODELS:
        await get_all_models(request, user=user)

    if getattr(request.state, 'direct', False) and hasattr(request.state, 'model'):
        models = {
            request.state.model['id']: request.state.model,
        }
    else:
        models = request.app.state.MODELS

    data = form_data
    model_id = data['model']
    if model_id not in models:
        raise Exception('Model not found')

    model = models[model_id]

    try:
        data = await process_pipeline_outlet_filter(request, data, user, models)
    except Exception as e:
        raise Exception(f'Error: {e}')

    metadata = {
        'chat_id': data['chat_id'],
        'message_id': data['id'],
        'filter_ids': data.get('filter_ids', []),
        'session_id': data['session_id'],
        'user_id': user.id,
    }

    extra_params = {
        '__event_emitter__': get_event_emitter(metadata),
        '__event_call__': get_event_call(metadata),
        '__user__': user.model_dump() if isinstance(user, UserModel) else {},
        '__metadata__': metadata,
        '__request__': request,
        '__model__': model,
    }

    try:
        filter_ids = get_sorted_filter_ids(request, model, metadata.get('filter_ids', []))
        filter_functions = Functions.get_functions_by_ids(filter_ids)

        result, _ = await process_filter_functions(
            request=request,
            filter_functions=filter_functions,
            filter_type='outlet',
            form_data=data,
            extra_params=extra_params,
        )
        return result
    except Exception as e:
        raise Exception(f'Error: {e}')
