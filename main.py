import time
import random
import threading
import queue
import curses
from datetime import datetime
import paho.mqtt.client as mqtt

# MQTT настройки
BROKER = "ip"
PORT = 1883
USERNAME = "<user login>_<device code>"
PASSWORD = "<device code>"
BASE = "users/<user id>/devices/<device code>"
TOPICS = {
    'temp': f"{BASE}/temp",
    'hum': f"{BASE}/hum",
    'air_hum': f"{BASE}/air_hum",
    'light': f"{BASE}/light"
}

# Очереди для отправленных и полученных сообщений
send_queue = queue.Queue()
recv_queue = queue.Queue()

def ui_thread(stdscr):
    """Отображение интерфейса в терминале с разделением на отправленные и полученные сообщения."""
    curses.curs_set(0)
    h, w = stdscr.getmaxyx()
    mid = w // 2

    sent_win = curses.newwin(h - 2, mid, 2, 0)
    recv_win = curses.newwin(h - 2, w - mid, 2, mid)

    recv_status = "⬜"
    stdscr.addstr(0, 0, "Sent".center(mid), curses.A_REVERSE)
    stdscr.hline(1, 0, curses.ACS_HLINE, w)

    sent_lines = []
    recv_lines = []

    while True:
        # Обработка отправленных сообщений
        try:
            topic, payload = send_queue.get_nowait()
            ts = datetime.now().strftime("%H:%M:%S")
            sent_lines.append(f"{ts} -> {topic}: {payload}")
            if len(sent_lines) > h - 3:
                sent_lines.pop(0)
        except queue.Empty:
            pass

        # Обработка полученных сообщений
        try:
            topic, payload = recv_queue.get_nowait()
            ts = datetime.now().strftime("%H:%M:%S")
            recv_lines.append(f"{ts} <- {topic}: {payload}")
            if len(recv_lines) > h - 3:
                recv_lines.pop(0)

            if payload.upper() == "ON":
                recv_status = "🟩"
            elif payload.upper() == "OFF":
                recv_status = "🟥"
        except queue.Empty:
            pass

        # Обновление интерфейса
        recv_header = f"Received {recv_status}"
        stdscr.addstr(0, mid, recv_header.ljust(w - mid), curses.A_REVERSE)

        sent_win.erase()
        for i, line in enumerate(sent_lines):
            sent_win.addstr(i, 0, line[:mid - 1])
        sent_win.noutrefresh()

        recv_win.erase()
        for i, line in enumerate(recv_lines):
            recv_win.addstr(i, 0, line[:w - mid - 1])
        recv_win.noutrefresh()

        stdscr.refresh()
        curses.doupdate()
        time.sleep(0.1)

def on_connect(client, userdata, flags, rc):
    """Подписка на топик при подключении."""
    client.subscribe(TOPICS['light'])

def on_message(client, userdata, msg):
    """Обработка входящих MQTT-сообщений."""
    recv_queue.put((msg.topic, msg.payload.decode()))

def mqtt_thread():
    """Эмулятор публикации случайных значений в MQTT."""
    client = mqtt.Client(protocol=mqtt.MQTTv311)
    client.username_pw_set(USERNAME, PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, 60)
    client.loop_start()

    try:
        while True:
            temp = round(random.uniform(20, 25), 2)
            hum = round(random.uniform(30, 60), 2)
            air = round(random.uniform(40, 80), 2)

            client.publish(TOPICS['temp'], temp)
            send_queue.put((TOPICS['temp'], temp))
            time.sleep(0.1)

            client.publish(TOPICS['hum'], hum)
            send_queue.put((TOPICS['hum'], hum))
            time.sleep(0.1)

            client.publish(TOPICS['air_hum'], air)
            send_queue.put((TOPICS['air_hum'], air))
            time.sleep(30)
    finally:
        client.loop_stop()
        client.disconnect()

def main():
    """Точка входа: запуск потока MQTT и curses-интерфейса."""
    t = threading.Thread(target=mqtt_thread, daemon=True)
    t.start()
    curses.wrapper(ui_thread)

if __name__ == "__main__":
    main()