from __future__ import annotations

import psutil
from flask import Blueprint, jsonify

stats_bp = Blueprint("stats", __name__)


@stats_bp.route("/stats")
def stats():
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return jsonify({
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": mem.percent,
        "memory_used": mem.used,
        "memory_total": mem.total,
        "disk_percent": disk.percent,
        "disk_used": disk.used,
        "disk_total": disk.total,
    })
