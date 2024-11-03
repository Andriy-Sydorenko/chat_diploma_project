import asyncio
import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# Налаштування логування
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", filename="websocket_monitor.log"
)
logger = logging.getLogger(__name__)


@dataclass
class ConnectionMetrics:
    """Клас для зберігання метрик з'єднання"""

    ip: str
    connect_time: datetime
    message_count: int = 0
    last_message_time: Optional[datetime] = None
    alerts: list = None
    messages_per_minute: float = 0.0

    def __post_init__(self):
        if self.alerts is None:
            self.alerts = []


class WebSocketMonitor:
    def __init__(self):
        # Налаштування порогових значень
        self.thresholds = {
            "max_messages_per_minute": 100,
            "max_connections_per_ip": 5,
            "max_message_size": 1024 * 1024,  # 1MB
            "min_message_interval": 0.05,  # 50ms
            "suspicious_patterns": [
                re.compile(r"<script.*?>.*?</script>", re.I | re.S),
                re.compile(r"eval\(.*?\)"),
                re.compile(r"javascript:", re.I),
                re.compile(r"onload=", re.I),
                re.compile(r"onerror=", re.I),
            ],
        }

        # Зберігання активних з'єднань та метрик
        self.connections: Dict[WebSocket, ConnectionMetrics] = {}
        self.ip_connections: Dict[str, Set[WebSocket]] = defaultdict(set)

        # Заблоковані IP
        self.blocked_ips: Set[str] = set()

        # Запуск фонового завдання для очищення старих даних
        asyncio.create_task(self._cleanup_old_data())

    async def handle_new_connection(self, websocket: WebSocket, ip: str) -> bool:
        """Обробка нового WebSocket з'єднання"""
        # Перевірка чи IP не заблокований
        if ip in self.blocked_ips:
            logger.warning(f"Blocked connection attempt from banned IP: {ip}")
            return False

        # Перевірка кількості з'єднань з IP
        if len(self.ip_connections[ip]) >= self.thresholds["max_connections_per_ip"]:
            logger.warning(f"Too many connections from IP: {ip}")
            await self._handle_violation(ip, "Too many connections", severity="medium")
            return False

        # Створення нових метрик для з'єднання
        self.connections[websocket] = ConnectionMetrics(ip=ip, connect_time=datetime.now())
        self.ip_connections[ip].add(websocket)

        logger.info(f"New connection established from IP: {ip}")
        return True

    async def handle_message(self, websocket: WebSocket, message: str) -> bool:
        """Обробка вхідного повідомлення"""
        if websocket not in self.connections:
            return False

        metrics = self.connections[websocket]
        current_time = datetime.now()

        # Оновлення метрик
        metrics.message_count += 1
        if metrics.last_message_time:
            interval = (current_time - metrics.last_message_time).total_seconds()
            if interval < self.thresholds["min_message_interval"]:
                await self._handle_violation(
                    metrics.ip, "Message interval too small", websocket=websocket, severity="low"
                )

        metrics.last_message_time = current_time

        # Перевірки
        violations = []

        # Перевірка розміру повідомлення
        if len(message.encode("utf-8")) > self.thresholds["max_message_size"]:
            violations.append("Message size exceeded")

        # Перевірка частоти повідомлень
        time_connected = (current_time - metrics.connect_time).total_seconds() / 60
        metrics.messages_per_minute = metrics.message_count / time_connected if time_connected > 0 else 0

        if metrics.messages_per_minute > self.thresholds["max_messages_per_minute"]:
            violations.append("Message rate exceeded")

        # Перевірка на підозрілий контент
        for pattern in self.thresholds["suspicious_patterns"]:
            if pattern.search(message):
                violations.append("Suspicious content detected")
                break

        # Обробка порушень
        if violations:
            severity = "high" if len(violations) > 1 else "medium"
            await self._handle_violation(metrics.ip, ", ".join(violations), websocket=websocket, severity=severity)
            return False

        return True

    async def handle_disconnect(self, websocket: WebSocket):
        """Обробка відключення клієнта"""
        if websocket in self.connections:
            metrics = self.connections[websocket]
            self.ip_connections[metrics.ip].remove(websocket)
            if not self.ip_connections[metrics.ip]:
                del self.ip_connections[metrics.ip]
            del self.connections[websocket]
            logger.info(f"Connection closed for IP: {metrics.ip}")

    async def _handle_violation(
        self, ip: str, reason: str, websocket: Optional[WebSocket] = None, severity: str = "low"
    ):
        """Обробка порушень безпеки"""
        logger.warning(f"Security violation from {ip}: {reason} (severity: {severity})")

        alert = {"timestamp": datetime.now().isoformat(), "ip": ip, "reason": reason, "severity": severity}

        if websocket and websocket in self.connections:
            self.connections[websocket].alerts.append(alert)

        if severity == "high":
            self.blocked_ips.add(ip)
            # Закриття всіх з'єднань з цього IP
            for ws in self.ip_connections.get(ip, set()).copy():
                await self._close_connection(ws, 1008, "Security violation")

        elif severity == "medium":
            if websocket:
                await self._close_connection(websocket, 1003, "Security violation")

        # Запис у лог
        logger.warning(json.dumps(alert))

        # Тут можна додати надсилання сповіщень через Slack, Email тощо
        await self._send_alert_notification(alert)

    async def _close_connection(self, websocket: WebSocket, code: int, reason: str):
        """Закриття WebSocket з'єднання"""
        try:
            await websocket.close(code=code, reason=reason)
        except Exception as e:
            logger.error(f"Error closing WebSocket connection: {e}")
        finally:
            await self.handle_disconnect(websocket)

    async def _cleanup_old_data(self):
        """Фонове завдання для очищення старих даних"""
        while True:
            try:
                current_time = datetime.now()
                # Видалення з'єднань, неактивних протягом години
                for websocket, metrics in list(self.connections.items()):
                    if metrics.last_message_time and current_time - metrics.last_message_time > timedelta(hours=1):
                        await self.handle_disconnect(websocket)
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
            await asyncio.sleep(300)  # Перевірка кожні 5 хвилин

    async def _send_alert_notification(self, alert: dict):
        """Надсилання сповіщень про порушення"""
        # Приклад інтеграції зі Slack
        # from slack_sdk.web.async_client import AsyncWebClient
        # slack = AsyncWebClient(token="your-token")
        # await slack.chat_postMessage(
        #     channel="#security-alerts",
        #     text=f"🚨 Security Alert!\nIP: {alert['ip']}\nReason: {alert['reason']}\nSeverity: {alert['severity']}"
        # )
        pass


