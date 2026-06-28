"""
Клиент прямого API SBP (api.sbp.business) для Ресто (Like at Home).

Все запросы POST, авторизация одинаковая - три заголовка:
  Content-Type: application/json
  x-api-key: <ключ терминала>
  Authorization: Basic base64("<login>:<terminal_key>")

  z1.php -> {"url_pay","qr","id_order_glob","Status",...}  ссылка на рублёвую оплату
  st.php -> {"id_order","st":"CONFIRMED"}                  статус операции

Наши заявки помечаются префиксом LAH{order_id}SBP, чтобы не пересекаться с
кошельком (VKP) и P1 (BORD). Креды ТОЛЬКО из окружения, в коде/логах их нет.
"""
import base64
import json

import requests

from .config import (
    SBP_BASE,
    SBP_LOGIN,
    SBP_PASSWORD,
    SBP_API_KEY,
    SBP_ORDER_PREFIX,
    SBP_ORDER_SUFFIX,
)


def configured() -> bool:
    return bool(SBP_LOGIN and SBP_PASSWORD and SBP_API_KEY)


def order_id_for(order_id) -> str:
    """LAH{order_id}SBP для нашего заказа."""
    return f"{SBP_ORDER_PREFIX}{order_id}{SBP_ORDER_SUFFIX}"


def parse_order_id(id_order: str):
    """LAH{order_id}SBP -> order_id (строка UUID) или None, если не наш формат."""
    if not id_order:
        return None
    s = str(id_order)
    if s.startswith(SBP_ORDER_PREFIX) and s.endswith(SBP_ORDER_SUFFIX):
        mid = s[len(SBP_ORDER_PREFIX):len(s) - len(SBP_ORDER_SUFFIX)]
        return mid or None
    return None


def _headers() -> dict:
    if not configured():
        raise RuntimeError("SBP креды не заданы (.env)")
    basic = base64.b64encode(f"{SBP_LOGIN}:{SBP_PASSWORD}".encode()).decode()
    return {
        "Content-Type": "application/json",
        "x-api-key": SBP_API_KEY,
        "Authorization": f"Basic {basic}",
    }


def create_payment(rub, id_order: str, callback_url: str, type_: str = "3") -> dict:
    """
    z1.php: создать ссылку на рублёвую оплату. Синхронно возвращает dict с
    url_pay/qr/id_order_glob/Status. Кидает RuntimeError при ошибке SBP
    (тело-ошибка вроде 'Error 003' - не JSON / без url_pay).
    """
    body = json.dumps({
        "rub": f"{float(rub):.2f}",
        "type": type_,
        "id_order": id_order,
        "CallbackUrl": callback_url,
    })
    r = requests.post(f"{SBP_BASE}/z1.php", headers=_headers(), data=body, timeout=20)
    txt = (r.text or "").strip()
    try:
        data = r.json()
    except Exception:
        raise RuntimeError(f"SBP z1.php вернул не-JSON: {txt[:80]!r}")
    if not isinstance(data, dict) or "url_pay" not in data:
        raise RuntimeError(f"SBP z1.php ошибка: {txt[:80]!r}")
    return data


def check_status(id_order: str) -> str:
    """st.php: статус операции. 'CONFIRMED'/'CREATED'/... в верхнем регистре, либо ''."""
    body = json.dumps({"id_order": id_order})
    try:
        r = requests.post(f"{SBP_BASE}/st.php", headers=_headers(), data=body, timeout=15)
        data = r.json()
    except Exception:
        return ""
    return str(data.get("st") or data.get("Status") or "").upper()
