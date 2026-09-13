import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from claude_service import generate_answer, analyze_response
from database import Database

load_dotenv()

app = Flask(__name__)
CORS(app)  # frontend is deployed separately (e.g. Vercel), so allow cross-origin calls

db = Database()


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "storage": db.backend_name()})


@app.route("/api/scan", methods=["POST"])
def scan():
    data = request.get_json(force=True, silent=True) or {}
    question = (data.get("question") or "").strip()
    response_text = (data.get("response") or "").strip()

    if not question:
        return jsonify({"error": "question is required"}), 400

    try:
        if not response_text:
            response_text = generate_answer(question)

        result = analyze_response(question, response_text)
        record = db.insert_scan(question, response_text, result)

        return jsonify({
            "id": record.get("id"),
            "created_at": record.get("created_at"),
            "question": question,
            "response": response_text,
            "result": result,
        })
    except Exception as e:
        app.logger.exception("scan failed")
        return jsonify({"error": str(e)}), 500


@app.route("/api/history", methods=["GET"])
def history():
    limit = int(request.args.get("limit", 50))
    try:
        return jsonify(db.list_scans(limit=limit))
    except Exception as e:
        app.logger.exception("history fetch failed")
        return jsonify({"error": str(e)}), 500


@app.route("/api/history", methods=["DELETE"])
def clear_history():
    try:
        db.clear_scans()
        return jsonify({"cleared": True})
    except Exception as e:
        app.logger.exception("history clear failed")
        return jsonify({"error": str(e)}), 500


@app.route("/api/benchmark", methods=["GET"])
def benchmark():
    try:
        return jsonify(db.benchmark())
    except Exception as e:
        app.logger.exception("benchmark failed")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
