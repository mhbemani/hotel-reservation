# فایل server/handlers.py

"""
توابع پردازش درخواست‌های کلاینت برای سامانه رزرو هتل
"""
import json
from utils import load_json, save_json, log_activity
import datetime
import os
# from server import current_date

# بارگذاری کدهای خطا
ERRORS = load_json('Errors.json')

def send_response(client_sock, code, data=None):
    """
    ارسال پاسخ JSON به کلاینت: {
      "code": "<کد>", "message": "<پیام>", "data": <اختیاری>
    }
    """
    response = {
        'code': str(code),
        'message': ERRORS.get(str(code), ''),
    }
    if data is not None:
        response['data'] = data
    raw = json.dumps(response).encode('utf-8') + b"\n"
    client_sock.sendall(raw)

def save_users(users_data, change_summary=None, user_id=None):
    save_json('UsersInfo.json', users_data, change_summary, user_id, 'write_UsersInfo')

def save_rooms(rooms_data, change_summary=None, user_id=None):
    save_json('RoomsInfo.json', rooms_data, change_summary, user_id, 'write_RoomsInfo')

def handle_login(client_sock, request):
    req = request.get('params', {})
    username = req.get('username')
    password = req.get('password')
    users_data = load_json('UsersInfo.json')['users']
    for u in users_data:
        if u['user'] == username and u['password'] == password:
            return {'code': '230', 'message': ERRORS.get('230', ''), 'data': {'id': u['id'], 'admin': u.get('admin', False)}}
    return {'code': '430', 'message': ERRORS.get('430', '')}

def handle_signup(client_sock, request):
    req = request.get('params', {})
    username = req.get('username')
    password = req.get('password')
    if not username or not password:
        return {'code': '401', 'message': ERRORS.get('401', '')}
    users = load_json('UsersInfo.json')
    for u in users['users']:
        if u['user'] == username:
            return {'code': '451', 'message': ERRORS.get('451', '')}
    new_id = max(u['id'] for u in users['users']) + 1
    new_user = {'id': new_id, 'user': username, 'password': password, 'admin': False, 'purse': 0}
    users['users'].append(new_user)
    save_users(users, change_summary=f"Added user id={new_id}", user_id=new_id)
    user_log_path = os.path.join('logs', 'users', f'{username}.txt')
    with open(user_log_path, 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}] USER_CREATED | user_id={new_id} | action=signup | username={username}\n")
    return {'code': '231', 'message': ERRORS.get('231', ''), 'data': {'id': new_id, 'admin': False}}

def handle_view_user(client_sock, request):
    user_id = request.get('params', {}).get('id')
    users = load_json('UsersInfo.json')['users']
    for u in users:
        if u['id'] == user_id:
            info = {k: v for k, v in u.items() if k != 'password'}
            return {'code': '001', 'message': ERRORS.get('001', ''), 'data': info}
    return {'code': '102', 'message': ERRORS.get('102', '')}

def handle_view_rooms(client_sock, request):
    rooms = load_json('RoomsInfo.json')['rooms']
    return {'code': '001', 'message': ERRORS.get('001', ''), 'data': rooms}

def handle_booking(client_sock, request):
    p = request.get('params', {})
    user_id = p.get('id')
    room_number = str(p.get('room'))
    beds = p.get('beds')
    checkin = p.get('checkin')
    checkout = p.get('checkout')
    try:
        ci = datetime.datetime.strptime(checkin, '%d-%m-%Y')
        co = datetime.datetime.strptime(checkout, '%d-%m-%Y')
        current_date_str = load_json('Config.json').get('current_date')
        current_date = datetime.datetime.strptime(current_date_str, '%d-%m-%Y')
        if co <= ci or ci < current_date:
            return {'code': '401', 'message': ERRORS.get('401', '')}
    except:
        return {'code': '401', 'message': ERRORS.get('401', '')}
    data = load_json('RoomsInfo.json')
    for room in data['rooms']:
        if room['number'] == room_number:
            for reservation in room.get('users', []):
                try:
                    res_ci = datetime.datetime.strptime(reservation['reserveDate'], '%d-%m-%Y')
                    res_co = datetime.datetime.strptime(reservation['checkoutDate'], '%d-%m-%Y')
                    if not (co <= res_ci or ci >= res_co):
                        return {'code': '401', 'message': ERRORS.get('401', '')}
                except:
                    return {'code': '401', 'message': ERRORS.get('401', '')}
            if room['capacity'] < beds:
                return {'code': '109', 'message': ERRORS.get('109', '')}
            price = room['price'] * beds
            users = load_json('UsersInfo.json')
            for u in users['users']:
                if u['id'] == user_id:
                    if u.get('purse', 0) < price:
                        return {'code': '108', 'message': ERRORS.get('108', '')}
                    u['purse'] = u.get('purse', 0) - price
                    room['users'].append({'id': user_id, 'numOfBeds': beds, 'reserveDate': checkin, 'checkoutDate': checkout})
                    room['capacity'] -= beds
                    save_rooms(data, change_summary=f"Booked room number={room_number} for user id={user_id}", user_id=user_id)
                    save_users(users, change_summary=f"Updated purse for user id={user_id}", user_id=user_id)
                    return {'code': '104', 'message': ERRORS.get('104', '')}
    return {'code': '101', 'message': ERRORS.get('101', '')}

