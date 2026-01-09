import os

def create_file_if_not_exist(path):
    if os.path.isfile(path):
        return False
    
    database_dir = os.path.dirname(path)
    
    if not os.path.exists(database_dir):
        os.makedirs(database_dir)

    with open(path, 'a'):
        os.utime(path, None)

    return True