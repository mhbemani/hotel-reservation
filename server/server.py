import socket
import threading
import json
from utils import get_config, load_json, save_json, log_activity

from handlers import handle_client_request
import datetime



def start_server():
    host, port = get_config()
    # ایجاد سوکت TCP
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((host, port))
    server_sock.listen()
    print(f"Server listening on {host}:{port}")

    shutdown_thread = threading.Thread(target=listen_for_shutdown, args=(server_sock,), daemon=True)
    shutdown_thread.start()

    while True:
        try:
            client_sock, addr = server_sock.accept()
            print(f"Connection from {addr}")
            # هر اتصال در ترد جداگانه پردازش می‌شود
            t = threading.Thread(target=handle_client_request, args=(client_sock, addr))
            t.daemon = True
            t.start()
        except socket.error:
            break

def listen_for_shutdown(server_sock):
    """
    گوش دادن به ورودی ترمینال برای خاموش کردن سرور
    """
    while True:
        command = input().strip()
        if command == 'exit':
            print("Shutting down server...")
            server_sock.close()  # بستن سوکت سرور

if __name__ == '__main__':
    current_date = None
    while current_date is None:
        try:
            date_input = input("Enter current date (DD-MM-YYYY): ").strip()
            current_date = datetime.datetime.strptime(date_input, '%d-%m-%Y')
        except ValueError:
            print("Invalid date format. Please use DD-MM-YYYY (e.g., 01-01-2025).")
    # save the current date in config.json
    config_data = load_json('config.json')
    config_data['current_date'] = date_input
    save_json('config.json', config_data, change_summary="Updated current_date", user_id=None, action='write_config') #############
    #remove the reservations whose checkout date has passed
    rooms_data = load_json('RoomsInfo.json') ###############
    change_summary = []
    for room in rooms_data['rooms']:
        valid_reservations = []
        for reservation in room.get('users', []):
            try:
                checkout_date = datetime.datetime.strptime(reservation['checkoutDate'], '%d-%m-%Y')
                if checkout_date >= current_date:
                    valid_reservations.append(reservation)
                else:
                    room['capacity'] += reservation['numOfBeds']
                    change_summary.append(f"Removed expired reservation for room number={room['number']}, user id={reservation['id']}")
            except ValueError:
                continue
        room['users'] = valid_reservations
    if change_summary:
        save_json('RoomsInfo.json', rooms_data, change_summary="; ".join(change_summary), user_id=None, action='write_RoomsInfo')
    else:
        save_json('RoomsInfo.json', rooms_data)
    # open the portal
    host, port = get_config()
    print(f"Server will run on {host}:{port}")
    users_data = load_json('UsersInfo.json')
    rooms_data = load_json('RoomsInfo.json')
    print(f"Loaded {len(users_data['users'])} users and {len(rooms_data['rooms'])} rooms.")

    # حالا سرور واقعی را اجرا کنید
    start_server()