# ... other imports and handlers ...

def handle_get_reservations(client_sock, request):
    """
    دریافت رزروهای کاربر
    """
    p = request.get('params', {})
    user_id = p.get('id')
    if not user_id:
        return {'code': '401', 'message': ERRORS.get('401', '')}
    
    rooms = load_json('RoomsInfo.json')
    reservations = []
    for room in rooms['rooms']:
        for res in room.get('users', []):
            if res['id'] == user_id:
                reservations.append({
                    'room_number': room['number'],
                    'numOfBeds': res['numOfBeds'],
                    'reserveDate': res['reserveDate'],
                    'checkoutDate': res['checkoutDate']
                })
    
    return {'code': '001', 'message': ERRORS.get('001', ''), 'data': reservations}

def handle_cancel(client_sock, request):
    """
    مدیریت لغو رزرو
    """
    p = request.get('params', {})
    user_id = p.get('id')
    room_number = str(p.get('room'))
    beds_to_cancel = p.get('beds')
    
    # خواندن تاریخ فعلی از Config.json
    try:
        current_date_str = load_json('Config.json').get('current_date')
        current_date = datetime.datetime.strptime(current_date_str, '%d-%m-%Y')
    except:
        return {'code': '401', 'message': ERRORS.get('401', '')}
    
    # اعتبارسنجی ورودی‌ها
    if not user_id or not room_number or not beds_to_cancel:
        return {'code': '401', 'message': ERRORS.get('401', '')}
    
    try:
        beds_to_cancel = int(beds_to_cancel)
        if beds_to_cancel <= 0:
            raise ValueError
    except:
        return {'code': '401', 'message': ERRORS.get('401', '')}
    
    rooms = load_json('RoomsInfo.json')
    users = load_json('UsersInfo.json')
    
    for room in rooms['rooms']:
        if room['number'] == room_number:
            # یافتن رزروهای قابل لغو کاربر
            matches = [
                r for r in room.get('users', [])
                if r['id'] == user_id
                and datetime.datetime.strptime(r['reserveDate'], '%d-%m-%Y') >= current_date
            ]
            if not matches:
                return {'code': '101', 'message': ERRORS.get('101', '')}
            
            # محاسبه تعداد کل تخت‌های رزرو شده
            total_beds = sum(r['numOfBeds'] for r in matches)
            if beds_to_cancel > total_beds:
                return {'code': '102', 'message': ERRORS.get('102', '')}
            
            # لغو رزروها تا رسیدن به تعداد تخت‌های درخواستی
            beds_remaining = beds_to_cancel
            for r in matches[:]:  # کپی لیست برای جلوگیری از تغییر در حین تکرار
                if beds_remaining <= 0:
                    break
                beds_in_res = r['numOfBeds']
                if beds_in_res <= beds_remaining:
                    # حذف کامل رزرو
                    room['users'].remove(r)
                    room['capacity'] += beds_in_res
                    # بازپرداخت نیمی از هزینه
                    price = room['price'] * beds_in_res / 2
                    for u in users['users']:
                        if u['id'] == user_id:
                            u['purse'] = u.get('purse', 0) + price
                            break
                    beds_remaining -= beds_in_res
                else:
                    # کاهش تعداد تخت‌ها در رزرو
                    r['numOfBeds'] -= beds_remaining
                    room['capacity'] += beds_remaining
                    price = room['price'] * beds_remaining / 2
                    for u in users['users']:
                        if u['id'] == user_id:
                            u['purse'] = u.get('purse', 0) + price
                            break
                    beds_remaining = 0
            
            save_rooms(rooms, change_summary=f"Cancelled {beds_to_cancel} beds in room number={room_number} for user id={user_id}", user_id=user_id)
            save_users(users, change_summary=f"Refunded purse for user id={user_id}", user_id=user_id)
            return {'code': '110', 'message': ERRORS.get('110', '')}
    
    return {'code': '101', 'message': ERRORS.get('101', '')}

