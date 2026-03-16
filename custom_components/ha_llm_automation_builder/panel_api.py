"""HTTP API and simple sidebar panel for LLM automation workflows."""

from __future__ import annotations

from typing import Any
from dataclasses import asdict

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .automation_manager import async_get_automation, async_list_automations
from .const import DOMAIN

_API_FLAG = f"{DOMAIN}_api_registered"
_PANEL_PATH = "llm-automation-builder"


def _find_runtime(hass: HomeAssistant):
    entries = list(hass.data.get(DOMAIN, {}).values())
    return entries[0] if entries else None


async def _call_service(hass: HomeAssistant, service: str, data: dict[str, Any]) -> Any:
    try:
        return await hass.services.async_call(
            DOMAIN,
            service,
            data,
            blocking=True,
            return_response=True,
        )
    except TypeError:
        await hass.services.async_call(DOMAIN, service, data, blocking=True)
        runtime = _find_runtime(hass)
        return runtime.last_result if runtime else {}
    except Exception as err:  # broad by design for API boundary
        return {"ok": False, "error": str(err)}


class _BaseApiView(HomeAssistantView):
    requires_auth = True

    def _runtime_or_400(self, hass: HomeAssistant):
        runtime = _find_runtime(hass)
        if runtime is None:
            raise web.HTTPBadRequest(reason="Integration runtime is not loaded.")
        return runtime


class GenerateView(_BaseApiView):
    url = "/api/llm_automation/generate"
    name = "api:llm_automation:generate"

    async def post(self, request: web.Request) -> web.Response:
        payload = await request.json()
        response = await _call_service(
            request.app["hass"],
            "generate_automation",
            {
                "description": payload.get("prompt", payload.get("description", "")),
                "entity_hints": payload.get("entity_hints", []),
                "template": payload.get("template"),
                "style": payload.get("style", "readable"),
                "model": payload.get("model"),
                "temperature": payload.get("temperature"),
                "top_p": payload.get("top_p"),
                "max_tokens": payload.get("max_tokens"),
            },
        )
        return web.json_response(response)


class ValidateView(_BaseApiView):
    url = "/api/llm_automation/validate"
    name = "api:llm_automation:validate"

    async def post(self, request: web.Request) -> web.Response:
        payload = await request.json()
        response = await _call_service(
            request.app["hass"],
            "validate_automation_yaml",
            {"yaml": payload.get("yaml", "")},
        )
        return web.json_response(response)


class ImproveView(_BaseApiView):
    url = "/api/llm_automation/improve"
    name = "api:llm_automation:improve"

    async def post(self, request: web.Request) -> web.Response:
        payload = await request.json()
        response = await _call_service(
            request.app["hass"],
            "improve_automation",
            {
                "description": payload.get("prompt", payload.get("description", "")),
                "yaml": payload.get("yaml", ""),
            },
        )
        return web.json_response(response)


class HistoryView(_BaseApiView):
    url = "/api/llm_automation/history"
    name = "api:llm_automation:history"

    async def get(self, request: web.Request) -> web.Response:
        runtime = self._runtime_or_400(request.app["hass"])
        items = await runtime.history_store.async_load()
        return web.json_response({"items": [asdict(item) for item in items]})


class CreateView(_BaseApiView):
    url = "/api/llm_automation/create"
    name = "api:llm_automation:create"

    async def post(self, request: web.Request) -> web.Response:
        payload = await request.json()
        response = await _call_service(
            request.app["hass"],
            "create_automation_from_yaml",
            {"yaml": payload.get("yaml", ""), "enabled": bool(payload.get("enabled", False))},
        )
        return web.json_response(response)


class CreateAndEnableView(_BaseApiView):
    url = "/api/llm_automation/create_and_enable"
    name = "api:llm_automation:create_and_enable"

    async def post(self, request: web.Request) -> web.Response:
        payload = await request.json()
        response = await _call_service(
            request.app["hass"],
            "create_and_enable_automation_from_yaml",
            {"yaml": payload.get("yaml", "")},
        )
        return web.json_response(response)


