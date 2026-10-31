"""
ASSET_VERSION ต่อท้ายไฟล์ CSS/JS ของเราเอง (?v=...) เพราะ nginx ให้เบราว์เซอร์แคช /static/ 30 วันแบบ immutable
ค่าเปลี่ยนทุกครั้งที่เปิด container ใหม่ (deploy) เบราว์เซอร์จึงโหลดไฟล์ใหม่ทันที
"""

import os
import time

ASSET_VERSION = os.environ.get('ASSET_VERSION') or str(int(time.time()))


def asset_version(request):
    return {'ASSET_VERSION': ASSET_VERSION}