def handle_edit_info(client_sock, request):
    p = request.get('params', {})
    user_id = p.get('id')
    field = p.get('field')
    value = p.get('value')
    
    users_data = load_json('UsersInfo.json')
    
    for user in users_data['users']:
        if user['id'] == user_id:
            user[field] = str(value)
            break
    
    save_users(users_data, change_summary=f"Updated {field} for user id={user_id}", user_id=user_id)
    return {'code': '312', 'message': ERRORS.get('312', '')}

def handle_leaving(client_sock, request):
    """
    مدیریت خروج کاربر از اتاق
    """
    p = request.get('params', {})
    user_id = p.get('id')
    room_number = str(p.get('room'))
    
    # اعتبارسنجی ورودی‌ها
    if not user_id or not room_number:
        return {'code': '401', 'message': ERRORS.get('401', '')}
    
    # خواندن تاریخ فعلی
    try:
        current_date_str = load_json('Config.json').get('current_date')
        current_date = datetime.datetime.strptime(current_date_str, '%d-%m-%Y')
    except:
        return {'code': '401', 'message': ERRORS.get('401', '')}
    
    rooms = load_json('RoomsInfo.json')
    
    for room in rooms['rooms']:
        if room['number'] == room_number:
            # یافتن رزرو فعال
            for res in room.get('users', [])[:]:
                try:
                    reserve_date = datetime.datetime.strptime(res['reserveDate'], '%d-%m-%Y')
                    checkout_date = datetime.datetime.strptime(res['checkoutDate'], '%d-%m-%Y')
                    if res['id'] == user_id and reserve_date <= current_date <= checkout_date:
                        # حذف رزرو و به‌روزرسانی ظرفیت
                        room['users'].remove(res)
                        room['capacity'] += res['numOfBeds']
                        save_rooms(rooms, change_summary=f"User id={user_id} left room number={room_number}", user_id=user_id)
                        return {'code': '202', 'message': ERRORS.get('202', '')}
                    elif res['id'] == user_id and reserve_date > current_date:
                        return {'code': '401', 'message': ERRORS.get('401', '')}
                except:
                    continue
            return {'code': '101', 'message': ERRORS.get('101', '')}
    
    return {'code': '101', 'message': ERRORS.get('101', '')}

def handle_get_active_reservations(client_sock, request):
    """
    دریافت رزروهای فعال کاربر برای تاریخ فعلی
    """
    p = request.get('params', {})
    user_id = p.get('id')
    
    try:
        current_date_str = load_json('Config.json').get('current_date')
        current_date = datetime.datetime.strptime(current_date_str, '%d-%m-%Y')
    except:
        return {'code': '401', 'message': ERRORS.get('401', '')}
    
    rooms = load_json('RoomsInfo.json')
    reservations = []
    for room in rooms['rooms']:
        for res in room.get('users', []):
            if res['id'] == user_id:
                try:
                    reserve_date = datetime.datetime.strptime(res['reserveDate'], '%d-%m-%Y')
                    checkout_date = datetime.datetime.strptime(res['checkoutDate'], '%d-%m-%Y')
                    if reserve_date <= current_date <= checkout_date:
                        reservations.append({
                            'room_number': room['number'],
                            'numOfBeds': res['numOfBeds'],
                            'reserveDate': res['reserveDate'],
                            'checkoutDate': res['checkoutDate']
                        })
                except:
                    continue
    
    return {'code': '001', 'message': ERRORS.get('001', ''), 'data': reservations}