class ModifyView(_BaseApiView):
    url = "/api/llm_automation/modify"
    name = "api:llm_automation:modify"

    async def post(self, request: web.Request) -> web.Response:
        payload = await request.json()
        response = await _call_service(
            request.app["hass"],
            "modify_automation_with_ollama",
            {
                "target": payload.get("target", ""),
                "description": payload.get("prompt", payload.get("description", "")),
                "entity_hints": payload.get("entity_hints", []),
                "model": payload.get("model"),
                "temperature": payload.get("temperature"),
                "top_p": payload.get("top_p"),
                "max_tokens": payload.get("max_tokens"),
                "create_mode": payload.get("create_mode", "overwrite"),
                "apply_changes": bool(payload.get("apply_changes", False)),
                "enable": bool(payload.get("enable", False)),
            },
        )
        return web.json_response(response)


class OverwriteExistingView(_BaseApiView):
    url = "/api/llm_automation/overwrite_existing"
    name = "api:llm_automation:overwrite_existing"

    async def post(self, request: web.Request) -> web.Response:
        payload = await request.json()
        response = await _call_service(
            request.app["hass"],
            "overwrite_automation_from_yaml",
            {
                "target": payload.get("target", ""),
                "yaml": payload.get("yaml", ""),
                "enabled": payload.get("enabled"),
            },
        )
        return web.json_response(response)


class ListAutomationsView(_BaseApiView):
    url = "/api/llm_automation/list_automations"
    name = "api:llm_automation:list_automations"

    async def get(self, request: web.Request) -> web.Response:
        items = await async_list_automations(request.app["hass"])
        return web.json_response({"items": items})


class GetAutomationView(_BaseApiView):
    url = "/api/llm_automation/get_automation"
    name = "api:llm_automation:get_automation"

    async def post(self, request: web.Request) -> web.Response:
        payload = await request.json()
        target = payload.get("target", "")
        item = await async_get_automation(request.app["hass"], target)
        return web.json_response({"ok": item is not None, "item": item, "target": target})

    async def get(self, request: web.Request) -> web.Response:
        target = request.query.get("target", "")
        item = await async_get_automation(request.app["hass"], target)
        return web.json_response({"ok": item is not None, "item": item, "target": target})


class ListModelsView(_BaseApiView):
    url = "/api/llm_automation/models"
    name = "api:llm_automation:models"

    async def get(self, request: web.Request) -> web.Response:
        response = await _call_service(request.app["hass"], "list_available_models", {})
        return web.json_response(response)


class PanelView(_BaseApiView):
    url = "/api/llm_automation/panel"
    name = "api:llm_automation:panel"

    async def get(self, request: web.Request) -> web.Response:
        html = _PANEL_HTML
        return web.Response(text=html, content_type="text/html")


async def async_register_panel_api(hass: HomeAssistant) -> None:
    if hass.data.get(_API_FLAG):
        return

    hass.http.register_view(GenerateView)
    hass.http.register_view(ValidateView)
    hass.http.register_view(ImproveView)
    hass.http.register_view(HistoryView)
    hass.http.register_view(CreateView)
    hass.http.register_view(CreateAndEnableView)
    hass.http.register_view(ModifyView)
    hass.http.register_view(OverwriteExistingView)
    hass.http.register_view(ListAutomationsView)
    hass.http.register_view(GetAutomationView)
    hass.http.register_view(ListModelsView)
    hass.http.register_view(PanelView)

    frontend = getattr(hass.components, "frontend", None)
    if frontend is not None:
        frontend.async_register_built_in_panel(
            component_name="iframe",
            sidebar_title="LLM Automation",
            sidebar_icon="mdi:robot",
            frontend_url_path=_PANEL_PATH,
            config={"url": "/api/llm_automation/panel"},
            require_admin=False,
        )

    hass.data[_API_FLAG] = True


