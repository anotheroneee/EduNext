import subprocess
import sys
import getpass
import os

def setup_postgres():
    print("Автоматическая настройка PostgreSQL для проекта")
    
    db_name = input("Имя базы данных (default: edunextdb): ") or "edunextdb"
    db_user = input("Имя пользователя (default: postgres): ") or "postgres"
    db_password = getpass.getpass("Пароль пользователя: ")
    
    if not db_password:
        print("Введите пароль!")
        return
    
    try:
        print(f"Проверка существования базы данных '{db_name}'...")
        result = subprocess.run([
            'psql', '-U', 'postgres', '-lqt'
        ], capture_output=True, text=True, check=True)
        
        db_exists = any(db_name in line for line in result.stdout.split('\n'))
        
        if db_exists:
            print(f"База данных '{db_name}' уже существует.")
            choice = input("Удалить базу данных и создать новую? (y/n): ").lower().strip()
            
            if choice == 'y' or choice == 'yes':
                print(f"Удаление базы данных '{db_name}'...")
                subprocess.run([
                    'psql', '-U', 'postgres', '-c', 
                    f'DROP DATABASE IF EXISTS {db_name} WITH (FORCE);'
                ], check=True)
                print("Старая база данных удалена")
            else:
                print("Отмена настройки базы данных")
                return
        
        print("Создание новой базы данных...")
        subprocess.run([
            'psql', '-U', 'postgres', '-c', 
            f"CREATE DATABASE {db_name} ENCODING 'UTF8' LC_COLLATE 'en_US.UTF-8' LC_CTYPE 'en_US.UTF-8' TEMPLATE template0;"
        ], check=True)
        
        print("Выдача прав...")
        subprocess.run([
            'psql', '-U', 'postgres', '-c',
            f'GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};'
        ], check=True)
        
        print("Обновление/создание .env файла...")
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(f"""# PostgreSQL Database
DATABASE_URL=postgresql://{db_user}:{db_password}@localhost:5432/{db_name}

# Security Project
SECRET_KEY=
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=4320
MAX_COUNT_ACCESS_TOKENS=3

# Project
PROJECT_NAME=edunext
PROJECT_VERSION=1.0.0

# Deploy
DEPLOY_HOST=localhost
DEPLOY_PORT=8000

# Email
SMTP_SERVER=smtp.mail.ru
SMTP_PORT=587
SMTP_USERNAME=edunext@bk.ru
SMTP_PASSWORD=

# GigaChat
GIGACHAT_AUTHORIZATION_KEY=
""")
        sql_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db/create_insert_tables.sql')

        if sql_file_path:
            print("Создание необходимых сущностей...")
            subprocess.run([
                'psql', '-U', 'postgres', '-d', db_name, '-f', sql_file_path
            ], check=True)
            print("Сущности созданы успешно!")
        else:
            print("Файл не был найден, сущности не созданы!")
        
        print("\nPostgreSQL успешно настроен!")
        
        
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при настройке PostgreSQL: {e}")
        print(f"Детали: {e.stderr}")
    except FileNotFoundError:
        print("PostgreSQL не установлен или psql не найден в PATH")
    except Exception as e:
        print(f"Непредвиденная ошибка: {e}")

if __name__ == "__main__":
    setup_postgres()