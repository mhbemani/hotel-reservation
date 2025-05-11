import json
import os
import threading
import datetime

# مسیر پوشه data نسبت به این فایل
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


def load_json(filename):
    """
    فایل JSON با نام filename را از DATA_DIR بارگذاری و دیکشنری برمی‌گرداند.
    """
    path = os.path.join(DATA_DIR, filename)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {'rooms': []} if 'RoomsInfo' in filename else {'users': []} if 'UsersInfo' in filename else {}
    except json.JSONDecodeError:
        return {'rooms': []} if 'RoomsInfo' in filename else {'users': []} if 'UsersInfo' in filename else {}


def save_json(filename, data, change_summary=None, user_id=None, action=None):
    """
    دیکشنری data را در فایل JSON با نام filename در DATA_DIR ذخیره می‌کند.
    """
    path = os.path.join(DATA_DIR, filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    if change_summary and action:
        log_activity(
            entry_type='FILE_CHANGE',
            user_id=user_id,
            action=action,
            file_name=filename,
            change_summary=change_summary
        )

def save_rooms(rooms_data, change_summary=None, user_id=None):
    """
    ذخیره RoomsInfo.json
    """
    save_json('RoomsInfo.json', rooms_data, change_summary, user_id, 'write_RoomsInfo')

def get_config():
    """
    تنظیمات اتصال (hostName, commandChannelPort) را از config.json می‌خواند.
    """
    cfg = load_json('config.json')
    host = cfg.get('hostName', '127.0.0.1')
    port = cfg.get('commandChannelPort', 8000)
    return host, port

log_lock = threading.Lock()

def ensure_log_directories():
    """
    اطمینان از وجود دایرکتوری‌های logs/ و logs/users/
    """
    log_dir = 'logs'
    user_log_dir = os.path.join(log_dir, 'users')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    if not os.path.exists(user_log_dir):
        os.makedirs(user_log_dir)

def get_main_log_file_path():
    """
    دریافت مسیر فایل لاگ اصلی برای تاریخ فعلی
    """
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    return os.path.join('logs', f'log_{today}.txt')

def get_user_log_file_path(user_id):
    """
    دریافت مسیر فایل لاگ کاربر بر اساس user_id
    """
    username = get_username_by_id(user_id) if user_id else None
    if not username:
        return None
    return os.path.join('logs', 'users', f'{username}.txt')

def get_username_by_id(user_id):
    """
    دریافت نام کاربری از user_id
    """
    if not user_id:
        return None
    try:
        users_data = load_json('UsersInfo.json')
        for user in users_data['users']:
            if user['id'] == user_id:
                return user['user']
    except:
        pass
    return None

def log_activity(entry_type, user_id, action, params=None, status=None, message=None, file_name=None, change_summary=None):
    """
    ثبت فعالیت در فایل لاگ اصلی و فایل لاگ کاربر (اگر user_id وجود داشته باشد)
    """
    ensure_log_directories()
    timestamp = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    log_entry = {
        'timestamp': timestamp,
        'type': entry_type,
        'user_id': user_id if user_id is not None else 'null',
        'action': action
    }
    
    if params is not None:
        # حذف اطلاعات حساس مانند پسورد
        safe_params = params.copy() if isinstance(params, dict) else {}
        if 'password' in safe_params:
            safe_params['password'] = '****'
        log_entry['params'] = safe_params
    if status is not None:
        log_entry['status'] = status
    if message is not None:
        log_entry['message'] = message
    if file_name is not None:
        log_entry['file'] = file_name
    if change_summary is not None:
        log_entry['change_summary'] = change_summary
    
    log_line = (
        f"[{timestamp}] {entry_type} | user_id={log_entry['user_id']} | "
        f"action={action} | "
        f"params={json.dumps(log_entry.get('params', {}))} | "
        f"status={log_entry.get('status', 'N/A')} | "
        f"message={log_entry.get('message', 'N/A')}"
    )
    if file_name:
        log_line += f" | file={file_name}"
    if change_summary:
        log_line += f" | change_summary={change_summary}"
    
    with log_lock:
        # ثبت در لاگ اصلی
        with open(get_main_log_file_path(), 'a', encoding='utf-8') as f:
            f.write(log_line + '\n')
        
        # ثبت در لاگ کاربر (اگر user_id وجود داشته باشد)
        user_log_path = get_user_log_file_path(user_id)
        if user_log_path:
            with open(user_log_path, 'a', encoding='utf-8') as f:
                f.write(log_line + '\n')