_PANEL_HTML = """<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>LLM Automation Panel</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; padding: 16px; background: #f4f6f8; color: #1b1f23; }
    h1, h2 { margin: 0 0 8px; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .card { background: #fff; border-radius: 10px; padding: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
    textarea, input, select { width: 100%; padding: 8px; border: 1px solid #c7ccd1; border-radius: 8px; box-sizing: border-box; }
    textarea { min-height: 120px; resize: vertical; }
    .row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
    .btns { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
    button { border: 0; border-radius: 8px; padding: 8px 12px; background: #0b5fff; color: #fff; cursor: pointer; }
    button.secondary { background: #5b6470; }
    pre { background: #0f1720; color: #d4e0ee; padding: 10px; border-radius: 8px; white-space: pre-wrap; }
    @media (max-width: 960px) { .grid { grid-template-columns: 1fr; } .row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <h1>LLM Automation Panel</h1>
  <div class="grid">
    <div class="card">
      <h2>Prompt</h2>
      <textarea id="prompt" placeholder="Describe automation or modification..."></textarea>
      <div class="row" style="margin-top:8px">
        <div><label>Model</label><select id="model"></select></div>
        <div><label>Temperature</label><input id="temperature" type="number" step="0.1" value="0.2"/></div>
        <div><label>Top P</label><input id="top_p" type="number" step="0.05" value="0.9"/></div>
      </div>
      <div class="row" style="margin-top:8px">
        <div><label>Max tokens</label><input id="max_tokens" type="number" value="1200"/></div>
        <div><label>Entity hints (comma)</label><input id="entity_hints" type="text" placeholder="light.kitchen, sensor.temp"/></div>
        <div><label>Existing automation</label><select id="automation_select"></select></div>
      </div>
      <div class="btns">
        <button id="generate_btn">Generate</button>
        <button id="validate_btn" class="secondary">Validate</button>
        <button id="improve_btn" class="secondary">Improve</button>
        <button id="modify_btn">Modify with Ollama</button>
        <button id="copy_btn" class="secondary">Copy YAML</button>
      </div>
      <div class="btns">
        <button id="save_btn" class="secondary">Save automation</button>
        <button id="add_btn">Add to Home Assistant</button>
        <button id="enable_btn">Create and enable automation</button>
        <button id="overwrite_btn" class="secondary">Overwrite existing</button>
      </div>
    </div>
    <div class="card">
      <h2>Result</h2>
      <label>YAML</label>
      <textarea id="yaml_out" style="min-height:220px"></textarea>
      <label>Explanation</label>
      <pre id="explanation_out"></pre>
      <label>Warnings</label>
      <pre id="warnings_out"></pre>
      <label>Diff summary</label>
      <pre id="diff_out"></pre>
    </div>
  </div>
  <div class="card" style="margin-top:12px">
    <h2>History</h2>
    <pre id="history_out"></pre>
  </div>
<script>
const byId = (id) => document.getElementById(id);
const toHints = () => byId('entity_hints').value.split(',').map(s => s.trim()).filter(Boolean);

async function api(path, method='GET', payload=null) {
  const res = await fetch(path, {
    method,
    headers: {'Content-Type': 'application/json'},
    body: payload ? JSON.stringify(payload) : null,
    credentials: 'same-origin'
  });
  return await res.json();
}

async function refreshModels() {
  const data = await api('/api/llm_automation/models');
  const models = data.models || [];
  byId('model').innerHTML = models.map(m => `<option value="${m}">${m}</option>`).join('');
}

async function refreshAutomations() {
  const data = await api('/api/llm_automation/list_automations');
  const items = data.items || [];
  byId('automation_select').innerHTML = items.map(i => `<option value="${i.id || i.alias || ''}">${i.alias || i.id || '-'}</option>`).join('');
}

async function loadSelectedAutomation() {
  const target = byId('automation_select').value;
  if (!target) return;
  const data = await api('/api/llm_automation/get_automation', 'POST', {target});
  if (data.ok && data.item) {
    byId('yaml_out').value = data.item.yaml || '';
  }
}

async function refreshHistory() {
  const data = await api('/api/llm_automation/history');
  const items = data.items || [];
  byId('history_out').textContent = items.slice(-20).map(i => `${i.timestamp} | ${i.model} | ${i.prompt} | status:${i.create_status || '-'} | id:${i.created_automation_id || '-'}`).join('\\n');
}

function setResult(data) {
  if (data.yaml) byId('yaml_out').value = data.yaml;
  if (data.improved_yaml) byId('yaml_out').value = data.improved_yaml;
  byId('explanation_out').textContent = data.explanation || JSON.stringify(data.metadata || {}, null, 2);
  byId('warnings_out').textContent = (data.warnings || data.validation?.warnings || []).join('\\n') || '-';
  byId('diff_out').textContent = data.diff_summary || (data.apply_result ? JSON.stringify(data.apply_result, null, 2) : '-');
}

byId('generate_btn').onclick = async () => {
  const data = await api('/api/llm_automation/generate', 'POST', {
    prompt: byId('prompt').value,
    model: byId('model').value,
    temperature: Number(byId('temperature').value),
    top_p: Number(byId('top_p').value),
    max_tokens: Number(byId('max_tokens').value),
    entity_hints: toHints()
  });
  setResult(data); await refreshHistory();
};

byId('validate_btn').onclick = async () => {
  const data = await api('/api/llm_automation/validate', 'POST', {yaml: byId('yaml_out').value});
  setResult({warnings: data.warnings || [], explanation: JSON.stringify(data, null, 2)});
};

byId('improve_btn').onclick = async () => {
  const data = await api('/api/llm_automation/improve', 'POST', {
    prompt: byId('prompt').value,
    yaml: byId('yaml_out').value
  });
  setResult(data);
};

byId('modify_btn').onclick = async () => {
  const target = byId('automation_select').value;
  const data = await api('/api/llm_automation/modify', 'POST', {
    target,
    prompt: byId('prompt').value,
    model: byId('model').value,
    temperature: Number(byId('temperature').value),
    top_p: Number(byId('top_p').value),
    max_tokens: Number(byId('max_tokens').value),
    entity_hints: toHints(),
    create_mode: 'overwrite',
    apply_changes: false
  });
  setResult(data); await refreshHistory();
};

byId('save_btn').onclick = async () => {
  const blob = new Blob([byId('yaml_out').value], {type: 'text/yaml'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'automation.yaml';
  a.click();
};

byId('add_btn').onclick = async () => {
  const data = await api('/api/llm_automation/create', 'POST', {yaml: byId('yaml_out').value, enabled: false});
  setResult({explanation: JSON.stringify(data, null, 2), warnings: data.warnings || []});
  await refreshAutomations(); await refreshHistory();
};

byId('enable_btn').onclick = async () => {
  const data = await api('/api/llm_automation/create_and_enable', 'POST', {yaml: byId('yaml_out').value});
  setResult({explanation: JSON.stringify(data, null, 2), warnings: data.warnings || []});
  await refreshAutomations(); await refreshHistory();
};

byId('overwrite_btn').onclick = async () => {
  const target = byId('automation_select').value;
  const data = await api('/api/llm_automation/overwrite_existing', 'POST', {target, yaml: byId('yaml_out').value});
  setResult({explanation: JSON.stringify(data, null, 2), warnings: data.warnings || []});
  await refreshAutomations(); await refreshHistory();
};

byId('copy_btn').onclick = async () => {
  await navigator.clipboard.writeText(byId('yaml_out').value || '');
};

byId('automation_select').onchange = async () => { await loadSelectedAutomation(); };

(async function init() { await refreshModels(); await refreshAutomations(); await loadSelectedAutomation(); await refreshHistory(); })();
</script>
</body>
</html>
"""
