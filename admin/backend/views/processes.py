from __future__ import annotations

from flask import Blueprint, current_app, jsonify

from ..readers.process_reader import ProcessReader

processes_bp = Blueprint("processes", __name__)


@processes_bp.route("/")
def index():
    bench_root = current_app.config["BENCH_ROOT"]
    try:
        processes = ProcessReader(bench_root).read_all()
    except Exception as error:
        return jsonify({"error": str(error)}), 500

    return jsonify({
        "processes": [
            {
                "name": p.name,
                "status": p.status,
                "pid": p.pid,
                "uptime": p.uptime,
                "log_filename": p.log_file.name,
            }
            for p in processes
        ],
    })
