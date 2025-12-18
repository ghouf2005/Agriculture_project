#!/usr/bin/env python
import os
import sys
from dotenv import load_dotenv


def main():
    # 🔥 FORCE loading the .env next to manage.py
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(BASE_DIR, ".env")
    load_dotenv(env_path)

    # ✅ DEBUG (temporary)
    print(">>> DB_HOST =", os.getenv("DB_HOST"))

    os.environ.setdefault(
        'DJANGO_SETTINGS_MODULE',
        'agriculture_sys_project.settings'
    )

    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
