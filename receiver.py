import tkinter as tk
import requests
import uuid
import threading
import time

API = "https://ratka66-production.up.railway.app"

class Receiver:
    def __init__(self, root):
        self.root = root
        self.root.title("РАТКА — приёмник сообщений")
        self.root.geometry("440x330")

        self.device_id = str(uuid.uuid4())
        self.token = None
        self.running = True

        tk.Label(
            root, text="РАТКА",
            font=("Segoe UI", 24, "bold")
        ).pack(pady=12)

        tk.Label(
            root,
            text="Добровольный приёмник шуточных сообщений"
        ).pack()

        tk.Label(
            root,
            text="Программа ничего не скрывает и не управляет Windows.",
            wraplength=390
        ).pack(pady=12)

        self.status = tk.Label(root, text="Подключение...")
        self.status.pack()

        self.code = tk.Label(
            root, text="------",
            font=("Consolas", 26, "bold")
        )
        self.code.pack(pady=12)

        tk.Label(
            root,
            text="Передай этот код отправителю, если согласен подключиться."
        ).pack(padx=15)

        tk.Button(
            root,
            text="Отключить и закрыть",
            command=self.close
        ).pack(pady=20)

        root.protocol("WM_DELETE_WINDOW", self.close)

        threading.Thread(
            target=self.connect,
            daemon=True
        ).start()

    def connect(self):
        try:
            response = requests.post(
                API + "/api/register",
                json={"device_id": self.device_id},
                timeout=10
            )
            response.raise_for_status()

            code = response.json()["code"]
            self.root.after(
                0, lambda: self.code.config(text=code)
            )
            self.root.after(
                0, lambda: self.status.config(
                    text="Ожидание подключения..."
                )
            )

            while self.running:
                if not self.token:
                    self.check_pairing()
                else:
                    self.get_messages()
                time.sleep(3)

        except Exception:
            self.root.after(
                0, lambda: self.status.config(
                    text="Ошибка соединения. Проверь адрес сервера."
                )
            )

    def check_pairing(self):
        try:
            response = requests.get(
                API + "/api/status/" + self.device_id,
                timeout=8
            )
            response.raise_for_status()
            data = response.json()

            if data.get("paired"):
                self.token = data["token"]
                self.root.after(
                    0, lambda: self.status.config(
                        text="Компьютер подключён!"
                    )
                )
        except Exception:
            pass

    def get_messages(self):
        try:
            response = requests.get(
                API + "/api/messages/" + self.device_id,
                headers={"X-Device-Token": self.token},
                timeout=8
            )
            if response.status_code == 200:
                for item in response.json().get("messages", []):
                    self.root.after(
                        0,
                        lambda x=item: self.show_message(x)
                    )
        except Exception:
            pass

    def show_message(self, item):
        window = tk.Toplevel(self.root)
        window.title("РАТКА — шуточное сообщение")
        window.geometry("500x300")
        window.configure(bg="#07140d")
        window.attributes("-topmost", True)

        tk.Label(
            window,
            text="СИМУЛЯЦИЯ / ПРАНК",
            fg="#65ff9b",
            bg="#07140d",
            font=("Consolas", 15, "bold")
        ).pack(pady=20)

        tk.Label(
            window,
            text=item["title"],
            fg="#65ff9b",
            bg="#07140d",
            font=("Consolas", 18, "bold"),
            wraplength=450
        ).pack(pady=10)

        tk.Label(
            window,
            text=item["body"],
            fg="white",
            bg="#07140d",
            font=("Segoe UI", 12),
            wraplength=450
        ).pack(pady=10)

        tk.Label(
            window,
            text="Это шутка. Компьютер не взломан.",
            fg="#a8b8ad",
            bg="#07140d"
        ).pack()

        tk.Button(
            window,
            text="Понятно — закрыть",
            command=window.destroy
        ).pack(pady=15)

    def close(self):
        self.running = False

        if self.token:
            try:
                requests.delete(
                    API + "/api/device/" + self.device_id,
                    headers={"X-Device-Token": self.token},
                    timeout=3
                )
            except Exception:
                pass

        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    Receiver(root)
    root.mainloop()