def handle_admin_rooms(client_sock, request):
    p = request.get('params', {})
    user_id = p.get('id')  # Uncommented for logging
    cmd = p.get('cmd')
    room_number = str(p.get('room')) if 'room' in p else None
    price = p.get('price')
    max_capacity = p.get('maxCapacity')
    
    valid_cmds = {'add', 'delete', 'modify_price', 'modify_capacity'}
    if cmd not in valid_cmds:
        return {'code': '401', 'message': ERRORS.get('401', '')}
    
    rooms_data = load_json('RoomsInfo.json')
    
    if cmd == 'add':
        # اعتبارسنجی برای افزودن
        if not room_number or price is None or max_capacity is None:
            return {'code': '401', 'message': ERRORS.get('401', '')}
        try:
            price = int(price)
            max_capacity = int(max_capacity)
            if price <= 0 or max_capacity <= 0:
                raise ValueError
        except:
            return {'code': '401', 'message': ERRORS.get('401', '')}
        
        # بررسی عدم وجود اتاق
        for room in rooms_data['rooms']:
            if room['number'] == room_number:
                return {'code': '111', 'message': ERRORS.get('111', '')}
        
        # افزودن اتاق جدید
        new_room = {
            'number': room_number,
            'capacity': max_capacity,
            'price': price,
            'maxCapacity': max_capacity,
            'status': 0,
            'users': []
        }
        rooms_data['rooms'].append(new_room)
        save_rooms(rooms_data, change_summary=f"Added room number={room_number}", user_id=user_id)
        return {'code': '104', 'message': ERRORS.get('104', '')}
    
    target_room = None
    for room in rooms_data['rooms']:
        if room['number'] == room_number:
            target_room = room
            break
    
    if not target_room:
        return {'code': '101', 'message': ERRORS.get('101', '')}
    
    if cmd == 'delete':
        # بررسی عدم وجود رزرو
        if target_room.get('users', []):
            return {'code': '109', 'message': ERRORS.get('109', '')}
        rooms_data['rooms'].remove(target_room)
        save_rooms(rooms_data, change_summary=f"Deleted room number={room_number}", user_id=user_id)
        return {'code': '106', 'message': ERRORS.get('106', '')}
    
    if cmd == 'modify_price':
        try:
            price = int(price)
            if price <= 0:
                raise ValueError
        except:
            return {'code': '401', 'message': ERRORS.get('401', '')}
        target_room['price'] = price
        save_rooms(rooms_data, change_summary=f"Modified price for room number={room_number}", user_id=user_id)
        return {'code': '105', 'message': ERRORS.get('105', '')}
    
    if cmd == 'modify_capacity':
        if max_capacity is None:
            return {'code': '401', 'message': ERRORS.get('401', '')}
        try:
            max_capacity = int(max_capacity)
            if max_capacity <= 0:
                raise ValueError
        except:
            return {'code': '401', 'message': ERRORS.get('401', '')}
    
        if max_capacity < target_room['maxCapacity'] and target_room.get('users', []):
            return {'code': '109', 'message': ERRORS.get('109', '')}
        
        target_room['capacity'] = max_capacity - target_room['maxCapacity'] + target_room['capacity']
        target_room['maxCapacity'] = max_capacity
        save_rooms(rooms_data, change_summary=f"Modified capacity for room number={room_number}", user_id=user_id)
        return {'code': '105', 'message': ERRORS.get('105', '')}

def handle_view_all_users(client_sock, request):
    users = load_json('UsersInfo.json')['users']
    users_info = [
        {key: value for key, value in u.items() if key != 'password'} if u.get('admin', False)
        else {key: value for key, value in u.items()}
        for u in users
    ]
    return {'code': '001', 'message': ERRORS.get('001', ''), 'data': users_info}

def handle_logout(client_sock, request):
    return {'code': '201', 'message': ERRORS.get('201', '')}

def handle_client_request(client_sock, addr):
    try:
        buffer = b''
        while True:
            data = client_sock.recv(4096)
            if not data:
                break
            buffer += data
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                try:
                    request = json.loads(line.decode('utf-8'))
                except json.JSONDecodeError:
                    send_response(client_sock, "401")
                    continue
                action = request.get('action')
                params = request.get('params', {})
                user_id = params.get('id')
                log_activity(
                    entry_type='COMMAND',
                    user_id=user_id,
                    action=action,
                    params=params
                )
                mapping = {
                    'login': handle_login,
                    'signup': handle_signup,
                    'view_user_information': handle_view_user,
                    'view_rooms': handle_view_rooms,
                    'booking': handle_booking,
                    'cancel': handle_cancel,
                    'edit_info': handle_edit_info,
                    'get_reservations': handle_get_reservations,
                    'leaving': handle_leaving,
                    'get_active_reservations': handle_get_active_reservations,
                    'view_all_users': handle_view_all_users,
                    'admin_rooms': handle_admin_rooms,
                    'logout': handle_logout,
                }
                func = mapping.get(action)
                response = None
                if func:
                    try:
                        response = func(client_sock, request)
                        if not isinstance(response, dict) or 'code' not in response:
                            response = {'code': '500', 'message': 'Internal server error'}
                    except Exception as e:
                        print(f"Handler error for {action}: {e}")
                        response = {'code': '500', 'message': 'Internal server error'}
                else:
                    response = {'code': '503', 'message': 'Unknown action'}
                
                log_activity(
                    entry_type='COMMAND_RESULT',
                    user_id=user_id,
                    action=action,
                    params=params,
                    status=response['code'],
                    message=response.get('message', '')
                )
                response_dict = {
                    'code': response['code'],
                    'message': response.get('message', ERRORS.get(response['code'], '')),
                    'data': response.get('data')
                }
                raw = json.dumps(response_dict).encode('utf-8') + b"\n"
                print(f"Sending response: {response_dict}")  # Debug print
                client_sock.sendall(raw)
    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        client_sock.close()