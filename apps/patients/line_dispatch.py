"""
ทำงานหลังตอบ webhook ของ LINE ไปแล้ว เพื่อให้ไฟล์ใหญ่หรือ LINE API ที่ช้าไม่ทำให้แชทค้าง
คนเดียวกันเข้าคิวเดียวกันเสมอ ลำดับข้อความจึงไม่สลับ เช่น เปิดบอทแล้วค่อยถาม
"""

import logging
import threading
import zlib
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.db import connections

logger = logging.getLogger(__name__)

QUEUE_COUNT = 4
_queues = {}
_queues_lock = threading.Lock()


def submit(line_user_id: str, func, *args) -> None:
    if settings.LINE_DISPATCH_INLINE:
        func(*args)
        return
    _queue_for(line_user_id).submit(_run, func, *args)


def _queue_for(line_user_id: str) -> ThreadPoolExecutor:
    # สร้างตอนใช้งานจริง เพราะ thread ต้องเกิดหลัง gunicorn แยก worker แล้ว
    index = zlib.crc32(line_user_id.encode('utf-8')) % QUEUE_COUNT
    with _queues_lock:
        if index not in _queues:
            _queues[index] = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f'line-{index}')
        return _queues[index]


def _run(func, *args) -> None:
    try:
        func(*args)
    except Exception as e:
        logger.error(f"[LINE Dispatch] Error processing event: {e}", exc_info=True)
    finally:
        connections.close_all()
