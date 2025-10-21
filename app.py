from flask import Flask, request, jsonify
import hashlib
from datetime import datetime

app = Flask(__name__)
database = {}

def analyze_string(value):
    value_lower = value.lower()
    return {
        "length": len(value),
        "is_palindrome": value_lower == value_lower[::-1],
        "unique_characters": len(set(value)),
        "word_count": len(value.split()),
        "sha256_hash": hashlib.sha256(value.encode()).hexdigest(),
        "character_frequency_map": {char: value.count(char) for char in set(value)}
    }

@app.route("/strings", methods=["POST"])
def create_string():
    data = request.get_json()
    if not data or "value" not in data:
        return jsonify({"error": "Missing 'value' field"}), 400

    value = data["value"]
    if not isinstance(value, str):
        return jsonify({"error": "'value' must be a string"}), 422

    string_hash = hashlib.sha256(value.encode()).hexdigest()
    if string_hash in database:
        return jsonify({"error": "String already exists"}), 409

    props = analyze_string(value)
    database[string_hash] = {
        "id": string_hash,
        "value": value,
        "properties": props,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    return jsonify(database[string_hash]), 201

@app.route("/strings/<string_value>", methods=["GET"])
def get_string(string_value):
    for item in database.values():
        if item["value"] == string_value:
            return jsonify(item), 200
    return jsonify({"error": "String not found"}), 404

@app.route("/strings", methods=["GET"])
def get_all_strings():
    # Start with all strings in the database
    results = list(database.values())

    # Get query parameters from the URL
    is_palindrome = request.args.get("is_palindrome")
    min_length = request.args.get("min_length", type=int)
    max_length = request.args.get("max_length", type=int)
    word_count = request.args.get("word_count", type=int)
    contains_character = request.args.get("contains_character")

    # Apply filters if provided
    if is_palindrome is not None:
        is_palindrome = is_palindrome.lower() == "true"
        results = [r for r in results if r["properties"]["is_palindrome"] == is_palindrome]

    if min_length is not None:
        results = [r for r in results if r["properties"]["length"] >= min_length]

    if max_length is not None:
        results = [r for r in results if r["properties"]["length"] <= max_length]

    if word_count is not None:
        results = [r for r in results if r["properties"]["word_count"] == word_count]

    if contains_character:
        results = [r for r in results if contains_character in r["value"]]

    # Build response
    return jsonify({
        "data": results,
        "count": len(results),
        "filters_applied": {
            "is_palindrome": is_palindrome,
            "min_length": min_length,
            "max_length": max_length,
            "word_count": word_count,
            "contains_character": contains_character
        }
    }), 200


if __name__ == "__main__":
    app.run(debug=True)
