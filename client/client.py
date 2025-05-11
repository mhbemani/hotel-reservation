# محتویات client/client.py
import socket
import json
import os
from utils import send_request, SERVER_HOST, SERVER_PORT

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def input_json(fields):
    """
    دریافت ورودی از کاربر بر اساس فیلدها (name, prompt)
    """
    params = {}
    for name, prompt in fields:
        v = input(f"{prompt}: ")
        if name in ['id','room','beds','count','price','maxCapacity']:
            v = int(v)
        params[name] = v
    return params

def format_response_data(data, action):
    """
    فرمت‌بندی داده‌های دریافتی از سرور برای نمایش کاربرپسند
    """
    if not data:
        return "No data to display."

    output = []

    if action == 'view_user_information':
        # فرمت‌بندی اطلاعات کاربر
        output.append("User Information:")
        output.append("-" * 20)
        if 'id' in data:
            output.append(f"ID: {data['id']}")
        if 'user' in data:
            output.append(f"Username: {data['user']}")
        if 'purse' in data:
            output.append(f"Purse: {data['purse']}")
        if 'phoneNumber' in data:
            output.append(f"Phone Number: {data['phoneNumber']}")
        if 'address' in data:
            output.append(f"Address: {data['address']}")
        if 'admin' in data:
            output.append(f"Admin: {'Yes' if data['admin'] else 'No'}")

    elif action == 'view_rooms':
        # فرمت‌بندی لیست اتاق‌ها
        output.append("Available Rooms:")
        output.append("-" * 20)
        for room in data:
            output.append(f"Room Number: {room['number']}")
            output.append(f"  Status: {'Available' if room['status'] == 0 else 'Occupied'}")
            output.append(f"  Price per Bed: {room['price']}")
            output.append(f"  Max Capacity: {room['maxCapacity']}")
            output.append(f"  Current Capacity: {room['capacity']}")
            if room['users']:
                output.append("  Current Users:")
                for user in room['users']:
                    output.append(f"    - User ID: {user['id']}, Beds: {user['numOfBeds']}, "
                                f"Check-in: {user['reserveDate']}, Check-out: {user['checkoutDate']}")
            output.append("")  # خط خالی برای جداسازی اتاق‌ها

    elif action == 'view_users':
        # فرمت‌بندی لیست همه کاربران (برای ادمین)
        output.append("All Users:")
        output.append("-" * 20)
        for user in data:
            output.append(f"ID: {user['id']}")
            output.append(f"  Username: {user['user']}")
            output.append(f"  Password: {user.get('password', '********')}")
            output.append(f"  Purse: {user.get('purse', 'N/A')}")
            output.append(f"  Phone Number: {user.get('phoneNumber', 'N/A')}")
            output.append(f"  Address: {user.get('address', 'N/A')}")
            output.append(f"  Admin: {'Yes' if user.get('admin', False) else 'No'}")
            output.append("")  # خط خالی برای جداسازی کاربران

    elif action == 'get_reservations':
        output.append("Your Reservations:")
        output.append("-" * 20)
        for res in data:
            output.append(f"Room: {res['room_number']}")
            output.append(f"  Beds: {res['numOfBeds']}")
            output.append(f"  Check-in: {res['reserveDate']}")
            output.append(f"  Check-out: {res['checkoutDate']}")
            output.append("")

    return "\n".join(output)

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((SERVER_HOST, SERVER_PORT))

    user_id = None
    is_admin = False
    # ورود یا ثبت‌نام
    clear_screen()
    while user_id is None:
        print("1) Login  2) Signup  0) leave")
        c = input("Choose: ")
        if c == '1':
            creds = input_json([('username','Username'),('password','Password')])
            resp = send_request(sock,'login',creds)
            clear_screen()  # پاک کردن صفحه پس از پاسخ
            print(f"Status code: {resp['code']} - {resp['message']}")
            if resp['code']=='230':
                user_id = resp['data']['id']
                is_admin = resp['data']['admin']
        elif c=='2':
            creds = input_json([('username','Username'),('password','Password')])
            resp = send_request(sock,'signup',creds)
            clear_screen()  # پاک کردن صفحه پس از پاسخ
            print(f"Status code: {resp['code']} - {resp['message']}")
            if resp['code']=='231':
                user_id = resp['data']['id']
                is_admin = resp['data']['admin']
        elif c=='0':
            break
        else:
            clear_screen()  # پاک کردن صفحه در صورت ورودی نامعتبر
            print("Status code: 401 - Invalid value!")
            print("Invalid")
    if(c=='0') :return
    # منوی اصلی
    while True:
        print("\nMenu:")
        print("1) View my info")
        print("2) View rooms")
        print("3) Booking")
        print("4) Cancel")
        print("5) Edit info")
        print("6) Leaving")
        if is_admin:
            print("7) View users")
            print("8) Manage rooms")
        print("0) Logout")
        cmd = input("command -> ")
        if cmd=='0':
            resp = send_request(sock,'logout',{'id':user_id})
            clear_screen()  # پاک کردن صفحه پس از پاسخ
            print(f"Status code: {resp['code']} - {resp['message']}")
            print(resp['message'])
            break
        
        elif cmd=='1': resp=send_request(sock,'view_user_information',{'id':user_id})
        
        elif cmd=='2': resp=send_request(sock,'view_rooms')
        
        elif cmd=='3': resp=send_request(sock,'booking', {'id': user_id, **input_json([('room','Room'),('beds','Beds'),('checkin','Check-in'),('checkout','Check-out')])})
        
        elif cmd == '4':
            resp = send_request(sock, 'get_reservations', {'id': user_id})
            clear_screen()
            print(f"Status code: {resp['code']} - {resp['message']}")
            if 'data' in resp:
                print(format_response_data(resp['data'], 'get_reservations'))
            print("--------------------")
            # print("Press any key to continue...")
            # input()
            # clear_screen()
            if resp['code'] == '001' and resp['data']:
                cancel_params = input_json([('room', 'Room'), ('beds', 'Beds')])
                cancel_params['id'] = user_id
                resp = send_request(sock, 'cancel', cancel_params)
        
        elif cmd == '5':
            clear_screen()
            print("Edit Information:")
            print("1) Edit Password")
            print("2) Edit Address")
            print("3) Edit Phone Number")
            choice = input("Choose (1-3): ")
            field = None
            if choice == '1':
                field = 'password'
            elif choice == '2':
                field = 'address'
            elif choice == '3':
                field = 'phoneNumber'
            else:
                clear_screen()
                print("Status code: 503 - Invalid value!")
                print("--------------------")
                print("Press any key to continue...")
                input()
                clear_screen()
                continue
            value = input("New value: ")
            resp = send_request(sock, 'edit_info', {'id': user_id, 'field': field, 'value': value})
        
        elif cmd == '6':
            resp = send_request(sock, 'get_active_reservations', {'id': user_id})
            clear_screen()
            print(f"Status code: {resp['code']} - {resp['message']}")
            if 'data' in resp:
                print(format_response_data(resp['data'], 'get_reservations'))
            print("--------------------")
            # print("Press any key to continue...")
            # input()
            # clear_screen()
            if resp['code'] == '001' and resp['data']:
                leaving_params = input_json([('room', 'Room')])
                leaving_params['id'] = user_id
                resp = send_request(sock, 'leaving', leaving_params)

        elif is_admin and cmd=='7': resp=send_request(sock,'view_all_users')
        
        elif is_admin and cmd == '8':
            resp = send_request(sock, 'view_rooms')
            clear_screen()
            print(f"Status code: {resp['code']} - {resp['message']}")
            if 'data' in resp:
                print(format_response_data(resp['data'], 'view_rooms'))
            print("--------------------")
            # print("Press any key to continue...")
            # input()
            # clear_screen()
            print("Manage Rooms:")
            print("1) Add a new room")
            print("2) Remove a room")
            print("3) Change the price for a room")
            print("4) Change the max capacity")
            choice = input("Choose (1-4): ")
            params = {'id': user_id}
            cmd = None
            if choice == '1':
                cmd = 'add'
                params.update(input_json([
                    ('room', 'Room Number'),
                    ('price', 'Price per Bed'),
                    ('maxCapacity', 'Max Capacity')
                ]))
            elif choice == '2':
                cmd = 'delete'
                params.update(input_json([('room', 'Room Number')]))
            elif choice == '3':
                cmd = 'modify_price'
                params.update(input_json([
                    ('room', 'Room Number'),
                    ('price', 'New Price per Bed')
                ]))
            elif choice == '4':
                cmd = 'modify_capacity'
                params.update(input_json([
                    ('room', 'Room Number'),
                    ('maxCapacity', 'New Max Capacity')
                ]))
            else:
                clear_screen()
                print("Status code: 401 - Invalid value!")
                print("Invalid choice")
                print("--------------------")
                print("Press any key to continue...")
                input()
                clear_screen()
                continue
            params['cmd'] = cmd
            resp = send_request(sock, 'admin_rooms', params)
        
        else:
            clear_screen()  # پاک کردن صفحه در صورت ورودی نامعتبر
            print("Status code: 401 - Invalid value!")
            continue
        clear_screen()  # پاک کردن صفحه پس از دریافت پاسخ
        print(f"Status code: {resp['code']} - {resp['message']}")
        if 'data' in resp:
            if(cmd=='1'):
                print(format_response_data(resp['data'], 'view_user_information'))
            elif (cmd=='2'): 
                print(format_response_data(resp['data'], 'view_rooms'))
            elif(cmd=='7'):
                print(format_response_data(resp['data'], 'view_users'))
        # else:
            # print(f"Status code: {resp['code']} - {resp['message']}")
        print("--------------------")
        print("Press any key to continue...")
        input()
        clear_screen()  # پاک کردن صفحه پس از فشردن کلید

    sock.close()

if __name__=='__main__': main()