# Приклад використання з FastAPI
app = FastAPI()
monitor = WebSocketMonitor()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Отримання IP клієнта
    client_ip = websocket.client.host

    # Прийняття з'єднання
    if not await monitor.handle_new_connection(websocket, client_ip):
        await websocket.close(code=1008, reason="Connection rejected")
        return

    await websocket.accept()

    try:
        while True:
            message = await websocket.receive_text()

            # Перевірка повідомлення
            if not await monitor.handle_message(websocket, message):
                await websocket.close(code=1008, reason="Message rejected")
                break

            # Обробка повідомлення...
            await websocket.send_text(f"Message received: {message}")

    except WebSocketDisconnect:
        await monitor.handle_disconnect(websocket)
    except Exception as e:
        logger.error(f"Error in WebSocket connection: {e}")
        await monitor.handle_disconnect(websocket)


# Додаткові ендпоінти для адміністрування
@app.get("/monitor/stats")
async def get_monitor_stats():
    """Отримання статистики моніторингу"""
    stats = {
        "active_connections": len(monitor.connections),
        "connections_per_ip": {ip: len(connections) for ip, connections in monitor.ip_connections.items()},
        "blocked_ips": list(monitor.blocked_ips),
    }
    return stats


@app.post("/monitor/block-ip/{ip}")
async def block_ip(ip: str):
    """Ручне блокування IP"""
    monitor.blocked_ips.add(ip)
    # Закриття всіх активних з'єднань з цього IP
    if ip in monitor.ip_connections:
        for websocket in monitor.ip_connections[ip].copy():
            await monitor._close_connection(websocket, 1008, "IP blocked")
    return {"status": "success", "message": f"IP {ip} blocked"}


@app.post("/monitor/unblock-ip/{ip}")
async def unblock_ip(ip: str):
    """Розблокування IP"""
    monitor.blocked_ips.discard(ip)
    return {"status": "success", "message": f"IP {ip} unblocked"}
