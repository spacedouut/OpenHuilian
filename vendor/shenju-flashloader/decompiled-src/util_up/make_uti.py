# Source Generated with Decompyle++
# File: make_uti.pyc (Python 3.10)

import os
import shutil
import tempfile

def remove_temp_directory(dir_name):
    if os.path.exists(dir_name):
        shutil.rmtree(dir_name)
        return None


def clear_directory(path):
    ''' 清空指定路径下的所有内容，但不删除目录本身 '''
    pass
# WARNING: Decompyle incomplete


def create_temp_directory(dir_name):
    '''
    在临时目录中创建一个新的子目录

    :param dir_name: 要创建的目录的名称
    '''
    temp_dir = tempfile.gettempdir()
    new_dir_path = os.path.join(temp_dir, dir_name)
    if os.path.exists(new_dir_path):
        shutil.rmtree(new_dir_path)
    os.makedirs(new_dir_path)
    return new_dir_path


def get_file_data(_path):
    if not os.path.exists(_path):
        print('Error: %s file is not exist.' % _path)
        return None
    with None(_path, 'rb') as f:
        None(None, None, None)
        return f.read()
        with None:
            if not None:
                pass


def get_file_list(_dir):
    file_list = []
    if _dir:
        for root, _, files in os.walk(_dir):
            for file in files:
                file_list.append(os.path.join(root, file))
        return file_list


def add_suffix_to_filename(filepath, suffix):
    (filename, file_extension) = os.path.splitext(filepath)
    new_filename = f'''{filename}{suffix}{file_extension}'''
    return new_filename


def find_first_file_with_suffix(directory, suffix):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(suffix):
                return os.path.join(root, file)
            return None


def format_hex(number):
    '''将十进制数转换为0000_0000格式的十六进制字符串'''
    hex_str = format(number, '08X')
    if len(hex_str) > 4:
        return hex_str[:4] + '_' + hex_str[4:]


def align_4KB_bin(_bin):
    if len(_bin) % 4096 != 0:
        return _bin + bytes(4096 - len(_bin) % 4096)


def align_cap_bin(_bin, cap):
    if cap > 0:
        padding_length = cap - len(_bin)
        if padding_length > 0:
            return _bin + b'\x00' * padding_length
        return None
    return None(_bin)

